#!/usr/bin/env python3
"""Scan an application tree for resilience review prompts.

This is intentionally heuristic. It finds code worth inspecting; it does not
prove a system is resilient or broken.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


CODE_EXTENSIONS = {
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".ts",
    ".tsx",
}
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".nuxt",
    ".turbo",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
    "__pycache__",
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str
    message: str
    evidence: str


def iter_code_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in CODE_EXTENSIONS:
            yield path


def line_window(lines: list[str], index: int, radius: int = 4) -> str:
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)
    return "\n".join(lines[start:end])


def has_nearby(pattern: str, lines: list[str], index: int, radius: int = 6) -> bool:
    window = line_window(lines, index, radius)
    return re.search(pattern, window, re.IGNORECASE) is not None


def scan_file(path: Path, root: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    findings: list[Finding] = []
    relative = str(path.relative_to(root))

    for index, line in enumerate(lines):
        stripped = line.strip()
        line_number = index + 1

        if re.search(r"\b(fetch|axios|http\.|requests\.|Guzzle|Http::|Faraday|Net::HTTP|URLSession)\b", stripped):
            if not has_nearby(r"\b(timeout|signal|AbortController|connectTimeout|readTimeout|deadline)\b", lines, index):
                findings.append(
                    Finding(
                        relative,
                        line_number,
                        "external-call-without-timeout",
                        "External call appears near no explicit timeout or deadline.",
                        stripped,
                    )
                )

        if re.search(r"\b(retry|retries|attempts?)\b", stripped, re.IGNORECASE):
            if not has_nearby(r"\b(backoff|jitter|delay|maxAttempts|max_attempts|retry_after|retryAfter)\b", lines, index):
                findings.append(
                    Finding(
                        relative,
                        line_number,
                        "retry-without-budget",
                        "Retry logic appears near no backoff, jitter, delay, or max-attempt budget.",
                        stripped,
                    )
                )

        if re.search(r"\b(enqueue|dispatch|queue|perform_async|send_later|ShouldQueue|Job)\b", stripped):
            if not has_nearby(r"\b(idempot|unique|dedupe|dedup|lock|lease|key|WithoutOverlapping|onGroup)\b", lines, index):
                findings.append(
                    Finding(
                        relative,
                        line_number,
                        "queued-work-without-identity",
                        "Queued work appears near no stable work key, uniqueness, lock, or dedupe signal.",
                        stripped,
                    )
                )

        if re.search(r"\b(status|state)\b.*\b(pending|running|processing)\b", stripped, re.IGNORECASE):
            if not has_nearby(r"\b(expires_at|lease|heartbeat|stale|timeout|next_run|retry_after|visibility)\b", lines, index):
                findings.append(
                    Finding(
                        relative,
                        line_number,
                        "state-without-stale-recovery",
                        "Pending/running state appears near no stale-state recovery signal.",
                        stripped,
                    )
                )

        if re.search(r"\b(console\.log|logger\.|Log::|logging\.|log\.)\b", stripped):
            if not has_nearby(r"\b(correlation|request_id|requestId|trace_id|traceId|job_id|jobId|work_key|workKey|attempt|outcome)\b", lines, index):
                findings.append(
                    Finding(
                        relative,
                        line_number,
                        "low-context-log",
                        "Log call appears near no correlation ID, work key, attempt, or outcome field.",
                        stripped,
                    )
                )

        if re.search(r"\b(catch|except)\b", stripped):
            if not has_nearby(r"\b(throw|raise|return|fail|logger|Log::|metric|report|capture|retry)\b", lines, index, radius=8):
                findings.append(
                    Finding(
                        relative,
                        line_number,
                        "swallowed-error",
                        "Error handler appears to swallow failure without reporting, retrying, failing, or returning.",
                        stripped,
                    )
                )

        if re.search(r"\b(metric|counter|histogram|gauge|Meter|StatsD|prometheus)\b", stripped, re.IGNORECASE):
            if not has_nearby(r"\b(latency|traffic|request|error|saturation|queue_age|queueAge|oldest|duration)\b", lines, index):
                findings.append(
                    Finding(
                        relative,
                        line_number,
                        "metric-without-golden-signal",
                        "Metric appears unrelated to latency, traffic, errors, saturation, queue age, or duration.",
                        stripped,
                    )
                )

    return findings


def format_text(findings: list[Finding]) -> str:
    if not findings:
        return "No obvious resilience review prompts found."

    lines = ["Application resilience review prompts:"]
    for finding in findings:
        lines.append(
            f"- {finding.path}:{finding.line} [{finding.kind}] "
            f"{finding.message} Evidence: {finding.evidence}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find application resilience review prompts for self-healing app work."
    )
    parser.add_argument("path", nargs="?", default=".", help="Project path to scan. Default: current directory.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        parser.error(f"path does not exist: {root}")
    if root.is_file():
        files = [root]
        scan_root = root.parent
    else:
        files = list(iter_code_files(root))
        scan_root = root

    findings: list[Finding] = []
    for file_path in files:
        findings.extend(scan_file(file_path, scan_root))

    findings.sort(key=lambda item: (item.path, item.line, item.kind))

    if args.json:
        print(json.dumps({"findings": [asdict(finding) for finding in findings]}, indent=2))
    else:
        print(format_text(findings))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

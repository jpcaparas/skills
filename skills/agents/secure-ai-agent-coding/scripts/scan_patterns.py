#!/usr/bin/env python3
"""Heuristic scanner for dangerous AI agent coding patterns.

This is a triage aid, not a security proof. It looks for patterns that deserve
manual review when building LLM apps, RAG systems, tool-calling agents, or AI
coding agents.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}

DEFAULT_EXCLUDES = {
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
}

IGNORE_MARKER = "secure-ai-agent-scan: ignore"

TEXT_EXTENSIONS = {
    ".c",
    ".cc",
    ".cfg",
    ".conf",
    ".cs",
    ".css",
    ".go",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".md",
    ".mjs",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

PATTERNS = [
    {
        "id": "model-output-exec",
        "severity": "high",
        "regex": r"\b(exec|eval)\s*\(\s*(response|completion|model_output|llm_output|assistant_output|agent_output|result)\b",
        "message": "Possible raw model output passed to exec/eval.",
        "guidance": "Map validated intent to fixed actions. Never execute raw model text.",
    },
    {
        "id": "model-output-sql",
        "severity": "high",
        "regex": r"\b(cursor|db|conn)\.execute\s*\(\s*(response|completion|model_output|llm_output|assistant_output|agent_output|result)\b",
        "message": "Possible raw model output passed to a database execute call.",
        "guidance": "Use parameterized queries or constrained query builders behind authorization.",
    },
    {
        "id": "shell-true",
        "severity": "high",
        "regex": r"subprocess\.\w+\s*\([^#\n]*shell\s*=\s*True",
        "message": "subprocess call uses shell=True.",
        "guidance": "Prefer argv arrays and fixed commands. Do not pass model output to a shell.",
    },
    {
        "id": "broad-tool-access",
        "severity": "high",
        "regex": r"(allow_all_tools\s*=\s*True|allowed_tools\s*=\s*\[\s*['\"]\*['\"]|tools\s*=\s*['\"]\*['\"])",
        "message": "Possible wildcard or allow-all agent tool access.",
        "guidance": "Use explicit allowlists and per-action authorization.",
    },
    {
        "id": "safety-disabled",
        "severity": "high",
        "regex": r"(BLOCK_NONE|disable[_-]?safety\s*=\s*True|safety[_-]?filters?\s*=\s*False|guardrails?\s*=\s*False|content[_-]?filter\s*=\s*False)",  # secure-ai-agent-scan: ignore
        "message": "Possible disabled safety, guardrail, or content-filter setting.",
        "guidance": "Enable strict safety settings unless a documented exception exists.",
    },
    {
        "id": "prompt-user-concat",
        "severity": "medium",
        "regex": r"\b(prompt|system_prompt)\s*(\+=|=)\s*f?['\"].*(user_input|raw_input|request\.|web_page|document|email)",
        "message": "Possible direct construction of prompts from untrusted input.",
        "guidance": "Use prompt templates with separate instruction and untrusted data fields.",
    },
    {
        "id": "hardcoded-ai-key",
        "severity": "medium",
        "regex": r"(?i)(openai|anthropic|gemini|cohere|mistral|huggingface)[A-Z0-9_ -]*(api[_-]?key|token)\s*=\s*['\"][^'\"]{12,}",
        "message": "Possible hardcoded AI provider credential.",
        "guidance": "Use a secrets manager and run a dedicated secrets scanner.",
    },
    {
        "id": "approval-bypass-marker",
        "severity": "medium",
        "regex": r"(?i)(skip_approval|bypass_approval|auto_approve|require_approval\s*=\s*False)",  # secure-ai-agent-scan: ignore
        "message": "Possible approval bypass for agent actions.",
        "guidance": "Require explicit approval for high-impact actions or document the accepted alternative.",
    },
]


def is_text_candidate(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    if path.name in {"Dockerfile", "Makefile", "AGENTS.md", "SKILL.md"}:
        return True
    return False


def iter_files(root: Path, include_hidden: bool) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in DEFAULT_EXCLUDES and (include_hidden or not name.startswith("."))
        ]
        for filename in filenames:
            if not include_hidden and filename.startswith("."):
                continue
            path = Path(dirpath) / filename
            if is_text_candidate(path):
                files.append(path)
    return files


def scan_file(path: Path, root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError as exc:
        return [
            {
                "id": "read-error",
                "severity": "low",
                "file": str(path.relative_to(root)),
                "line": 0,
                "message": f"Could not read file: {exc}",
                "guidance": "Inspect file permissions if this path is in scope.",
            }
        ]

    compiled = [(pattern, re.compile(pattern["regex"])) for pattern in PATTERNS]
    for line_number, line in enumerate(lines, start=1):
        if IGNORE_MARKER in line:
            continue
        for pattern, regex in compiled:
            if regex.search(line):
                findings.append(
                    {
                        "id": pattern["id"],
                        "severity": pattern["severity"],
                        "file": str(path.relative_to(root)),
                        "line": line_number,
                        "message": pattern["message"],
                        "guidance": pattern["guidance"],
                        "snippet": line.strip()[:240],
                    }
                )
    return findings


def format_text(findings: list[dict[str, object]]) -> str:
    if not findings:
        return "No heuristic findings. This does not prove the AI system is safe."

    lines = [f"Findings: {len(findings)}"]
    for finding in findings:
        lines.append(
            "[{severity}] {file}:{line} {id} - {message}".format(**finding)
        )
        lines.append(f"  Guidance: {finding['guidance']}")
        if finding.get("snippet"):
            lines.append(f"  Snippet: {finding['snippet']}")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan source files for dangerous AI agent coding patterns."
    )
    parser.add_argument("path", help="Project, file, or directory to scan")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files and directories except common dependency/build folders",
    )
    parser.add_argument(
        "--fail-on",
        choices=sorted(SEVERITY_ORDER),
        help="Exit 2 when any finding has at least this severity",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        print(f"error: path does not exist: {root}", file=sys.stderr)
        return 1

    if root.is_file():
        files = [root] if is_text_candidate(root) else []
        base = root.parent
    else:
        files = iter_files(root, args.include_hidden)
        base = root

    findings: list[dict[str, object]] = []
    for path in files:
        findings.extend(scan_file(path, base))

    findings.sort(key=lambda item: (-SEVERITY_ORDER[str(item["severity"])], str(item["file"]), int(item["line"])))

    payload = {
        "path": str(root),
        "files_scanned": len(files),
        "findings": findings,
        "note": "Heuristic findings are review prompts, not proof of exploitability or safety.",
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(format_text(findings))

    if args.fail_on:
        threshold = SEVERITY_ORDER[args.fail_on]
        if any(SEVERITY_ORDER[str(item["severity"])] >= threshold for item in findings):
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

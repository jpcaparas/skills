#!/usr/bin/env python3
"""
Create a local agent-readiness report packet for a repository.

Usage:
    python3 scripts/create_report_packet.py --repo . --url https://example.com
    python3 scripts/create_report_packet.py --repo /path/to/repo --save-root ./reports
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SOURCE_URLS = [
    "https://isitagentready.com/",
    "https://blog.cloudflare.com/agent-readiness/",
    "https://isitagentready.com/.well-known/agent-skills/index.json",
    "https://isitagentready.com/.well-known/mcp.json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a local report packet with agent-readiness-report.md, "
            "sources.md, and metadata.json."
        )
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository path to audit. The git root is used when available.",
    )
    parser.add_argument(
        "--url",
        help="Optional production URL tied to the repository.",
    )
    parser.add_argument(
        "--save-root",
        help=(
            "Visible directory where the packet folder should be created. "
            "Defaults to the repository root."
        ),
    )
    parser.add_argument(
        "--slug",
        help="Optional slug override for the packet directory name.",
    )
    return parser.parse_args()


def resolve_repo_root(path_value: str) -> Path:
    repo_path = Path(path_value).expanduser().resolve()
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
    if not repo_path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {repo_path}")

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return repo_path

    resolved = result.stdout.strip()
    return Path(resolved).resolve() if resolved else repo_path


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)
    cleaned = cleaned.strip("-")
    return cleaned or "repo"


def render_template(template_text: str, repo_root: Path, production_url: str | None) -> str:
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    replacements = {
        "{{REPO_NAME}}": repo_root.name,
        "{{REPO_PATH}}": str(repo_root),
        "{{PRODUCTION_URL}}": production_url or "[Ask the user for the production URL if live checks are needed]",
        "{{CREATED_AT}}": created_at,
    }
    rendered = template_text
    for needle, value in replacements.items():
        rendered = rendered.replace(needle, value)
    return rendered


def build_sources_document() -> str:
    lines = [
        "# Sources",
        "",
        "External baseline used by this report packet:",
        "",
    ]
    for url in SOURCE_URLS:
        lines.append(f"- {url}")
    lines.extend(
        [
            "",
            "Add any extra runtime URLs, RFC links, or framework docs below when the audit uses them.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = resolve_repo_root(args.repo)
    save_root = Path(args.save_root).expanduser().resolve() if args.save_root else repo_root
    save_root.mkdir(parents=True, exist_ok=True)

    slug = slugify(args.slug or repo_root.name)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = save_root / f"isitagentready-{slug}-{timestamp}"
    output_dir.mkdir(parents=False, exist_ok=False)

    skill_root = Path(__file__).resolve().parent.parent
    template_path = skill_root / "templates" / "agent-readiness-report.md"
    report_path = output_dir / "agent-readiness-report.md"
    metadata_path = output_dir / "metadata.json"
    sources_path = output_dir / "sources.md"
    scan_results_path = output_dir / "scan-results.json"

    template_text = template_path.read_text(encoding="utf-8")
    report_text = render_template(template_text, repo_root, args.url)

    metadata = {
        "repo_path": str(repo_root),
        "repo_name": repo_root.name,
        "production_url": args.url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir),
        "report_path": str(report_path),
        "sources_path": str(sources_path),
        "scan_results_path": str(scan_results_path),
        "source_urls": SOURCE_URLS,
    }

    report_path.write_text(report_text.rstrip() + "\n", encoding="utf-8")
    sources_path.write_text(build_sources_document(), encoding="utf-8")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    payload = {
        "output_dir": str(output_dir),
        "files": [
            str(report_path),
            str(sources_path),
            str(metadata_path),
        ],
        "scan_results_path": str(scan_results_path),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

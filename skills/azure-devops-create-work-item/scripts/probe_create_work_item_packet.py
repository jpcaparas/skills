#!/usr/bin/env python3
"""
Probe the packet generator end to end in a temporary directory.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run_generator(skill_dir: Path, item_type: str | None, title: str, context_text: str) -> Path:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".md") as handle:
        handle.write(context_text)
        context_path = Path(handle.name)

    temp_root = Path(tempfile.mkdtemp(prefix="ado-work-item-probe-"))
    command = [
        sys.executable,
        str(skill_dir / "scripts" / "create_work_item_packet.py"),
        "--title",
        title,
        "--context-file",
        str(context_path),
        "--save-root",
        str(temp_root),
    ]
    if item_type:
        command[2:2] = ["--type", item_type]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    return Path(payload["output_dir"])


def assert_file_contains(path: Path, snippet: str) -> None:
    content = path.read_text(encoding="utf-8")
    if snippet not in content:
        raise AssertionError(f"Expected '{snippet}' in {path}")


def main() -> int:
    skill_dir = Path(__file__).resolve().parent.parent

    pbi_dir = run_generator(
        skill_dir,
        None,
        "Restore login after token expiry",
        "Users are forced to start over after their session expires during login.",
    )
    bug_dir = run_generator(
        skill_dir,
        "bug",
        "Checkout button freezes on Safari",
        "Observed on Safari 17.4 after applying a coupon on the cart page.",
    )

    for packet_dir in [pbi_dir, bug_dir]:
        for name in ["work-item.md", "context.md", "sources.md", "metadata.json"]:
            path = packet_dir / name
            if not path.exists():
                raise AssertionError(f"Missing expected file: {path}")

    assert_file_contains(pbi_dir / "work-item.md", "**Acceptance Criteria**")
    assert_file_contains(pbi_dir / "work-item.md", "**Developer Notes**")
    assert_file_contains(pbi_dir / "work-item.md", "**Test Scenario**")
    assert_file_contains(pbi_dir / "work-item.md", "Manual QA Scenario Contract")
    assert_file_contains(pbi_dir / "context.md", "**Context**")
    assert_file_contains(pbi_dir / "context.md", "**Codebase investigation**")
    assert_file_contains(pbi_dir / "metadata.json", "\"work_item_type\": \"Product Backlog Item\"")
    assert_file_contains(bug_dir / "work-item.md", "**Test Scenario**")
    assert_file_contains(bug_dir / "work-item.md", "Manual QA Scenario Contract")
    assert_file_contains(bug_dir / "work-item.md", "**Reproduction Steps**")
    assert_file_contains(bug_dir / "sources.md", "manage-bugs")

    print("PASS: packet generator created default PBI and bug packets successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

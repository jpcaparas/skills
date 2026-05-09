#!/usr/bin/env python3
"""Run structural and unit tests for repo-intent-documenter."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def run_step(label: str, command: list[str]) -> tuple[bool, str]:
    result = subprocess.run(command, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    ok = result.returncode == 0
    rendered = f"{'PASS' if ok else 'FAIL'}: {label}"
    if output:
        rendered += f"\n{output}"
    return ok, rendered


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1

    skill_path = Path(sys.argv[1]).resolve()
    python = sys.executable
    results: list[tuple[bool, str]] = []

    evals_path = skill_path / "evals" / "evals.json"
    try:
        evals = json.loads(evals_path.read_text(encoding="utf-8"))
        count = len(evals.get("evals", []))
        results.append((count >= 4, f"{'PASS' if count >= 4 else 'FAIL'}: eval definitions present ({count})"))
    except Exception as exc:  # noqa: BLE001
        results.append((False, f"FAIL: could not read evals/evals.json: {exc}"))

    results.append(
        run_step(
            "validate structure",
            [python, str(skill_path / "scripts" / "validate.py"), str(skill_path)],
        )
    )
    results.append(
        run_step(
            "inventory unit tests",
            [python, str(skill_path / "scripts" / "test_repo_intent_inventory.py")],
        )
    )
    results.append(
        run_step(
            "inventory help",
            [python, str(skill_path / "scripts" / "repo_intent_inventory.py"), "--help"],
        )
    )

    passed = all(ok for ok, _message in results)
    summary = {
        "skill": skill_path.name,
        "passed": passed,
        "steps": [message for _ok, message in results],
    }
    print(json.dumps(summary, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

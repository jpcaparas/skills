#!/usr/bin/env python3
"""Run focused structural and regression checks for bootstrap-agents-md."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def run(label: str, command: list[str]) -> tuple[bool, str]:
    result = subprocess.run(command, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, f"{'PASS' if result.returncode == 0 else 'FAIL'}: {label}" + (f"\n{output}" if output else "")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: test_skill.py <skill-path>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    python = sys.executable
    results = [
        run("package validation", [python, str(root / "scripts" / "validate.py"), str(root)]),
        run("generated-file validator tests", [python, str(root / "scripts" / "test_validate_agents_md.py")]),
        run("generated-file validator help", [python, str(root / "scripts" / "validate_agents_md.py"), "--help"]),
    ]
    passed = all(ok for ok, _ in results)
    print(json.dumps({"skill": root.name, "passed": passed, "steps": [message for _, message in results]}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

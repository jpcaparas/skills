#!/usr/bin/env python3

"""Validate the fixture log-analyzer package and its preserved behavior."""

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_skill.py <skill-path>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    required = [
        root / "SKILL.md",
        root / "scripts/parse_logs.py",
        root / "evals/evals.json",
        root / "evals/files/sample.ndjson",
    ]
    errors = [f"missing: {path.relative_to(root)}" for path in required if not path.is_file()]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    skill_text = required[0].read_text(encoding="utf-8")
    if "name: log-analyzer" not in skill_text:
        errors.append("SKILL.md name must remain log-analyzer")
    if "newline-delimited JSON" not in skill_text and "NDJSON" not in skill_text:
        errors.append("SKILL.md must define the accepted NDJSON format")

    try:
        eval_payload = json.loads(required[2].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"evals/evals.json is invalid: {exc}")
        eval_payload = {}
    if eval_payload.get("skill_name") != "log-analyzer" or not eval_payload.get("evals"):
        errors.append("evals must retain a non-empty log-analyzer suite")
    serialized_evals = json.dumps(eval_payload).casefold()
    if "plain-text" not in serialized_evals and "plain text" not in serialized_evals:
        errors.append("evals must include the adjacent plain-text-log near-miss")

    run = subprocess.run(
        [sys.executable, str(required[1]), str(required[3])],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        actual = json.loads(run.stdout)
    except json.JSONDecodeError:
        actual = None
    if run.returncode != 0 or actual != {"events": 2, "errors": 1}:
        errors.append("parse_logs.py must report exactly two events and one error")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("PASS: log-analyzer package and NDJSON behavior")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

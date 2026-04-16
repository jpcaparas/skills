#!/usr/bin/env python3
"""Run structural, unit, and optional live tests for audify."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def run_step(label: str, command: list[str]) -> tuple[bool, str]:
    result = subprocess.run(command, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    status = result.returncode == 0
    prefix = "PASS" if status else "FAIL"
    rendered = f"{prefix}: {label}"
    if output:
        rendered += f"\n{output}"
    return status, rendered


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
        eval_count = len(evals.get("evals", []))
        results.append((eval_count > 0, f"{'PASS' if eval_count > 0 else 'FAIL'}: eval definitions present ({eval_count})"))
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
            "unit tests",
            [python, str(skill_path / "scripts" / "test_audify_unit.py")],
        )
    )

    api_key_present = bool(os.environ.get("GEMINI_API_KEY"))
    if api_key_present:
        with tempfile.TemporaryDirectory(prefix="audify-live-test-") as temp_dir:
            results.append(
                run_step(
                    "live Gemini smoke probe",
                    [
                        python,
                        str(skill_path / "scripts" / "probe_gemini_tts.py"),
                        "--mode",
                        "smoke",
                        "--output-root",
                        temp_dir,
                    ],
                )
            )
    else:
        results.append((True, "SKIP: live Gemini smoke probe (GEMINI_API_KEY not set)"))

    passed = all(status for status, _ in results)
    summary = {
        "skill": skill_path.name,
        "passed": passed,
        "steps": [message for _status, message in results],
    }
    print(json.dumps(summary, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

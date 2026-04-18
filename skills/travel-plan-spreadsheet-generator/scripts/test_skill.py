#!/usr/bin/env python3
"""Run structural and functional smoke tests for the skill."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def find_python_with_openpyxl() -> str | None:
    candidates = []
    env_candidate = os.environ.get("TRAVEL_PLAN_SPREADSHEET_PYTHON")
    if env_candidate:
        candidates.append(env_candidate)
    candidates.extend(
        [
            sys.executable,
            shutil.which("python3") or "",
            shutil.which("python") or "",
        ]
    )
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen or not Path(candidate).exists():
            continue
        seen.add(candidate)
        command = [candidate, "-c", "import openpyxl"]
        if subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
            return candidate
    return None


def create_temporary_openpyxl_runtime(temp_dir: Path) -> str | None:
    venv_dir = temp_dir / "openpyxl-venv"
    builder = venv.EnvBuilder(with_pip=True)
    builder.create(venv_dir)
    runtime_python = venv_dir / "bin" / "python"
    install = subprocess.run(
        [str(runtime_python), "-m", "pip", "install", "--quiet", "openpyxl"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if install.returncode != 0:
        return None
    check = subprocess.run(
        [str(runtime_python), "-c", "import openpyxl"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return str(runtime_python) if check.returncode == 0 else None


def run(command: list[str], cwd: Path) -> tuple[int, str]:
    completed = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return completed.returncode, completed.stdout


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        raise SystemExit(1)

    skill_path = Path(sys.argv[1]).expanduser().resolve()
    script_dir = skill_path / "scripts"
    validate_script = script_dir / "validate.py"
    build_script = script_dir / "build_workbook.py"
    workbook_validator = script_dir / "validate_workbook.py"
    render_check = script_dir / "render_check.py"
    example_model = script_dir / "example_trip_model.json"

    report: dict[str, object] = {
        "skill_name": skill_path.name,
        "steps": [],
        "errors": [],
        "passed": True,
    }

    rc, output = run([sys.executable, str(validate_script), str(skill_path)], skill_path.parent)
    report["steps"].append({"name": "validate.py", "returncode": rc})
    if rc != 0:
        report["errors"].append(output)
        report["passed"] = False

    with tempfile.TemporaryDirectory(prefix="travel-plan-skill-") as temp_dir:
        temp_dir_path = Path(temp_dir)
        runtime_python = find_python_with_openpyxl()
        if not runtime_python:
            runtime_python = create_temporary_openpyxl_runtime(temp_dir_path)
            report["steps"].append(
                {
                    "name": "provision_openpyxl_runtime",
                    "returncode": 0 if runtime_python else 1,
                    "runtime": runtime_python,
                }
            )

        if not runtime_python:
            report["errors"].append("Could not find or provision a Python interpreter with openpyxl for the functional smoke test.")
            report["passed"] = False
        else:
            workbook_path = temp_dir_path / "sample.xlsx"

            rc, output = run(
                [
                    runtime_python,
                    str(build_script),
                    "--trip-model",
                    str(example_model),
                    "--output",
                    str(workbook_path),
                    "--normalized-model-out",
                    str(temp_dir_path / "normalized.json"),
                ],
                skill_path.parent,
            )
            report["steps"].append({"name": "build_workbook.py", "returncode": rc})
            if rc != 0 or not workbook_path.exists():
                report["errors"].append(output)
                report["passed"] = False
            else:
                rc, output = run(
                    [
                        runtime_python,
                        str(workbook_validator),
                        str(workbook_path),
                        "--trip-model",
                        str(example_model),
                        "--json",
                    ],
                    skill_path.parent,
                )
                report["steps"].append({"name": "validate_workbook.py", "returncode": rc})
                if rc != 0:
                    report["errors"].append(output)
                    report["passed"] = False

                rc, output = run([runtime_python, str(render_check), str(workbook_path)], skill_path.parent)
                report["steps"].append({"name": "render_check.py", "returncode": rc})
                if rc != 0:
                    report["errors"].append(output)
                    report["passed"] = False

    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()

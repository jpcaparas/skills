#!/usr/bin/env python3
"""
Lightweight checks plus temp-project integration tests for scaffold-github-cloud-agent-environment.
"""

from __future__ import annotations

import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path


BASH_SCRIPTS = [
    "scripts/audit_project.sh",
]
PYTHON_SCRIPTS = [
    "scripts/copilot_env_lib.py",
    "scripts/suggest_plan.py",
    "scripts/render_setup_workflow.py",
    "scripts/doctor.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
]


def extract_file_references(content: str) -> list[str]:
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|\s")
    refs: list[str] = []

    for match in re.finditer(
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`",
        stripped,
    ):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.append(path)

    for match in re.finditer(
        r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
        stripped,
    ):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.append(path)

    return sorted(set(refs))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_skill(skill_path: Path) -> dict:
    results = {
        "skill_name": skill_path.name,
        "tests_found": 0,
        "files_verified": {"passed": 0, "total": 0},
        "cross_references": {"passed": 0, "total": 0},
        "syntax_checks": {"passed": 0, "total": 0},
        "integration_checks": {"passed": 0, "total": 0},
        "errors": [],
        "passed": True,
    }

    evals_path = skill_path / "evals" / "evals.json"
    if not evals_path.is_file():
        results["errors"].append("evals/evals.json not found")
        results["passed"] = False
    else:
        evals_data = load_json(evals_path)
        evals_list = evals_data.get("evals", [])
        results["tests_found"] = len(evals_list)
        for eval_item in evals_list:
            for rel_path in eval_item.get("files", []):
                results["files_verified"]["total"] += 1
                if (skill_path / rel_path).exists():
                    results["files_verified"]["passed"] += 1
                else:
                    results["errors"].append(f"Eval referenced file not found: {rel_path}")
                    results["passed"] = False

    skill_md = (skill_path / "SKILL.md").read_text(encoding="utf-8")
    for ref in extract_file_references(skill_md):
        results["cross_references"]["total"] += 1
        if (skill_path / ref).exists():
            results["cross_references"]["passed"] += 1
        else:
            results["errors"].append(f"Cross-reference not found: {ref}")
            results["passed"] = False

    for ref_file in (skill_path / "references").glob("*.md"):
        ref_content = ref_file.read_text(encoding="utf-8")
        for ref in extract_file_references(ref_content):
            results["cross_references"]["total"] += 1
            if (skill_path / ref).exists():
                results["cross_references"]["passed"] += 1
            else:
                results["errors"].append(
                    f"Cross-reference in {ref_file.relative_to(skill_path)} not found: {ref}"
                )
                results["passed"] = False

    for rel_path in BASH_SCRIPTS:
        results["syntax_checks"]["total"] += 1
        proc = run(["bash", "-n", str(skill_path / rel_path)])
        if proc.returncode == 0:
            results["syntax_checks"]["passed"] += 1
        else:
            results["errors"].append(f"bash -n failed for {rel_path}: {proc.stderr.strip()}")
            results["passed"] = False

    for rel_path in PYTHON_SCRIPTS:
        results["syntax_checks"]["total"] += 1
        try:
            py_compile.compile(str(skill_path / rel_path), doraise=True)
            results["syntax_checks"]["passed"] += 1
        except py_compile.PyCompileError as exc:
            results["errors"].append(f"Python compile failed for {rel_path}: {exc.msg}")
            results["passed"] = False

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project = tmp / "project"
        project.mkdir()
        (project / ".github" / "workflows").mkdir(parents=True)
        (project / "package.json").write_text(
            json.dumps(
                {
                    "name": "fixture-project",
                    "packageManager": "npm@10.8.0",
                    "engines": {"node": "20"},
                    "scripts": {
                        "build": "echo build",
                        "lint": "echo lint",
                        "test": "echo test"
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (project / "package-lock.json").write_text("{}\n", encoding="utf-8")
        (project / ".gitattributes").write_text("*.bin filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8")
        run(["git", "init"], cwd=project)

        audit_proc = run(["bash", str(skill_path / "scripts" / "audit_project.sh"), str(project)])
        results["integration_checks"]["total"] += 1
        if audit_proc.returncode != 0:
            results["errors"].append(f"audit_project.sh failed: {audit_proc.stderr.strip()}")
            results["passed"] = False
        else:
            audit = json.loads(audit_proc.stdout)
            if "npm" in audit.get("package_managers", []) and audit.get("lfs_detected") is True:
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("audit_project.sh did not detect npm and LFS as expected")
                results["passed"] = False

        plan_path = tmp / "plan.json"
        suggest_proc = run(
            [
                "python3",
                str(skill_path / "scripts" / "suggest_plan.py"),
                "--project",
                str(project),
                "--output",
                str(plan_path),
            ]
        )
        results["integration_checks"]["total"] += 1
        if suggest_proc.returncode != 0:
            results["errors"].append(f"suggest_plan.py failed: {suggest_proc.stderr.strip()}")
            results["passed"] = False
        else:
            plan = load_json(plan_path)
            if not plan.get("questions") and any(step.get("run") == "npm ci" for step in plan.get("steps", [])):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("suggest_plan.py did not produce the expected npm plan without open questions")
                results["passed"] = False

        render_proc = run(
            [
                "python3",
                str(skill_path / "scripts" / "render_setup_workflow.py"),
                "--project",
                str(project),
                "--plan",
                str(plan_path),
            ]
        )
        results["integration_checks"]["total"] += 1
        workflow_path = project / ".github" / "workflows" / "copilot-setup-steps.yml"
        if render_proc.returncode != 0 or not workflow_path.is_file():
            results["errors"].append(
                f"render_setup_workflow.py failed: {(render_proc.stderr or render_proc.stdout).strip()}"
            )
            results["passed"] = False
        else:
            rendered = workflow_path.read_text(encoding="utf-8")
            if "copilot-setup-steps:" in rendered and "actions/checkout@v5" in rendered and "lfs: true" in rendered:
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("rendered workflow is missing expected Copilot setup content")
                results["passed"] = False

        doctor_proc = run(
            [
                "python3",
                str(skill_path / "scripts" / "doctor.py"),
                "--project",
                str(project),
                "--symptom",
                "dependencies fail to install",
                "--json",
            ]
        )
        results["integration_checks"]["total"] += 1
        if doctor_proc.returncode != 0:
            results["errors"].append(f"doctor.py failed: {doctor_proc.stderr.strip()}")
            results["passed"] = False
        else:
            doctor = json.loads(doctor_proc.stdout)
            if doctor.get("workflow_exists") and isinstance(doctor.get("findings"), list):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("doctor.py did not return the expected JSON structure")
                results["passed"] = False

        ambiguous = tmp / "ambiguous"
        ambiguous.mkdir()
        (ambiguous / "package.json").write_text(
            json.dumps({"name": "ambiguous", "scripts": {"test": "echo test"}}, indent=2) + "\n",
            encoding="utf-8",
        )
        (ambiguous / "package-lock.json").write_text("{}\n", encoding="utf-8")
        run(["git", "init"], cwd=ambiguous)

        ambiguous_plan_path = tmp / "ambiguous-plan.json"
        ambiguous_proc = run(
            [
                "python3",
                str(skill_path / "scripts" / "suggest_plan.py"),
                "--project",
                str(ambiguous),
                "--output",
                str(ambiguous_plan_path),
            ]
        )
        results["integration_checks"]["total"] += 1
        if ambiguous_proc.returncode != 0:
            results["errors"].append(f"suggest_plan.py failed on ambiguous project: {ambiguous_proc.stderr.strip()}")
            results["passed"] = False
        else:
            ambiguous_render = run(
                [
                    "python3",
                    str(skill_path / "scripts" / "render_setup_workflow.py"),
                    "--project",
                    str(ambiguous),
                    "--plan",
                    str(ambiguous_plan_path),
                ]
            )
            if ambiguous_render.returncode != 0:
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("renderer should refuse to write when the plan still has unresolved questions")
                results["passed"] = False

    return results


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1

    skill_path = Path(sys.argv[1]).resolve()
    if not skill_path.is_dir():
        print(f"Error: '{skill_path}' is not a directory", file=sys.stderr)
        return 1

    result = test_skill(skill_path)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

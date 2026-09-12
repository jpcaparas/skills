#!/usr/bin/env python3
"""
Draft a scaffold plan for GitHub Copilot cloud agent's setup workflow from repo facts.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from copilot_env_lib import load_json, parse_simple_workflow


def run_audit(project: Path, script_dir: Path) -> dict[str, Any]:
    audit_script = script_dir / "audit_project.sh"
    proc = subprocess.run(
        ["bash", str(audit_script), str(project)],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or "audit_project.sh failed")
    return json.loads(proc.stdout)


def read_text_if_exists(path: Path) -> str | None:
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return None


def first_existing(root: Path, candidates: list[str]) -> str | None:
    for rel_path in candidates:
        if (root / rel_path).exists():
            return rel_path
    return None


def package_json_engine_node(audit: dict[str, Any]) -> str | None:
    for package_json in audit.get("package_jsons", []):
        engines = package_json.get("engines") or {}
        node = engines.get("node")
        if isinstance(node, str) and node.strip():
            return node.strip()
    return None


def detect_primary_package_manager(audit: dict[str, Any]) -> str | None:
    managers = audit.get("package_managers", [])
    if len(managers) == 1:
        return managers[0]

    for package_json in audit.get("package_jsons", []):
        package_manager = package_json.get("packageManager")
        if isinstance(package_manager, str) and package_manager:
            return package_manager.split("@", 1)[0]

    return managers[0] if managers else None


def add_node_steps(
    project_root: Path,
    audit: dict[str, Any],
    steps: list[dict[str, Any]],
    questions: list[str],
    assumptions: list[str],
) -> None:
    package_manager = detect_primary_package_manager(audit)
    node_version_file = first_existing(project_root, [".nvmrc", ".node-version"])
    engines_node = package_json_engine_node(audit)

    if package_manager not in {"npm", "pnpm", "yarn"}:
        if package_manager == "bun":
            questions.append(
                "The repo appears to use Bun. Should the setup workflow install Bun explicitly, or is a Node-only bootstrap sufficient?"
            )
        return

    setup_step: dict[str, Any] = {
        "name": "Set up Node.js",
        "uses": "actions/setup-node@v4",
        "with": {
            "cache": package_manager,
        },
    }

    if node_version_file:
        setup_step["with"]["node-version-file"] = node_version_file
    elif engines_node:
        setup_step["with"]["node-version"] = engines_node
    else:
        questions.append(
            "Which Node version should Copilot use? The repo has Node signals but no clear version file or engines.node declaration."
        )
        assumptions.append("The rendered plan should wait for a Node version decision before final generation.")

    steps.append(setup_step)

    if package_manager in {"pnpm", "yarn"}:
        steps.append(
            {
                "name": "Enable Corepack",
                "run": "corepack enable",
            }
        )

    if package_manager == "npm":
        steps.append({"name": "Install JavaScript dependencies", "run": "npm ci"})
    elif package_manager == "pnpm":
        steps.append({"name": "Install JavaScript dependencies", "run": "pnpm install --frozen-lockfile"})
    elif package_manager == "yarn":
        steps.append({"name": "Install JavaScript dependencies", "run": "yarn install --immutable"})


def add_python_steps(
    project_root: Path,
    audit: dict[str, Any],
    steps: list[dict[str, Any]],
    questions: list[str],
    assumptions: list[str],
) -> None:
    python_version_file = first_existing(project_root, [".python-version"])
    requirements = (project_root / "requirements.txt").is_file()
    poetry_lock = (project_root / "poetry.lock").is_file()
    pyproject = (project_root / "pyproject.toml").is_file()

    if not any([requirements, poetry_lock, pyproject]):
        return

    setup_step: dict[str, Any] = {
        "name": "Set up Python",
        "uses": "actions/setup-python@v5",
        "with": {},
    }
    if python_version_file:
        setup_step["with"]["python-version-file"] = python_version_file
    else:
        questions.append(
            "Which Python version should Copilot use? The repo has Python signals but no `.python-version` file."
        )
        assumptions.append("The rendered plan should wait for a Python version decision before final generation.")
    steps.append(setup_step)

    if requirements:
        steps.append({"name": "Install Python dependencies", "run": "python -m pip install -r requirements.txt"})
    elif poetry_lock:
        steps.append(
            {
                "name": "Install Python dependencies",
                "run": "python -m pip install poetry && poetry install --no-interaction --no-root",
            }
        )
    elif pyproject:
        questions.append(
            "The repo has `pyproject.toml` without an obvious lockfile or requirements file. Which Python packaging workflow should the setup steps use?"
        )


def add_go_steps(project_root: Path, steps: list[dict[str, Any]]) -> None:
    if not (project_root / "go.mod").is_file():
        return

    steps.append(
        {
            "name": "Set up Go",
            "uses": "actions/setup-go@v5",
            "with": {
                "go-version-file": "go.mod",
            },
        }
    )
    steps.append({"name": "Download Go modules", "run": "go mod download"})


def suggest_plan(audit: dict[str, Any]) -> dict[str, Any]:
    project_root = Path(audit["repo_root"])
    workflow_candidates = audit.get("copilot", {}).get("workflow_files", [])
    workflow_path = ".github/workflows/copilot-setup-steps.yml"
    if workflow_candidates:
        workflow_path = workflow_candidates[0]

    parsed_workflow = parse_simple_workflow(project_root / workflow_path)

    mode = "refresh" if parsed_workflow["exists"] else "bootstrap"
    questions: list[str] = []
    assumptions: list[str] = []
    notes: list[str] = []
    manual_settings: list[str] = []
    steps: list[dict[str, Any]] = []

    if len(audit.get("package_managers", [])) > 1:
        questions.append(
            "The repo contains more than one JavaScript package-manager signal. Which package manager should the Copilot setup workflow treat as authoritative?"
        )

    checkout_step: dict[str, Any] = {
        "name": "Checkout code",
        "uses": "actions/checkout@v5",
    }
    if audit.get("lfs_detected"):
        checkout_step["with"] = {"lfs": True}
    steps.append(checkout_step)

    languages = set(audit.get("languages", []))
    if "javascript-typescript" in languages:
        add_node_steps(project_root, audit, steps, questions, assumptions)
    if "python" in languages:
        add_python_steps(project_root, audit, steps, questions, assumptions)
    if "go" in languages:
        add_go_steps(project_root, steps)

    unsupported_languages = languages.intersection({"ruby", "jvm", "dotnet", "rust"})
    if unsupported_languages:
        questions.append(
            "The repo uses "
            + ", ".join(sorted(unsupported_languages))
            + ". Should the workflow also bootstrap those toolchains, or only the primary environment needed by Copilot?"
        )

    runner = {
        "kind": "github-hosted-standard",
        "runs_on": "ubuntu-latest",
    }
    if parsed_workflow.get("runs_on_raw"):
        runner["kind"] = "existing-workflow"
        runner["runs_on"] = parsed_workflow["runs_on_raw"]

    if audit.get("windows_markers"):
        questions.append(
            "Does Copilot need a Windows runner to build or validate this repository, or is Ubuntu sufficient?"
        )
        manual_settings.append(
            "If you choose Windows, use self-hosted runners or larger GitHub-hosted runners with Azure private networking because the integrated firewall is not compatible with Windows."
        )

    runner_mentions = "\n".join(audit.get("runner_mentions", []))
    if "self-hosted" in runner_mentions or "arc-" in runner_mentions:
        questions.append(
            "The existing CI config mentions self-hosted runners. Must Copilot also run on self-hosted infrastructure to reach internal resources?"
        )
        manual_settings.append(
            "If you choose self-hosted runners, disable the integrated firewall and allow the documented GitHub and Copilot hosts."
        )

    if audit.get("registry_files"):
        questions.append(
            "Which registry credentials or proxy settings must be available in the repository's `copilot` environment for private dependencies or internal tooling?"
        )
        manual_settings.append(
            "Add required credentials as `copilot` environment secrets or variables, then align firewall allowlists or self-hosted network access with those hosts."
        )

    if audit.get("container_files"):
        notes.append(
            "The repo has container or Compose assets. Only translate them into GitHub Actions `services` if the needed services are simple and well understood."
        )

    if not audit.get("copilot", {}).get("has_custom_instructions"):
        notes.append(
            "Consider adding `.github/copilot-instructions.md` so Copilot knows how to build, test, and validate changes after the environment is ready."
        )

    if parsed_workflow.get("checkout_fetch_depth"):
        notes.append(
            "The existing workflow sets `fetch-depth`, but the live docs say Copilot overrides that value."
        )

    timeout_minutes = 45 if audit.get("monorepo") or len(steps) > 4 else 30

    return {
        "mode": mode,
        "workflow_path": workflow_path,
        "job_name": "copilot-setup-steps",
        "runner": runner,
        "permissions": {"contents": "read"},
        "timeout_minutes": timeout_minutes,
        "include_validation_triggers": True,
        "steps": steps,
        "services": {},
        "manual_settings": manual_settings,
        "assumptions": assumptions,
        "questions": sorted(dict.fromkeys(questions)),
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", help="Target project path")
    parser.add_argument("--audit", help="Path to a precomputed audit JSON file")
    parser.add_argument("--output", help="Optional output file")
    args = parser.parse_args()

    if not args.project and not args.audit:
        parser.error("provide either --project or --audit")

    script_dir = Path(__file__).resolve().parent
    if args.audit:
        audit = load_json(Path(args.audit))
    else:
        audit = run_audit(Path(args.project).resolve(), script_dir)

    plan = suggest_plan(audit)
    output = json.dumps(plan, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Shared helpers for the scaffold-github-cloud-agent-environment skill.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SUPPORTED_JOB_KEYS = {
    "steps",
    "permissions",
    "runs-on",
    "services",
    "snapshot",
    "timeout-minutes",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def quote_yaml(value: str) -> str:
    simple = re.fullmatch(r"[A-Za-z0-9._/@+-]+", value)
    if simple and value not in {"true", "false", "null", "~"}:
        return value

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return quote_yaml(str(value))


def yaml_lines(value: Any, indent: int) -> list[str]:
    prefix = " " * indent

    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {yaml_scalar(item)}")
        return lines

    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.extend(yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}- {yaml_scalar(item)}")
        return lines

    return [f"{prefix}{yaml_scalar(value)}"]


def parse_simple_workflow(workflow_path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "exists": workflow_path.is_file(),
        "workflow_path": str(workflow_path),
        "job_names": [],
        "job_found": False,
        "job_keys": [],
        "unsupported_job_keys": [],
        "runs_on_raw": None,
        "runs_on_contains_windows": False,
        "runs_on_contains_self_hosted": False,
        "timeout_minutes": None,
        "uses_checkout": False,
        "checkout_lfs": False,
        "checkout_fetch_depth": False,
        "run_steps_present": False,
        "step_count": 0,
        "triggers": {
            "workflow_dispatch": False,
            "push": False,
            "pull_request": False,
        },
        "job_block_text": "",
    }
    if not workflow_path.is_file():
        return info

    text = workflow_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    in_on = False
    in_jobs = False
    current_job: str | None = None
    in_target_job = False
    in_steps = False
    job_keys: set[str] = set()
    block_lines: list[str] = []
    current_step_uses: str | None = None

    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw) - len(raw.lstrip(" "))

        if indent == 0:
            if stripped == "on:":
                in_on = True
                in_jobs = False
                current_job = None
                in_target_job = False
                in_steps = False
                continue
            in_on = False

            if stripped == "jobs:":
                in_jobs = True
                current_job = None
                in_target_job = False
                in_steps = False
                continue

            in_jobs = False
            current_job = None
            in_target_job = False
            in_steps = False

        if in_on and indent == 2:
            match = re.match(r"^([A-Za-z0-9_-]+):", stripped)
            if match and match.group(1) in info["triggers"]:
                info["triggers"][match.group(1)] = True

        if in_jobs and indent == 2 and stripped.endswith(":"):
            current_job = stripped[:-1]
            info["job_names"].append(current_job)
            in_target_job = current_job == "copilot-setup-steps"
            in_steps = False
            current_step_uses = None
            if in_target_job:
                info["job_found"] = True
                block_lines = []
            continue

        if current_job and indent <= 2 and not (indent == 2 and stripped.endswith(":")):
            current_job = None
            in_target_job = False
            in_steps = False
            current_step_uses = None

        if not in_target_job:
            continue

        block_lines.append(raw)

        if indent == 4:
            match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", stripped)
            if match:
                key = match.group(1)
                value = match.group(2).strip()
                job_keys.add(key)
                in_steps = key == "steps"
                current_step_uses = None

                if key == "runs-on" and value:
                    info["runs_on_raw"] = value
                if key == "timeout-minutes" and value:
                    try:
                        info["timeout_minutes"] = int(value)
                    except ValueError:
                        info["timeout_minutes"] = None
            continue

        if indent <= 4 and stripped != "steps:":
            in_steps = False
            current_step_uses = None

        if not in_steps:
            continue

        if indent == 6 and stripped.startswith("-"):
            info["step_count"] += 1
            current_step_uses = None
            inline_uses = re.search(r"uses:\s*(\S+)", stripped)
            inline_run = re.search(r"run:\s*(.+)$", stripped)
            if inline_uses:
                current_step_uses = inline_uses.group(1)
                if current_step_uses.startswith("actions/checkout@"):
                    info["uses_checkout"] = True
            if inline_run:
                info["run_steps_present"] = True
            continue

        if indent >= 8:
            uses_match = re.match(r"uses:\s*(\S+)", stripped)
            run_match = re.match(r"run:\s*(.+)$", stripped)
            lfs_match = re.match(r"lfs:\s*(.+)$", stripped)
            fetch_match = re.match(r"fetch-depth:\s*(.+)$", stripped)

            if uses_match:
                current_step_uses = uses_match.group(1)
                if current_step_uses.startswith("actions/checkout@"):
                    info["uses_checkout"] = True
                continue

            if run_match:
                info["run_steps_present"] = True
                continue

            if current_step_uses and current_step_uses.startswith("actions/checkout@"):
                if lfs_match and lfs_match.group(1).strip().lower() == "true":
                    info["checkout_lfs"] = True
                if fetch_match:
                    info["checkout_fetch_depth"] = True

    job_block_text = "\n".join(block_lines)
    info["job_block_text"] = job_block_text
    info["job_keys"] = sorted(job_keys)
    info["unsupported_job_keys"] = sorted(job_keys - SUPPORTED_JOB_KEYS)
    info["runs_on_contains_windows"] = bool(re.search(r"windows", job_block_text, re.IGNORECASE))
    info["runs_on_contains_self_hosted"] = bool(re.search(r"self-hosted|arc-", job_block_text, re.IGNORECASE))
    if info["runs_on_raw"] is None and job_block_text:
        match = re.search(r"^\s+runs-on:\s*(.+)$", job_block_text, re.MULTILINE)
        if match:
            info["runs_on_raw"] = match.group(1).strip()

    return info


def render_workflow_from_plan(plan: dict[str, Any]) -> str:
    workflow_path = plan.get("workflow_path", ".github/workflows/copilot-setup-steps.yml")
    if workflow_path not in {
        ".github/workflows/copilot-setup-steps.yml",
        ".github/workflows/copilot-setup-steps.yaml",
    }:
        raise ValueError("workflow_path must target copilot-setup-steps under .github/workflows/")

    job_name = plan.get("job_name", "copilot-setup-steps")
    if job_name != "copilot-setup-steps":
        raise ValueError("job_name must be 'copilot-setup-steps'")

    runner = plan.get("runner", {})
    runs_on = runner.get("runs_on", "ubuntu-latest")
    permissions = plan.get("permissions", {})
    timeout_minutes = int(plan.get("timeout_minutes", 30))
    include_validation_triggers = bool(plan.get("include_validation_triggers", True))
    services = plan.get("services", {})
    steps = plan.get("steps", [])
    if not isinstance(steps, list) or not steps:
        raise ValueError("plan.steps must be a non-empty list")

    lines = [
        'name: "Copilot Setup Steps"',
        "",
        "# Validate this workflow when it changes and allow manual test runs from the Actions tab.",
        "on:",
    ]
    if include_validation_triggers:
        lines.extend(
            [
                "  workflow_dispatch:",
                "  push:",
                "    paths:",
                "      - .github/workflows/copilot-setup-steps.yml",
                "  pull_request:",
                "    paths:",
                "      - .github/workflows/copilot-setup-steps.yml",
            ]
        )
    else:
        lines.append("  workflow_dispatch:")

    lines.extend(
        [
            "",
            "jobs:",
            "  # Copilot only reads the job named `copilot-setup-steps`.",
            f"  {job_name}:",
            f"    runs-on: {yaml_scalar(runs_on)}",
        ]
    )

    if permissions:
        lines.append("    permissions:")
        lines.extend(yaml_lines(permissions, 6))

    if services:
        lines.append("    services:")
        lines.extend(yaml_lines(services, 6))

    lines.append(f"    timeout-minutes: {timeout_minutes}")
    lines.append("    steps:")

    for step in steps:
        if not isinstance(step, dict):
            raise ValueError("each step must be an object")
        name = step.get("name")
        uses = step.get("uses")
        run = step.get("run")
        with_block = step.get("with", {})
        env_block = step.get("env", {})

        if not name:
            raise ValueError("each step must include a name")
        if bool(uses) == bool(run):
            raise ValueError(f"step '{name}' must contain exactly one of 'uses' or 'run'")

        lines.append(f"      - name: {yaml_scalar(name)}")
        if uses:
            lines.append(f"        uses: {yaml_scalar(uses)}")
        if run:
            lines.append(f"        run: {yaml_scalar(run)}")
        if with_block:
            lines.append("        with:")
            lines.extend(yaml_lines(with_block, 10))
        if env_block:
            lines.append("        env:")
            lines.extend(yaml_lines(env_block, 10))

    return "\n".join(lines) + "\n"

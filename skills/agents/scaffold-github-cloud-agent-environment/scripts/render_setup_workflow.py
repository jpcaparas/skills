#!/usr/bin/env python3
"""
Render or refresh .github/workflows/copilot-setup-steps.yml from a plan JSON.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from copilot_env_lib import load_json, render_workflow_from_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Target project path")
    parser.add_argument("--plan", required=True, help="Plan JSON path")
    parser.add_argument(
        "--allow-questions",
        action="store_true",
        help="Render even if the plan still contains unresolved questions",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the rendered workflow instead of writing it to disk",
    )
    args = parser.parse_args()

    project_root = Path(args.project).resolve()
    plan = load_json(Path(args.plan).resolve())
    questions = plan.get("questions", [])
    if questions and not args.allow_questions:
        raise SystemExit(
            "Refusing to render because the plan still contains unresolved questions:\n- "
            + "\n- ".join(questions)
        )

    rendered = render_workflow_from_plan(plan)
    workflow_rel = plan.get("workflow_path", ".github/workflows/copilot-setup-steps.yml")
    workflow_path = project_root / workflow_rel

    if args.stdout:
        print(rendered, end="")
        return 0

    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = None
    changed = True
    if workflow_path.exists():
        current = workflow_path.read_text(encoding="utf-8")
        changed = current != rendered
        if changed:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_path = workflow_path.with_suffix(workflow_path.suffix + f".bak.{timestamp}")
            workflow_path.replace(backup_path)

    workflow_path.write_text(rendered, encoding="utf-8")
    print(
        json.dumps(
            {
                "workflow_path": str(workflow_path),
                "changed": changed,
                "backup_path": str(backup_path) if backup_path else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

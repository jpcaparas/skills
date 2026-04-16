#!/usr/bin/env python3
"""
Diagnose GitHub Copilot cloud agent environment issues in a repository.
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


def add_finding(
    findings: list[dict[str, Any]],
    *,
    severity: str,
    code: str,
    title: str,
    evidence: list[str],
    fix: str,
    can_fix_in_repo: bool,
) -> None:
    findings.append(
        {
            "severity": severity,
            "code": code,
            "title": title,
            "evidence": evidence,
            "fix": fix,
            "can_fix_in_repo": can_fix_in_repo,
        }
    )


def doctor(audit: dict[str, Any], symptom: str | None, script_dir: Path) -> dict[str, Any]:
    repo_root = Path(audit["repo_root"])
    workflow_candidates = audit.get("copilot", {}).get("workflow_files", [])
    workflow_rel = workflow_candidates[0] if workflow_candidates else ".github/workflows/copilot-setup-steps.yml"
    workflow = parse_simple_workflow(repo_root / workflow_rel)
    symptom_text = (symptom or "").lower()

    findings: list[dict[str, Any]] = []
    manual_checks: list[str] = []
    next_actions: list[str] = []

    if not workflow["exists"]:
        add_finding(
            findings,
            severity="error",
            code="missing-workflow",
            title="Copilot setup workflow is missing",
            evidence=[f"{workflow_rel} does not exist in the repository."],
            fix="Draft a plan and render `.github/workflows/copilot-setup-steps.yml` before debugging runtime behavior.",
            can_fix_in_repo=True,
        )
    else:
        if not workflow["job_found"]:
            add_finding(
                findings,
                severity="error",
                code="missing-job",
                title="Required `copilot-setup-steps` job is missing",
                evidence=[f"{workflow_rel} does not contain a job named `copilot-setup-steps`."],
                fix="Rename or regenerate the workflow so the required job name is present.",
                can_fix_in_repo=True,
            )

        if workflow["unsupported_job_keys"]:
            add_finding(
                findings,
                severity="warning",
                code="unsupported-job-keys",
                title="Workflow uses job keys outside the documented allowlist",
                evidence=[
                    "Unsupported keys in `copilot-setup-steps`: "
                    + ", ".join(workflow["unsupported_job_keys"])
                ],
                fix="Limit the setup job to `steps`, `permissions`, `runs-on`, `services`, `snapshot`, and `timeout-minutes`.",
                can_fix_in_repo=True,
            )

        if workflow["timeout_minutes"] is not None and workflow["timeout_minutes"] > 59:
            add_finding(
                findings,
                severity="error",
                code="timeout-too-large",
                title="`timeout-minutes` exceeds the documented maximum",
                evidence=[f"Found `timeout-minutes: {workflow['timeout_minutes']}`."],
                fix="Reduce `timeout-minutes` to `59` or less.",
                can_fix_in_repo=True,
            )

        if workflow["run_steps_present"] and not workflow["uses_checkout"]:
            add_finding(
                findings,
                severity="error",
                code="missing-checkout",
                title="Setup commands run before the repository is checked out",
                evidence=[
                    "The workflow contains `run:` steps but no `actions/checkout` step.",
                    "The docs only guarantee automatic checkout after setup steps complete.",
                ],
                fix="Check out the repository before any setup commands that depend on repo files.",
                can_fix_in_repo=True,
            )

        if audit.get("lfs_detected") and not workflow["checkout_lfs"]:
            add_finding(
                findings,
                severity="warning",
                code="missing-lfs",
                title="Repository uses Git LFS but checkout does not enable it",
                evidence=["`.gitattributes` contains `filter=lfs`, but checkout is not configured with `lfs: true`."],
                fix="Use `actions/checkout@v5` with `lfs: true` in the setup workflow.",
                can_fix_in_repo=True,
            )

        if workflow["checkout_fetch_depth"]:
            add_finding(
                findings,
                severity="info",
                code="fetch-depth-overridden",
                title="Checkout `fetch-depth` is not stable in Copilot's environment",
                evidence=["The live docs say Copilot overrides `actions/checkout` `fetch-depth`."],
                fix="Do not rely on a custom `fetch-depth` value for Copilot setup behavior.",
                can_fix_in_repo=True,
            )

        if workflow["runs_on_contains_self_hosted"]:
            manual_checks.append(
                "If the workflow targets self-hosted runners, confirm that the repository-level integrated firewall is disabled. The docs say self-hosted runners are not compatible with the integrated firewall."
            )

        if workflow["runs_on_contains_windows"]:
            manual_checks.append(
                "If the workflow targets Windows, confirm that your network controls live outside the integrated firewall. The docs say Windows is not compatible with the integrated firewall."
            )

    if audit.get("registry_files"):
        manual_checks.append(
            "The repo contains private-registry or mirror config files. Confirm which values belong in the repository's `copilot` environment as secrets or variables."
        )
        manual_checks.append(
            "If dependency hosts are blocked, update the firewall allowlist or move the run to a network path that can reach them."
        )

    if not audit.get("copilot", {}).get("has_custom_instructions"):
        add_finding(
            findings,
            severity="warning",
            code="missing-instructions",
            title="Repository instructions for build and validation are missing",
            evidence=[
                "No `.github/copilot-instructions.md`, `.github/instructions/**/*.instructions.md`, `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md` was found."
            ],
            fix="Add `.github/copilot-instructions.md` so Copilot knows how to build, test, and validate its changes after setup completes.",
            can_fix_in_repo=True,
        )

    if "stuck" in symptom_text or "hang" in symptom_text:
        manual_checks.append(
            "Inspect the live session logs before editing files. The official docs say Copilot can appear stuck for a while, and genuinely stuck sessions time out after about an hour."
        )
        manual_checks.append(
            "If the session stayed stuck, try unassigning and reassigning the issue or repeating the pull-request comment after you review the logs."
        )

    if any(token in symptom_text for token in ["workflow", "ci", "actions", "approve"]):
        manual_checks.append(
            "If GitHub Actions did not run after Copilot pushed, review the pull request for the **Approve and run workflows** gate or the repository's cloud-agent workflow-approval setting."
        )

    if any(token in symptom_text for token in ["network", "firewall", "blocked", "registry", "proxy"]):
        manual_checks.append(
            "Open the official firewall doc and compare the blocked host against the recommended allowlist, your custom rules, and any self-hosted runner network controls."
        )

    if any(token in symptom_text for token in ["runner", "self-hosted", "windows"]):
        manual_checks.append(
            "Check the organization-level runner policy. The docs say organization owners can force a default runner type and block repository overrides."
        )

    if any(token in symptom_text for token in ["ignored", "not picked up", "not used", "no effect"]):
        manual_checks.append(
            "Confirm that the setup workflow exists on the repository's default branch. A correct file on a feature branch does not affect real Copilot runs."
        )

    if workflow["exists"] and workflow["job_found"] and not findings:
        next_actions.append(
            "Use session logs to decide whether the remaining failure is in repo settings, runner access, or the task prompt rather than the setup workflow shape."
        )
    else:
        next_actions.append(
            "Fix the highest-severity in-repo findings first, then validate the workflow manually or in a pull request before changing GitHub settings."
        )

    docs = load_json(script_dir.parent / "assets" / "official-docs.json")
    return {
        "project_root": audit["project_root"],
        "repo_root": audit["repo_root"],
        "workflow_path": str(repo_root / workflow_rel),
        "workflow_exists": workflow["exists"],
        "symptom": symptom,
        "findings": findings,
        "manual_checks": list(dict.fromkeys(manual_checks)),
        "next_actions": next_actions,
        "live_docs": docs["docs"],
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"Project: {result['repo_root']}",
        f"Workflow: {result['workflow_path']}",
    ]
    if result["findings"]:
        lines.append("")
        lines.append("Findings:")
        for finding in result["findings"]:
            lines.append(f"- [{finding['severity']}] {finding['title']}")
            for item in finding["evidence"]:
                lines.append(f"  evidence: {item}")
            lines.append(f"  fix: {finding['fix']}")
    if result["manual_checks"]:
        lines.append("")
        lines.append("Manual checks:")
        for item in result["manual_checks"]:
            lines.append(f"- {item}")
    if result["next_actions"]:
        lines.append("")
        lines.append("Next actions:")
        for item in result["next_actions"]:
            lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Target project path")
    parser.add_argument("--symptom", help="Short description of the observed failure")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    audit = run_audit(Path(args.project).resolve(), script_dir)
    result = doctor(audit, args.symptom, script_dir)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render_text(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

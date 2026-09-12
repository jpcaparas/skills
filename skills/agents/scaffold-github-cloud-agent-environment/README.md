# scaffold-github-cloud-agent-environment

Repository-agnostic skill for auditing a project and scaffolding or repairing GitHub Copilot cloud agent's development environment.

## What It Adds

- live-doc verification against the current GitHub Docs contract before real scaffolding
- a repo audit that looks at runners, package managers, toolchains, LFS, containers, and private registries
- a plan-driven renderer for `.github/workflows/copilot-setup-steps.yml`
- targeted questions when repo signals are ambiguous
- doctor mode for session failures, workflow-shape mistakes, runner and firewall issues, and settings-only failure modes

## Key Files

- `SKILL.md` for the canonical workflow
- `references/live-docs.md` for the official source URLs
- `references/project-analysis.md` for the audit checklist and question triggers
- `references/scaffold-layout.md` for the generated layout and plan shape
- `references/patterns.md` for ecosystem-specific setup guidance
- `references/doctor-mode.md` for symptom-led troubleshooting
- `references/gotchas.md` for non-obvious platform traps
- `scripts/audit_project.sh` to profile a real repository
- `scripts/suggest_plan.py` to turn repo facts into an explicit scaffold plan
- `scripts/render_setup_workflow.py` to generate or refresh `.github/workflows/copilot-setup-steps.yml`
- `scripts/doctor.py` to diagnose an existing setup before editing it

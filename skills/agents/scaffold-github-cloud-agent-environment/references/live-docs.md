# Live Docs

These URLs were recorded while creating this skill on April 16, 2026. Use them to answer relevant open questions, not as a checklist to browse on every invocation. Repository files, installed tool evidence, and session logs may be sufficient for a stable known repair.

## Targeted Sources

| URL | Why it matters | Re-open when |
|-----|----------------|--------------|
| `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/customize-the-agent-environment` | Primary contract for `.github/workflows/copilot-setup-steps.yml`, supported job keys, runner choices, LFS, and environment settings | a platform-sensitive assumption is uncertain, stale, or changing |
| `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/customize-the-agent-firewall` | Firewall behavior, allowlist semantics, and security limitations | network evidence leaves a policy question unresolved or a firewall change is proposed |
| `https://docs.github.com/en/copilot/how-tos/administer-copilot/manage-for-organization/configure-runner-for-coding-agent` | Organization-level runner defaults and repository override policy | a runner mismatch suggests policy override or runner policy will change |
| `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/troubleshoot-cloud-agent` | Official symptom-led troubleshooting and session behavior | logs and repository evidence do not explain the failure |
| `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/track-copilot-sessions` | Session logs, CLI access, and investigation workflow | the supported way to inspect sessions is unclear |
| `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/configuring-agent-settings` | Built-in validation tools and workflow-approval behavior | an approval/settings contract is unclear or changing |
| `https://docs.github.com/en/copilot/tutorials/cloud-agent/get-the-best-results` | Custom instructions, task quality, and environment-prep guidance | an open setup-quality question needs product guidance |
| `https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions` | Authoritative syntax for `runs-on`, `permissions`, `services`, `snapshot`, and `timeout-minutes` | any time you touch a supported job key and need exact syntax |

## Refresh Rules

1. Start from the observed failure or requested outcome and identify the unresolved contract.
2. Read only the relevant source above when local evidence is insufficient, stale, or platform behavior will change. Prefer official docs; use version-matched tool help or trusted source when docs leave a gap.
3. Separate platform support from bundled helper behavior. Read `references/scaffold-layout.md` before assuming the renderer or doctor enforces a rule.
4. If live evidence is unavailable, report the uncertainty. Continue independent safe diagnosis, but do not apply a change whose correctness or safety depends on that unresolved contract.

## Evidence To Pull From The Docs

Check only the points relevant to the proposed change:

- the workflow path is still `.github/workflows/copilot-setup-steps.yml`
- the job name is still `copilot-setup-steps`
- the supported job keys are unchanged
- `timeout-minutes` is still capped at `59`
- self-hosted and Windows firewall rules are unchanged
- workflow-approval behavior is still the same
- the recommended runner hosts for GitHub and Copilot are unchanged

The primary environment page checked on 2026-09-25 still documents `.yml`, job `copilot-setup-steps`, the six bundled job keys, and a maximum timeout of `59`. Its examples now use `actions/checkout@v6`; bundled `@v5` and `ubuntu-latest` examples are snapshots, not required permanent selections. Keep repository action pins unless an authorized compatibility change warrants updating them.

When a passage is stale, record its location, the current official source and applicable version/date, the proposed correction, and a regression check. Follow `SKILL.md`'s proposed-update route: edit the canonical package only when in scope, otherwise report the proposal. Never silently update installed skill files or claim a helper supports a new contract before it is implemented and tested.

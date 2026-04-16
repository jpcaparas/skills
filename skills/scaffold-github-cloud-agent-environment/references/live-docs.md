# Live Docs

These URLs were verified while creating this skill on April 16, 2026. Treat them as live sources, not frozen references.

## Required Sources

| URL | Why it matters | Re-open when |
|-----|----------------|--------------|
| `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/customize-the-agent-environment` | Primary contract for `.github/workflows/copilot-setup-steps.yml`, supported job keys, runner choices, LFS, and `copilot` environment variables | every scaffold, refresh, or doctor run involving the workflow |
| `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/customize-the-agent-firewall` | Firewall behavior, allowlist semantics, and security limitations | any network, registry, or self-hosted runner issue |
| `https://docs.github.com/en/copilot/how-tos/administer-copilot/manage-for-organization/configure-runner-for-coding-agent` | Organization-level runner defaults and repository override policy | any runner mismatch or when `runs-on` may be ignored |
| `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/troubleshoot-cloud-agent` | Official symptom-led troubleshooting and session behavior | any doctor run |
| `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/track-copilot-sessions` | Session logs, `gh agent-task`, and investigation workflow | any runtime failure or suspected stuck session |
| `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/configuring-agent-settings` | Built-in validation tools and workflow-approval behavior | CI or Actions workflow-run complaints |
| `https://docs.github.com/en/copilot/tutorials/cloud-agent/get-the-best-results` | Custom instructions, task quality, and environment-prep guidance | when the user wants a higher-quality overall setup, not only YAML |
| `https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions` | Authoritative syntax for `runs-on`, `permissions`, `services`, `snapshot`, and `timeout-minutes` | any time you touch a supported job key and need exact syntax |

## Refresh Rules

1. Re-open the primary environment doc before every real scaffold or repair.
2. Re-open the firewall doc whenever registries, proxies, internal hosts, or self-hosted runners appear.
3. Re-open the runner-policy doc whenever repo intent and actual runner behavior may diverge.
4. Re-open the session and troubleshooting docs before concluding that the YAML is wrong.

## Evidence To Pull From The Docs

When you read the live docs, confirm these points before acting:

- the workflow path is still `.github/workflows/copilot-setup-steps.yml`
- the job name is still `copilot-setup-steps`
- the supported job keys are unchanged
- `timeout-minutes` is still capped at `59`
- self-hosted and Windows firewall rules are unchanged
- workflow-approval behavior is still the same
- the recommended runner hosts for GitHub and Copilot are unchanged

If any of those changed, update the scaffold plan and any baked-in examples before generating files.

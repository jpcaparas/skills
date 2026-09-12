# Doctor Mode

Doctor mode is for real failures from real Copilot cloud agent runs.

Start with:

1. the user's symptom
2. the current repo state
3. the current `copilot-setup-steps.yml` file
4. the live session logs if available

Run `python3 scripts/doctor.py --project /path/to/project --symptom "describe the failure" --json`, then map the output to the actions below.

## Symptom Map

| Symptom | First evidence to inspect | Likely cause classes |
|---------|---------------------------|----------------------|
| Workflow seems ignored | file path, job name, default-branch status | wrong path, wrong job name, workflow not merged to default branch |
| Dependencies fail to install | setup workflow plus session logs | missing checkout, wrong package manager, missing toolchain version, private registry auth |
| Network or registry access is blocked | PR warning, session logs, firewall settings | firewall allowlist, self-hosted runner firewall incompatibility, proxy or internal-host setup |
| Agent run starts but gets stuck | session logs, troubleshooting doc | long-running setup, blocked network, normal long-running behavior, eventual timeout |
| CI workflows did not run after Copilot pushed | pull request UI and repo settings | workflow approval requirement |
| Copilot can build locally but not in the cloud environment | custom instructions, runner choice, secrets | missing `copilot` environment variables, wrong runner, underspecified instructions |

## Use Session Logs Early

The official docs say you can inspect session logs from GitHub, IDE integrations, Raycast, or the GitHub CLI.

If the GitHub CLI is available and recent enough, the docs mention:

- `gh agent-task list`
- `gh agent-task view --repo OWNER/REPO PR_NUMBER`
- `gh agent-task view --repo OWNER/REPO PR_NUMBER --log --follow`

Use those commands to understand what Copilot actually tried before editing the workflow.

## Findings That Usually Mean Repo Changes

- missing `.github/workflows/copilot-setup-steps.yml`
- missing `copilot-setup-steps` job
- unsupported job keys in the setup job
- `timeout-minutes` over `59`
- install commands that run before checkout
- LFS repo without `lfs: true`
- obvious package-manager mismatch

## Findings That Usually Mean Settings Changes

- self-hosted runners with the integrated firewall still enabled
- Windows runners without an explicit network-control decision
- repository-level `runs-on` intent overridden by organization policy
- CI workflows waiting for **Approve and run workflows**
- missing `copilot` environment secrets or variables for registry auth or proxies

## Recommended Doctor Sequence

1. Confirm the workflow path and job name.
2. Inspect session logs before rewriting YAML.
3. Separate repo-local fixes from repo or org settings fixes.
4. Patch local files first when the problem is local and clear.
5. Ask the user for settings access or confirmation when the fix lives outside the repository.
6. Re-run the workflow manually or validate in a pull request after patching.

## What Not To Do

- Do not rewrite the workflow because the agent was merely slow once.
- Do not disable the firewall casually to paper over missing allowlist design.
- Do not move a repo to self-hosted runners without confirming that internal-resource access is actually required.
- Do not assume a CI failure means the environment workflow failed; Actions approval is often the real blocker.

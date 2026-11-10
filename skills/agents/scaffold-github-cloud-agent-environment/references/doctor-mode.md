# Doctor mode

Start from the user's symptom, the current `copilot-setup-steps.yml` and, when available, the session logs, before editing any YAML. Run `scripts/doctor.py` and map its findings. Its parser is indentation-based, not a YAML or schema validator, so confirm findings against the real file.

Session logs: check the installed `gh` help first. Earlier docs used `gh agent-task list`, `gh agent-task view --repo OWNER/REPO PR_NUMBER` and `... --log --follow`; do not upgrade the CLI to match them. Logs are also reachable from GitHub, IDE integrations and Raycast.

| Symptom | Inspect first | Usual cause |
|---|---|---|
| Workflow ignored | path, job name, default-branch status | wrong path or job name; not merged |
| Dependencies fail | workflow and logs | install before checkout; wrong package manager or version; registry auth |
| Network or registry blocked | PR warning, logs, firewall settings | allowlist; firewall on self-hosted runner; proxy or internal host |
| Run stuck | logs, troubleshooting doc | long setup, blocked network, eventual timeout |
| CI did not run after Copilot pushed | PR UI, repo settings | workflow approval |
| Works locally, not in the cloud | instructions, runner, secrets | missing `copilot` variables; wrong runner; thin instructions |

Repo-local fixes: missing file or job, unsupported job keys, timeout over 59, install before checkout, LFS without `lfs: true`, package-manager mismatch. Settings fixes: self-hosted runner with firewall on, Windows without a network plan, org runner policy overriding `runs-on`, workflows waiting for **Approve and run workflows**, missing `copilot` secrets or variables.

Do not rewrite the workflow because one run was slow, and do not assume a CI failure means the setup workflow failed. After patching, re-run the workflow manually or validate in a pull request.

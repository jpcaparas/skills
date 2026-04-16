# Gotchas

## 1. Default branch status matters

The setup workflow does not affect real Copilot runs until it exists on the repository's default branch.

## 2. Only a narrow set of job keys is honored

The live docs say the `copilot-setup-steps` job only supports `steps`, `permissions`, `runs-on`, `services`, `snapshot`, and `timeout-minutes`.

## 3. Setup-step failures degrade, they do not abort

If a setup step exits non-zero, Copilot skips the remaining setup steps and starts work anyway with the environment it already has.

## 4. Checkout is not optional when your setup reads the repo

If you run install or bootstrap commands that need repository files, check out the code first. The docs only promise automatic checkout after setup steps complete.

## 5. Self-hosted runners and the integrated firewall do not mix

The docs explicitly say the integrated firewall is not compatible with self-hosted runners.

## 6. Windows needs a deliberate network plan

The docs explicitly say the integrated firewall is not compatible with Windows. Treat a Windows decision as a network-controls decision too.

## 7. Workflow approval is a separate gate

By default, GitHub Actions workflows do not run automatically when Copilot pushes to its pull request branch.

## 8. `fetch-depth` is not under your control

Copilot overrides `actions/checkout` `fetch-depth`, so do not encode behavior that depends on a specific shallow-clone depth.

## 9. The firewall is not a full sandbox

The firewall applies to processes started by the agent in the Actions appliance. It does not cover setup steps or MCP servers.

## 10. Private registries usually need two fixes, not one

The common pattern is:

- `copilot` environment secrets or variables for auth
- firewall allowlist entries or self-hosted runner access for the host itself

## 11. Runner policy can override repo YAML

Organization owners can force a default runner type and prevent repositories from overriding it.

## 12. Great setup YAML is not enough without instructions

If the environment can install dependencies but Copilot still does not know which checks matter, add `.github/copilot-instructions.md`.

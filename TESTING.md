# Testing

The repository has two complementary test paths: a fast native suite for everyday work and an opt-in GitHub Actions preflight through [nektos/act](https://nektosact.com/).

## Native validation

Use any compatible Python 3.11 or newer. Create a local Python environment and install the pinned validation packages once; the canonical validator and agent hooks automatically prefer this repository-local environment:

```bash
validation_python="${SKILLS_VALIDATION_PYTHON:-python3}"
"$validation_python" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-validation.txt
```

Set `SKILLS_VALIDATION_PYTHON` to a compatible executable path or command name when the desired interpreter is not the default `python3`. The native suite also requires Bun because the `scaffold-hooks` integration probes execute its OpenCode TypeScript helpers, plus Node.js/npx for skill discovery. Put compatible commands on `PATH`, or select them explicitly with `SKILLS_VALIDATION_BUN`, `SKILLS_VALIDATION_NODE`, and `SKILLS_VALIDATION_NPX`. Install Bun with the [official installer](https://bun.sh/docs/installation). The remaining command-line dependencies are Git, `jq`, ripgrep (`rg`), and HTTPie (`http`). Hosted validation remains deterministic and currently pins Python 3.11, Node.js 24, and Bun 1.3.11.

Then run the complete repository suite with:

```bash
pnpm validate
```

This is the canonical validator used by the hosted workflow, the pre-push hook, and agent stop hooks. It does not require Docker and never launches `act` recursively.

## Local GitHub Actions matrix

The checked-in workflow targets `ubuntu-24.04` and `macos-15`. To exercise both legs locally, install [act v0.2.89 or later](https://github.com/nektos/act/releases/tag/v0.2.89), start Docker, and run the command on an Apple Silicon Mac:

```bash
brew install act
pnpm validate:act
```

The wrapper invokes the two matrix legs sequentially. Ubuntu uses a pinned `linux/amd64` container image; macOS uses act's `-self-hosted` mode and therefore runs directly on the current Mac. Act's local checkout bridge copies the current non-ignored worktree into an isolated job workspace, including staged, unstaged, and untracked files. The canonical validator still rejects untracked files under `skills/`, because those files would be absent from a fresh hosted checkout.

For deterministic execution, the wrapper isolates repository and XDG `actrc` configuration and rejects an active `$HOME/.actrc`. It accepts only logging flags after `--`, ignores act's default `.env`, `.input`, `.secrets`, and `.vars` files, and prevents automatic GitHub-token import. It also disables bind and remote-checkout overrides so the workflow cannot replace the local checkout copy. The macOS leg accepts Python 3.11 or newer plus working Node.js/npm/npx and Bun installations, then creates a temporary Python environment and host-tool shim. Use the `SKILLS_ACT_MACOS_PYTHON`, `SKILLS_ACT_MACOS_NODE`, `SKILLS_ACT_MACOS_NPM`, `SKILLS_ACT_MACOS_NPX`, and `SKILLS_ACT_MACOS_BUN` overrides with absolute executable paths when compatible runtimes are installed outside the normal `PATH` or do not share one binary directory. Hosted GitHub Actions remains deterministic and pins Python 3.11, Node.js 24, and Bun 1.3.11.

Run one leg when that is all the host supports:

```bash
pnpm validate:act:ubuntu
pnpm validate:act:macos
```

Ubuntu requires a running Docker daemon. The macOS leg requires Apple Silicon macOS and does not require Docker. On Linux, use the Ubuntu-only command and leave macOS coverage to GitHub Actions.

After the image and actions are cached, prevent act from fetching them again:

```bash
SKILLS_ACT_PULL=false SKILLS_ACT_OFFLINE=true pnpm validate:act
```

This only makes act's own image and action lookup offline. Workflow package installation can still require network access unless those package-manager caches are already populated.

List the workflow without starting Docker or running jobs:

```bash
bash scripts/validate-ci-with-act.sh --list
```

## What the local matrix proves

The local preflight catches workflow wiring, shell portability, dependency, and tool-discovery failures across Linux and macOS. It does not reproduce GitHub's virtual machines exactly: the macOS leg uses this workstation's toolchain, the Ubuntu leg uses an act-compatible container, and [some GitHub Actions features are not implemented by act](https://nektosact.com/not_supported.html). The wrapper prevents the Ubuntu job from mounting the host Docker daemon socket.

Treat the hosted `ubuntu-24.04` / `macos-15` GitHub Actions matrix as the authoritative compatibility gate.

## macOS host security

The macOS leg is not sandboxed. Workflow commands run with your account's filesystem and process permissions, and act's host executor inherits the invoking process environment. Run it only for trusted worktrees on a trusted Mac; use a disposable Mac or virtual machine before testing untrusted pull-request code. The isolated checkout protects the source path from ordinary workflow writes, but it does not isolate the rest of the host account.

# AGENTS.md

This repository is a public source for installable agent skills.

## Conventions

- Put every installable skill in `skills/<skill-name>/`.
- This is a public repository used across many developer machines. Keep local and userland tooling requirements flexible: accept compatible version ranges and explicit executable overrides instead of pinning one exact Python, Node.js, Bun, or other runtime version unless compatibility truly requires it. Put deterministic exact pins at reproducible boundaries such as GitHub Actions, containers, and lockfiles, and document the distinction.
- Treat this repository as the source of truth for existing skills. When modifying an existing skill, make the change in this repo first, not only in an installed copy under another skills directory.
- Keep `SKILL.md` as the canonical instruction file for each skill.
- Treat `README.md`, `AGENTS.md`, and `metadata.json` beside a skill as thin packaging wrappers, not alternate sources of truth.
- Prefer repo-agnostic instructions. Do not hard-code a single workspace or machine path unless the user explicitly requires it.
- When a skill creates other skills, detect whether the best destination is repo-local or global before writing files.

## Validation

### Native validation

Use any compatible Python 3.11 or newer. Create a repository-local environment and install the pinned validation packages once; the canonical validator and agent hooks automatically prefer `.venv`:

```bash
validation_python="${SKILLS_VALIDATION_PYTHON:-python3}"
"$validation_python" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-validation.txt
```

Native validation also requires Bun, Node.js with `npx`, Git, `jq`, and ripgrep (`rg`). Put compatible executables on `PATH`, or select non-standard installations with `SKILLS_VALIDATION_PYTHON`, `SKILLS_VALIDATION_BUN`, `SKILLS_VALIDATION_NODE`, and `SKILLS_VALIDATION_NPX`. These userland runtimes intentionally accept compatible versions; the hosted workflow remains deterministic and currently pins Python 3.11, Node.js 24, and Bun 1.3.11.

For any skill that ships scripts, run its local validators and confirm repository discovery still works:

```bash
python3 skills/<skill-name>/scripts/validate.py skills/<skill-name>
python3 skills/<skill-name>/scripts/test_skill.py skills/<skill-name>
npx --yes skills add . --list
```

Run the complete native repository suite before handing off a change:

```bash
pnpm validate
```

This is the canonical validator used by GitHub Actions, the pre-push hook, and agent stop hooks. It does not require Docker or invoke `act` recursively.

### Local GitHub Actions preflight

For a higher-fidelity preflight, install [nektos/act v0.2.89 or newer](https://github.com/nektos/act/releases/tag/v0.2.89). The full matrix requires Docker and an Apple Silicon Mac:

```bash
pnpm validate:act
```

The wrapper runs Ubuntu in a pinned `linux/amd64` container, then runs the macOS job directly on the host through act's self-hosted mode. Run a single supported leg when necessary:

```bash
pnpm validate:act:ubuntu
pnpm validate:act:macos
```

The Ubuntu leg requires Docker. The macOS leg requires Apple Silicon macOS plus compatible Python 3.11+, Node.js/npm/`npx`, Bun, ripgrep, and HTTPie installations. When the runtime tools are outside the normal `PATH`, set `SKILLS_ACT_MACOS_PYTHON`, `SKILLS_ACT_MACOS_NODE`, `SKILLS_ACT_MACOS_NPM`, `SKILLS_ACT_MACOS_NPX`, and `SKILLS_ACT_MACOS_BUN` to their executable paths.

The wrapper isolates project and XDG act configuration, rejects an active `$HOME/.actrc`, ignores act's default environment, input, secret, and variable files, and prevents automatic GitHub-token import. The macOS leg is not sandboxed: workflow commands inherit the invoking account's filesystem, process, and environment access. Run it only for trusted worktrees on a trusted Mac; use a disposable machine or virtual machine for untrusted pull-request code.

Act is a preflight, not an exact reproduction of GitHub's runners. Treat the hosted `ubuntu-24.04` and `macos-15` workflow as the authoritative compatibility gate.

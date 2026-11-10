# AGENTS.md

This repository is a public source for installable agent skills. It is the source of truth for them: change a skill here first, not in an installed copy under another skills directory.

## Conventions

- Put every installable skill in `skills/<category>/<skill-name>/`, in the best existing category from `scripts/skill_catalog.py`. That script owns category order and package discovery; derive inventories from it, not from recursive `SKILL.md` scans.
- Skill names are globally unique across categories. Categories organise source paths; they are not part of installation or invocation names.
- `SKILL.md` is the only instruction file in a package. Add no README, AGENTS.md or metadata.json beside it. Name a fixture that is itself a skill `SKILL.fixture.md`, because hosts install every file named `SKILL.md` as a skill.
- Keep each description at most 450 characters and all descriptions together under 13,000. Hosts load every description at startup, and Codex shortens and then drops skills past its budget.
- Write what a capable model would get wrong without the skill: the outcome, what needs the user's approval, facts it would misremember, and exact rules for safety, standards and tool contracts. Leave implementation, aesthetics, presentation and workflow to the model. Templates and numeric defaults are examples unless a consumer or user requires them.
- Give facts that can go stale a date and a source, and a recovery route: when advice fails, the skill checks the installed tool or version-matched official docs and proposes a sourced correction. A skill never rewrites an installed copy of itself.
- Add `scripts/` only for deterministic work that is wasteful or risky to re-derive. A script that executes gets an offline standard-library `scripts/test_<name>.py`. Add no validator or test that asserts how a `SKILL.md` is worded; it proves nothing about behaviour and blocks rewording.
- Evals under `evals/` are the behavioural specification. Authoring them, or passing structural checks, is not evidence that a model run passed; say which of the two you have.
- Keep instructions repo-agnostic: no workspace or machine paths unless the user requires one.
- This repository runs on many developer machines. Local tooling accepts compatible version ranges and executable overrides; exact pins belong at reproducible boundaries (GitHub Actions, lockfiles). Install a missing validation binary with a user-local method and never weaken or skip a check to compensate for one.

## Adding, renaming or removing a skill

A skill has three derived surfaces, and validation fails until they agree with `skills/`:

- A `#### \`<name>\`` section in `README.md` under its category, with the install line, the card block and a description.
- A 1024x576 `skill-card.png` in the package, with a scene entry in `SKILL_SCENES` in `scripts/render-skill-art.py`.
- Every other mention of the name (README starting points, other skills that hand off to it).

`python3 scripts/render-skill-art.py --readme-only` refreshes the README card blocks without network access, and `--normalize-only` strips metadata from existing cards. Generating a card calls a paid image API: it needs credentials and the user's explicit authorization, then `python3 scripts/render-skill-art.py --skill <skill-name> --force`.

## Validation

Use Python 3.11 or newer. Create the repository environment once; the validator and the agent stop gate prefer `.venv`:

```bash
validation_python="${SKILLS_VALIDATION_PYTHON:-python3}"
"$validation_python" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-validation.txt
python -m playwright install chromium --no-shell
scripts/run-pnpm.sh install --frozen-lockfile
```

Validation also needs Bun, Node.js with `npx`, Git, `jq` and ripgrep (`rg`) on `PATH`, or selected with `SKILLS_VALIDATION_PYTHON`, `SKILLS_VALIDATION_BUN`, `SKILLS_VALIDATION_NODE` and `SKILLS_VALIDATION_NPX`. On Linux, add `--with-deps` to the browser installation when system libraries are missing.

Run the whole suite before handing off a change:

```bash
pnpm validate
```

`scripts/validate-all-skills.sh` is the one entrypoint: GitHub Actions, the pre-push hook and the agent stop gate all run it. It checks what breaks installs and hosts, not how a skill words its instructions:

- `scripts/validate-skills.py`: frontmatter, the description budget, stray nested `SKILL.md` files, `SKILL.md` links that are broken or leave the package, and Python that does not compile.
- `scripts/validate-readme-skills.py` and `scripts/validate-skill-art.py`: the README catalogue and the cards.
- Each skill's own tests. To run one skill's tests alone: `python3 -m unittest discover -s skills/<category>/<skill-name>/scripts -p 'test_*.py'`.
- Skill files a fresh checkout would not contain (untracked, or hidden by a user-global gitignore), then `skills` installer discovery and the Codex context budget.

Browser tests use the Chromium revision that the pinned Playwright package selects, never a browser found on `PATH`, and they advance a paused clock. Do not replace that with real-time sleeps or retry a failing fixture until it passes. Tests that execute temporary tool doubles use `scripts/executable-temp-dir.sh`, which falls back to the repository filesystem when the temporary directory is mounted `noexec`; set `SKILLS_EXECUTABLE_TMPDIR` to choose another location.

The hosted workflow is the compatibility gate. It runs `ubuntu-24.04` and `macos-15` with Python 3.11, Node.js 24 and Bun 1.4.4, and pins every GitHub Action to a commit SHA with a `# vX.Y.Z` comment. Dependabot proposes the bumps; change the SHA and its comment together.

## Agent stop gate

`scripts/agent-stop-checks.sh <harness>` runs the validation suite when an agent finishes with uncommitted or unpushed work, and sends the agent back with the end of the log when it fails. Each harness config (`.claude/settings.json`, `.codex/hooks.json`, `.devin/hooks.v1.json`, `.opencode/hook/hooks.md`, `.amp/plugins/repository-hooks.ts`) holds only the adapter that calls it. Put new policy in the script or the validator, not in an adapter.

## Amp orb lifecycle

- `.agents/setup` prepares a new orb: system tools, the Python validation environment, the pinned Chromium revision, locked Node dependencies, the repository skills installed into Amp, and Gemini CLI skill links.
- `.agents/resume` only rechecks the skill links when a warm orb resumes.
- A change to `.agents/setup` reaches future orbs only after it is on the default branch.

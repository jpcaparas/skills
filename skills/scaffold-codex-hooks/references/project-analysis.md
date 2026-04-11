# Project Analysis

Audit the target repository before deciding which Codex hooks to enable.

## Audit Order

1. Find the repo root and canonicalize the absolute path with `pwd -P`.
2. Inspect existing Codex files first:
   - `.codex/config.toml`
   - `.codex/hooks.json`
   - `.codex/hooks/`
3. Inspect project instructions and automation context:
   - `AGENTS.md`
   - `README*`
   - repo-local docs or workflow notes
4. Inspect real build, lint, test, and validation entry points:
   - `package.json` scripts
   - `Makefile`
   - `justfile`
   - `Taskfile.yml`
   - CI workflows
5. Inspect environment and safety signals:
   - `.envrc`
   - `.env*`
   - generated files
   - lockfiles
   - migrations
   - infra folders
6. Inspect existing Git hook tooling:
   - `.husky/`
   - `lefthook.yml`
   - `.githooks/`
7. Decide whether the feature flag belongs in repo config or user config.

Run `scripts/audit_project.sh /path/to/project` first. The script reports repo facts, not policy conclusions.

## Signals That Matter

| Signal | Why it matters for hook planning |
|--------|----------------------------------|
| Existing `.codex/config.toml` | Strong signal that project-scoped feature config is already acceptable |
| Existing `.codex/hooks.json` | Determines whether the refresh should be additive or a managed-overhaul |
| Existing `.codex/hooks/README.md` or managed manifest | Tells you whether the repo already has a convention worth preserving |
| `package.json` with `lint`, `test`, or `check` scripts | Good candidates for `PostToolUse` or `Stop` hooks |
| Monorepo markers like `pnpm-workspace.yaml`, `turbo.json`, or `nx.json` | Hooks may need workspace-aware commands and narrow checks |
| `.envrc`, `.env`, or toolchain files | Good candidates for lightweight `SessionStart` reminders or environment checks |
| Existing Git hook managers like Husky or Lefthook | Codex hooks should complement, not silently duplicate, human Git hooks |
| Sensitive files or directories | Strong candidates for `PreToolUse` Bash guardrails or `Stop` follow-up checks |

## Questions To Answer Before Scaffolding

- Should the scaffold commit `.codex/config.toml`, or should the feature remain user-local?
- Does the project already have custom hook handlers that must stay untouched?
- Which commands are cheap enough for `SessionStart` versus expensive enough to defer to `Stop`?
- Does the repo need a Bash safety gate, or only start/stop bookends?
- Are there already CI or Git hooks that make some Codex checks redundant?
- Does the project need repo-shared hooks, or only personal/local automation?

## Recommended Planning Output

A project-specific plan JSON should answer at least:

- `hooks_target`
- `managed_root`
- `feature_scope`
- `mode`
- `enabled_events`

Keep the plan narrow and explicit. The scaffold script should not guess repo policy on its own.

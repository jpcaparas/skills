# Project Analysis

Audit the target repository before deciding which Devin hooks to enable.

## Audit Order

1. Find the repo root and determine whether the project is single-package or a workspace.
2. Inspect existing Devin files:
   `.devin/hooks.v1.json`, `.devin/config.json`, `.devin/config.local.json`, `.devin/hooks/`, `AGENTS.md`, and any Devin-specific scripts or docs.
3. Inspect existing Claude hook config only to understand inherited behavior that Devin may read by default. Do not write generated config there.
4. Inspect automation entry points:
   `package.json` scripts, `Makefile`, `justfile`, `Taskfile.yml`, CI workflows, and custom runner scripts.
5. Inspect safety boundaries:
   secrets, lockfiles, generated files, migrations, infra folders, deployment scripts, and protected branches.
6. Inspect environment signals:
   `.env`, `.envrc`, `mise.toml`, toolchain files, direnv usage, or per-directory shells.
7. Inspect existing Git hook tooling:
   `.husky/`, `lefthook.yml`, `.githooks/`, repo-local wrappers, or server-side gates in CI.
8. Decide which events must block with exit code `2` and which events should only log or add context.

Run `scripts/audit_project.sh /path/to/project` first. The script reports repo facts, not policy conclusions.

## Signals That Matter

| Signal | Why it matters for hook planning |
|--------|----------------------------------|
| Existing repo command sources | Good candidates for `PreToolUse`, `PostToolUse`, or `Stop` hooks when the project already owns the check |
| Monorepo markers like `pnpm-workspace.yaml`, `turbo.json`, or `nx.json` | Hooks may need package-aware matching, targeted tests, or workspace-relative commands |
| `.envrc`, `.env`, or toolchain files | Strong candidate for `SessionStart` or `PreToolUse` context and safety behavior |
| `.devin/hooks.v1.json` | Determines whether the refresh should be additive or managed-overhaul |
| `.devin/config*.json` with hooks | May already contain hook policy; prefer migrating generated project hooks to `.devin/hooks.v1.json` unless the user asks otherwise |
| Claude hook config | Possible inherited behavior; useful to warn about duplicate hooks, but not a managed target |
| Git hook managers like Husky or Lefthook | Devin hooks should complement, not silently duplicate, human Git hooks |
| Sensitive files like `.env`, lockfiles, migrations, or infra code | Strong candidate for `PreToolUse` file or command guards |
| Existing notification or audit tooling | Good candidates for `PostToolUse`, `SessionStart`, `SessionEnd`, or `PostCompaction` hooks |

## Questions To Answer Before Scaffolding

- Which commands are the real source of truth for lint, test, format, and typecheck?
- Are those commands already available as documented repo commands, task-runner entries, CI jobs, or local scripts?
- Are there existing custom Devin hooks that must stay untouched?
- Which operations must block Devin with exit code `2`, and which should only observe or report?
- Which files or directories are too risky to edit without an explicit gate?
- Does the project need environment setup at session start?
- Does the project already have CI or Git hooks that make some Devin hooks redundant?
- Does inherited Claude config create duplicate hook behavior that the user should know about?

## Recommended Planning Output

After the audit, create a small plan JSON with:

- `hooks_target`
- `managed_root`
- `mode`
- `enabled_events`
- optional per-event `scripts` arrays for repo-owned reusable scripts
- optional per-event `commands` arrays for stable existing repo commands
- per-event `block_on_failure` so exit code `2` is intentional

Keep the plan narrow and explicit. The scaffold script should not guess project policy on its own.

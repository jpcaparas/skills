# Project Analysis

Audit the target repository before deciding which Claude Code hooks to enable.

## Audit Order

1. Find the repo root and determine whether the project is single-package or a workspace. Record the canonical absolute path with `pwd -P`, because Claude Code workspace trust is keyed by exact path.
2. Inspect existing Claude Code files:
   `CLAUDE.md`, `.claude/settings.json`, `.claude/settings.local.json`, `.claude/hooks/`, `.claude/rules/`, plugin hooks, and generated hook folders.
3. Inspect automation entry points:
   `package.json` scripts, `Makefile`, `justfile`, `Taskfile.yml`, CI workflows, and any custom runner scripts.
4. Inspect safety boundaries:
   secrets, lockfiles, generated files, migrations, infra folders, deployment scripts, and protected branches.
5. Inspect environment reload signals:
   `.env`, `.envrc`, `mise.toml`, toolchain files, direnv usage, or per-directory shells.
6. Inspect existing Git hook tooling:
   `.husky/`, `lefthook.yml`, `.githooks/`, repo-local wrappers, or server-side gates in CI.
7. Decide which settings file should own the shared hook config.

Run `scripts/audit_project.sh /path/to/project` first. The script is intentionally deterministic and reports repo facts, not policy conclusions.

## Signals That Matter

| Signal | Why it matters for hook planning |
|--------|----------------------------------|
| Existing repo command sources | Good candidates for `PostToolUse`, `Stop`, or `TaskCompleted` hooks when the project already owns the check |
| Monorepo markers like `pnpm-workspace.yaml`, `turbo.json`, or `nx.json` | Hooks may need package-aware matching, targeted tests, or workspace-relative commands |
| `.envrc`, `.env`, or toolchain files | Strong candidate for `CwdChanged` or `FileChanged` hooks |
| Existing `.claude/settings*.json` | Determines whether the refresh should be additive or managed-overhaul |
| Existing `.claude/hooks/README.md` or generated hook folders | Tells you whether the repo already has a convention worth preserving |
| Git hook managers like Husky or Lefthook | Claude Code hooks should complement, not silently duplicate, human Git hooks |
| Sensitive files like `.env`, lockfiles, migrations, or infra code | Strong candidate for `PreToolUse` file guards |
| Existing notification or audit tooling | Good candidates for async `Notification`, `PostToolUse`, `ConfigChange`, or `SessionEnd` hooks |

## Questions To Answer Before Scaffolding

- Which commands are the real source of truth for lint, test, format, and typecheck?
- Are those commands already available as documented repo commands, task-runner entries, CI jobs, or local scripts that the hook can call directly?
- Does the project need shareable hooks in `.claude/settings.json`, or machine-local hooks in `.claude/settings.local.json`?
- Are there existing custom hooks that must stay untouched?
- If hooks already exist or the user wants verification, is the exact repo path already trusted in `~/.claude.json`?
- Which operations must block Claude, and which should only observe or report?
- Which files or directories are too risky to edit without an explicit gate?
- Does the project need environment reload behavior when the working directory or `.env`-style files change?
- Does the project already have CI or Git hooks that make some Claude Code hooks redundant?

## Recommended Planning Output

After the audit, create a small plan JSON with:

- `settings_target`
- `managed_root`
- `mode`
- `enabled_events`
- optional per-event `commands` arrays for existing repo commands the generated hook should run before custom logic

Keep the plan narrow and explicit. The scaffold script should not guess project policy on its own.

# Project Analysis

Audit before writing hooks. The best hook scaffold depends on how the repository already runs checks, manages agent instructions, and treats sensitive files.

## Fast Audit

Run:

```bash
scripts/audit_project.sh /path/to/project
```

Then inspect the output and open the relevant files before choosing enabled events.

## Checklist

Inspect these areas:

- repository root and whether it is a monorepo
- package managers and task runners: `package.json`, `pnpm-workspace.yaml`, `turbo.json`, `Makefile`, `justfile`, `Taskfile.yml`, `pyproject.toml`, `go.mod`, `Cargo.toml`
- lint/test/build commands documented in README, AGENTS, package scripts, Make, Just, or CI
- `.github/hooks/*.json`
- `.github/copilot/settings.json` and `.github/copilot/settings.local.json`
- `.github/copilot/` scripts, instructions, docs, or generated folders
- `.github/workflows/copilot-setup-steps.yml`, because environment setup and hooks often interact
- `.claude/settings.json` and `.claude/settings.local.json` only as Copilot CLI inherited-hook context
- `AGENTS.md`, `CLAUDE.md`, `README.md`, and repo-specific instructions
- existing Git hooks, Husky, Lefthook, pre-commit, or CI gates
- sensitive paths: `.env*`, secrets, migrations, generated code, lockfiles, infra, deployment config
- reusable scripts under `scripts/`, `bin/`, `tools/`, or `.github/scripts/`

## Event Selection Heuristics

| Need | Event |
|------|-------|
| Block dangerous shell/file actions | `preToolUse` |
| Let Copilot CLI allow or deny permission requests in pipe mode | `permissionRequest` |
| Log prompt text or add prompt policy checks | `userPromptSubmitted` |
| Add context after failed commands | `postToolUseFailure` |
| Enforce "do not stop until checks run" behavior | `agentStop` |
| Add session startup context | `sessionStart` |
| Collect final logs or cleanup local temp files | `sessionEnd` |
| Notify humans from local CLI | `notification` |

Use fewer enabled hooks than generated stubs. Generate all stubs for discoverability, but wire only the events that the project actually needs.

## Cloud Agent vs CLI

Prefer hooks that work in both surfaces when possible:

- `preToolUse` instead of `permissionRequest` for security decisions.
- repo-relative bash scripts instead of GUI notifications.
- stdout JSON decisions instead of interactive prompts.
- short execution under the default 30 second timeout.

Use CLI-only events only when the user specifically needs local CLI ergonomics.

## See Also

- `references/hook-events.md`
- `references/reusable-scripts.md`

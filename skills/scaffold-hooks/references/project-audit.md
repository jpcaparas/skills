# Project Audit

Before running `/scaffold-hooks`, inspect the project for existing hook surfaces and reusable validation scripts.

## Files to Inspect

- `.claude/settings.json`
- `.claude/settings.local.json`
- `.claude/hooks/`
- `.codex/hooks.json`
- `.codex/config.toml`
- `.codex/hooks/`
- `.devin/hooks.v1.json`
- `.devin/config*.json`
- `opencode.json`
- `.opencode/hook/hooks.md`
- `.opencode/hook/.managed/`
- `.opencode/plugins/`
- `.opencode/package.json`
- `.github/hooks/copilot-hooks.json`
- `.github/copilot/hooks/generated/`
- `hooks/`
- `./scripts/agent-stop-checks.sh`
- `./scripts/agent-session-context.sh`
- `./scripts/validate-project.sh`

## Questions to Answer

- Which harnesses are actually used by the team?
- Which supported hook surfaces already exist? A bare run refreshes only this detected set.
- Which old generated roots are present?
- Which hooks are custom and must be preserved?
- Which project validation scripts already exist?
- Is Codex configured with the hooks feature enabled in project or user scope?
- Does OpenCode already use `opencode-froggy`, and does it have old scaffold-owned or custom local plugins?

## Output to Expect

The universal run should leave config files readable and boring:

- shell harness configs point into `hooks/<event>/<harness>.sh`
- shared behavior lives in `hooks/<event>/script.sh`
- harness-specific config lives in `hooks/<event>/<harness>.json`
- OpenCode loads `opencode-froggy` from `opencode.json` and reads `.opencode/hook/hooks.md`
- generated-root legacy commands are absent from selected shell harness configs
- `hooks/.state/scaffold-hooks/manifest.json` records detected harnesses and the selection source

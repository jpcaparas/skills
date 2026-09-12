# Project Analysis

Before scaffolding OpenCode:

1. Check whether the target is a git repo.
2. Read `opencode.json` or `opencode.jsonc` if present.
3. Inspect `.opencode/hook/hooks.md`.
4. Inspect `.opencode/hook/.managed/manifest.json`.
5. Inspect `.opencode/plugins/` for unmanaged custom plugins and old `.managed` state.
6. Inspect `.opencode/package.json` for old local-plugin dependency artifacts.
7. Identify repo-owned scripts that hooks should call:
   - `./scripts/agent-session-context.sh`
   - `./scripts/validate-project.sh`
   - `./scripts/agent-stop-checks.sh`
8. Check package scripts and validation commands.
9. Check AGENTS/README instructions that affect validation or generated files.

Scope decision:

- Use project scope for repo-owned scripts and team-shared behavior.
- Use global scope for personal behavior that should not be committed.

Migration signal:

- `.opencode/plugins/.managed/manifest.json` with `scaffold_hooks.harness == "opencode"` means the previous scaffold can be cleaned up.

# OpenCode Froggy Hooks

Project-local OpenCode hook configuration managed by `scaffold-hooks` through `opencode-froggy`.

## Managed Paths

- OpenCode config: `opencode.json`
- Froggy hook config: `.opencode/hook/hooks.md`
- Managed state: `.opencode/hook/.managed`

## Active Hooks

| Event | Conditions | Actions | Notes |
|-------|------------|---------|-------|
| `session.created` | isMainSession | `bash` | Record the skills repo session baseline quietly. |
| `session.idle` | isMainSession | `bash` | Run the repository stop checks after the main OpenCode session goes idle. |

## Notes

- `opencode.json` loads `opencode-froggy`; hook behavior lives in `hooks.md`.
- Froggy merges global hooks first, then project hooks.
- Bash actions receive `OPENCODE_PROJECT_DIR`, `OPENCODE_SESSION_ID`, and JSON context on stdin.
- `tool.before.*` and `tool.before.<name>` bash actions can block by exiting `2` and writing the reason to stderr.
- Exit code controls success, failure, or blocking; stderr is for diagnostics and block reasons, not successful status messages.
- The old scaffold-owned `.opencode/plugins/*.ts` lifecycle adapter is intentionally removed during migration.

## Sources

- https://opencode.ai/docs/plugins/
- https://opencode.ai/docs/config/
- https://github.com/smartfrog/opencode-froggy
- https://www.npmjs.com/package/opencode-froggy

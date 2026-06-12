# scaffold-hooks

Use `SKILL.md` as the canonical workflow. This skill composes the Claude Code, Codex, Devin CLI, and OpenCode hook scaffolders into one `/scaffold-hooks` workflow that writes shared project behavior under `hooks/` and keeps harness config files as thin adapters.

Do not duplicate harness event semantics here. Update the dedicated harness skill first, then adjust the universal composition layer.


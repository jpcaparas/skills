# scaffold-hooks

Thin wrapper for the installable `scaffold-hooks` skill.

Use this skill when a user wants `/scaffold-hooks` to scaffold or migrate Claude Code, Codex, Devin CLI, and OpenCode hook configuration into one shared `hooks/` directory.

It provides:

- one universal command for all four harnesses
- migration away from old `.claude/hooks/generated`, `.codex/hooks/generated`, and `.devin/hooks/generated` command roots
- a shared `hooks/<event>/script.sh` behavior layer
- thin harness adapters beside each shared event script
- conservative config merges that preserve non-managed custom hooks

Read `SKILL.md` for the canonical workflow.


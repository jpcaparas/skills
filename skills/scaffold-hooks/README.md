# scaffold-hooks

Thin wrapper for the installable `scaffold-hooks` skill.

Use this skill when a user wants `/scaffold-hooks` to scaffold or migrate Claude Code, Codex, GitHub Copilot, Devin CLI, or OpenCode hook configuration into one shared `hooks/` directory. It asks which harnesses to target and defaults to all supported harnesses.

It provides:

- one universal command for all supported harnesses, with `--harnesses` subsets
- bundled per-harness components under `harnesses/<name>/` (formerly the dedicated scaffold-cc-hooks, scaffold-codex-hooks, scaffold-github-copilot-hooks, scaffold-devin-hooks, and scaffold-opencode-hooks skills)
- migration away from old `.claude/hooks/generated`, `.codex/hooks/generated`, and `.devin/hooks/generated` command roots
- a shared `hooks/<event>/script.sh` behavior layer
- thin harness adapters beside each shared event script
- conservative config merges that preserve non-managed custom hooks

Read `SKILL.md` for the canonical workflow.

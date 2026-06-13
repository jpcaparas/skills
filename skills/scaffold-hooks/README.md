# scaffold-hooks

Thin wrapper for the installable `scaffold-hooks` skill.

Use this skill when a user wants `/scaffold-hooks` to scaffold, refresh, or migrate Claude Code, Codex, GitHub Copilot, Devin CLI, or OpenCode hook configuration into one shared `hooks/` directory. Bare runs detect existing hook surfaces and refresh only those harnesses; new harnesses are added only when explicitly requested.

It provides:

- one universal command for all supported harnesses, with `--harnesses` subsets for explicit additions
- bundled per-harness components under `harnesses/<name>/` (formerly the dedicated scaffold-cc-hooks, scaffold-codex-hooks, scaffold-github-copilot-hooks, scaffold-devin-hooks, and scaffold-opencode-hooks skills)
- migration away from old `.claude/hooks/generated`, `.codex/hooks/generated`, and `.devin/hooks/generated` command roots
- a shared `hooks/<event>/script.sh` behavior layer
- thin harness adapters beside each shared event script
- conservative config merges that preserve non-managed custom hooks
- manifest provenance so future re-runs can refresh managed scaffolding incrementally

Read `SKILL.md` for the canonical workflow.

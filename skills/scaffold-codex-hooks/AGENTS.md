# scaffold-codex-hooks

Thin wrapper for the installable `scaffold-codex-hooks` skill.

Use this skill when a user wants Codex hooks scaffolded or refreshed in a real project, especially when the work needs:

- live verification of the current Codex hooks docs, schemas, and runtime source
- deterministic inspection or enablement of the canonical `hooks` feature flag
- a managed `.codex/hooks.json` merge that preserves unrelated custom hooks
- one generated bash stub per current source-backed Codex hook event

Read `SKILL.md` for the canonical workflow.

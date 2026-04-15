# scaffold-opencode-hooks

Thin wrapper for the installable `scaffold-opencode-hooks` skill.

Use this skill when a user wants OpenCode hooks scaffolded or refreshed in a real project, especially when the work needs:

- live verification of the current official OpenCode plugin and config docs
- deterministic inspection of project-vs-global OpenCode plugin state
- a managed `.opencode/plugins/` scaffold that preserves unrelated user plugins
- repeatable merges for `opencode.json` plugin arrays and config-dir package dependencies
- one generated reference stub per current OpenCode hook surface, plus live managed plugin files for only the enabled patterns

Read `SKILL.md` for the canonical workflow.


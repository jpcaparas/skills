# scaffold-opencode-hooks

Thin wrapper for the installable `scaffold-opencode-hooks` skill.

Use this skill when a user wants OpenCode hooks scaffolded or refreshed in a real project, especially when the work needs:

- live verification of the current official OpenCode plugin and config docs
- deterministic inspection of project-vs-global OpenCode plugin state
- a minimal TypeScript lifecycle/action plugin with visible OpenCode TUI feedback
- path-aware calls into repo-owned reusable scripts
- one controlled automatic repair/follow-up pass without infinite loops
- repeatable merges for `opencode.json` plugin arrays and config-dir package dependencies only when needed
- optional broad hook-surface stubs when the user explicitly asks for a full catalog

Read `SKILL.md` for the canonical workflow.

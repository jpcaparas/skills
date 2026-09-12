# Source Notes

This skill is grounded in official OpenAI Codex documentation checked on 2026-07-06.

## Official Sources

| Source | Used for |
|---|---|
| https://developers.openai.com/codex/subagents | Availability, explicit triggering, managing subagents, sandbox inheritance, built-in/custom agents, `[agents]` settings |
| https://developers.openai.com/codex/concepts/subagents | Context-pollution rationale, subagent terminology, explicit triggering, model/reasoning guidance |
| https://developers.openai.com/codex/config-reference | `agents.max_threads`, `agents.max_depth`, and related config keys |
| https://developers.openai.com/codex/concepts/customization | How subagents fit with AGENTS.md, skills, MCP, and customization layers |
| https://developers.openai.com/codex/cli/features | CLI feature summary for subagents and related workflow behavior |
| https://developers.openai.com/codex/hooks | Subagent hook events and lifecycle context |

## Source-Derived Principles

- Subagents are for explicit subagent or parallel-agent requests, not silent automatic delegation.
- They are strongest for noisy, read-heavy, independent work such as exploration, tests, triage, review, and summarization.
- Write-heavy parallelism needs extra coordination because file conflicts and integration failures can erase the speed benefit.
- Subagents inherit sandbox and approval behavior from the parent session.
- Custom agents should be narrow and can inherit model and config fields from the parent session.
- Global depth and thread caps matter. Recursive fan-out should stay rare and deliberate.

## Advisor-Skill Inspiration

The gating style follows `{{ skill:claude-code-auto-advisor }}`:

- Exit immediately outside the intended harness.
- Require a concrete reason before invoking an expensive or risky secondary agent capability.
- Gather evidence before delegation or review.
- Treat delegated reasoning as an extra pass, not a substitute for local verification.
- Do not simulate a missing harness-specific feature with unrelated tools.

## Refresh Triggers

Re-check the official docs before changing this skill when:

- Codex exposes subagent visibility in additional surfaces.
- Custom agent schema changes.
- `[agents]` configuration keys change.
- Codex adds new built-in agent roles.
- The current session exposes different callable subagent behavior than the docs describe.

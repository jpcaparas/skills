---
name: claude-code-auto-advisor
description: "Claude Code only passive advisor policy. Use in Claude Code for security, code reviews, high-stakes design, multi-step high-level plan validation for substantial work, complex refactors, recurring failures, or completion checks. Consult the configured advisor without user prompting. Do NOT use outside Claude Code, without an advisor model/tool, for trivial tasks, or for ordinary planning."
compatibility: "Requires Claude Code v2.1.98+ with a configured advisor model. Optional helper scripts require python3."
metadata:
  version: "1.0.0"
  short-description: "Auto-consult Claude Code advisor for high-stakes work"
  openclaw:
    category: "development"
    requires:
      bins: [python3]
references:
  - advisor-policy
  - claude-code-mechanics
---

# claude-code-auto-advisor

Invoke Claude Code's configured advisor automatically for tasks where a second model materially reduces risk.

## Decision Tree

Before applying this skill, answer these gates in order:

- Not running in Claude Code:
  Stop. Do not simulate the advisor with subagents, web search, another model, or a different harness feature.

- No configured advisor model or no callable advisor tool in this Claude Code session:
  Do not call the advisor. Continue with normal verification and record the skip reason only when it matters to the final handoff.

- Task is security-related, a code review, high-stakes design, multi-step high-level plan validation before substantial work, a risky refactor, production/data-affecting work, a recurring failure, or a complex completion check:
  Gather enough local evidence, then consult the advisor before committing to the approach or final conclusion. Read `references/advisor-policy.md`.

- Task is routine, reversible, single-step, ordinary planning, a small checklist, or already fully determined by local evidence:
  Do not consult the advisor.

- Unsure whether the advisor is enabled:
  Prefer the actual Claude Code tool list as source of truth. Optionally run `python3 scripts/detect_advisor_config.py --format text` for a conservative settings preflight, then read `references/claude-code-mechanics.md`.

## Quick Reference

| Situation | Action |
|---|---|
| Security, auth, secrets, permissions, sandboxing, supply chain, data exposure | Consult the advisor after initial context gathering and before recommendations or edits |
| Code review, PR review, or requested independent review | Consult the advisor before final findings |
| Big multi-step implementation plan, migration plan, multi-agent handoff, or high-level plan with meaningful blast radius | Draft the plan with evidence and constraints, then consult before work begins |
| Large refactor, migration, concurrency, data model, irreversible deploy, production impact | Consult before locking the plan; consult again before done if risk remains |
| Same error pattern repeats after two credible attempts | Consult before another speculative fix |
| No advisor model/tool, unsupported main model, disabled advisor, or non-Claude harness | Do not call; do not ask the user to configure it unless they requested advisor setup |
| Small formatting change, simple command output, obvious typo, short stable Q&A, one-step plan, or ordinary task planning | Do not consult |

## Operating Rules

1. Use this skill only inside Claude Code. If the current harness is Codex, Gemini CLI, Cursor, OpenCode, or unknown, exit the skill immediately.
2. Treat the callable advisor tool in the current Claude Code session as the strongest signal that an advisor model is configured. The helper script only checks visible settings and cannot detect every session override.
3. Do not call the advisor just because it exists. The consult must have a concrete planning, review, risk, or debugging reason.
4. For mandatory categories, gather the relevant files, diffs, logs, tests, docs, and constraints first. A low-context advisor call is usually worse than a later evidence-backed call.
5. For high-level planning validation, require a substantial plan with several dependent steps or phases and meaningful blast radius. Draft the actual plan first: goal, phases, files/subsystems, assumptions, risks, rollback or stop points, and verification. Consult the advisor before starting implementation. Do not use the advisor for ordinary planning, small todo lists, or choosing the next local command.
6. When consulting, make the current uncertainty explicit in normal assistant text before the call. Do not try to pass hidden arguments; Claude Code's advisor receives the conversation context server-side.
7. Apply advisor guidance critically. If local evidence contradicts it, trust the evidence, explain the conflict, and proceed with the verified path.
8. Never read secrets, credentials, or private data solely to enrich the advisor context. The advisor receives the full conversation and tool results, so minimize sensitive transcript content.

## Reading Guide

| Need | Read |
|---|---|
| Decide whether a task requires advisor consultation | `references/advisor-policy.md` |
| Understand Claude Code advisor setup, requirements, model pairing, cost, caching, and failure modes | `references/claude-code-mechanics.md` |
| Check local Claude Code settings without invoking advisor | `scripts/detect_advisor_config.py` |

## Gotchas

1. Advisor configuration is session-sensitive. A saved `advisorModel` is not the same as a callable advisor in the current request if the main model, provider, organization allowlist, or disable flag blocks it.
2. The advisor reads the full conversation, including tool results. Do not pull sensitive files into context just to get a better second opinion.
3. Calling too early wastes the strongest review moment. For reviews and security work, inspect the real code first, then consult.
4. Plan validation is for substantial multi-step plans only. It happens after the plan is concrete, not while brainstorming, and never for ordinary planning or small todo lists.
5. The advisor is not a substitute for tests, static analysis, or local evidence. It is an extra reasoning pass.
6. Claude Code controls advisor timing. This skill increases pressure to consult at the right moments, but it must still respect disabled or unconfigured advisor sessions.

---
name: codex-subagents
description: "Codex CLI/App only passive delegation policy. Use in Codex when the user asks for subagents, delegation, parallel agents, one-agent-per-point reviews, multi-agent plans, or custom Codex agents. Spawn bounded subagents when useful; do NOT use outside Codex CLI/App, without explicit subagent/parallel-agent authorization, for trivial tasks, or as a fixed-model policy."
compatibility: "Requires Codex CLI or Codex app with subagent workflows available. No fixed model requirement. Optional helper scripts require python3."
metadata:
  version: "1.0.0"
  short-description: "Use Codex subagents correctly"
  openclaw:
    category: "development"
    requires:
      bins: [python3]
references:
  - delegation-policy
  - codex-mechanics
  - patterns
  - source-notes
---

# codex-subagents

Use Codex subagents deliberately for authorized parallel delegation while keeping the main thread clean, accountable, and model-neutral.

## Decision Tree

Before applying this skill, answer these gates in order:

- Not running in Codex CLI or Codex app:
  Stop. Do not simulate Codex subagents with Claude advisor, web search, another model, another harness, or manual background prompts.

- Running in Codex IDE extension, Codex web/cloud, or an unknown Codex-like surface:
  Stop. The public docs currently surface subagent activity in Codex CLI and Codex app; update this skill from official docs before extending it to another surface.

- User did not explicitly ask for subagents, parallel agents, delegation in parallel, one agent per point, multi-agent work, or custom Codex agents:
  Do not spawn subagents. Continue normally. Mention subagents only if the user asks how to speed up or parallelize the work.

- User did explicitly ask for subagents or parallel agent work:
  Read `references/delegation-policy.md`, do a short local plan first, keep the immediate critical-path task local, and delegate only bounded work that can run independently.

- User asks about setup, custom agents, `/agent`, sandbox behavior, `[agents]` config, or why a subagent did or did not run:
  Read `references/codex-mechanics.md` before answering or editing config.

- User asks for prompt examples or repeatable delegation shapes:
  Read `references/patterns.md` and adapt the closest pattern.

## Quick Reference

| Situation | Action |
|---|---|
| Parallel code review requested | Spawn focused reviewers after inspecting the diff shape; split by risk category and ask for file-referenced findings |
| Large research or codebase exploration requested | Spawn read-only explorers for independent questions; keep synthesis in the main thread |
| Multi-step implementation requested | Split only when write sets are disjoint; assign ownership and tell workers not to revert others |
| Tests/log triage can run beside implementation | Delegate the concrete test/log question while the main agent continues non-overlapping work |
| Security, permissions, sandboxing, secrets, or production data | Gather evidence first, then use specialized subagents only if they reduce risk without exposing unnecessary sensitive content |
| Recurring failure after two credible attempts | Delegate an independent diagnostic pass before another speculative fix |
| Completion check for risky work | Spawn a reviewer/checker pass before declaring done, then verify locally |
| No explicit subagent request | Do not spawn; subagent workflows are not automatic |
| Unknown or non-Codex harness | Exit the skill and do not emulate subagents |

## Operating Rules

1. Use this skill only in Codex CLI or Codex app sessions where subagent workflows are available.
2. Treat explicit user authorization as mandatory. "Be thorough", "research deeply", or "review carefully" is not enough by itself.
3. Plan before delegating. Identify the immediate task the main agent should do locally and the sidecar tasks that can run in parallel.
4. Prefer subagents for read-heavy, noisy, or independently verifiable work: exploration, triage, tests, log analysis, review, summarization, and completion checks.
5. Be cautious with write-heavy parallelism. Use it only when each worker has a clear, disjoint file/module ownership boundary.
6. Keep model choice open-ended. Inherit the parent session model by default; steer capability, speed, or reasoning effort only when the task actually needs it and avoid hard-coded model-version policy.
7. Keep sandbox and approval expectations explicit. Subagents inherit the parent sandbox policy, and child approval failures can surface back to the parent workflow.
8. Prompt subagents for distilled outputs: findings, changed files, commands run, confidence, blockers, and exact file references. Do not ask them to paste noisy logs unless needed.
9. Integrate results critically. The main agent remains responsible for final decisions, conflict resolution, local verification, and the user-facing answer.
10. Close or ask Codex to close completed agent threads when they are no longer needed.

## Reading Guide

| Need | Read |
|---|---|
| Decide whether to spawn, skip, split, wait, or review | `references/delegation-policy.md` |
| Codex availability, built-in/custom agents, sandbox inheritance, `/agent`, and `[agents]` config | `references/codex-mechanics.md` |
| Prompt templates for reviews, research, implementation, triage, and completion checks | `references/patterns.md` |
| Official-source summary and refresh points | `references/source-notes.md` |
| Conservative local Codex preflight | `scripts/detect_codex_surface.py` |

## Gotchas

1. Subagents are explicit opt-in in Codex. A skill can pressure correct use after authorization, but it should not silently spawn agents for ordinary work.
2. More agents can make work slower or more expensive when tasks are coupled. Parallelism helps only when the work can proceed independently.
3. Recursive delegation is easy to overdo. Keep spawned agents shallow unless the user explicitly needs deeper fan-out and understands the cost.
4. A subagent summary is evidence, not proof. Verify high-risk claims against files, tests, or docs before finalizing.
5. Model names age. Write policy around task demands and inheritance rather than freezing a specific model version into the skill.
6. Sandbox permissions are inherited. A read-only or approval-gated parent workflow can still block a child action, especially in non-interactive runs.

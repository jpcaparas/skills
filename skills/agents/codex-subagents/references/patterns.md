# Delegation Patterns

Use these patterns as starting points. Adapt scope, file paths, and output contracts to the actual task.

## Parallel PR Review

Use after inspecting the diff enough to know the risk categories.

```text
Review this branch with parallel Codex subagents.
Spawn one subagent for security and permissions risks, one for correctness and bugs, one for test gaps, and one for maintainability.
Each subagent should inspect the relevant diff and return only actionable findings with severity, file references, and confidence.
Wait for all agents, then synthesize findings by severity. Do not let subagents edit files.
```

## Codebase Exploration

Use when questions are independent and read-heavy.

```text
Delegate codebase exploration in parallel.
Spawn one explorer to map where <feature/state> is created, one explorer to map consumers, and one explorer to identify tests or fixtures that cover it.
Each explorer should return exact file references, the shortest path through the code, and unanswered questions.
Do not edit files. The main thread will synthesize.
```

## Test Or Log Triage

Use when logs are noisy and can be split by suite, failure, or platform.

```text
Use parallel subagents for test triage.
Spawn one agent per failing suite: <suite A>, <suite B>, <suite C>.
Each agent should inspect the command output and relevant tests, identify the likely root cause, and propose one focused verification command.
Do not edit files unless explicitly assigned a disjoint fix scope.
```

## Disjoint Implementation

Use only when write ownership is clear.

```text
Implement this plan with parallel workers using disjoint ownership.
Worker 1 owns <module/files>. Worker 2 owns <tests/files>. Worker 3 owns <docs/files>.
Each worker may edit only its owned scope unless it reports a blocker first.
Workers are not alone in the codebase: do not revert or overwrite edits made by others.
Return changed files, commands run, remaining risks, and any integration notes.
The main thread will inspect and integrate all changes.
```

## Independent Diagnostic Pass

Use after two credible attempts failed or when root cause is ambiguous.

```text
The same failure survived two plausible fixes. Spawn one diagnostic subagent to independently analyze the failure from current files and logs.
Do not edit files.
Return the most likely root cause, evidence, rejected hypotheses, and the next verification command.
```

## Risky Completion Check

Use before declaring done on broad or high-risk work.

```text
Before finalizing, spawn a checker subagent for a completion audit.
Scope: <changed files / objective / tests run>.
Check whether every explicit requirement is satisfied, whether verification is strong enough, and whether any changed file violates the requested boundaries.
Return blockers first, then residual risks. Do not edit files.
```

## Custom Agent Authoring

Use when the user asks to create a reusable Codex custom agent.

```text
Create a Codex custom agent TOML for <role>.
Keep it narrow and opinionated.
Required fields: name, description, developer_instructions.
Do not pin a model unless the user explicitly asks or project policy requires it.
Prefer inherited settings and only override sandbox, MCP servers, skills, or reasoning effort when the role needs that boundary.
```

## Summary Format

Ask subagents to return compact, structured summaries:

```text
Return:
- Result: complete / partial / blocked
- Findings or changes, ordered by severity or dependency
- File references
- Commands run and outcomes
- Confidence and verification gaps
- Changed files, if any
```

This format keeps noisy exploration out of the main context while preserving enough evidence for integration.

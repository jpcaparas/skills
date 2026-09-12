# Delegation Policy

Use this reference to decide when Codex subagents should be spawned, how to divide the work, and how to integrate their results.

## Spawn Gate

Spawn subagents only when all conditions are true:

1. The session is Codex CLI or Codex app.
2. The user explicitly asked for subagents, delegation, parallel agents, one agent per point, multi-agent work, or equivalent wording.
3. The work has independent slices that can run in parallel without blocking the main agent's immediate next step.
4. The delegated task can be described with a concrete output contract.
5. The expected value outweighs extra token use, latency, approval overhead, and integration cost.

If any condition fails, do the work locally. Do not simulate subagents with another harness feature.

## Strong Use Cases

| Category | Examples | Timing |
|---|---|---|
| Parallel review | Security, correctness, test gaps, maintainability, accessibility, API compatibility | After initial diff/code shape is known; before final findings |
| Codebase exploration | "Find where auth state is created", "Map consumers of this event", "Identify route handlers" | As soon as questions are independent and the main agent can keep working |
| Test and log triage | Separate failing suites, flaky tests, stack traces, CI logs, coverage gaps | While implementation or local inspection continues |
| Research and summarization | Large docs, multiple packages, release notes, migration notes | When sources can be split and summarized independently |
| Multi-step implementation | Separate modules, platforms, packages, or docs/tests slices | Only after disjoint write ownership is clear |
| Recurring failure | Same error survived two credible attempts, or root cause is ambiguous | Before another speculative fix |
| Risky completion check | Security work, large generated changes, broad refactors, production workflows | Before declaring done, after local verification evidence exists |

## Skip Conditions

Do not spawn subagents for:

- Non-Codex or unknown harnesses.
- Codex surfaces outside CLI/App unless this skill has first been updated from official docs to support that surface.
- Work without explicit user authorization for subagents or parallel delegation.
- Trivial one-step tasks, formatting-only edits, simple command output, stable Q&A, or ordinary planning.
- Work where the next main action is blocked on the delegated result.
- Tasks that require reading secrets or private data solely to enrich a subagent prompt.
- Parallel code edits with overlapping files or unclear ownership.
- Cases where local tests, compiler errors, or explicit user instructions mechanically determine the next action.

## Delegation Plan

Before spawning, write a compact local plan:

1. Main-thread responsibility: the immediate task the main agent will do locally.
2. Subagent slices: independent questions or owned write sets.
3. Output contract: exact summary format, file references, commands run, confidence, blockers, and changed files if editing.
4. Wait policy: whether to wait for all agents before continuing or continue local work and integrate later.
5. Risk controls: sandbox expectations, no-secrets boundary, non-overlap instructions, and verification commands.

Keep the plan short. It is there to prevent accidental delegation of the critical path.

## Prompt Packet

Every subagent prompt should include:

- The concrete task and success criteria.
- The files, directories, commands, or sources it owns.
- What not to touch or duplicate.
- The expected final format.
- Whether it may edit files.
- For write tasks, a reminder that other agents may be working in the codebase and it must not revert their edits.
- For review tasks, a severity or priority rubric.

Example structure:

```text
You own <bounded task>. Do not edit files.
Inspect <scope>. Answer only these questions:
1. ...
Return: findings with file references, confidence, and any verification gaps.
Do not repeat raw logs unless they are essential evidence.
```

## Write-Heavy Work

Use parallel workers for implementation only when all of these are true:

- Each worker owns a disjoint set of files, modules, packages, docs, or tests.
- The main agent can integrate changes without semantic merge conflicts.
- The prompt names the owned scope and tells the worker not to revert others.
- Verification can prove the combined behavior, not just each slice in isolation.

If ownership overlaps, keep implementation local and use subagents for review or research instead.

## Waiting And Integration

Avoid waiting by reflex. After spawning, continue non-overlapping local work unless the next action genuinely needs the subagent result.

When results return:

1. Read the summary first, not raw transcripts.
2. Check file references and changed-file lists.
3. Resolve conflicts or contradictory findings with local evidence.
4. Run focused tests, typechecks, linters, or validators that cover the integrated behavior.
5. Report subagent findings as supporting evidence, not as a substitute for verification.

## Completion Gate

Before declaring done on risky delegated work, confirm:

- Every requested subagent either completed, was intentionally skipped, or has a documented blocker.
- All changed files from workers were inspected by the main agent.
- No worker changed outside its ownership scope without explanation.
- Verification covers the integrated result.
- The final answer distinguishes confirmed facts from subagent hypotheses.

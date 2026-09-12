# Advisor Policy

Use this reference to decide when Claude Code's advisor should be consulted and what evidence should exist before the call.

## Consultation Gate

Consult the advisor only when all conditions are true:

1. The harness is Claude Code.
2. A callable advisor tool is available in this session or advisor configuration is otherwise confirmed.
3. The task has real uncertainty, risk, or independent-review value.
4. You have gathered enough local evidence for the advisor to evaluate the problem usefully.

If any condition fails, skip the advisor and continue with normal engineering verification.

## Mandatory Consults

Call the advisor for these categories once initial context is available:

| Category | Examples | Timing |
|---|---|---|
| Security-sensitive work | Authentication, authorization, secrets, sandboxing, prompt injection, SSRF, SQL injection, supply chain, permission models, production data exposure | Before finalizing design or edits; again before final if residual risk remains |
| Code review | User asks for review, PR review, diff audit, "second pair of eyes", security review, architecture review | Before final findings, after inspecting the diff/code |
| High-level planning validation | Big multi-step implementation plans, migration plans, multi-agent handoffs, broad refactor plans, cross-module sequencing, or plans that commit the agent to several dependent steps across meaningful surface area | After the draft plan is concrete and before implementation begins |
| High-stakes architecture | Cross-service contracts, migrations, data loss risk, concurrency, irreversible deploys, billing/payments, privacy, compliance | Before committing to the plan |
| Complex refactors | Broad module moves, behavior-preserving rewrites, public API changes, test-suite reshaping | After mapping the existing behavior and before editing broadly |
| Recurring failures | Same test/build/runtime error survives two credible attempts or the failure mode is ambiguous | Before the next speculative fix |
| Completion checks for risky work | Security fixes, code reviews, production workflows, migrations, large generated changes | Before declaring done |

For security and code review, treat the advisor call as required if the advisor is configured. If no advisor is configured, do not call; document the lack of advisor only when the final answer would otherwise imply independent review happened.

## Optional Consults

Consult if it will change the outcome:

- Multiple valid implementation strategies with meaningful tradeoffs.
- The local codebase points in conflicting directions.
- The user asks for extra assurance but not a formal review.
- You are about to choose between speed, correctness, cost, or maintainability in a way that affects future work.
- The task spans enough files or subsystems that a planning mistake would be expensive.

## Skip Conditions

Do not call the advisor for:

- Non-Claude Code harnesses.
- Sessions with no configured advisor model or no callable advisor tool.
- Simple command execution, one-line fixes, formatting-only changes, typo fixes, or stable factual answers.
- Ordinary planning, small todo lists, one-step plans, two-step plans, or "what should I do next?" prompts without substantial multi-step implementation risk.
- Work where the correct action is mechanically determined by tests, compiler errors, or explicit user instructions.
- Prompts asking how to configure advisor itself, unless the advisor is already configured and the question is high-stakes.
- Cases where the advisor would need secrets or private data you have not already needed for the task.

## Evidence Packet

Before consulting, gather enough context for the transcript to answer:

- What the user asked for and what "done" means.
- Relevant files, diffs, tests, logs, errors, and configuration.
- The current hypothesis or proposed plan.
- For plan validation: several dependent phases, target files/subsystems, assumptions, risk controls, stop points, and verification commands.
- The specific risk, uncertainty, or review question.
- Constraints from the user, repository, runtime, or deployment environment.

Do not over-gather. The advisor receives the full transcript, and every advisor call sends conversation context to the advisor model.

## How To Phrase The Call

Use a concise lead-in before invoking the advisor. Good examples:

- "I have inspected the auth middleware and token refresh path. I am consulting the advisor on whether this fix closes the privilege escalation without breaking session renewal."
- "I have drafted the implementation plan and mapped the affected subsystems. I am consulting the advisor before starting work to check sequencing, missing risks, and verification gaps."
- "The test failure has survived two plausible fixes. I am consulting the advisor before trying another approach."
- "I have the review findings drafted. I am consulting the advisor for a second pass on severity and missed security issues."

Avoid vague calls like "advisor, thoughts?" because the transcript may contain a lot of unrelated context.

Do not use planning language to bypass the skip rules. "Plan the next edit", "make a quick checklist", and "outline the next command" are ordinary planning unless the work requires several dependent phases across meaningful code, data, deployment, security, or review surface area.

## After The Advisor Returns

1. Compare the advice against local evidence.
2. Apply recommendations that fit the code and constraints.
3. If advice conflicts with files, tests, docs, or observed behavior, state the conflict and use the verified evidence.
4. If the advisor found a new risk, investigate it before finalizing.
5. Do not mention advisor details in the final answer unless it affects user-facing confidence, risk, or a skipped mandatory consult.

## See Also

- `references/claude-code-mechanics.md`

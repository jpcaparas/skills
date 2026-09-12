# Secure AI Agent Review Workflow

Use this workflow when reviewing a design, repository, pull request, incident, or production AI agent deployment.

## Output Shape

Start reviews with findings, not a long summary. Use this format:

```text
Findings
- [Severity] Title
  Evidence: file, endpoint, prompt, workflow, or config observed
  Risk: concrete failure mode
  Fix: specific control or implementation change

Open questions
- Missing fact needed to confirm risk or scope

Residual risk
- What remains after the proposed fix
```

## Severity

| Severity | Use when |
|----------|----------|
| Blocker | The agent can expose sensitive data, execute unapproved high-impact actions, bypass authorization, or continue after partial failure |
| High | The design relies on prompt-only controls, broad tool permissions, unvalidated model output, unsafe data handling, or missing rollback for consequential actions |
| Medium | A required control exists but is incomplete, unaudited, weakly tested, client-side only, or missing operational evidence |
| Low | Documentation, inventory, monitoring, usability, or maintainability gaps reduce confidence but do not create an immediate exploitable path |

## Review Phases

1. Define the AI surface.
   - List model providers, model versions, prompts, system instructions, RAG sources, vector stores, tools, plugins, memory, state stores, jobs, and downstream APIs.
   - Identify every place untrusted text can enter: user prompt, web page, document, email, issue, ticket, chat, transcript, retrieved chunk, tool output, or another model's response.

2. Draw trust boundaries.
   - Separate server-side trusted controls from client-side hints.
   - Mark boundaries between model output and interpreters such as SQL, shell, code execution, HTML rendering, workflow engines, and third-party APIs.
   - Verify all network calls use authenticated, certificate-validated endpoints.

3. Classify data.
   - Identify personal data, secrets, credentials, business-confidential material, regulated data, and user-provided content.
   - Confirm the model receives only the minimum fields needed for the task.
   - Check whether consent, retention, deletion, and logging obligations are explicit.

4. Inventory capabilities.
   - List every tool, permission, token, API scope, file path, database role, and external side effect the agent can reach.
   - Confirm allowlists are explicit and narrow.
   - Confirm credentials are scoped to the agent, not borrowed from an admin or broad user account.

5. Tier actions by risk.
   - Low: read-only, reversible, no sensitive data, no external side effect.
   - Medium: writes internal state, handles moderately sensitive data, or triggers recoverable automation.
   - High: sends communications, changes records, moves money, deletes data, executes code, grants access, calls external systems, or processes highly sensitive data.
   - High-risk actions need human approval or an equivalent policy-approved control.

6. Inspect validation.
   - Inputs should be length-limited, typed, schema-checked, and rejected when invalid.
   - Model outputs should be parsed into typed schemas and validated before downstream use.
   - Malicious or malformed input should be rejected, not "cleaned up" by the model.

7. Inspect workflow safety.
   - Look for idempotency keys, transaction boundaries, dry-run modes, preview-before-send flows, locks, sequencing, and retry limits.
   - Verify partial failures roll back or stop from a known safe state.
   - Confirm irreversible paths are avoided when a reversible path can satisfy the user.

8. Inspect observability.
   - Logs should cover significant inputs, decisions, tool calls, approvals, outputs, errors, policy violations, and telemetry.
   - Sensitive data should be redacted.
   - Alerts should cover anomaly patterns, not only hard errors.

9. Inspect supply chain and deployment.
   - Pin or record model versions where behavior matters.
   - Keep frameworks, SDKs, dependencies, prompts, and infrastructure under version control.
   - Verify model artifacts, datasets, retrieval indexes, and deployment packages have integrity controls where applicable.

10. Test safety regression paths.
   - Add tests for prompt injection, poisoned retrieval content, invalid structured output, tool denial, authorization failure, rollback, and rate limiting.
   - Re-run them after prompt, model, dependency, retrieval, or permission changes.

## Evidence Checklist

Ask for or inspect:

- architecture diagram or call graph
- prompt templates and system instructions
- model/provider configuration and model version
- tool registry and permission policy
- data classification and redaction policy
- RAG ingestion and retrieval code
- output schema validation
- authorization checks for each action
- rate limits and token budgets
- transaction and rollback behavior
- logs, metrics, alerts, and dashboards
- safety regression tests
- incident response and decommission plans

## Exception Handling

If a control does not apply, document:

- the control
- why it does not apply
- compensating controls
- owner
- expiry or review date
- risk accepted

Do not silently skip a control because it is inconvenient.

## Done Criteria

A review is complete when:

- every AI input, output, tool, credential, and side effect has an owner and a control
- high-risk actions have explicit approval or a documented equivalent
- sensitive data flow is minimized, consented, and logged safely
- model output cannot directly drive shell, code, SQL, file, API, or UI sinks without validation
- failures stop, roll back, or require deliberate recovery
- monitoring and tests can detect safety regressions

See also: `references/controls.md`, `references/threat-model.md`, and `references/gotchas.md`.

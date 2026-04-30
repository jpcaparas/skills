# Gotchas

Use this file when a design looks safe on paper but lacks enforceable controls.

## Prompt-Only Security

Symptom: The agent has broad tool access, and the main safety measure is an instruction such as "do not delete data."

Risk: Prompt injection or unexpected behavior can bypass the instruction.

Fix: Move controls outside the model: allowlists, authorization checks, schema validation, rate limits, approval gates, and rollback.

## The Validator Is Another Model

Symptom: A second model judges whether the first model's input or output is safe.

Risk: The validator can be manipulated, drift, or fail open.

Fix: Use deterministic validation for schemas, types, length, permissions, allowlists, and resource limits. Model-based classifiers can supplement but should not be the only control for high-impact decisions.

## Wildcard Tools

Symptom: The tool list includes broad shell, browser, file-system, database, or API access.

Risk: A small prompt failure becomes a broad production capability.

Fix: Replace wildcard tools with narrow named actions and validated arguments.

## Client-Side Guardrails

Symptom: The UI blocks unsafe actions, but the backend accepts direct requests from the agent workflow.

Risk: Attackers or automation bypass the UI.

Fix: Enforce safety and authorization on the server side for every action.

## Silent Safety Warnings

Symptom: Safety filters, policy checks, or tool denials log warnings but do not fail tests or alert owners.

Risk: Warnings become ignored production vulnerabilities.

Fix: Treat safety warnings as errors until triaged. Add alerting and CI coverage.

## Log Leakage

Symptom: Full prompts, retrieved documents, tool outputs, secrets, or user records are persisted for debugging.

Risk: The observability system becomes a sensitive data store.

Fix: Log event metadata and redacted payloads by default. Require explicit approval for raw sensitive traces.

## RAG Instruction Smuggling

Symptom: Retrieved chunks are inserted into prompts without clear data boundaries.

Risk: A poisoned document can instruct the agent to ignore rules, reveal secrets, or misuse tools.

Fix: Treat retrieved content as untrusted data. Record provenance, scan ingestion sources, delimit chunks, and test injection cases.

## Unsafe Model Updates

Symptom: The model alias changes, or a provider silently updates behavior, and tests only cover happy paths.

Risk: Output formats, refusal behavior, or safety characteristics change after deployment.

Fix: Pin behavior-sensitive versions where possible. Run safety and structured-output regression tests before rollout.

## Human Approval Theater

Symptom: Approval is requested after the action is effectively committed, or the approval screen hides the concrete action.

Risk: The human cannot make an informed or timely decision.

Fix: Approval must happen before execution and show the exact action, target, data, risk, and rollback implications.

## Overbroad "User Consent"

Symptom: A general product terms checkbox is treated as permission for every model use, log retention, or fine-tuning path.

Risk: Privacy and trust failures.

Fix: Track consent specific to the processing purpose and data category. Store evidence.

## False Confidence From Pattern Scans

Symptom: A heuristic scanner returns no findings, so the system is considered safe.

Risk: Design flaws rarely match a regex.

Fix: Use scanning as a triage aid, then perform the review workflow in `references/review-workflow.md`.

## Shared Mutable Agent State

Symptom: Agent memory or workflow state carries across users, tasks, or retries without explicit initialization.

Risk: Data leakage, stale context, and unpredictable decisions.

Fix: Initialize state explicitly. Prefer immutable state transitions and scoped memory.

See also: `references/implementation-patterns.md` and `references/threat-model.md`.

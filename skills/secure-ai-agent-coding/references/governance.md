# Governance And Lifecycle

Use this reference for production readiness, organizational controls, and long-running AI systems.

## Inventory

Maintain a current inventory of:

- AI features and agents
- model providers and model versions
- prompts, instruction files, and policy files
- tools, plugins, APIs, and scopes
- datasets, vector stores, embeddings, and retrieval indexes
- owners and on-call contacts
- deployment locations
- documentation links
- credentials and rotation schedule
- safety tests and monitoring dashboards

Audit the inventory at least annually, and after major system changes.

## Model And Framework Updates

Model updates can change output format, safety behavior, refusal behavior, latency, or cost without a normal code diff.

Before changing a model, SDK, framework, embedding model, retrieval strategy, or prompt:

1. Record the current version and intended target.
2. Run functional tests.
3. Run safety regression tests.
4. Compare structured output contracts.
5. Check cost and latency budgets.
6. Stage rollout behind a controlled release path.
7. Keep a rollback option.
8. Document the decision.

Avoid both extremes: never patching fast-moving AI dependencies, and blindly updating supply-chain-sensitive components without validation.

## Data, Consent, And Privacy

For user data:

- Verify consent before processing.
- Store consent records in a system of record.
- Minimize fields sent to models and providers.
- Avoid raw production data in development, demos, tests, and fine-tuning unless properly anonymized and approved.
- Use purpose-built anonymization or synthetic data generation for test sets.
- Document sensitive data flows into and out of the AI system.
- Encrypt sensitive data in transit and at rest.
- Define retention and deletion behavior for prompts, transcripts, embeddings, logs, and generated outputs.

## Credentials And Access

Use:

- a secrets manager
- commit-time secrets scanning
- dedicated service accounts
- narrow scopes
- MFA for administrative accounts
- key rotation
- immediate revocation path after suspected compromise
- secure session tokens with scope and expiry

Avoid:

- personal admin credentials for agent execution
- broad workspace scopes
- long-lived unscoped tokens
- credentials in prompts, logs, traces, or screenshots

## Operational Readiness

Before production launch, confirm:

- high-impact actions require approval or equivalent accepted control
- monitoring covers safety denials, unexpected behavior, prompt attacks, tool errors, data access anomalies, and volume spikes
- alerts have owners and thresholds
- incident response includes stopping agents, revoking credentials, preserving evidence, and restoring from known safe state
- business continuity and disaster recovery plans include AI dependencies
- administrators receive a hardening guide if they operate the system
- user-facing authentication and abuse defenses meet the risk level

## Decommissioning

When retiring an AI system:

1. Remove external access.
2. Revoke model, tool, API, and data credentials.
3. Disable scheduled jobs and automations.
4. Archive prompts, configs, tests, and incident-relevant docs.
5. Delete or retain data according to policy.
6. Remove or rebuild vector indexes as needed.
7. Update inventory and owner records.
8. Communicate downstream integration changes.

An abandoned agent with live credentials remains a security risk.

## Compliance And Frameworks

Use established frameworks and organizational policies rather than inventing a private compliance model inside a feature team. Relevant examples may include:

- OWASP Top 10 for LLM Applications
- NIST AI Risk Management Framework
- MITRE ATLAS
- local privacy law and sector-specific obligations
- internal AI safety and security standards

When the task requires legal interpretation, involve legal or compliance owners. The engineering role is to surface the data flows, controls, evidence, and residual risks clearly.

See also: `references/controls.md`, `references/threat-model.md`, and `references/gotchas.md`.

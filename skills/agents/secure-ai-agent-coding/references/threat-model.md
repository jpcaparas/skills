# AI Agent Threat Model

Use this reference when designing a new AI system or reviewing one that already exists.

## Assets

Track these assets explicitly:

- user data and consent records
- prompts, system instructions, and policy files
- model provider credentials and admin accounts
- tool credentials, API tokens, and service accounts
- vector stores, embeddings, datasets, and retrieved documents
- agent memory and workflow state
- logs, traces, transcripts, and telemetry
- generated code, files, database records, emails, messages, and external transactions
- model versions, framework versions, SDKs, plugins, and deployment artifacts

## Trust Boundaries

Draw boundaries around:

- browser or client to server
- user-controlled text to prompt builder
- retrieved content to model context
- model output to parser
- parsed model intent to authorization layer
- authorization layer to tool execution
- tool output back into the model
- logs and traces to storage or analytics systems
- non-production to production

Every crossing needs validation, authorization, encoding, redaction, or monitoring depending on the direction and risk.

## Threat Scenarios

| Threat | Scenario | Controls |
|--------|----------|----------|
| Prompt injection | A document or user message asks the model to ignore prior instructions or reveal secrets | Delimit untrusted content, separate instructions from data, constrain tools, validate output |
| Tool misuse | The model calls a permitted tool for an unauthorized purpose | Per-action authorization, allowlisted targets, human approval, audit logs |
| Data poisoning | A hostile document enters a retrieval index and influences future agent behavior | Ingestion checks, source allowlists, provenance, quarantine, rebuild process |
| Data exfiltration | Prompt or tool output includes sensitive data the user should not receive | Data classification, minimization, output filtering, authorization checks |
| Training data extraction | A user tries to recover private or proprietary content from model behavior | Provider controls, output monitoring, red-team tests, data minimization |
| Model inversion | An attacker probes outputs to infer sensitive model inputs or embeddings | Rate limits, monitoring, privacy controls, minimized embeddings metadata |
| Jailbreak | A user tries to bypass safety controls through adversarial language | Defense in depth, content filters, tool limits, safety evals |
| Denial of service | Attackers cause excessive token use, tool calls, retries, or external requests | Budgets, rate limits, retry caps, anomaly alerts |
| State confusion | Stale memory, mutable shared state, or cross-user context causes unsafe actions | Explicit state initialization, immutable transitions, scoped memory, locks |
| Race condition | Multiple agents or jobs modify shared resources out of order | Locking, idempotency, sequencing, transactional writes |
| Supply chain compromise | A model, SDK, plugin, dataset, or deployment artifact is tampered with | Inventory, version pinning, integrity checks, trusted sources, staged updates |
| Endpoint abuse | AI endpoints bypass normal API protections | Authentication, authorization, CSRF/CORS controls, TLS, monitoring |

## Action Risk Tiers

Use the highest applicable tier.

| Tier | Description | Examples | Minimum control |
|------|-------------|----------|-----------------|
| Low | Read-only or reversible, no sensitive data, no external side effect | Summarize public docs, draft private note | Input validation, output validation, logging |
| Medium | Internal write, recoverable action, moderate sensitivity | Create ticket, update draft, write internal note | Authorization, schema validation, rate limit, audit |
| High | External side effect, sensitive data, irreversible action, code execution, money, access, deletion | Send email, charge card, grant role, delete record, run shell | Human approval or accepted equivalent, scoped credentials, rollback, monitoring |
| Critical | Safety, legal, regulated, physical, medical, financial, or broad customer impact | Execute production migration, release agent with admin access | Formal risk acceptance, security review, staged rollout, incident plan |

## Design Questions

Ask these before implementation:

- What is the agent allowed to do, and what is explicitly out of scope?
- Which inputs are untrusted, and how are they validated before model use?
- What data is sensitive, and can the model complete the task with less?
- Which actions can affect other people, money, records, access, or production?
- Which controls run server-side and cannot be bypassed by client changes?
- Which permissions are needed only temporarily?
- How does the system stop after unexpected behavior?
- What can be rolled back, and what requires human approval before execution?
- How are prompts, models, data sources, and tools versioned?
- How will monitoring detect abuse, drift, or safety regressions?

## Threat Model Deliverable

Produce:

- one-paragraph system summary
- asset list
- trust-boundary diagram or bullet list
- action risk table
- top threat scenarios
- controls mapped to each scenario
- residual risks and owners
- tests or monitors required before launch

See also: `references/review-workflow.md` and `references/controls.md`.

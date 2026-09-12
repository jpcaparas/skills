# Control Catalog

Use this catalog as the checklist for new builds and security reviews. Prefer concrete evidence over assurances.

## Prompt And Input Boundary Controls

| Control | Evidence to look for |
|---------|----------------------|
| Treat every external document, message, page, retrieved chunk, and model response as untrusted | Validation and trust-boundary notes in code or design |
| Separate instructions from untrusted data | Prompt templates with clear roles, delimiters, or structured message fields |
| Validate before the model sees data | Type checks, length limits, file type checks, parser validation, content policy checks |
| Reject malicious or malformed input | Explicit reject path, not a model-based "repair" step |
| Minimize context | Only task-relevant fields are sent to the model |
| Use structured inputs and outputs | JSON schema, typed response format, parser, or strict tool schema |

Implementation notes:

- Use prompt templates that make the system instruction immutable from user perspective.
- Put untrusted content in a clearly marked data field, not inside instruction text.
- Avoid asking the model to decide whether safety controls apply to itself.

## Tool And Action Controls

| Control | Evidence to look for |
|---------|----------------------|
| Explicit tool allowlist | Named tool registry, not wildcard access |
| Per-action authorization | Server-side check for the specific action, resource, and user |
| Minimal agent accounts | Dedicated service account with narrow scopes |
| Dynamic least privilege | Access requested only for the current step and released or expired after use |
| Human approval for high-impact actions | Approval record before send, delete, transaction, code execution, access grant, or external write |
| Rate limits everywhere | Limits for API calls, tool invocations, files, tokens, and external requests |
| Reversible action preference | Draft, preview, soft delete, staging, or dry-run path exists |
| Rollback on error | Transaction, compensating action, or explicit stop-and-recover behavior |
| Locking and sequencing | Coordination for shared state, multi-agent flows, and external writes |

Implementation notes:

- Broad access is a design smell even when a prompt tells the model to behave.
- User authentication is only the start. Authorize the exact action at the time it is requested.
- High-impact actions need a human approval gate unless the organization has accepted a tested alternative.

## Output And Downstream Sink Controls

| Sink | Required control |
|------|------------------|
| UI rendering | Encode or sanitize output for the rendering context |
| SQL or database query | Use parameterized queries and reject model-generated query strings unless routed through a constrained builder |
| Shell or system call | Do not execute raw model output; map validated intent to fixed commands and arguments |
| Code interpreter | Sandbox, resource-limit, and gate execution; never run unreviewed high-impact code on privileged systems |
| API call | Validate schema, authorization, idempotency, rate limit, and target allowlist |
| File write/delete | Restrict paths, require preview for destructive changes, and preserve backups where appropriate |

Implementation notes:

- Treat AI output as another untrusted input.
- Validate output shape and meaning before it crosses a trust boundary.
- Prefer intent-to-action mapping over free-form command generation.

## Data Controls

| Control | Evidence to look for |
|---------|----------------------|
| Data classification before model use | Labels or documented classification process |
| Sensitive data minimization | Redaction, tokenization, hashing, field-level selection, or synthetic data |
| Consent tracking | Consent record before processing user data |
| Safe non-production data | No raw production data in development, tests, demos, or fine-tuning without approval and anonymization |
| Encrypted storage and transit | TLS and storage encryption for prompts, logs, vectors, embeddings, and model artifacts |
| RAG ingestion controls | Source allowlist, malware/content checks, provenance, freshness, and deletion strategy |
| Log redaction | Redaction before persistence or export |

Implementation notes:

- Vector stores and embeddings are part of the data system, not a harmless cache.
- Retrieved content can be hostile and should not be allowed to rewrite instructions.
- Prompt and tool logs can contain regulated or proprietary data.

## Operational Controls

| Control | Evidence to look for |
|---------|----------------------|
| Error logging and alerting | Errors, unexpected behavior, safety warnings, tool denials, and policy violations create observable events |
| Anomaly detection | Alerts for request spikes, jailbreak probing, token exhaustion, prompt flooding, unusual tool sequences, and data exfiltration patterns |
| Safety regression tests | CI tests for injection, malformed output, authorization denial, rollback, and rate limiting |
| Incident response | Playbook for stopping agents, revoking credentials, preserving evidence, and restoring service |
| Reusable safety controls | Shared library or platform control rather than per-feature reinvention |

Implementation notes:

- Treat AI safety warnings as engineering errors until triaged.
- Monitor trends and thresholds, not only exceptions.
- A quiet failure is still a failure.

## Supply Chain And Deployment Controls

| Control | Evidence to look for |
|---------|----------------------|
| Model and dependency inventory | Current list of models, versions, SDKs, datasets, tools, owners, deployment locations, and docs |
| Version control for AI behavior | Prompts, markdown instructions, infrastructure, safety policies, and evals are reviewed in version control |
| Safe model updates | Planned rollout, regression testing, rollback path, and documented compatibility decision |
| Integrity verification | Signed or checksum-verified artifacts where model or deployment tampering is plausible |
| Secrets management | Dedicated secrets manager, scanning in commits, rotation, MFA for admin accounts |
| Endpoint security | Authentication, authorization, TLS, CORS/CSRF controls where relevant, rate limits, and monitoring |
| Decommissioning | Access revoked, credentials removed, docs archived, inventory updated |

Implementation notes:

- Fast-moving AI dependencies make update hygiene important, but uncritical auto-updates can also introduce supply chain risk.
- Pin behavior-sensitive model choices or document how compatibility is tested.
- Old agents with live credentials are production systems, even when nobody remembers them.

See also: `references/implementation-patterns.md`, `references/governance.md`, and `references/threat-model.md`.

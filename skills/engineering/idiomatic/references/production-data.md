# Production evidence and data preparation

Read before inspecting production data/infrastructure or planning normalisation. Technical access is not authority. Prefer local schema and approved aggregate evidence until a live read is necessary and authorised.

## Inspect without turning an audit into an incident

Establish the target account/environment, purpose, permitted data classes and read scope. Prefer a read-only role and a replica where suitable; account for replica lag. Verify how the tool enforces read-only behaviour. A method named “query” or an environment variable present in the shell proves neither permission nor isolation.

Start with schema, constraints, migration history and existing operational reports. For data questions, design bounded aggregates or small redacted projections that distinguish the competing explanations. Avoid full exports and `SELECT *`. Inspect the query plan/cost where supported without executing a heavy query; limit execution time, rows and concurrency. A row limit does not make a table scan cheap. Read-only functions, application boot or `EXPLAIN ANALYZE` can still have effects or consume substantial resources.

Profile only relevant invariants: null/missing values, collisions under the proposed normal form, unknown states, orphan references, tenant scope, time zones, soft deletes, historical encoding or queued payload versions. Include the population, observation time and sampling/lag limits. A small sample can reveal a problem but cannot prove its absence. Do not run broad scans until their operational budget and authority are clear.

Report aggregate counts and synthetic examples by default. Keep personal data, secrets and payloads out of chat, fixtures, source control, external documentation tools and the agent handoff. Where a sensitive sample is essential, obtain scoped authority and use the approved storage/retention controls. Never ask for credentials to be pasted into the conversation.

Infrastructure reads should answer a specific dependency question: which code versions run in web and workers, when scheduled work runs, how releases overlap, or whether a restore path is verified. Do not restart workers, flush caches, rotate credentials or apply configuration during discovery. If access is missing, name the query/report needed, its purpose and safe execution constraints; continue independent local work.

## Decide whether data must change at all

Do not “normalise” away a domain distinction. Leading zeros, case, whitespace or nulls may encode contractual meaning. Test the proposed rule against producers, readers, vendor identifiers and uniqueness scope. Separate mechanically safe transformations from ambiguous cases requiring owner decisions. Never merge identities or invent a winner for collisions.

Describe before and after with redacted examples, affected counts or an explicitly unknown estimate, and invariants that must hold. Include records that remain unchanged and exceptions that will be quarantined/reported. Explain why an adapter or compatibility reader is insufficient, if recommending a rewrite of stored data.

Order deployment/data work by compatibility rather than aesthetics. For example:

1. Introduce compatible reads and prevent new invalid writes through **all** writers, including imports, integrations and older workers, or agree a controlled write pause.
2. Preview and rehearse remediation on disposable representative data.
3. With specific approval, apply bounded batches and reconcile results.
4. Verify the whole relevant population and live-write behaviour before tightening constraints or switching readers.
5. Remove compatibility code after old versions, queued work and rollback needs are retired.

This is an example of expand–migrate–contract, not an instruction to add dual writes to every system. Dual writes have their own consistency and recovery risks. A smaller in-place operation can be correct when its locking, concurrency and recovery costs are understood.

## Specify a temporary command as an operational tool

Prefer the project's native command/job mechanism so configuration, types, logging and deployment remain familiar. Keep the transformer separable from live execution. Choose a durable migration when every environment needs a versioned schema/data transition; choose a temporary command for controlled operational remediation. Do not hide an unbounded backfill in a request path or deploy hook.

The plan, and implementation when authorised, should cover:

- **Preview:** dry-run by default; exact environment/tenant/filter, selection criteria, before/after counts, collisions, unchanged and rejected records; no secrets in output.
- **Approval:** a reviewable invocation tied to the script revision, target and expected impact. Reconfirm when the transformation, scope or distribution differs materially from the approved preview.
- **Bounded execution:** stable cursor/checkpoint, batch size based on measured load, timeout and pause controls. Avoid offset pagination over a changing set. State how concurrent writers are excluded or checked, and what happens if a row changed since preview.
- **Replay and interruption:** idempotent transformations, transactions at an appropriate scope, a durable progress/changed-ID record and restart semantics. Distinguish safe reprocessing from duplicate external effects. Include a rerun and interruption test.
- **Validation:** independent pre/post queries for invariants and accounting of selected, changed, unchanged, skipped and failed records. A zero exit code or matching total count alone does not establish correctness.
- **Recovery:** approved backup/restore or reversible old-value journal when feasible, with access/retention rules and rehearsal. Irreversible or lossy transformations need an explicit forward-repair plan and stop threshold. Reverting code is not a data rollback; restoring a backup may discard newer valid writes.
- **Lifecycle:** named owner role, run/audit record, temporary command and sensitive-journal retention, removal condition and durable regression checks. Retain what is needed for delayed environments or incident review before deleting “throwaway” tools.

Rehearse collision, no-op rerun, partial failure and concurrent-change cases before requesting live execution. Avoid triggering model observers, emails or webhooks unintentionally; preserve required domain effects explicitly rather than assuming bulk updates and ORM saves are interchangeable.

## The live write gate

Before a live write, show the specific before/after and target population, exact reviewed operation, verification plan, operational window/load controls and recovery limits. Obtain explicit confirmation for that operation even under broad autonomy. If the read scope itself is unclear, pause live inspection too. Continue planning or local rehearsal while approvals are pending.

After execution, report actual counts and invariant results, deviations and delivery state. Missing evidence, ambiguous data or a failed gate blocks dependent tightening/removal; it does not justify guessing, silently broadening the command or retrying a non-idempotent operation.

# Protect behaviour before changing its owner

Use this reference when a proposed alignment touches fragile code. The harness should make one risky change decidable, not become a second implementation of the system.

## Establish the contract, not merely a snapshot

Trace the real entrypoint to the effect. Read relevant tests and history and ask the owner about unexplained rules when needed. Record which expectations come from a consumer contract, an incident, a domain requirement or only observed behaviour. An old test can encode a bug; a green test can omit the failing boundary.

Choose distinguishing cases where a plausible “cleanup” would be wrong. Examples include:

| Fragile boundary | What a naive refactor might lose | Useful evidence |
|---|---|---|
| Vendor acknowledgement | Treat an HTTP success as business acceptance | An approved/synthetic success-status response whose body rejects the operation; assert persisted state and whether retry is allowed |
| Payment/job retry | Repeat an effect after its acknowledgement is lost | Controlled timeout-after-acceptance, duplicate delivery and restart; assert stable operation identity and one external effect |
| Tenant-scoped persistence | Replace a custom lookup with an unscoped ORM helper | Two tenants with colliding business identifiers, including a forbidden access; assert both the returned value and non-disclosure |
| Legacy identifier | Trim whitespace, cast to an integer or change case | Values whose distinctness matters to the vendor; preserve byte-level behaviour where the contract requires it |
| Framework lifecycle | Move registration after the first consumer runs | Test real container/route/job wiring, not just the extracted function |
| Server/client boundary | Move private work into a browser bundle or change rendering/cache semantics | Runtime-appropriate build and request checks, multiple identities and stale/error states |
| Class/file rename | Break queued payloads, stored type names, imports or public URLs | Inspect persisted identifiers and older consumers; test the compatibility bridge before removal |

Pick only risks present in the target flow. Do not require all these cases for every project.

## Make isolation realistic

Keep application decisions behind narrow, application-owned integration contracts. The adapter owns vendor encoding, response interpretation and transport errors; the domain should not need the vendor SDK everywhere. Use the framework's ordinary container, test server, fake transport, fixture loader and database isolation facilities.

Fakes must preserve the troublesome part of the contract. Combine small domain tests with a boundary/contract test of the real adapter against controlled responses. An assertion that a mocked service was called proves neither wire compatibility nor the eventual database state. Disable real emails, webhooks, charges and production queues. Do not mirror production writes to compare implementations.

Sanitisation must preserve the triggering shape: null versus missing, duplicate keys, ordering, time zones, leading zeros, unexpected status/body pairs or historic schema versions. Prefer synthesising those shapes to copying customer records. Record provenance without sensitive payloads.

Establish baseline checks before moving code; choose the smallest harness that would fail for the suspected mistake. Where feasible, demonstrate discrimination with a controlled fault in a disposable copy, then remove it. Do not change a real vendor's state to prove retry behaviour. If no reliable oracle exists, make contract discovery a prerequisite and describe which observations would settle it.

## Use the harness to reduce risk

Keep structural and semantic changes separate. Exercise the same contract before and after extraction or rewiring. Normalise only understood nondeterminism in golden comparisons; blanket snapshot updates or stripping important error fields can conceal regressions.

When a current behaviour is wrong, keep a clearly labelled characterisation until the intended change and its rollout are agreed. For an urgent unsafe behaviour, prioritise an explicitly scoped mitigation rather than requiring preservation indefinitely. Test both the approved new rule and compatibility obligations that remain.

State what the harness cannot establish: sandbox/provider drift, live throughput, replica lag, historical data coverage or old workers still running. Those limits become rollout gates or later discovery, not silent assumptions that the rewrite is safe.

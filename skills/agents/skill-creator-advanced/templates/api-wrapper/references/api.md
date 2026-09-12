# {{API_NAME}} Contract Reference

## Contract Overview

- Style or transport: {{API_CONTRACT_STYLE}}
- Version or compatibility range: {{API_CONTRACT_VERSION}}
- Endpoint, service, or discovery source: {{API_ENTRY_POINT}}
- Input and output encoding: {{API_ENCODING_OR_SCHEMA}}
- Current evidence: {{API_CONTRACT_EVIDENCE}}

Describe the API in its native model. HTTP resources, RPC methods, graph
operations, messages, events, streams, and SDK-only calls need different
terminology and examples.

## Shared Request Context

{{SHARED_REQUEST_CONTEXT}}

Keep this section only for context shared by several operations, such as
metadata, headers, deadlines, version selectors, tenant scope, or content
negotiation. Put operation-specific context with the operation.

## Operation Index

| User intent | Contract operation | Effect | Detailed section |
|-------------|--------------------|--------|------------------|
{{OPERATION_INDEX_ROWS}}

## {{OPERATION_GROUP_NAME}}

### {{OPERATION_NAME}}

**Use when:** {{OPERATION_APPLICABILITY}}

**Effect:** {{OPERATION_EFFECT}}

**Contract form:**

```{{CONTRACT_FENCE_LANGUAGE}}
{{OPERATION_CONTRACT_FORM}}
```

**Inputs:**

| Input | Type or shape | Required | Constraints |
|-------|---------------|----------|-------------|
{{OPERATION_INPUT_ROWS}}

**Success outcome:** {{OPERATION_SUCCESS_CONTRACT}}

**Failure outcomes:** {{OPERATION_FAILURE_CONTRACT}}

**Safest verification:** {{OPERATION_VERIFICATION}}

**Example:**

```{{EXAMPLE_LANGUAGE}}
{{OPERATION_EXAMPLE}}
```

Repeat this operation section for each independently useful operation. If the
contract is HTTP, document methods, media types, and status semantics evidenced
by that API; do not assume JSON, CRUD, deletion, pagination, or `201 Created`.

## Failure Model

{{FAILURE_MODEL}}

Describe the contract's actual failure surface: status or error codes,
structured details, retry eligibility, partial success, stream termination, or
transport failures as applicable. Do not invent an HTTP status table for a
non-HTTP API.

## See Also

- `references/configuration.md` -- access and client setup
- `references/patterns.md` -- supported multi-step workflows
- `references/gotchas.md` -- evidenced contract pitfalls

## Release Gate

Replace every template token, remove unsupported contract concepts, and verify
every example against the pinned contract before release.

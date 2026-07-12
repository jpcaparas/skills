# {{API_NAME}} Supported Workflows

Include a workflow only when the API contract and the skill's invocation
branches require it. Potential examples include collection traversal,
asynchronous completion, event delivery, quota-aware retries, batching, and
idempotency; none is universal.

## Workflow Index

| Workflow | Use when | Read |
|----------|----------|------|
{{WORKFLOW_INDEX_ROWS}}

## {{WORKFLOW_NAME}}

**Use when:** {{WORKFLOW_APPLICABILITY}}

**Do not use when:** {{WORKFLOW_EXCLUSIONS}}

**Contract evidence:** {{WORKFLOW_EVIDENCE}}

### Invariants

{{WORKFLOW_INVARIANTS}}

### Procedure

```{{WORKFLOW_LANGUAGE}}
{{WORKFLOW_EXAMPLE}}
```

### Termination and Success Evidence

{{WORKFLOW_TERMINATION_AND_SUCCESS}}

### Failure and Recovery

{{WORKFLOW_FAILURE_AND_RECOVERY}}

Repeat the workflow section only for independently useful, evidenced patterns.
Co-locate a rule here when only one workflow needs it; move it to a shared
section only when multiple workflows genuinely depend on it.

## Conditional HTTP Retry Note

Keep this section only for an HTTP contract that can return `Retry-After`.
Honor the service contract and the HTTP field syntax: the value can be a delay
in seconds or an HTTP date, and it is not limited to one status code. Combine
it with the API's documented retry eligibility, idempotency guarantees, jitter,
attempt bound, and overall time budget. Never retry every failure blindly.

## See Also

- `references/api.md` -- operation and outcome contracts
- `references/configuration.md` -- access and client setup
- `references/gotchas.md` -- evidenced workflow pitfalls

## Release Gate

Replace every template token, duplicate the workflow skeleton only as needed,
and delete illustrative or unsupported sections before release.

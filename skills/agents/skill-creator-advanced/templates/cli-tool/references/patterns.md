# {{TOOL_NAME}} Supported Workflows

Include a workflow only when it is useful to an invocation branch and verified
against the supported command surface. Pipelines, structured-output parsing,
batch execution, and dry-run flags are contract-specific, not universal.

## Workflow Index

| Workflow | Use when | Effect boundary |
|----------|----------|-----------------|
{{WORKFLOW_INDEX_ROWS}}

## {{WORKFLOW_NAME}}

**Use when:** {{WORKFLOW_APPLICABILITY}}

**Do not use when:** {{WORKFLOW_EXCLUSIONS}}

**Command evidence:** {{WORKFLOW_EVIDENCE}}

### Preconditions and Invariants

{{WORKFLOW_PRECONDITIONS_AND_INVARIANTS}}

### Procedure

```{{COMMAND_FENCE_LANGUAGE}}
{{WORKFLOW_COMMANDS}}
```

### Effects and Authorization

{{WORKFLOW_EFFECTS_AND_AUTHORIZATION}}

### Success Evidence

{{WORKFLOW_SUCCESS_EVIDENCE}}

### Failure and Recovery

{{WORKFLOW_FAILURE_AND_RECOVERY}}

Repeat the section only for distinct workflows. When the tool supports a
preview, plan, validation, or dry-run mode, use it before effects. Otherwise use
the safest disposable or read-only verification available and say that no
native dry-run exists.

## Composition Rules

Keep this section only when composition is supported. Document the actual
output contract and quoting rules before piping to another tool. Do not assume
JSON, a POSIX shell, stable human-readable output, or successful partial
results.

## See Also

- `references/commands.md` -- command and outcome contracts
- `references/configuration.md` -- installation and identity
- `references/gotchas.md` -- evidenced workflow pitfalls

## Release Gate

Replace every template token, duplicate the workflow skeleton only as needed,
and remove illustrative or unsupported sections before release.

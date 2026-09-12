# {{TOOL_NAME}} Command Reference

## Command Surface

- Executable or entry point: `{{TOOL_ENTRY_POINT}}`
- Supported version or range: {{SUPPORTED_TOOL_VERSION_OR_RANGE}}
- Help or documentation evidence: {{COMMAND_SURFACE_EVIDENCE}}
- Invocation environments: {{SUPPORTED_INVOCATION_ENVIRONMENTS}}

## Shared Invocation Rules

{{SHARED_INVOCATION_RULES}}

Keep only rules shared by several commands, such as target selection, global
options, configuration precedence, output selection, quoting, or interaction
mode. Put command-specific options with the command.

## Command Index

| User intent | Command | Effect | Detailed section |
|-------------|---------|--------|------------------|
{{COMMAND_INDEX_ROWS}}

## {{COMMAND_GROUP_NAME}}

### `{{COMMAND_NAME}}`

**Use when:** {{COMMAND_APPLICABILITY}}

**Effect:** {{COMMAND_EFFECT}}

**Syntax:**

```{{COMMAND_FENCE_LANGUAGE}}
{{COMMAND_SYNTAX}}
```

**Inputs and options:**

| Input or option | Required | Default | Constraints |
|-----------------|----------|---------|-------------|
{{COMMAND_INPUT_ROWS}}

**Success outcome:** {{COMMAND_SUCCESS_CONTRACT}}

**Failure outcomes:** {{COMMAND_FAILURE_CONTRACT}}

**Safest verification:** {{COMMAND_VERIFICATION}}

Repeat this command section for each independently useful command. Do not infer
commands or flags from naming conventions; verify them against the pinned help
surface.

## Process and Outcome Model

{{PROCESS_AND_OUTCOME_MODEL}}

Document exit semantics, standard streams, structured output, partial success,
prompts, signals, and retryability only as the tool defines them. Do not assume
exit code zero, JSON output, or POSIX shell behavior without evidence.

## See Also

- `references/configuration.md` -- installation and identity setup
- `references/patterns.md` -- supported multi-step workflows
- `references/gotchas.md` -- evidenced command and platform pitfalls

## Release Gate

Replace every template token, remove unsupported command concepts, and verify
every example against the pinned command surface before release.

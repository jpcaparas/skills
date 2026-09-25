# Quickstart Design

A quickstart is the README's contract: the shortest verified path from a fresh checkout to useful local feedback.

## Runnable-Project Default

For projects with an executable first-use path, adapt this order to the actual workflow:

1. Install dependencies.
2. Create local configuration, if needed.
3. Start the app, service, package, or example.
4. Open or run a concrete verification point.
5. Run the shared quality gate.

Keep the quickstart near the top. Do not bury it under project background.

## Command Rules

- Use commands from manifests, Makefiles, task runners, scripts, or existing docs.
- Prefer the repository-level command when it exists.
- Use one command block per logical step.
- Avoid shell prompts and machine-specific paths.
- State useful compatibility ranges and link the toolchain source. Include an exact version when genuinely required or helpful, not as an unsupported universal pin.

## Configuration Rules

Mention local configuration only when it blocks the quickstart.

Good:

```markdown
Copy the example environment file and fill in the required local values.
```

Acceptable when the filename is stable and necessary:

```markdown
cp .env.example .env
```

Avoid dumping all environment variables. Group them by purpose when possible:

- database connection
- application secret
- external API credentials
- public base URL

## Verification Point

Every quickstart should tell the reader how they know it worked:

- local URL
- CLI output
- generated file
- passing test command
- successful health check

If the port is discoverable from scripts or config, include it. If it is not, say "open the URL printed by the dev server."

## Quality Gate Placement

Put the shared check after the run step:

```markdown
Run the project checks:

```bash
pnpm check
```
```

If there is no shared check, list the smallest verified equivalent such as test plus lint. Do not invent a quality command.

## Multi-App Workspaces

For multi-app repositories:

- start with the all-in-one workspace command if it exists
- explain app responsibilities in prose
- include single-app commands only when they are common and discoverable
- avoid a full path inventory

## Library Repositories

For libraries, choose the relevant consumer or contributor path, not both by default:

- install or build
- run tests
- minimal usage example if the public API is discoverable

Do not fake usage examples from implementation details. If usage is not clear, keep the README to setup and point to examples or tests.

## Non-Runnable Repositories

For documentation, infrastructure, or template repositories, first use may mean:

- how to preview docs
- how to validate configuration
- how to instantiate the template
- how to run policy checks

For datasets or archives, access, schema, provenance, licensing, or migration guidance may replace executable steps entirely. Do not invent a validator or preview command to complete this outline.

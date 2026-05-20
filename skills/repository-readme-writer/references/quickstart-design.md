# Quickstart Design

A quickstart is the README's contract: the shortest verified path from a fresh checkout to useful local feedback.

## Required Shape

Use this order unless the repository demands another one:

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
- Avoid exact version commands such as "install Node 20.11.1" unless the repository's own tooling requires that exact prose.

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

For libraries, the quickstart should include:

- install or build
- run tests
- minimal usage example if the public API is discoverable

Do not fake usage examples from implementation details. If usage is not clear, keep the README to setup and point to examples or tests.

## Non-Runnable Repositories

For documentation, infrastructure, or template repositories, "quickstart" still applies. It may mean:

- how to preview docs
- how to validate configuration
- how to instantiate the template
- how to run policy checks

# Migration From Harness-Specific Generated Roots

Use this flow when a project already has `.claude/hooks/generated`, `.codex/hooks/generated`, or `.devin/hooks/generated`.

## Steps

1. Read old plan files if they exist:
   - `.claude/hooks/plan.json`
   - `.codex/hooks/plan.json`
   - `.devin/hooks/plan.json`
2. Translate project-specific scripts and commands into a universal plan.
3. Run:

```bash
scripts/scaffold_all_hooks.sh --project /path/to/project --plan /path/to/scaffold-hooks.json --mode additive
```

4. Confirm final configs point to `hooks/<event>/<harness>.sh`.
5. Confirm old generated-root command entries are gone.
6. Run project validation.

## Refreshing a Scaffold That Emitted Stubs

Earlier versions wrote a stub script and an empty adapter for every event the harness documents. Re-run the scaffold with the plan (or without `--plan` to reuse the recorded one):

```bash
scripts/scaffold_all_hooks.sh --project /path/to/project --plan /path/to/scaffold-hooks.json
```

Events without scripts or commands lose their `hooks/<event>/` adapters, their untouched `script.sh` stub and their config entry. A `script.sh` whose code was edited stays, but is no longer wired; move that logic into a repo-owned script and list it in the plan. Custom hooks in harness configs, and anything outside the managed roots, are preserved.

## OpenCode: from opencode-froggy to a native plugin

A scaffold made with `opencode-froggy` is refreshed the same way. The refresh writes `.opencode/plugins/scaffold-hooks.ts` from the plan's OpenCode events, removes the managed block in `.opencode/hook/hooks.md` and the `opencode-froggy` entry in `opencode.json`, and keeps hooks and config the user wrote. Froggy-style `hooks:` plans are not read: restate each hook as an `enabled_events` entry with a script or command.

## What Does Not Migrate Automatically

The script does not parse arbitrary custom shell logic out of old generated event files. Move meaningful project behavior into repo-owned scripts such as:

- `./scripts/agent-stop-checks.sh`
- `./scripts/agent-session-context.sh`
- `./scripts/validate-project.sh`

Then reference those scripts from the universal plan.

## Why This Is Safer

Generated event files often accumulate hand edits and harness-specific assumptions. Moving project behavior into repo-owned scripts creates one reusable behavior surface and leaves each harness adapter responsible only for protocol translation.

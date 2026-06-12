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

## What Does Not Migrate Automatically

The script does not parse arbitrary custom shell logic out of old generated event files. Move meaningful project behavior into repo-owned scripts such as:

- `./scripts/agent-stop-checks.sh`
- `./scripts/agent-session-context.sh`
- `./scripts/validate-project.sh`

Then reference those scripts from the universal plan.

## Why This Is Safer

Generated event files often accumulate hand edits and harness-specific assumptions. Moving project behavior into repo-owned scripts creates one reusable behavior surface and leaves each harness adapter responsible only for protocol translation.

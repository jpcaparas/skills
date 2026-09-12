# Scaffold Layout

## Managed Target Layout

```text
.github/
├── workflows/
│   └── copilot-setup-steps.yml
└── copilot-instructions.md        # Optional but strongly recommended companion file
```

This skill only scaffolds the environment workflow directly. It may recommend adding `.github/copilot-instructions.md` when build, test, and validation guidance is missing.

## Why This Layout

- The official GitHub Docs contract points to a single workflow path.
- The job name remains obvious and easy to inspect in session logs.
- The workflow stays small and purpose-built: dependency bootstrapping and environment preparation, not full CI.
- The plan file keeps repo-specific judgment explicit.

## Plan File Shape

Use `templates/plan.example.json` as the starting point.

Top-level fields:

- `mode`
- `workflow_path`
- `job_name`
- `runner`
- `permissions`
- `timeout_minutes`
- `include_validation_triggers`
- `steps`
- `services`
- `manual_settings`
- `assumptions`
- `questions`
- `notes`

### `runner`

```json
{
  "kind": "github-hosted-standard",
  "runs_on": "ubuntu-latest"
}
```

Use `kind` to explain the decision, not only the final label.

### `steps`

Each step is either an action step or a shell step:

```json
{
  "name": "Checkout code",
  "uses": "actions/checkout@v5",
  "with": {
    "lfs": true
  }
}
```

```json
{
  "name": "Install JavaScript dependencies",
  "run": "npm ci"
}
```

Keep the steps deterministic and avoid burying open questions inside them.

### `manual_settings`

List the settings that cannot be expressed from the repository alone. Common examples:

- disable the integrated firewall for self-hosted runners
- confirm organization runner override policy
- add `copilot` environment secrets or variables
- change the workflow-approval setting for Copilot-created pull requests

### `questions`

If this array is non-empty, the renderer should stop and force the agent to ask the user before generating files.

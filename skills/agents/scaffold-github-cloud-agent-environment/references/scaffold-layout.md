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

`ubuntu-latest` and the action versions below are bundled example defaults. Select compatible runner labels and action refs from repository evidence and relevant official contracts; do not automatically upgrade repository pins.

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

The helper supports step-level `env` for non-secret setup constants and secret references, never inline secret values. Agent-wide secrets/variables belong in GitHub's documented configuration mechanism; do not infer job-level `env` support from ordinary Actions syntax.

### `manual_settings`

List the settings that cannot be expressed from the repository alone. Common examples:

- disable the integrated firewall for self-hosted runners
- confirm organization runner override policy
- add `copilot` environment secrets or variables
- change the workflow-approval setting for Copilot-created pull requests

### `questions`

Use this array for unresolved blockers that materially affect correctness or safety. Resolve them from repository evidence or the user before applying the affected change. Advisory choices belong in `assumptions` or `notes`; neither a renderer flag nor a missing answer authorizes a risky default.

The renderer rejects any non-empty `questions` array unless `--allow-questions` is passed. That flag bypasses the check and can write files; it is not a preview mode. For a labelled draft with unresolved blockers, use both `--allow-questions --stdout`, list those blockers alongside the preview, and do not apply it until resolved.

## Verified Helper Limits

These are implementation constraints, not GitHub platform guarantees:

- `render_setup_workflow.py` renders a whole file, not a merge. `mode` is not enforced as a no-clobber guard. Prefer minimal manual repair of custom workflows. For deliberate regeneration, preview with `--stdout`, review the diff, and ensure a recoverable backup; a changed existing file is moved to a timestamped `.bak` on write.
- The helper accepts both `.yml` and `.yaml`, but its validation-trigger paths are hardcoded to `.yml`. GitHub's cited Copilot contract documents `.github/workflows/copilot-setup-steps.yml`; use that path rather than treating helper acceptance as evidence of platform support for `.yaml`.
- `timeout_minutes` is converted to an integer but not range-checked. Verify it before writing: the documented maximum in the recorded contract is `59`.
- The doctor's allowlist includes `snapshot`, but the renderer does not emit a `snapshot` plan field. It also emits only the step fields it implements (`name`, `uses`/`run`, `with`, `env`); unsupported fields may be silently omitted. Inspect the preview and use a reviewed manual patch for needed supported platform fields the helper cannot preserve.
- The doctor uses a simple indentation-based parser, not a complete YAML/schema validator. Confirm findings against the actual workflow and logs before deleting unfamiliar syntax.

Propose fixes to these helper gaps with regression coverage through the canonical package maintenance route. Do not silently redesign installed tooling or replace custom steps to fit the helper.

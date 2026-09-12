# Rewrite Patterns

Improving an existing README is preservation work before it is rewrite work.

## Rewrite Workflow

1. Read the current README and identify what still helps.
2. Inspect repository evidence for setup, checks, configuration, and deployment.
3. Keep accurate sections, but simplify their wording.
4. Move fragile or exhaustive detail out of the README, or cut it when no better home exists.
5. Add or repair the quickstart.
6. Verify commands when feasible.

## Keep, Cut, Move

| Content | Action |
|---|---|
| One-line purpose | Keep and sharpen |
| Verified quickstart commands | Keep near the top |
| High-level architecture boundary | Keep, rewrite in stable language |
| Full file tree | Cut unless the layout is the product |
| Complete script catalog | Cut or reduce to common commands |
| Detailed deployment runbook | Move to dedicated docs when long |
| Exact runtime versions | Replace with toolchain-source guidance |
| Stale TODOs and placeholders | Remove |

## Compression Patterns

### Path Inventory To Boundary

Before:

```markdown
- `apps/web` contains the website.
- `apps/admin` contains the admin dashboard.
- `packages/ui` contains shared components.
```

After:

```markdown
The public app and admin app share UI and configuration through workspace packages. Keep browser-facing code separate from server-only integrations.
```

Use explicit paths only when a command or package README requires them.

### Command Catalog To Quality Gate

Before:

```markdown
Run lint, typecheck, tests, format checks, build, and policy checks separately.
```

After:

```markdown
Run the shared project gate:

```bash
pnpm check
```
```

Add narrow commands only for common local workflows.

### Version Pin To Toolchain Source

Before:

```markdown
Install Node.js 22.14.0 and pnpm 10.7.1.
```

After:

```markdown
Use the runtime and package manager configured by the repository.
```

If the repository has no version manager or manifest evidence, omit version guidance entirely.

## Existing README Tone

Respect a concise existing tone when it works. Do not replace a clear README with a more ornate one. The best edit is often deleting half the material and adding one missing command.

## Agent-Safe Rewrites

Avoid wording that creates brittle future obligations:

- "Always edit this exact directory..."
- "Never touch..."
- "The project has exactly..."
- "All commands are..."

Use narrower, current-state language:

- "The usual local path is..."
- "The shared quality gate is..."
- "The main boundary is..."
- "When changing the CMS schema, refresh generated types."

## When Not To Rewrite Fully

Do not rewrite from scratch if the existing README is mostly correct and the user asked for improvement. Patch the weak sections, especially quickstart, configuration, troubleshooting, and stale path lists.

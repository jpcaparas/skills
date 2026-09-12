# Methodology

Use this method to infer repository intent from real code without pretending weak signals are facts.

## Inspection Order

Start with the most explicit intent sources:

1. Root instructions: `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md`, or similar files.
2. Public docs: `README.md`, `docs/`, examples, tutorials, screenshots, demo scripts, changelogs, and release notes.
3. Manifests: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`, app manifests, extension manifests, and deploy configs.
4. Product surface: routes, commands, UI screens, API endpoints, schemas, prompts, workflows, fixtures, and seed data.
5. Tests: integration tests, end-to-end tests, snapshot names, fixtures, and regression cases.
6. Operations: CI, Dockerfiles, deploy manifests, migrations, environment examples, and monitoring configs.
7. Commit history only if the user asks or the current files are not enough.

Run the inventory script before manual reading:

```bash
python3 scripts/repo_intent_inventory.py /path/to/repo --json
```

The script is a scout, not an authority. Use it to choose files, then inspect important files directly.

## Signal Strength

| Signal | Strength | How to use it |
|---|---:|---|
| README or explicit docs say the purpose | High | Treat as `Certain` unless code strongly contradicts it |
| User-provided prompt or issue says the purpose | High | Treat as human intent and preserve separately from implementation status |
| Package name and description align with code | Medium | Treat as `Strong inference` when backed by routes/tests |
| Tests describe user workflows | Medium | Use as evidence for supported behavior |
| Directory names and filenames | Low | Use to navigate, not to claim product strategy |
| Unused dependencies | Low | Mention only as implementation clues |
| Generated files or lockfiles | Low | Ignore unless they reveal framework or runtime constraints |

## Confidence Labels

Use one of these labels for every material claim:

- `Certain`: directly stated in a source or verified by code behavior.
- `Strong inference`: supported by multiple independent signals.
- `Tentative`: plausible, but supported by one weak signal or incomplete evidence.
- `Open question`: requires the user to confirm or choose.

Do not mix labels in one sentence. Split claims until each has one confidence level.

## Evidence Anchors

Prefer anchors that a future agent can reopen quickly:

```markdown
- Certain: This is a browser extension for saving article highlights.
  Evidence: `manifest.json`, `src/content-script.ts`, `README.md`.
```

Use line numbers when already available from the tool output. Do not spend excessive time collecting line numbers for every claim; exact file anchors are usually enough.

## Contradictions

When sources conflict, preserve the conflict instead of resolving it silently.

Use this shape:

```markdown
### Tension

- `README.md` describes the project as a local-first notes app.
- `src/billing/` and `stripe` dependencies suggest a hosted subscription surface.
- Open question: Is the hosted subscription code current product direction, abandoned experiment, or planned future work?
```

## Question Design

Ask questions that convert uncertainty into durable instructions.

Good questions:

- "The README frames this as a CLI, but `src/server.ts` exposes an HTTP API. Is the CLI the primary product surface or an admin/helper interface?"
- "Should future agents treat `examples/legacy/` as supported behavior or historical reference?"
- "Is the current priority to preserve the existing architecture or simplify it around the documented core workflow?"

Weak questions:

- "What is this repo for?"
- "Can you explain the architecture?"
- "What should I know?"

Those make the user redo the inspection work the skill exists to perform.

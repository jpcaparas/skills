# Conversion Patterns

Use this catalog to choose the smallest deterministic artifact that captures a repeated heuristic without freezing subjective judgment.

## Pattern Matrix

| Heuristic shape | Deterministic artifact | Use when | Avoid when |
|---|---|---|---|
| "This required thing was missing" | Validator | Presence, schema, layout, command, or metadata can be checked | The rule depends on taste or temporary context |
| "This output varies by environment" | Normalizer | Formatting, image metadata, key order, paths, or line endings drift | The variation is meaningful data |
| "We keep hand-building the same files" | Generator | Shape is stable and inputs can be explicit | Project-specific judgment is still unresolved |
| "This decision needs one source of truth" | Manifest | Multiple adapters need the same event list, route list, hook list, or config table | The source changes live and must be fetched every time |
| "The model prompt works, but output must be bounded" | Prompt harness plus post-check | Creative generation needs repeatability around prompt and file constraints | You need exact pixel or semantic guarantees from the model |
| "This broke once and should never regress" | Fixture or golden test | A small input/output example captures the failure | The expected output is unstable or huge |
| "Agents must be stopped before shipping drift" | Hook or CI adapter | A local script already returns stable exit codes | The adapter would duplicate core logic |

## Validator

Validators answer "does the artifact satisfy the contract?" They should:

- accept a root path argument
- read files from that root only
- collect all errors before exiting
- print precise repair guidance
- return `2` for policy failures when used by stop hooks
- return `1` for usage errors, missing runtimes, or broken validators

Good validator targets:

- README section order and install commands
- generated prompt files matching a renderer
- PNG dimensions and metadata chunks
- hook event manifests and generated adapters
- package files that must remain tracked by git

## Normalizer

Normalizers make artifacts comparable before validation. They are useful when the desired state is exact but sources are noisy.

Good normalizer actions:

- strip image metadata
- resize rasters to fixed dimensions
- sort JSON keys
- remove generated timestamps
- format code with the repository's formatter
- convert path separators or line endings

Pair every normalizer with a validator. A normalizer alone hides whether the expected contract changed.

## Generator

Generators should be boring. Put human judgment in a plan or manifest, then make the generated layout deterministic.

Generator inputs should be explicit:

- target root
- source manifest
- managed marker or namespace
- dry-run flag when destructive writes are possible

Generator outputs should be reproducible:

- stable file order
- stable indentation
- no timestamps unless the target contract requires them
- clear managed markers around replaceable blocks

## Manifest

Use a manifest when several consumers need one stable source of truth. Examples:

- hook event names and payload fields
- README card paths and dimensions
- generated route lists
- required skill wrapper files
- approved runtime versions

If the manifest mirrors live external docs, add a drift check that forces re-verification before refreshes.

## Prompt Harness Plus Post-Check

Use this for AI-generated media or prose when the prompt matters but the output cannot be exactly predetermined.

Persist:

- the full prompt
- the model and image settings
- the output path
- the structural requirements a script can inspect

Validate:

- file type
- dimensions or aspect ratio
- maximum byte size
- metadata stripping
- README placement
- prompt drift

Do not validate subjective claims such as "looks beautiful" unless the user has supplied measurable acceptance criteria.

## Hook And CI Adapter

Adapters should call a reusable core command.

Good:

```bash
bash scripts/agent-stop-checks.sh
```

Weak:

```bash
# Large duplicated validation logic pasted into three hook systems.
```

Use one script as the shared source of truth, then call it from Claude Code, Codex, OpenCode, Husky, pre-commit, or GitHub Actions.

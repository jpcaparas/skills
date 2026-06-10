# Merge Strategy

Use this when updating a project that already has Copilot hooks.

## Modes

| Mode | Use When | Behavior |
|------|----------|----------|
| `additive` | Existing hooks should be preserved | Removes only previously managed hook entries whose command path contains the managed root, then appends the new generated entries |
| `overhaul` | The managed scaffold itself should be rebuilt | Backs up the managed script directory, regenerates stubs, then applies the same conservative hook-file merge |

## Managed Boundary

The managed boundary is the generated adapter path:

```text
.github/copilot/hooks/generated
```

The merge script treats a hook entry as managed only when one of its `bash`, `command`, or `powershell` fields contains that path. All other hook entries remain untouched.

## Existing File Rules

- Preserve top-level `disableAllHooks` when present.
- Preserve unrelated event arrays and custom hook entries.
- Ensure top-level `version` is `1`.
- Ensure top-level `hooks` exists.
- Remove empty event arrays after stripping managed entries.
- Do not edit `.claude/settings*.json`.

## Repeat-Run Contract

Running the scaffold repeatedly with the same plan should produce the same hook file shape except for generated timestamps in the manifest.

If a user manually edits generated event scripts, `additive` mode preserves those files. Use `overhaul` only when the user wants to refresh generated stubs.

## See Also

- `references/scaffold-layout.md`
- `references/gotchas.md`

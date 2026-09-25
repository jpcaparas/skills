# Verification

The goal is not to make every decision deterministic. The goal is to prove that the part you chose to enforce behaves the same for the next session, local machine, and CI runner.

## Proof Ladder

Select the rungs that establish the invariant at the task's risk level, not a mandatory sequence of new artifacts. Existing tests and check modes can supply the evidence; writers need repeat-run checks, while hook and CI checks apply only when those adapters are in scope.

1. Learning captured
   Write the lesson in plain language.

2. Invariant extracted
   Reduce the lesson to something inspectable: file exists, width equals `480`, command appears before image, JSON contains an event, or a runtime supports a flag.

3. Artifact chosen
   Pick validator, normalizer, generator, manifest, fixture, or adapter.

4. Fixture added
   Include at least one positive and one negative case when practical.

5. Local command passes
   Run the exact command an agent will run.

6. Re-run is clean
   Run the command twice and confirm the second run has no unexpected diff.

7. CI or hook calls the same core command
   Adapters should not fork behavior.

## Exit Codes

Preserve the underlying tool's documented exit codes. For a new script whose caller uses this convention:

- `0`: success
- `1`: usage error, missing runtime, broken script, or unexpected exception
- `2`: deterministic policy failure that should block a hook or CI gate

If the repository or hook uses a different contract, follow it and translate at the adapter boundary when needed. The key is that callers interpret failures correctly.

## Cross-Platform Checks

When the rule must work on Ubuntu and macOS:

- use `python3` and the standard library where practical
- avoid GNU-only flags unless the repo installs GNU tools
- sort output with `LC_ALL=C` when shell order matters
- do not assume `/tmp`, `$HOME`, Homebrew, or apt paths unless they are probed
- check runtime feature support before using version-gated flags
- pin CI actions or setup steps when the tool is not present by default

## Idempotence Checks

A deterministic fix should usually pass this loop:

```bash
command-that-generates-or-normalizes
git diff --check
command-that-generates-or-normalizes
git diff --exit-code -- path/to/managed/files
```

For files that intentionally change, write a manifest or report that explains why.

## Negative Tests

Negative tests are the strongest proof that a heuristic became enforceable. Include at least one case where:

- a required block is missing
- a file has the wrong extension
- a runtime flag is unsupported
- a generated prompt has drifted
- an image has the wrong dimensions
- a managed block is duplicated

The failure message should identify the exact invariant and the repair command.

## Live Specs And Docs

For relevant unstable claims about hook models, event payloads, APIs, or hosted runtimes, use authoritative evidence rather than stale memory. Choose evidence suited to the supported version and freshness risk:

- versioned primary documentation or installed-tool help
- a feature probe or fixture exercising the supported contract
- a versioned manifest refreshed after verification
- current primary docs or a drift check when the rule depends on live behavior

Document what the evidence establishes and any freshness gap; unrelated dependencies do not need refreshing.

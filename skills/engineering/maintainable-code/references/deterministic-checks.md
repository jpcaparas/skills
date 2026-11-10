# Turning a recurring mistake into a deterministic check

Write the observed failure as one sentence, reduce it to an inspectable invariant (file exists, width equals 480, command appears before image, runtime supports a flag), then pick the smallest mechanism that enforces that invariant and leaves unrelated choices open.

## Choosing the mechanism

- Required or forbidden structure: a validator.
- Noisy but exact desired state (metadata, key order, image size, line endings): a normalizer, run before validation.
- Repeated scaffold: a generator driven by a manifest or explicit plan. Fix only the shape the output contract needs.
- Several adapters need one list (events, routes, hooks): a manifest as the single source.
- Something broke once: a fixture or golden test that fails before the fix, with a negative case.
- Model output (art, prose): keep the prompt as source and add checks for what code can inspect (path, format, dimensions, byte size, prompt drift). The creative content stays non-deterministic.
- Taste with no measurable signal: do not fake it. Capture examples, ask for acceptance criteria, or leave it as review guidance.

Reuse before building: if the repository already has a formatter, schema, linter or check mode for the invariant, configure it and code only the missing part. Keep new checks portable: take a root path or discover it, no machine-specific absolute paths, standard library where practical, `LC_ALL=C` when shell sort order matters, no GNU-only flags unless installed.

## Rules

- Convert only stable claims. For tool- or version-specific behaviour, check the installed version or probe the feature, or read versioned primary docs; do not freeze a workaround into a validator.
- Policy lives in a small plan; scripts enforce shape, paths, schema, size and compatibility.
- Failures print the invariant that broke and the command or file that repairs it. A strict check with no repair path teaches agents to bypass it.
- Preserve the underlying tool's exit codes. For a new script, use 0 success, 1 usage or tool error, 2 policy failure only when the calling hook expects 2 (Claude Code-style stop hooks block on 2); translate at the adapter boundary otherwise.
- Hooks, Git hooks and CI call the same core command. Adapters stay thin so behaviour does not fork between local and CI.
- Writers and normalizers are idempotent: run twice, then `git diff --exit-code` on managed files. A normalizer that always rewrites hides drift; validate after normalizing, or offer a check mode that fails on dirty output.
- Show the check passes on valid input and fails on a relevant violation (missing block, wrong extension, unsupported flag, drifted prompt, wrong dimensions, duplicated managed block).

## Gotchas

- Overfitting one incident: if the invariant cannot be stated without naming one temporary file, use a regression fixture, not a global rule.
- Runtime flags exist on one runner and not another ("bad option"): pin the runtime, install it in CI, or feature-detect, and print the version in a preflight.
- Local validation passes because a file exists but CI fails because it is untracked or globally ignored; add a git-visibility check for files that must exist in a fresh checkout.
- Prompt guidance ("no text", "16-bit") with no script checking the output is not enforcement.
- "Not beautiful enough" is not a gate; convert only measurable parts.

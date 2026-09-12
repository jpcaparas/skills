---
name: heuristic-to-deterministic
description: "Convert repeated heuristics into deterministic behavior: validator scripts, normalizer tools, generators, fixtures, manifests, CI jobs, and hook-ready checks. Use to codify learnings and prevent future guessing. Do NOT use for pure brainstorming or one-off edits."
compatibility: "Requires: python3 for validation scripts. Generated checks may require the target repository's existing toolchain."
metadata:
  version: "1.0.0"
references:
  - conversion-patterns
  - verification
  - gotchas
---

# Heuristic to Deterministic

Turn session learnings and repeated review heuristics into repeatable checks, normalizers, generators, fixtures, CI jobs, and hook-ready workflows.

## Decision Tree

What kind of heuristic are you converting?

- A rule about required or forbidden structure
  Build a validator. Read `references/conversion-patterns.md`.

- A rule about canonical formatting, image shape, generated output, or metadata cleanup
  Build a normalizer, then validate the normalized artifact.

- A repeated scaffold or generated file layout
  Build a generator from a manifest or explicit plan. Keep the plan editable and the scaffold shape fixed.

- A flaky environment or cross-platform failure
  Add runtime discovery, version checks, fixtures, and CI matrix coverage. Read `references/verification.md`.

- A prompt guideline for generated media or model output
  Keep the prompt harness as source, then add deterministic post-generation checks for the properties a script can inspect.

- A taste or judgment call with no measurable signal
  Do not pretend it is deterministic. Capture examples, ask for acceptance criteria, or leave it as review guidance.

## Quick Reference

| Need | Artifact | First action |
|---|---|---|
| Prevent a missing file, README block, hook, or config | Validator | Encode the invariant and fail with actionable output |
| Make outputs consistent across machines | Normalizer | Strip metadata, sort keys, resize, format, or canonicalize before validation |
| Avoid hand-copying a scaffold | Generator | Use a manifest or plan file as source of truth |
| Stop repeated regressions | Fixture or golden test | Add positive and negative examples that fail before the fix |
| Reuse the check in hooks and CI | Thin wrapper | Keep the core script path-agnostic and callable from multiple adapters |
| Convert model art or prose rules | Prompt harness plus post-check | Persist the prompt, then verify dimensions, paths, format, or required metadata |

## Operating Contract

1. Start with the learning, not the tool. Write the observed failure as a sentence before choosing an artifact.
2. Convert only stable claims. If the underlying API, docs, or product behavior can drift, add a live documentation check or version probe before freezing assumptions.
3. Separate judgment from enforcement. Let humans or agents decide policy in a small plan; let scripts enforce shape, paths, schema, size, and compatibility.
4. Make every check path-agnostic. Accept a target path argument, resolve from that root, and avoid machine-specific absolute paths.
5. Use exit code `2` for hook-blocking validation failures when the caller already uses that convention. Use `1` for usage or tool errors.
6. Print the repair path. A deterministic failure should tell the next agent which command or file fixes the drift.

## Workflow

1. Inventory the heuristic.
   - What did we learn?
   - What repeated mistake or drift does it prevent?
   - What is stable enough to enforce?
   - What remains subjective?

2. Choose the lowest-freedom artifact.
   - Validator for yes/no structure.
   - Normalizer for canonical representation.
   - Generator for repeatable creation.
   - Fixture for regression behavior.
   - Manifest for shared source of truth.
   - CI or hook adapter for enforcement timing.

3. Build the core script first.
   - Use the target repo path as input.
   - Avoid global state and current-machine paths.
   - Prefer standard-library code unless the repo already depends on a parser or formatter.
   - Make the script idempotent.

4. Add proof.
   - Positive fixture passes.
   - Negative fixture fails with the expected message.
   - Running the tool twice produces no diff.
   - The same command works on macOS and Ubuntu when the repo claims both.

5. Wire adapters last.
   - Stop hooks, Git hooks, and GitHub Actions should call the same core script.
   - Keep adapter files thin so behavior does not fork by environment.

## Determinism Ladder

Use this ladder to avoid over-promising:

1. Structural: file exists, JSON schema matches, README block is present.
2. Canonical: sorted keys, normalized PNG, formatted code, stripped metadata.
3. Behavioral: fixture input produces expected output or exit code.
4. Environmental: dependency versions and feature flags are detected before use.
5. External: live docs or APIs are checked before freezing a spec-sensitive rule.
6. Subjective: examples and review rubrics only; no hard failure unless criteria become measurable.

## Helper

Use `scripts/classify_conversion.py` for a quick deterministic first pass:

```bash
python3 scripts/classify_conversion.py "README cards must be below install commands and hooks should block drift"
```

The classifier is intentionally simple. Treat it as a planning aid, not as proof that the chosen artifact is sufficient.

## Reference Guide

| Need | Read |
|---|---|
| Artifact patterns and when to choose each one | `references/conversion-patterns.md` |
| Verification depth, fixtures, CI, hooks, and exit codes | `references/verification.md` |
| Common ways deterministic checks become brittle | `references/gotchas.md` |

## Gotchas

1. Do not encode a workaround as truth. If a behavior is tool-version-specific, check the version or probe the feature.
2. A generated asset can be constrained deterministically without making its creative content deterministic. Validate dimensions, format, prompt file drift, size, and placement.
3. Avoid duplicate enforcement logic. Hook, CI, and local commands should delegate to the same script.
4. A validator that only checks the current dirty worktree can still fail in CI if files are untracked or globally ignored. Include git visibility checks when packaging matters.
5. A strict check with no repair command trains agents to bypass it. Make failures actionable.

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
  Use or extend a validator. Consult `references/conversion-patterns.md` when artifact selection needs detail.

- A rule about canonical formatting, image shape, generated output, or metadata cleanup
  Reuse a normalizer where available, then verify its postconditions.

- A repeated scaffold or generated file layout
  Use or extend a generator from a manifest or explicit plan. Fix only the shape required by the output contract; leave incidental file organization editable.

- A flaky environment or cross-platform failure
  Select runtime discovery, version checks, fixtures, or CI coverage for the failure. Consult `references/verification.md` when proof depth needs detail.

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
| Reuse the check in hooks and CI | Thin wrapper | Keep the core command portable and callable from multiple adapters |
| Convert model art or prose rules | Prompt harness plus post-check | Persist the prompt, then verify dimensions, paths, format, or required metadata |

## Operating Contract

1. Start with the learning, not the tool. Write the observed failure as a sentence before choosing an artifact.
2. Convert only stable claims. Support relevant unstable API or product claims with appropriate authoritative evidence: versioned docs, installed-tool help, a feature probe, or current primary docs. Refresh when freshness matters to the rule.
3. Separate judgment from enforcement. Let humans or agents decide policy in a small plan; let scripts enforce shape, paths, schema, size, and compatibility.
4. Keep checks portable within their intended scope. Reuse the tool's project-root discovery or accept a target path; avoid machine-specific absolute paths.
5. Follow the tool's documented exit semantics and the caller's contract. Use exit code `2` for hook-blocking failures only when that caller expects it; adapt codes at the boundary when needed.
6. Print the repair path. A deterministic failure should tell the next agent which command or file fixes the drift.

## Workflow

1. Inventory the heuristic.
   - What did we learn?
   - What repeated mistake or drift does it prevent?
   - What is stable enough to enforce?
   - What remains subjective?

2. Choose the smallest mechanism that reliably enforces the stable invariant while leaving unrelated choices open.
   - Validator for yes/no structure.
   - Normalizer for canonical representation.
   - Generator for repeatable creation.
   - Fixture for regression behavior.
   - Manifest for shared source of truth.
   - CI or hook adapter for enforcement timing.

3. Reuse before building.
   - Check the repository's existing formatter, checker, schema, or generator for the invariant.
   - Configure or extend it where sufficient; code only the missing behavior.
   - Keep new code portable and avoid hidden global state.
   - Make generators and normalizers idempotent where the output contract permits.

4. Add proof.
   - Select checks by risk and artifact; use existing tests or add focused fixtures.
   - Show the invariant passes and a relevant violation is detected.
   - Check repeat runs for writers and macOS/Ubuntu compatibility when claimed.

5. Wire adapters when enforcement timing is in scope.
   - Stop hooks, Git hooks, and GitHub Actions should call the same core command.
   - Keep adapter files thin so behavior does not fork by environment.

## Determinism Ladder

Use this ladder to avoid over-promising:

1. Structural: file exists, JSON schema matches, README block is present.
2. Canonical: sorted keys, normalized PNG, formatted code, stripped metadata.
3. Behavioral: fixture input produces expected output or exit code.
4. Environmental: dependency versions and feature flags are detected before use.
5. External: authoritative evidence establishes the supported contract before freezing a spec-sensitive rule; check live sources when freshness matters.
6. Subjective: examples and review rubrics only; no hard failure unless criteria become measurable.

## Helper

Use `scripts/classify_conversion.py` for a quick deterministic first pass:

```bash
python3 scripts/classify_conversion.py "README cards must be below install commands and hooks should block drift"
```

The classifier is intentionally simple. Treat it as a planning aid, not as proof that the chosen artifact is sufficient.

## When Guidance Stops Helping

If a proposed invariant conflicts with repository behavior or a current tool contract, inspect the installed tool and official version-matched sources before encoding it. Do not freeze a stale workaround into a validator. Propose a canonical skill correction with the failed advice, source/version, and a distinguishing fixture; do not silently update installed copies or claim unavailable evidence is verified.

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

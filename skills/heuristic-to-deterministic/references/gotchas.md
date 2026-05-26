# Gotchas

## Overfitting A Single Incident

Symptom: A script blocks valid future work because it encoded one broken example too literally.

Fix: Extract the invariant. If the invariant cannot be described without naming one temporary file, use a regression fixture instead of a global rule.

## Treating Prompt Guidance As Enforcement

Symptom: The prompt says "no text" or "make it 16-bit", but no script checks anything about the output.

Fix: Persist the prompt, then validate the deterministic properties available to code: file path, extension, dimensions, byte size, metadata, placement, and prompt drift.

## Hiding Drift With Normalization

Symptom: A normalizer always rewrites the file, so CI passes while the source contract is unknown.

Fix: Validate after normalization and report when normalization had to change something. For managed files, consider a check mode that fails on dirty output.

## Forking Hook And CI Logic

Symptom: Local stop hooks pass but GitHub Actions fails, or the reverse.

Fix: Move behavior into one repo-owned script. Hooks and CI should be thin adapters around that script.

## Assuming Runtime Flags Exist

Symptom: A local Node or Bun feature works on one runner but fails on another with a "bad option" or missing binary error.

Fix: Pin the runtime, install it in CI, or feature-detect and fall back. Add a preflight version print when the toolchain is part of the contract.

## Ignoring Git Visibility

Symptom: Local validation passes because a generated file exists, but CI fails because the file was untracked or globally ignored.

Fix: Add a git visibility check for packaged skill files, generated prompts, fixtures, and assets that must exist in a fresh checkout.

## Making Subjective Taste A Hard Gate

Symptom: A validator fails with "not beautiful enough" or "not clear enough".

Fix: Convert only measurable parts to checks. Keep subjective criteria as examples, review rubrics, or prompt guidance until measurable acceptance criteria exist.

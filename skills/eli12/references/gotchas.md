# Gotchas

## 1. Simple language can still be wrong

If the code branches on feature flags, tenant state, retry state, or environment, those conditions belong in the explanation. Do not simplify them away.

## 2. Analogies can drift

An analogy is useful only if it stays close to the real mechanism. The moment it starts carrying the explanation instead of supporting it, pull back to the code.

## 3. File maps are not explanations

Listing folders and saying what each one "probably" does is not enough. Trace the actual flow.

## 4. Broad questions tempt broad answers

If the user asks for one feature flow, answer that feature flow first. Do not spill into unrelated architecture unless it is required for understanding.

## 5. Some complexity is structural

If the codebase is hard to explain because the implementation is tangled, say that directly and isolate the confusing seams.

## 6. Jargon can sneak back in

Words like "hydration," "memoization," "fan-out," or "idempotent" are fine only if you define them where they first appear.

## 7. Observation and inference are not the same

When a behavior is implied by naming or nearby code but not directly confirmed, mark it as an inference.

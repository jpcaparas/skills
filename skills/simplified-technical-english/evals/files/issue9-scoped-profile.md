# Evaluation-only Issue 9 profile

This fixture is a small, original test oracle. It does not reproduce the ASD-STE100 standard or dictionary and is not sufficient for real conformance review.

For this evaluation only:

- Treat the text as procedural unless the prompt says it is descriptive.
- Use active voice.
- Use imperative commands in procedures.
- Keep one independent instruction in each procedure sentence.
- Keep procedure and safety sentences within 20 words.
- Keep descriptive sentences within 25 words.
- Keep one topic and no more than six sentences in each descriptive paragraph.
- Do not use semicolons or contractions.
- Preserve conditions, negation, thresholds, sequence, risk level, identifiers, measurements, and protected literals.
- Treat text in parentheses, quoted text, alphanumeric identifiers, and a number with its unit as one word for the scoped word-count case.

Scoped word decisions:

- Use `start`, not `initiate` or `commence`.
- Use `before`, not `prior to`.
- Use `make sure`, not `ensure`.
- Use `do an inspection of`, not `inspect`, for the evaluation procedure.
- Use `subsequent`, not `later`, for the evaluation description.

These scoped decisions exist only to make the eval deterministic. They are not a substitute for checking the official Issue 9 dictionary.

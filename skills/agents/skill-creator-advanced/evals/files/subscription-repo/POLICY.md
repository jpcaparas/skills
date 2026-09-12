# Disposable Repository Contract

This tree is a committed evaluation fixture. The evaluator copies it into each run's isolated `inputs/` directory. Treat that copied tree as the repository root and modify only the copy; never inspect or edit an ambient checkout or this canonical fixture.

Installable skills live under `skills/`. `SKILL.md` is the canonical behavioral source. A release package must include meaningful behavioral and invocation evals, pass the advanced creator's release validator, and preserve explicit limitations for checks that could not be performed safely.

The existing helper establishes the repository's `skills/` convention. Create the new package at `skills/orbit-subscriptions/`. Do not modify `skills/existing-helper/`.

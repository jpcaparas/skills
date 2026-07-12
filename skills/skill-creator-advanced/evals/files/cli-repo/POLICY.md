# Disposable Repository Contract

This tree is a committed evaluation fixture. The evaluator copies it into each run's isolated `inputs/` directory. Treat that copied tree as the repository root and modify only the copy; never inspect or edit an ambient checkout or this canonical fixture.

Installable skills live under `skills/`. `SKILL.md` is the canonical behavioral source. A release package must include meaningful behavioral and invocation evals, pass the advanced creator's release validator, and label any check that could not be run as a limitation.

The existing helper establishes the repository's `skills/` convention. Create the new package at `skills/orbitctl-deployments/`. Do not modify `skills/existing-helper/`.

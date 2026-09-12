# heuristic-to-deterministic

Installable skill for converting repeated heuristics, session learnings, and manual review habits into deterministic validators, normalizers, fixtures, generators, CI checks, and hook-ready workflows.

## Install

```bash
npx skills add jpcaparas/skills --skill heuristic-to-deterministic
```

## Includes

- `SKILL.md` as the canonical workflow
- `references/conversion-patterns.md` for choosing the right deterministic artifact
- `references/verification.md` for proof, fixtures, hooks, and CI coverage
- `references/gotchas.md` for common failure modes
- `scripts/classify_conversion.py` as a small planning helper

Use this when a session discovers a repeatable failure mode and the next agent should inherit a script, validator, manifest, or check instead of re-learning the same lesson.

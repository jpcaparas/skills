# Skill Creator Advanced

Repository-agnostic, path-aware skill creator for production-grade skills.

## What It Adds

- Progressive disclosure and blueprint-driven skill design
- Structural validation and lightweight test coverage
- Cross-harness compatibility guidance
- Destination inference so new skills land in the right repo-local or global skills directory

## Key Files

- `SKILL.md` — authoritative instructions
- `references/placement.md` — destination selection heuristics
- `scripts/infer_destination.py` — placement recommendation helper
- `scripts/scaffold.sh` — scaffold a new skill into the recommended root
- `scripts/validate.py` — structural validation
- `scripts/test_skill.py` — eval and cross-reference checks

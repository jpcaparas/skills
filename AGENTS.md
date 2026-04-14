# AGENTS.md

This repository is a public source for installable agent skills.

## Conventions

- Put every installable skill in `skills/<skill-name>/`.
- Treat this repository as the source of truth for existing skills. When modifying an existing skill, make the change in this repo first, not only in an installed copy under another skills directory.
- Keep `SKILL.md` as the canonical instruction file for each skill.
- Treat `README.md`, `AGENTS.md`, and `metadata.json` beside a skill as thin packaging wrappers, not alternate sources of truth.
- Prefer repo-agnostic instructions. Do not hard-code a single workspace or machine path unless the user explicitly requires it.
- When a skill creates other skills, detect whether the best destination is repo-local or global before writing files.

## Validation

For any skill that ships scripts, run its local validators and confirm repository discovery still works:

```bash
python3 skills/<skill-name>/scripts/validate.py skills/<skill-name>
python3 skills/<skill-name>/scripts/test_skill.py skills/<skill-name>
npx --yes skills add . --list
```

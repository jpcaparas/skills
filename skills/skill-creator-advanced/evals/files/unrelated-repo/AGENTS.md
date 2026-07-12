# Repository Instructions

This application keeps project-local installable skills under `.agents/skills/`. Improve existing skills in place. `SKILL.md` is canonical, scripts carry deterministic behavior, and release changes must pass `python3 scripts/validate_skill.py <skill-path>`.

Do not copy application skills into a global skill library or into the authoring tool's own source tree.

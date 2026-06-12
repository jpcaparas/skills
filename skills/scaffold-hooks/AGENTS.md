# scaffold-hooks

Use `SKILL.md` as the canonical workflow. This skill is the single hooks scaffolder for Claude Code, Codex, GitHub Copilot, Devin CLI, and OpenCode. The former dedicated scaffolder skills are retired; each harness now lives as a self-contained component under `harnesses/<name>/` with its own `PLAYBOOK.md`, scripts, manifest, templates, references, validator, and tests.

Ask the user which harnesses to scaffold and default to all supported harnesses.

Do not duplicate harness event semantics in the universal layer. Update the harness component first (manifest, references, scripts, tests), then adjust the universal composition.

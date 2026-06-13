# scaffold-hooks

Use `SKILL.md` as the canonical workflow. This skill is the single hooks scaffolder for Claude Code, Codex, GitHub Copilot, Devin CLI, and OpenCode. The former dedicated scaffolder skills are retired; each harness now lives as a self-contained component under `harnesses/<name>/` with its own `PLAYBOOK.md`, scripts, manifest, templates, references, validator, and tests.

On a bare invocation, inspect the target repo and refresh only detected hook surfaces or managed scaffold state. Ask the user which harnesses to scaffold only when creating a new scaffold or when they want to add harnesses; default to all supported harnesses only when no supported hook surface exists.

Do not duplicate harness event semantics in the universal layer. Update the harness component first (manifest, references, scripts, tests), then adjust the universal composition.

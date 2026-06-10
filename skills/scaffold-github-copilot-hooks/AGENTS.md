# scaffold-github-copilot-hooks

Use `SKILL.md` as the canonical workflow. This skill scaffolds GitHub Copilot hooks into `.github/hooks/copilot-hooks.json`, verifies the live official GitHub hook docs first, audits the target project, and keeps generated adapter files under `.github/copilot/hooks/generated`.

Do not convert this scaffold to Claude, Codex, Devin, Husky, or cloud-agent environment setup config. Existing Claude files may be inspected only because Copilot CLI can inherit cross-tool hooks from them.

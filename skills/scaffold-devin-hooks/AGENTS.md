# scaffold-devin-hooks

Use `SKILL.md` as the canonical workflow. This skill scaffolds Devin CLI hooks into `.devin/hooks.v1.json`, verifies the live official Devin hook docs first, audits the target project, and keeps generated hook files under `.devin/hooks/generated`.

Do not convert this scaffold to Claude config. Existing Claude files may be inspected only to avoid inherited-hook surprises.

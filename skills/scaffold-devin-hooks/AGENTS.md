# scaffold-devin-hooks

Use `SKILL.md` as the canonical workflow. This skill scaffolds Devin CLI hooks into `.devin/hooks.v1.json`, verifies the live official Devin hook docs first, audits the target project, and keeps executable behavior in the shared `hooks/` tree with Devin adapters under `hooks/<event>/devin.sh`.

Do not convert this scaffold to Claude config. Existing Claude files may be inspected only to avoid inherited-hook surprises.

# claude-code-auto-advisor

Installable passive Claude Code skill that consults the configured advisor for security work, code reviews, high-stakes design, complex refactors, recurring failures, and risky completion checks.

## Install

```bash
npx skills add jpcaparas/skills --skill claude-code-auto-advisor
```

## Includes

- `SKILL.md` as the canonical workflow
- `references/advisor-policy.md` for consult and skip rules
- `references/claude-code-mechanics.md` for Claude Code advisor requirements, setup, and failure modes
- `scripts/detect_advisor_config.py` as a conservative local settings preflight

This skill is Claude Code specific and should stay inert in other harnesses.

# Source Notes

These sources were checked on 2026-07-12. They inform the skill's authoring method, not the content copied into generated project instructions.

## Primary Sources

| Source | Adapted principle |
|---|---|
| https://learn.chatgpt.com/docs/customization/overview | Keep root guidance small, repository-specific, and complementary to skills and mechanical enforcement. |
| https://learn.chatgpt.com/docs/agent-configuration/agents-md | Root guidance is layered with more specific instructions; discovery and precedence must be considered. |
| https://openai.com/index/harness-engineering/ | Treat repository knowledge as a maintained system of record; avoid a monolithic instruction manual that rots and consumes context. |
| https://cdn.openai.com/pdf/6a2631dc-783e-479b-b1a4-af0cfbd38630/how-openai-uses-codex.pdf | Prefer project facts an agent cannot reliably infer, such as domain rules, naming semantics, and known architectural constraints. |
| https://cdn.openai.com/API/docs/gpt-5-for-coding-cheatsheet.pdf | Avoid vague, conflicting, overly forceful instructions; use structured groupings and calibrated autonomy. |
| https://code.claude.com/docs/en/memory | Keep persistent instructions concise and concrete; import `AGENTS.md` from `CLAUDE.md` with `@AGENTS.md`; treat prose as context rather than enforcement. |
| https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices | Use explicit success criteria, examples where earned, and self-checks; prefer positive steering for ordinary behavior. |
| https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview | Define success criteria and evaluate behavior rather than assuming prompt quality from wording alone. |
| https://ai.google.dev/gemini-api/docs/prompting-strategies | Use clear, direct instructions, consistent structure, relevant context, and deliberate ordering. |

## Deliberate Adaptations

- The user's portability constraint excludes concrete paths, commands, package names, versions, and URLs from generated `AGENTS.md` files even though product documentation often uses concrete commands and locations as examples. The skill retains project specificity through conceptual architecture, domain invariants, risk boundaries, and evidence-backed completion rules.
- Negative-first wording is reserved for costly mistakes and paired with a permitted action. This preserves the requested protective tone without relying on repetition, emotional pressure, or blanket prohibitions.
- The exact `CLAUDE.md` import is isolated to one line. This prevents instruction drift and remains more portable than a symbolic filesystem link.
- Root guidance is treated as behavioral context. Invariants that require guaranteed enforcement should be represented by the repository's existing automation rather than stronger prose.

## Refresh Triggers

Re-check the primary sources when:

- either harness changes instruction discovery, precedence, import syntax, or file-size guidance
- behavioral evals show that ordering, negative wording, or section structure no longer improves adherence
- the repository's target harnesses or publication contract change
- generated files begin accumulating tool-specific details despite the output contract

## See Also

- `SKILL.md` — canonical runtime workflow and output contract

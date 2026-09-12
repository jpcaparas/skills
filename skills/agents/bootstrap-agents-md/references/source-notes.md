# Source Notes

These sources were checked on 2026-07-20. They inform the skill's maintenance, not text copied into generated project instructions.

## Primary Sources

| Source | Adapted principle |
|---|---|
| https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | Use the smallest set of high-signal context that produces the desired behavior. Keep instructions specific enough to guide and flexible enough for capable models to reason; add rules and examples in response to observed failure modes. |
| https://www.youtube.com/watch?v=aVO6E181cNU | As models improve, reduce directions, constraints, and examples that merely narrow valid outputs. Preserve true format constraints, state preferences with their reasons, and give the model room to find a better exception. |
| https://learn.chatgpt.com/docs/customization/overview | Keep root guidance repository-specific and complementary to skills and mechanical enforcement. |
| https://learn.chatgpt.com/docs/agent-configuration/agents-md | Root guidance is layered with more specific instructions; discovery and precedence must be considered. |
| https://openai.com/index/harness-engineering/ | Treat repository knowledge as a maintained system of record rather than a monolithic instruction manual that rots and consumes context. |
| https://cdn.openai.com/pdf/6a2631dc-783e-479b-b1a4-af0cfbd38630/how-openai-uses-codex.pdf | Prefer project facts an agent cannot reliably infer, such as domain rules, naming semantics, and known architectural constraints. |
| https://cdn.openai.com/API/docs/gpt-5-for-coding-cheatsheet.pdf | Avoid vague, conflicting, and overly forceful instructions; calibrate autonomy to consequence. |
| https://code.claude.com/docs/en/memory | Keep persistent instructions concise and concrete; import `AGENTS.md` from `CLAUDE.md` with `@AGENTS.md`; treat prose as context rather than enforcement. |
| https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview | Define success criteria and evaluate behavior rather than assuming prompt quality from wording alone. |

## Deliberate Adaptations

- The exact `CLAUDE.md` import is a harness contract and remains exact. Headings, section order, prose shape, and implementation advice are not format contracts, so the skill leaves them open unless the repository or user supplies a reason to constrain them.
- Literal commands, repository-relative paths, tool names, dependency names, versions, and maintained URLs are not universally brittle. They earn root context when exactness materially changes behavior and the value is stable; machine-local paths, secrets, inventories, and easily rediscovered detail do not.
- Inspection is proportional. The author gathers enough evidence for each retained rule and stops when additional repository traversal is unlikely to change persistent guidance.
- Examples are reserved for exact forms or demonstrated ambiguity. Ordinary prose and layout examples are omitted because they can become accidental output templates.
- Negative-first wording is reserved for costly mistakes and paired with the safe action. Ordinary guidance states the desired outcome and its project-specific reason.
- Root guidance is behavioral context. Invariants that require guaranteed enforcement should be represented by repository automation rather than stronger prose.

## Behavioral Eval Record

On 2026-07-20, the replacement and sparse-library cases now represented by evals 3 and 6 were run once per variant with `gpt-5.6-terra` at medium reasoning. The baseline used repository commit `47698650c8585918d69557b8ad0c18f2b4b9d7b9`; the candidate used the 1.1.0 working package. Both variants received the same prompts and project evidence.

| Case | Baseline behavior | Candidate behavior |
|---|---|---|
| Ledgerbird replacement | Preserved the domain invariants, but dropped the repository's exact test and lint commands, added generic workflow sections, and produced an exhaustive disposition table. | Preserved the same invariants and the configured `uv run pytest` and `ruff check src tests` contracts, removed unsupported literals and blanket rules, and summarized only material decisions. |
| Pocketcalc sparse library | Produced three generic sections and omitted the exact configured checks. | Produced a smaller project-specific file with `bun test` and `bun run typecheck`. An initial candidate run wrongly converted absent subsystems into a permanent prohibition; after adding the current-state rule and regression assertion, a fresh run omitted that prohibition while retaining the signed-zero contract and exact checks. |

These are discriminating behavioral observations, not a deterministic release gate. The sample is one run per variant, so future model or skill changes should repeat the comparison when they affect selection, specificity, examples, or output freedom.

## Refresh Triggers

Re-check the primary sources when:

- a target harness changes instruction discovery, precedence, import syntax, or file-size guidance
- a new model generation or comparative eval shows that a retained rule no longer changes behavior
- behavioral evals reveal a recurring failure that the minimal guidance does not prevent
- generated files accumulate generic sections, copied examples, or transient literals
- the repository's target harnesses or publication contract change

## See Also

- `SKILL.md` — canonical runtime workflow and output contract

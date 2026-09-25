# Output Contract

Use this reference when writing the final response after a zoom-out pass.

## Principles

- Show the map first, then supporting evidence.
- Group by responsibility, not by filesystem happenstance.
- Keep the result small enough that the user can act on it.
- Mark uncertainty instead of sanding it off.
- End with the shortest useful next path: files to read, tests to run, or implementation target.

## Recommended Shape

```markdown
**Target**
<one sentence naming the target and scope>

**One-Layer Map**
| Role | Files / Symbols | Why they matter |
| --- | --- | --- |
| Entry points | ... | ... |
| Orchestrators | ... | ... |
| Target owner | ... | ... |
| Downstream dependencies | ... | ... |
| Tests / fixtures | ... | ... |

**Caller Paths**
1. <entrypoint> -> <caller> -> <target> [verified by <file/symbol>]
2. <possible path> -> <target> [lead only: textual match/import/export]

**Boundaries**
- <boundary>: <what crosses it and where>

**Unknowns**
- <uncertainty and how to verify it>

**Next Reads**
1. <file>
2. <file>
3. <file>
```

Use tables when comparing module roles. Use a compact ASCII flow when execution order matters more than role comparison.

## Evidence Labels

Always distinguish observed relationships from inference and unresolved gaps. These labels are optional shorthand; plain prose is equally valid:

- `Verified`: direct call, runtime registration, focused test, or framework wiring was inspected.
- `Likely`: import/export relationship or multiple naming signals point to the relationship, but runtime wiring was not inspected.
- `Lead`: textual search match or naming similarity only.
- `Unknown`: expected relationship could not be confirmed from available files.

## Diagram Rules

Prefer narrow diagrams:

```text
POST /api/session
  -> session route handler
  -> SessionService.create
  -> token repository
  -> database
```

Avoid giant diagrams that list every dependency. When the graph is dense, summarize clusters and list the few edges that matter for the user's task.

## Evidence Section

Include only evidence that helps the user verify or continue:

- commands run, especially search queries
- files read
- symbols inspected
- tests that cover the path
- assumptions and unresolved dynamic wiring

Do not dump raw search output. Summarize it into the map.

## Next Reads

Order next reads by the user's goal and the uncertainty blocking it. Useful candidates include:

- the central owner or orchestrator for understanding responsibility
- an upstream caller for understanding how execution begins
- a downstream dependency for understanding effects
- a focused test or fixture for understanding the behavior contract
- config or registration that resolves an unverified path

For example, read registration first when the question is how a job is scheduled; read the behavior test first when preparing a change. Do not pad the list to match the template.

## See Also

- `templates/zoom-out-map.md` for a reusable Markdown shell.
- `references/caller-mapping.md` for evidence strength and relationship labels.
- `references/gotchas.md` for wording uncertainty around dynamic code.

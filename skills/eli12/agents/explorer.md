# Explorer Agent

Use this agent when the question spans enough code that a dedicated evidence pass is worthwhile.

Read `references/explorer-prompt.md` and return structured findings, not a polished end-user explanation. If the prompt is too vague to choose a useful slice of the codebase, ask for narrower scope before starting a broad evidence pass.

# jev-opportunities

An explicitly invoked opportunity audit for an existing application without Jev.
It checks relevant current primary docs, maps scoped semantic decisions in the codebase,
and finishes approved spikes with a before/after comparison and a recommendation
on whether to adopt Jev in that codebase.

```bash
npx skills add jpcaparas/skills --skill jev-opportunities
```

Invoke it by name, for example:

> Use jev-opportunities on this application. Find cost reductions, fast paths,
> adjudication and other useful opportunities. Prepare spike plans; no live calls yet.

Public documentation and offline planning need no API key. Live spikes require
`TYPESAFE_API_KEY`, explicit spend/data approval, and a bounded experiment.
The skill does not deploy or add Jev to production by default.

`SKILL.md` is the canonical workflow. Python 3.11+ runs the standard-library docs
scraper; the agent can use a web reader if Python is unavailable. Local package
validation additionally uses PyYAML. Evals distinguish discovery, live execution,
negative results, and permission boundaries; structural checks do not execute
those model-behaviour scenarios.

Manual invocation uses Claude Code's documented
[`disable-model-invocation`](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill)
and Codex's
[`allow_implicit_invocation`](https://developers.openai.com/codex/skills#optional-metadata)
controls. Other harnesses receive the explicit-only instruction in the description
and body; equivalent mechanical enforcement is not assumed.

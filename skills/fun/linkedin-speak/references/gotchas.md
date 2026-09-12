# Gotchas

## 1. Vague Inputs Produce Generic Cringe

If the input is something like `good day` or `it worked`, the engine will fall back to generic growth-and-gratitude language because it has no specific nouns to map onto better hashtags or action phrases.

Fix:

- include the actual action, project, role, or topic
- use `--intensity 1` if the user wants a smaller joke

## 2. Reverse Mode Removes The Joke, Not Just The Noise

Reverse mode strips hype aggressively. That is the point. If a user actually wants a polished but still warm tone, use `{{ skill:better-writing }}` instead of this skill.

## 3. Deterministic Means Repeatable Patterns

The translator uses hash-based selection so the same input stays stable. That helps tests, but heavy reuse can expose the same sentence shapes repeatedly.

Fix:

- change the input wording slightly
- change `--intensity`
- turn hashtags or emoji off for a different feel

## 4. Kagi Comparison Is Web-Only

Research found public web routing for LinkedIn Speak but no documented public API contract. This skill therefore treats Kagi as a comparison target, not a hard dependency.

## 5. Satire Can Overshoot

Do not use this skill for press releases, performance reviews, layoffs, legal notices, or other contexts where parody can backfire.

## Read Next

- `references/patterns.md` for how the parody engine decides what to say
- `references/configuration.md` for the safe invocation patterns

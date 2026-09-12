# Product Question

Installable skill for answering product, PM, and stakeholder questions about app behavior by inspecting the codebase and returning a share-ready plain-English response.

## What It Covers

- product-facing answers grounded in codebase evidence
- user-visible behavior, business rules, and exceptions
- concise responses suitable for email, Teams, Slack, or product docs
- uncertainty handling when code evidence is incomplete
- guardrails against code dumps and technical over-explanation

## Key Files

- `SKILL.md` for the authoritative routing, workflow, and response contract
- `references/discovery.md` for codebase investigation workflow
- `references/answer-contract.md` for the final share-ready answer shape
- `references/gotchas.md` for common failure modes
- `templates/product-answer.md` for a copyable answer shell

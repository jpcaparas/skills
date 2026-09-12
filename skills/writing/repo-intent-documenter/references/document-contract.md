# Document Contract

The intent document is a durable briefing for future agents. It should be short enough to read at session start and precise enough to prevent false assumptions.

## Destination

Default path:

```text
REPO_INTENT.md
```

Use this default because root-level files are highly discoverable by agents and humans. Use `docs/repo-intent.md` when the repository clearly keeps all durable documentation under `docs/`.

Do not silently add links from `AGENTS.md`, `CLAUDE.md`, or `README.md`. Add a suggested integration note in the doc and ask before changing persistent agent instructions.

## Required Sections

Use `templates/repo-intent.md` as the starting shell. A complete document includes:

1. Status block with review state and last-updated date.
2. One-paragraph executive read.
3. Evidence-backed purpose.
4. What is certain.
5. Strong inferences.
6. Tentative reads.
7. Open questions for the user.
8. Architecture map focused on why the repo is shaped this way.
9. Future-agent working notes.
10. Review log.

## Status Values

Use one of these values:

- `Draft from code inspection`: first pass written before user answers.
- `User-reviewed`: user has corrected or confirmed the core intent.
- `Needs refresh`: code has drifted materially from the document.
- `Deprecated`: document no longer describes the active repo.

## Writing Rules

Keep the document concrete:

- Lead with purpose, not stack.
- Include evidence anchors for the most important claims.
- Keep architecture notes tied to intent, tradeoffs, or workflows.
- Put unknowns in `Open questions` instead of hiding them in vague language.
- Record human confirmations in the review log so future agents know which claims came from the user.

Avoid:

- long file inventories
- generic "this repo is a modern web app" language
- claims about users, business model, roadmap, or non-goals without evidence
- replacing the README; this doc explains intent for agents, not installation for users

## Review Loop

After writing the first draft:

1. Summarize the strongest conclusions in chat.
2. List the highest-value open questions.
3. Open the document if requested and possible.
4. Ask the user to answer or correct the questions.
5. Update the document from the user's answers.
6. Add a review log entry with the date and what changed.

If the user does not answer, leave the open questions in place and state that the doc is an evidence-backed draft rather than confirmed intent.

## Suggested Integration Note

When useful, include this section near the end:

```markdown
## Suggested Integration

Future agents should read this file after `AGENTS.md` and before making architectural changes. Add a one-line pointer from `AGENTS.md` only after the user confirms this document reflects their intent.
```

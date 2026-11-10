---
name: bootstrap-agents-md
description: "Creates or refreshes a repository's root AGENTS.md and the CLAUDE.md that imports it. Not for READMEs, nested instruction files or skills."
---

# Bootstrap AGENTS.md

Write the smallest root `AGENTS.md` that tells a capable coding agent what it cannot work out from the repository: project purpose and domain invariants, public boundaries, the exact checks that gate a change, delivery or migration risk, and conventions the code shows repeatedly but nothing enforces. Everything else belongs in the code, the tooling or a narrower file.

## Output

- Root `AGENTS.md`.
- Root `CLAUDE.md` containing exactly `@AGENTS.md` and one trailing newline. Claude Code reads `CLAUDE.md`, and the import keeps one source of truth.
- Create nothing else. Leave nested `AGENTS.md` files alone, since they take precedence in their directories, unless the user includes them. Keep unrelated working-tree changes untouched.

Run `scripts/validate_agents_md.py <repo-root>` afterwards. It checks the pair's structure, a 200-line and 1,200-word ceiling, and flags machine-local paths and unpaired prohibitions. It cannot judge whether the rules are true.

## Deciding what to keep

Keep a rule when it applies project-wide, changes behaviour, is supported by repository evidence (repeated code, tests, CI configuration, design records), and will stay true. Existing root files are evidence of intent, not a template: write a coherent replacement instead of editing in place, and carry over supported intent, not structure.

- Exact commands, repo-relative paths, tool names, versions and URLs stay when their literal form matters and CI or configuration shows they are stable. The configured test and lint commands almost always qualify.
- Drop secrets, machine-local absolute paths, pinned versions nothing enforces, blanket rules the evidence does not support ("comment every function", "always use X"), volatile inventories, and generic advice any agent follows anyway.
- A subsystem, dependency or workflow that does not exist today is a current fact, not a prohibition. Do not write "never add a database" because there is none.
- Pair each costly-failure guardrail with the safe action and its reason. Leave design, test shape, headings and documentation volume to the agent.
- If a rule can be enforced by a test, linter or CI step, say so and prefer that over stronger prose.
- A small project may need ten lines. Do not add reliability, security or architecture sections the evidence does not support.

Inspect only enough to support each rule; skip generated, vendored, binary and secret-bearing areas. Ask the user only when competing roots or instruction owners would change the result.

## Report

Say which evidence you read, what the file now asserts, what you changed, and what you could not confirm. If instructions existed before, account for them by material group (kept, reworded, removed, moved to a narrower file) with a reason. A line-by-line ledger is only for safety-critical or contested files, or when the user asks for one.

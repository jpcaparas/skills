---
name: skill-creator-advanced
description: "Creates, improves, evaluates and curates installable agent skills and skill libraries: placement, SKILL.md versus reference files, triggering descriptions, evals, and merge, rename or retire decisions. Not for a single prompt or AGENTS.md."
---

# Skill creator

A skill earns its place when a capable model would get a recurring task wrong without it: the knowledge is not in its training data, several valid approaches exist and one is wanted, or the task hangs on unwritten rules (thresholds, approvals, which source is truth, what done means). Test first: run the task a few times without the skill. If the model already does it the way you want, write no skill. Success is a better result with less instruction, not identical wording across runs.

## Package shape

- `SKILL.md` is the only instruction file, with `name` and `description` frontmatter (add `license`, `disable-model-invocation`, or `compatibility` only when they carry something the agent cannot infer, such as a required binary or API key). No README, AGENTS.md, metadata.json or placeholder directories beside it, and no generated validator or tests that assert the Markdown's wording; they prove nothing about behaviour and block rewording.
- Create `references/` only for detail some tasks need and others do not, linked from `SKILL.md` by one line saying when to read it. Reference files do not link to each other.
- Add `scripts/` only for deterministic work that is wasteful or risky to re-derive each time (API helpers with cost guards, renderers, security-sensitive file handling), with `--help`, no interactive prompts and errors that say what to try next. Scripts that execute need a `scripts/test_<name>.py` standard-library `unittest` that runs offline; the repository runs `python3 -m unittest discover -s scripts -p 'test_*.py'`.
- Add `evals/` as the behavioural specification (see below). Name any fixture that is itself a skill `SKILL.fixture.md`, so the only `SKILL.md` in a package is its own; hosts install stray ones as real skills.
- Create the directory and write `SKILL.md` directly. Match the destination to where the user's skills already live (see placement); the user's explicit path wins.

## Writing the body

Lead with what the model would get wrong: the chosen way, thresholds and limits, what needs user approval and what the agent may decide alone, what done looks like, facts it would misremember (API quirks, prices, quotas, exact commands, formats), and mistakes that actually happened. Cut numbered workflows of ordinary steps, generic advice, personas, capitalised emphasis, self-verification checklists, output templates no program parses, and "when to use" sections that repeat the description. Keep an order only where a model would get it wrong, and say why. Give one default, not a menu. Date and source facts that can go stale. Typical length is 40–150 lines; facts-and-commands skills run longer, behavioural skills shorter.

Description: third person, trigger words first, what it does and when, the nearest thing it is not for, at most 450 characters. More keywords reduce precision; name exclusions only for realistic near-misses shown by trigger evals. A skill that only the user should start gets `disable-model-invocation`, where the harness supports it; read `references/cross-harness.md` before promising any invocation control, discovery path or metadata on a given harness.

Ground facts in supplied contracts, installed `--help`, or version-matched docs before writing them, using the safest rung: documented contract, then dry run or sandbox, then read-only live call. Do not perform writes, sends or purchases to verify a draft. When guidance proves stale, propose a correction (passage, source and version, replacement, regression case) rather than silently editing an installed copy.

## Placement

`scripts/infer_destination.py [--skill-name N] [--target-harness agents|codex|copilot|gemini|opencode] [--format json]` recommends a skills root from the current repository, the family this skill runs from, and existing libraries. State the recommendation before creating a new package. Read `references/placement.md` for the decision order and recognised roots.

## Evals

`evals/evals.json` holds realistic cases (id, name, prompt, expected_output, typed assertions, fixtures under `evals/files/`) covering the smoke path, an edge, a near-miss negative, and, for multi-file skills, which reference loads for which branch. A separate trigger file uses `query` and `should_trigger`. Grade outcomes, not incidental tool sequences, and keep a case where an unconventional but valid approach must pass. A structural check is not behavioural evidence; if you cannot run model evals, say so. Read `references/testing.md` when designing or running them, including evaluator-health failures (an all-zero score from a logged-out runner says nothing about the skill).

## Libraries

Adding, merging, composing, promoting, renaming, deprecating or removing a skill changes every derived surface: catalogs, registries, routers, installer lists, dependents, evals. Update them together and search for stale names afterwards; a skill may be promoted only after its release evidence exists, and removed only after zero-reference proof. Read `references/curation.md` for ownership decisions and the affected-surface ledger. Feedback becomes a rule only after repeated evidence; merge or delete before adding.

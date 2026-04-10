---
name: better-writing
description: "Modern writing system for any prose humans read: docs, essays, explainers, PRs, memos, reports, newsletters, UI copy, and landing pages. Starts with Strunk's durable clarity rules, then routes into revision passes for structure, cadence, voice, genericity cleanup, and style-family calibration across technical, analytical, editorial, reflective, and conversion writing. Triggers on: 'rewrite this', 'make this clearer', 'tighten this', 'this sounds stiff', 'fix the voice', 'improve this memo', 'improve this doc', 'sharpen this essay', 'improve this landing page copy'. Do NOT trigger for code-only work, raw research without prose, or factual verification tasks that do not need writing help."
compatibility: "Requires: python3 for `scripts/probe_better_writing.py`, `scripts/validate.py`, and `scripts/test_skill.py`."
metadata:
  version: "1.0.0"
references:
  - foundations
  - revision-pass-stack
  - voice-and-rhythm
  - genericity-and-stiffness
  - style-bundles
  - genre-modes
  - gotchas
---

# Better writing

Build prose that is clear, specific, well-shaped, and alive on the page.

## What this extends

This skill starts from the enduring core of William Strunk Jr.'s *The Elements of Style*: active voice, positive form, specific language, disciplined paragraphs, and omitted excess.

It does not stop there.

`better-writing` adds:

- staged revision passes instead of one undifferentiated "polish" step
- cadence repair so clarity does not collapse into clipped prose
- diction and structure checks for canned, ceremonial, or generic writing
- style bundles for technical guides, operator analysis, reported writing, essays, memos, and copy
- genre routing so the opening, middle, and ending match the deliverable

## Decision tree

What kind of help does the draft need?

- You want first principles or a modernized Strunk baseline
  Read `references/foundations.md`.

- The draft is messy, bloated, or unclear and you need the right pass order
  Read `references/revision-pass-stack.md`.

- The draft is clear enough but sounds stiff, bloodless, too formal, or rhythmically flat
  Read `references/voice-and-rhythm.md` and `references/genericity-and-stiffness.md`.

- You know the deliverable but not the right shape
  Read `references/genre-modes.md`.

- The prose needs a deliberate voice family or publication-adjacent calibration
  Read `references/style-bundles.md`.

- The edit keeps getting worse with each pass
  Read `references/gotchas.md`.

## Quick reference

| Situation | Open / run | Why |
|---|---|---|
| Need the shortest operating contract | `references/revision-pass-stack.md` | pass order, stop conditions, and read-aloud tests |
| Need the classic rules plus modern corrections | `references/foundations.md` | Strunk core, updated for modern prose |
| Draft feels generic, ceremonial, or over-signposted | `references/genericity-and-stiffness.md` | cut canned scaffolds and false gravity |
| Draft feels clenched after editing | `references/voice-and-rhythm.md` | restore motion, emphasis, and voice |
| Need the right structure for a guide, memo, essay, or landing page | `references/genre-modes.md` | choose the page shape before line editing |
| Need a stronger mode for technical, editorial, operator, essay, or copy work | `references/style-bundles.md` | borrow discipline, not imitation |
| Need a quick routing hint from the terminal | `python3 scripts/probe_better_writing.py --prompt "..."` | surfaces the smallest relevant reference set |

## Default operating mode

Use this order unless there is a strong reason not to.

1. Diagnose the actual failure mode.
2. Fix paragraph architecture before sentence polish.
3. Tighten sentences without draining cadence.
4. Remove canned phrasing, false suspense, and generic abstractions.
5. Calibrate the piece to its genre and style family.
6. Read aloud and stop once the prose is clear, specific, and owned.

## Constitutional rules

### 1. Clarity before flair

Do not reach for personality, prestige, or brand tone until the reader can follow the sentence on first read.

### 2. Structure before synonyms

Weak prose usually fails because the paragraph job, sentence motion, or emphasis pattern is wrong. Swapping words around will not save it.

### 3. Cadence matters

A clear sentence can still sound dead. Good revision keeps connective tissue, contrast, and some asymmetry in sentence length.

### 4. Specificity beats force

If a sentence sounds important only because it announces its own importance, rewrite it with a sharper noun, verb, number, or consequence.

### 5. Voice is earned, not sprayed on

Do not fake humanity with random slang, empty contractions, forced jokes, or borrowed publication tics.

### 6. Genre decides the page

A memo, essay, guide, landing page, report, README, and newsletter do not open or close the same way. Pick the shape on purpose.

## Style families at a glance

| Family | Use when | Read |
|---|---|---|
| Technical teacher | explain systems, tools, docs, runbooks, and field guides | `references/style-bundles.md` |
| Operator analyst | write memos, professional deep dives, work analysis, or executive explainers | `references/style-bundles.md` |
| Reported editorial | write journalism-adjacent analysis, impact pieces, or market reporting | `references/style-bundles.md` |
| Essay and reflection | write personal, braided, reported-personal, or reflective pieces | `references/style-bundles.md` |
| Conversion copy | write landing pages, pricing pages, product pages, and CTA-heavy prose | `references/style-bundles.md` |

## Templates

- `templates/rewrite-worksheet.md`
  Use when you want a deliberate multi-pass edit log instead of vague "cleanup."

- `templates/personal-style-sheet.md`
  Use when the writing needs to sound more like one identifiable person and less like a competent average.

## Gotchas

1. If you compress every sentence, the prose will read like a cleaned transcript instead of finished writing.
2. If you fix stiffness by adding drama, you will trade one weakness for another.
3. If you borrow one writer's surface tics without their discipline, the draft will sound imitative rather than strong.
4. If you choose style before structure, the piece will feel dressed up rather than well built.
5. If the opening still does not earn the next paragraph, keep editing the opening. Do not escape into later sections.

## Reading guide

| Need | Read |
|---|---|
| The enduring rules and where they still hold | `references/foundations.md` |
| Triage, pass order, and stop conditions | `references/revision-pass-stack.md` |
| Cadence, emphasis, hedging, and read-aloud repair | `references/voice-and-rhythm.md` |
| Cutting genericity, false drama, and corporate sludge | `references/genericity-and-stiffness.md` |
| Choosing and blending style families | `references/style-bundles.md` |
| Choosing the right shape for the deliverable | `references/genre-modes.md` |
| Failure modes and recovery | `references/gotchas.md` |

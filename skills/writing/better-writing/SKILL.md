---
name: better-writing
description: "Drafts, rewrites, reviews, humanises and adapts prose (docs, wikis, product copy, memos, essays, email, UI text) without losing facts, uncertainty or voice, and rebuilds formulaic or AI-sounding language. Not for code-only work or authorship detection."
compatibility: "Optional scripts/scan_aiisms.py needs python3 3.10+."
---

# Better writing

Make prose clear, faithful, specific and recognisably the writer's own. Fidelity to the source and to the requested output beats polish at every scale.

## Scope

- Edit only natural-language prose. Never alter code, identifiers, selectors, config keys, paths, commands or other machine-readable text, even to satisfy a diction rule; in mixed content, protect it exactly.
- Protect facts, numbers, dates, names, quotations, citations, legal or technical terms, explicit uncertainty and lines that carry the writer's voice. Never turn uncertainty into confidence, and never invent experience, quotations, evidence, approval, customer language or proof. Unsupported praise is not a fact to preserve; if removing it leaves nothing, surface the evidence gap or ask for the mechanism instead of rearranging the same abstractions.
- Ask only when a missing choice would materially change the result (reader, outcome, how much change is allowed, source authority). Empty input: ask for the material. A tiny edit: do it and stop.
- Review-only requests get a diagnosis, not a rewrite: exact passages, ranked by reader impact, with a rewrite only as a labelled example.
- Fix the right layer first: whole piece (genre, order, thesis), section, paragraph (mixed jobs, buried point), sentence (unclear actor, abstraction), surface (grammar, house style). Preserve what already works; stop when remaining changes are merely different, not better. Do not compress every sentence: clipped notes lose the connective logic.
- Follow repository, organisation or locale style and exact terminology before any general guidance. Dialect, accessibility choices and second-language voice are identity, not defects.
- Human signal comes from judgement, selection and concrete detail, not fake typos, random slang or forced informality. Do not mimic a named writer's signature; translate the request into high-level traits.
- Never claim a passage was AI-written, and never use a phrase list or detector score as proof of authorship.

## Formulaic and AI-sounding language

Identify what a formula hides (the actor, mechanism, evidence, consequence) and rebuild the sentence from supported meaning. Never swap in a synonym: "bridge the gap" does not become "close the divide"; say what is missing and what changes it. "Marks a significant shift" needs the before and after; "plays a critical role", "unlocks value" and "research shows" need a supported action, result or source. If the source lacks the substance, delete, narrow or query the claim. Ordinary words, punctuation, courtesy and deliberate rhetoric are not defects, and literal, technical, legal, measured, quoted and writer-owned uses stay.

Read `references/ai-isms-and-humanisation.md` when the diagnosis of generic or machine-smooth prose is uncertain, and `references/formulaic-language-catalogue.md` for phrase families, natural rewrite moves and protected uses. Do not load both just because a sentence is being edited.

`python3 scripts/scan_aiisms.py path/to/draft.md` lists pattern matches from an explicit corpus (`--format json` for automation, `--gate` for a conservative multi-pattern cluster gate). It cannot tell whether a use is exact, genre-appropriate or evidence of authorship; judge each hit against its exceptions, and refresh the scan after edits if you rely on it.

## Punctuation

Only on an explicit request to remove, replace, limit or standardise em dashes, semicolons or colons: read `references/punctuation-and-sentence-flow.md`. Classify the relation before changing a mark, let a conjunction or clause name the logic, and protect literal punctuation in code, URLs, times, ratios, quotations and labels. Ordinary line editing implies no punctuation ban.

## Technical documentation and wikis

Establish reader, starting state, terminology and finish line before styling. Follow repository or organisation style, locale and destination constraints before the adapted Google developer documentation guidance in `references/technical-documentation-and-wikis.md`, which covers headings, procedures, links, accessibility and global-audience clarity.

## Gotchas

- A smoother edit that moved a number, condition, causal claim or degree of certainty: restore the source and make the smallest edit for the original language problem.
- Over-editing flattens cadence and grandeur replaces clarity; reread aloud and restore connective tissue.
- Chopping long prose into bullets or headings does not repair reasoning. Split at changes of job, not at arbitrary lengths, and choose paragraphs, lists or tables from the information's real shape.
- If a usage or documentation convention appears stale or conflicts with this guidance, check the applicable house style or current primary documentation, disclose unresolved gaps, and propose a sourced correction rather than editing an installed copy.

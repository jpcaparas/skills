---
name: simplified-technical-english
description: "Rewrites or audits procedures, descriptions and safety instructions against ASD-STE100 Simplified Technical English, preserving technical meaning and exact literals. Use when STE governs the text. Not for general simplification or translation."
compatibility: "Optional scripts/analyze_ste_surface.py needs Python 3.11+."
---

# Simplified Technical English

A restrictive, standard-specific skill: apply STE vocabulary, sentence, counting and safety rules only when ASD-STE100 is requested or governs the publication. Technical meaning outranks language, and a rewrite must never guess it.

## Mode

Rewrite when replacement text is asked for; audit (findings only, no replacement document) when findings are asked for. Procedures, work steps, maintenance tasks and safety text follow `references/procedures-and-safety.md`; systems, components, theory of operation and reports follow `references/descriptive-writing.md`. Segment mixed documents and apply each branch to its own blocks, then restore the original order. Read `references/terminology-and-verification.md` for every rewrite or audit: it defines the evidence modes, source precedence, the term ledger and the claim language.

Evidence mode decides what you may claim: full reference-backed review (official issue, dictionary, governed terminology and directives all available), scoped reference-backed review (a supplied profile covers a declared subset), or Issue 9-oriented rewrite (sources incomplete; list what is unverified). "Strict", "fully compliant" or "certified" means reference-backed review; if the sources are absent, say strict verification is blocked and offer a separately labelled provisional rewrite.

## Issue and sources

Issue 9 (15 January 2025) is this skill's dated baseline, not a live status claim. Use the issue governing the user's publication and never silently upgrade or mix rules or dictionary entries across issues. Verify against official ASD/STEMG sources only when issue status is uncertain, later material is supplied or the latest issue is requested. Official sources checked 2026-07-29: https://www.asd-ste100.org/ (home, FAQ, downloads, tools guidance) and the Issue 9 PDF https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf. Do not reproduce or reconstruct the standard, dictionary, examples or cover art; paraphrase and cite.

## Preserve

Before rewriting, identify what must not change and compare against it afterwards (a compact note for a short low-risk selection, a full ledger for safety-sensitive or review-bound work):

- facts, causal direction, conditions, exceptions, uncertainty, sequence; negation, polarity, comparison operators (never `<` into `≤`, `unless` into `if`, `after` into `before`, a permission into a requirement, a recommendation into a command)
- warning level, hazard, mitigation, consequence; mandated wording
- numbers, units, tolerances, ranges, part numbers, designators, product names, labels, abbreviations and approved terms
- code fences, inline code, commands, paths, URLs, identifiers, schema keys, tags, placeholders, citations, quoted regulated text, headings and markers, and everything outside the selected text. Rewrite only the natural-language prose around protected literals and compare them character for character afterwards. Do not widen a selection because adjacent prose has similar problems.

If an ambiguity changes the action, target, condition, sequence or risk (what `it` refers to, whether two actions are simultaneous, a threshold), ask a focused question or record the alternatives; do not repair it through grammar. Stop a reference-backed rewrite when unresolved ambiguity could change safety, legality or product behaviour.

## Shared surface rules (Issue 9 baseline)

Approved vocabulary only in its verified meaning and part of speech; governed technical nouns and verbs; short complete sentences without contractions; active voice (descriptive passive only when the agent is unknown); controlled verb forms and tightly limited `-ing` forms; no semicolons; one term per concept; American English spelling unless a directive requires otherwise. Limits: 20 words per procedure or safety sentence, 25 per descriptive sentence, 6 sentences per descriptive paragraph, counted under the official Issue 9 rules. Transform meaning units, not single words: order information as the reader needs it, split independent instructions, make actor, action, object, condition and result explicit, and use a vertical list when one sentence carries several items.

## Gotchas

- Splitting a sentence can detach a condition, exception, negation or consequence from its action; after splitting, recheck condition scope, sequence, threshold polarity and the hazard-mitigation link, and restore explicit connectors.
- A simple or familiar synonym is not approved by being simple. Approval depends on the dictionary entry's meaning and part of speech; if the dictionary is unavailable the decision stays unverified. An unfamiliar word is not a technical noun or verb without a drawing, parts source, specification, glossary or terminology owner.
- Do not cut a long official technical noun into an invented short name.
- Passive can preserve truth in descriptions; do not invent an actor to force active voice. In procedures, address the reader directly, and if the real actor is another person or system, keep that fact.
- `-ing` is not a raw suffix ban; it can be permitted inside governed nouns or non-verb roles. Judge scanner hits in context.
- Plain whitespace word counts do not implement the Issue 9 counting rules (parentheticals, quoted text, identifiers, numbers with units, proper nouns, labels, hyphenated words, vertical lists).
- Mandated safety, legal, regulatory or contractual wording can override STE: keep it unchanged, record the conflict, and give any STE candidate to its owner as a proposal, never as approved.
- A note informs and never hides a command; do not invent a work step from a fact, and do not turn description into instruction.

## Optional scanner

`python3 scripts/analyze_ste_surface.py --text-type procedure|description [--format json] path` (or `-` for stdin) reports surface candidates: contractions, semicolons, probable passive, `-ing` forms, coordinated actions, and an estimated word count against the limits. It ignores code, parentheticals and quoted text, has no dictionary, and targets Issue 9 only. Every hit is a candidate to judge in context; it cannot establish conformance, and do not claim it supports another issue without evidence.

## Audits and reporting

An audit diagnoses the supplied text and does not silently replace it; do no engineering, safety or legal validation through language review. Classify each finding as confirmed (the available source proves it), candidate (a signal needing judgement, such as probable passive or an unclear pronoun) or unresolved (missing technical or authoritative evidence, with an owner), with a severity (blocker when a rewrite would have to guess meaning, risk or legal force; high when a confirmed issue can change action, condition, sequence or consequence; medium; low; information). Give source location, rule or source, a short exact excerpt, explanation, a local correction only if allowed, and the evidence or owner needed. Lead with scope, evidence mode and blockers; if only findings were requested, append no full rewrite.

For a rewrite, lead with the full rewritten selection, then a compact note: evidence mode, issue and terminology source, protected literals checked, unresolved terms or conflicts, and that technical, safety, legal or organisational approval needs a human reviewer.

Say "candidate STE rewrite", "Issue 9-oriented rewrite", "checked against the supplied scoped profile" or "checked for the listed Issue 9 constraints". Never claim ASD certification, endorsement, approval or guaranteed compliance; ASD and the STEMG treat tools, including AI, as optional aids that cannot replace the writer or the standard. Never invent an approved dictionary status, meaning or part of speech, and never present provisional word choices as dictionary-approved.

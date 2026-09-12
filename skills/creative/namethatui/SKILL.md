---
name: namethatui
description: "Name unfamiliar UI components from descriptions, screenshots, live pages, or DOM/code clues; return ranked aliases, prompt-ready wording, and authoritative links without using namethatui.com. Skip implementation of already-named components."
compatibility: "Core classification is portable; helper scripts require Python 3.10+. Screenshot analysis needs local image access. Live verification uses a harness web-search tool/API or agent-browser when available."
metadata:
  version: "1.0.0"
  short-description: "Name unfamiliar UI components and return authoritative matches"
---

# namethatui

Turn “I know it when I see it” into precise UI vocabulary, evidence-backed links, and wording the user can paste into a coding-agent prompt.

## Route the evidence

Choose the strongest available input. Combine routes when the user supplies more than one.

- **Plain-language description** — extract behavior before guessing from appearance.
- **Screenshot or mockup** — read [visual intake](references/visual-intake.md); use it to separate observed geometry from behavior that an image cannot prove.
- **Live page or user-supplied URL** — inspect read-only with the active browser tool. If using agent-browser, load its current core instructions first, then inspect the accessibility tree, visible state, and relevant DOM without submitting forms or changing data.
- **DOM, code, or accessibility clues** — inspect native elements, roles, ARIA relationships, event behavior, and library component names. Treat them as evidence, not truth: implementations can be mislabeled.

Use [component families](references/component-families.md) when two or more nearby patterns could fit; use it to identify the behavior that separates them. Use [research and sources](references/research-and-sources.md) whenever links need live discovery or verification.

**Complete when:** observed facts and inferred behavior are clearly separated, and the evidence is strong enough to form candidates or is explicitly marked insufficient.

## 1. Build a clue fingerprint

Capture the clues that actually distinguish interaction patterns:

| Dimension | Questions |
| --- | --- |
| Trigger | Click, hover, focus, typing, keyboard shortcut, scroll, or automatic event? |
| Placement | Inline, anchored to a control, centered over content, attached to an edge, or persistent in layout? |
| Lifetime | Persistent, manually dismissed, selection-dismissed, timed, or present only while hovering/focused? |
| Interaction | Informational only, accepts input, selects a value, invokes an action, navigates, or reveals content? |
| Focus and modality | Can it receive focus? Is outside content usable? Does focus move or become trapped? |
| Content relationship | Help text, commands, choices, status, navigation, nested content, or a separate task? |
| Platform | Web, iOS, Android, macOS, Windows, desktop app, or a named design system? |
| Native clues | HTML element, ARIA role/state, framework component, platform class, or accessibility-tree label? |

Do not require every field. Three discriminating clues are usually enough; a single cosmetic clue rarely is.

**Complete when:** the fingerprint contains the most decision-relevant facts and records which important behaviors remain unknown.

## 2. Form a small candidate set

Generate one to three plausible names. Include:

- the common cross-platform name
- important aliases such as autocomplete/typeahead or scrim/backdrop
- a platform-native primitive or class only when a primary source supports it
- a composite description when the thing is made from several patterns, such as a command palette implemented as a dialog plus combobox/listbox behavior

Rank by behavioral fit, not keyword overlap. Use **high**, **medium**, or **low** confidence; numeric percentages imply precision the evidence does not provide.

Ask at most one focused clarifying question when one unknown behavior would reverse the ranking. Otherwise continue with the ranked candidates and make the uncertainty visible.

**Complete when:** every candidate has a reason to remain in the set and one observable fact that would strengthen or rule it out.

## 3. Research without the blocked origin

Treat a hostname as blocked when it is exactly `namethatui.com` or ends in `.namethatui.com`.

- Never navigate to, request, preview, screenshot, cache, proxy, archive, or return a link from that hostname family.
- Filter search results before opening them and before composing the answer. Immediately before every live open, run `scripts/prepare_research.py check-url` on the exact intended URL and keep that successful preflight in the visible action record. A retry or reopen is a new open: rerun the guard even when the URL is unchanged.
- Redirects count as navigation. After opening an allowed URL, inspect the final hostname; if it resolves to the blocked family, stop, close or leave the page, and discard the result.
- It is safe for an exclusion query such as `-site:namethatui.com` to contain the literal hostname because the query does not request that origin.

Use the safest available route:

1. Prefer a harness-provided web-search tool or authenticated search API. Use its domain-exclusion parameter when available and add the negative-site term as defense in depth.
2. Without search API access, use agent-browser to open the curated standards and design-system indexes in [research and sources](references/research-and-sources.md). Direct source browsing is the fallback; unattended browser searches on public search engines are frequently challenged.
3. Without either capability, use the bundled taxonomy and provide only direct source links already recorded there. Label them as not live-checked in this run.

For repeated query construction or URL checks, run:

~~~bash
python3 scripts/prepare_research.py plan --clue "typing filters a popup list" --candidate combobox --candidate autocomplete
python3 scripts/prepare_research.py check-url "https://www.w3.org/WAI/ARIA/apg/patterns/combobox/"
~~~

The URL guard establishes destination safety, not source relevance. Call a page live-checked only after opening it, inspecting the behavior or terminology it supports, and checking the final URL; otherwise label the link as not live-checked in this run.

Do not send screenshots to a third-party recognition or vision service. Analyse supplied images with the active model's local/native image capability, then search only with derived text clues.

**Complete when:** the top match has direct behavioral or platform evidence, every returned URL passed the hostname guard, and no blocked link appears in the answer.

## 4. Explain the distinction

For each candidate:

1. State the name and meaningful aliases.
2. Explain in plain language what job it performs.
3. Point to the observed clues that fit.
4. Name the closest confusable pattern and the behavior that separates them.
5. Link directly to the standard, platform guideline, or maintained design-system component—not to a search-results page.

Prefer a standards/accessibility source for semantics and a platform or design-system source for naming and examples. One strong source can be enough for a simple, standard pattern; ambiguous or vendor-specific names benefit from two independent primary sources.

**Complete when:** the user can tell both what to call the component and why that term is more accurate than the alternatives.

## Answer contract

Lead with the useful name, not the research process.

~~~markdown
## Likely component: [name]

**Confidence:** High | Medium | Low

[One-sentence plain-English explanation.]

**Why it fits**
- [Observed clue and its implication]
- [Observed clue and its implication]

**Possible matches**
1. **[Candidate / aliases]** — [why it fits; what would rule it out]. Direct example: [verified source URL].
2. **[Candidate / aliases]** — [why it remains plausible]. Direct example: [verified source URL].

**Prompt-ready wording**
> Use a [precise component phrase] that [important behavior and state].

**One thing to check**
[Only when a missing behavior could change the answer.]
~~~

Keep the candidate list to three. Omit the final question when confidence is already high. If no candidate is defensible, say “No confident match yet,” give the best search terms, and ask for the single most discriminating missing clue.

## Guardrails

1. A visual resemblance does not prove keyboard, focus, modality, or selection semantics.
2. An ARIA role or framework name can be wrong; reconcile it with actual behavior.
3. Vendor names are aliases, not universal standards. Say which system owns the term.
4. A component can be a composition. Name both the user-facing pattern and important primitives when that helps implementation.
5. Do not invent a canonical name to make the answer feel decisive.
6. Do not drift into redesign or implementation unless the user asks after identification.

## Verification

- Run `python3 scripts/validate.py .` from the skill directory.
- Run `python3 scripts/test_skill.py .` for URL-guard, query-plan, eval, and packaging checks.
- After behavioral grading, run `python3 scripts/check_benchmark_evidence.py . <benchmark.json>` to prove every current assertion was graded for every declared run and unavailable resource metrics were not presented as measurements.
- For live research, record which links were opened and ensure the final output contains no blocked hostname.

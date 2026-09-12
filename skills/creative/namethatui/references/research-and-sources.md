# Research and sources

Use this reference when candidate links need discovery or live verification. It defines the source ladder, search-tool route, direct agent-browser fallback, and blocked-host checks.

## Source ladder

Prefer sources in this order:

1. **Standards and semantic guidance** — WAI-ARIA APG, MDN, HTML/Open UI.
2. **Platform guidance** — Apple, Android/Material, Microsoft/Windows.
3. **Maintained design systems** — Fluent, Carbon, Spectrum, Polaris, GOV.UK, USWDS, or the system the user named.
4. **Library documentation** — the actual component library in the user's codebase.
5. **Secondary explanations** — only when primary sources do not cover the term; label them as secondary.

Do not use search-result snippets alone as evidence. Open the direct allowed source and confirm that its described behavior matches the clue fingerprint.

## Curated indexes

These broad indexes work well for direct browser lookup:

- [WAI-ARIA APG pattern index](https://www.w3.org/WAI/ARIA/apg/patterns/) — behavior and accessibility semantics for common widgets.
- [Open UI Component Name Matrix](https://open-ui.org/research/component-matrix/) — cross-design-system naming aliases; useful vocabulary research, not a normative standard.
- [MDN ARIA role reference](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles) — implementation semantics.
- [Fluent components](https://fluent2.microsoft.design/components/web/react/) — maintained web component examples and distinctions.
- [Carbon components](https://carbondesignsystem.com/components/overview/components/) — broad enterprise component taxonomy.
- [GOV.UK components](https://design-system.service.gov.uk/components/) — conservative, task-focused public-service patterns.
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/) — Apple platform terminology and behavior.
- [Material 3 components](https://m3.material.io/components) — Android/Material terminology and examples.

## Search API or harness search

When a web-search tool or authenticated API already exists:

1. Build two or three queries:
   - behavior and geometry without a guessed name
   - top candidate plus aliases
   - candidate plus the relevant platform or authoritative domain
2. Pass `namethatui.com` through the provider's exclude-domain field when supported.
3. Add `-site:namethatui.com` to free-text queries as defense in depth.
4. Reject blocked URLs before opening, logging as evidence, or returning them.
5. Prefer results whose titles or snippets already describe the distinguishing behavior, then verify on the direct page.

Useful query shapes:

~~~text
"anchored panel interactive content" UI component official documentation -site:namethatui.com
"combobox" autocomplete typeahead UI pattern site:w3.org OR site:developer.mozilla.org
"bottom sheet" mobile actions platform design guidelines
~~~

Use [scripts/prepare_research.py](../scripts/prepare_research.py) to create bounded queries and guard candidate URLs. It emits JSON so an agent or another tool can consume the result without parsing prose.

`check-url` proves only that the intended destination is allowed. It does not prove that a page exists or supports the claimed distinction; live verification still requires opening the page, inspecting relevant content, and checking the final URL.

## Direct agent-browser fallback

Browser-driven Google, Bing, DuckDuckGo, and Brave searches commonly present bot challenges in unattended sessions. Use agent-browser for direct source inspection instead of treating public search-engine pages as the normal fallback.

Load the installed agent-browser core guide before using the CLI. A minimal read-only route is:

~~~bash
python3 scripts/prepare_research.py check-url "https://www.w3.org/WAI/ARIA/apg/patterns/"
agent-browser --session namethatui open "https://www.w3.org/WAI/ARIA/apg/patterns/"
agent-browser --session namethatui get text body
python3 scripts/prepare_research.py check-url "https://open-ui.org/research/component-matrix/"
agent-browser --session namethatui open "https://open-ui.org/research/component-matrix/"
agent-browser --session namethatui get text body
~~~

Run the guard commands from the skill directory, or resolve the script to its installed path first. Before every later `agent-browser open`, repeat the guard for that exact candidate URL; retries and reopens also require a fresh guard, even when the URL has not changed. After opening, inspect its text and final URL. Use a distinct session name so the research does not disturb the user's other browser work, and close it when finished.

If the curated index is long, use the browser's text locator or page search for the candidate term. Resolve a link's destination, record a successful exact-URL guard, and only then click or open it.

## Blocked-host algorithm

For every proposed or final URL:

1. Parse it as an HTTP or HTTPS URL.
2. Reject credentials embedded in the URL.
3. Normalize the hostname to lowercase without a trailing dot.
4. Block the exact host `namethatui.com` and every host ending `.namethatui.com`.
5. After navigation, repeat the check on the final URL to catch redirects.

Do not evade the block through archives, translation proxies, screenshot services, cached copies, or URL shorteners.

## Evidence packet

For each retained candidate, capture:

- direct URL
- source owner
- the behavior or terminology the source supports
- whether the page was live-checked in this run
- any platform/version boundary

One source may establish several facts, but every link must earn its place. A gallery that merely looks similar is weaker than a source that states the behavior.

## Completion check

Research is complete when:

- every returned link is direct, allowed, and relevant
- the top candidate's defining behavior is supported
- aliases are attributed to the system that uses them
- blocked or unverifiable results were discarded rather than softened into evidence

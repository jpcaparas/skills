---
name: seo-analysis
description: "Framework- and language-agnostic SEO analysis skill for auditing real codebases, metadata, rendering, crawlability, canonicals, structured data, OG/social previews, internationalization, sitemaps, robots directives, internal linking, and AI-era search surface readiness. Use when a user wants a thorough SEO audit, a technical/content SEO review, metadata or schema debugging, indexability analysis, or a handoff prompt for another session to implement fixes. Triggers on: SEO audit, technical SEO, schema, canonical, hreflang, robots, sitemap, OG tags, social cards, title/meta, AI Overviews, search visibility. Do NOT trigger for paid ads, off-page link building, or rank-tracking reports without codebase analysis."
compatibility: "Requires: python3. Optional: command-line access to the target repo, local build/test tooling, and browser or HTTP tooling for rendered-page verification."
---

# seo-analysis

Audit a codebase for search visibility risks, then produce a fix-ready prompt another session can execute.

This skill is framework- and language-agnostic. Start from the live repository and rendered output, not from assumptions about React, Next.js, Rails, Laravel, Astro, WordPress, or any other stack.

## Decision Tree

What SEO problem are you solving?

- Need a full technical and on-page audit of a codebase
  - Run `python3 scripts/build_fix_prompt.py --help`
  - Read `references/methodology.md`
  - Then read `references/technical-audit.md`

- Need metadata, social preview, canonicals, or indexability checks
  - Read `references/metadata-and-previews.md`

- Need schema.org / JSON-LD / entity / rich result analysis
  - Read `references/structured-data-and-entities.md`

- Need content quality, information architecture, internal linking, or template-level page targeting analysis
  - Read `references/content-and-information-architecture.md`

- Need AI-era search guidance for crawl/render controls, preview controls, and answer-engine readiness
  - Read `references/agentic-search-and-ai-surfaces.md`

- Need the exact remediation handoff format for another session
  - Read `references/fix-prompt-spec.md`
  - Use `templates/fix-prompt-template.md`
  - Optionally generate a draft with `python3 scripts/build_fix_prompt.py --input findings.json`

- Need edge cases, policy traps, or common false positives
  - Read `references/gotchas.md`

## Quick Reference

| Task | Use | Outcome |
| --- | --- | --- |
| Run a full repo audit | `references/methodology.md` | Ordered checklist and evidence collection flow |
| Check indexability and rendering | `references/technical-audit.md` | Crawl, render, canonical, robots, sitemap, and status-code findings |
| Check titles, meta descriptions, OG, X cards, favicons, site names | `references/metadata-and-previews.md` | SERP and social preview findings |
| Check structured data and entity signals | `references/structured-data-and-entities.md` | Rich-result and graph readiness findings |
| Check content and link architecture | `references/content-and-information-architecture.md` | Content gaps, duplication, orphan pages, weak anchors |
| Check AI-era search readiness | `references/agentic-search-and-ai-surfaces.md` | Preview controls, crawl access, citation readiness |
| Produce a fix session prompt | `references/fix-prompt-spec.md` + `templates/fix-prompt-template.md` | Copy-paste prompt for a second implementation session |
| Generate a prompt draft from findings JSON | `python3 scripts/build_fix_prompt.py --input findings.json --repo /abs/path` | Structured prompt with priorities, constraints, and acceptance criteria |

## Core Workflow

1. Inspect the repository structure, routing model, page templates, layout files, and any head/metadata abstractions before drawing conclusions.
2. Inspect representative URLs or templates for each page type: home, category, product/service, article/docs, auth/account, paginated/filter pages, and utility pages.
3. Separate findings by severity and by layer:
   - Crawl/index controls
   - Render/discovery/canonicalization
   - Metadata/social preview
   - Structured data/entity signals
   - Content/internal linking/information architecture
   - Performance/page experience
   - AI-era search surface readiness
4. For every finding, capture evidence from code, built HTML, or runtime behavior. Do not speculate when you can verify.
5. Turn the findings into an implementation prompt for another session only after deduplicating root causes. One broken metadata abstraction can explain hundreds of bad pages.

## Audit Deliverables

Produce these artifacts in the response:

1. **Executive summary** — what is blocking or suppressing search visibility right now.
2. **Findings table** — severity, URL/template scope, evidence, impact, fix direction.
3. **Page-type coverage map** — which templates or routes were checked and which were not.
4. **Remediation sequence** — what to fix first, second, and later.
5. **Implementation prompt** — a clean handoff for another session to make code changes safely.

## Analysis Rules

1. Work from the rendered reality of the site, not only source files. SSR, SSG, CSR, hydration, and edge rendering change what crawlers actually receive.
2. Treat crawlability, renderability, and canonicalization as prerequisites. Title tweaks do not matter if important pages are blocked, duplicated, or undiscoverable.
3. Evaluate page types, not just single pages. SEO failures usually come from shared template logic.
4. Distinguish intentional exclusions from mistakes. Login, cart, internal search, faceted combinations, and thin utility pages are often meant to be `noindex`.
5. Check both search-result previews and social previews. Missing or conflicting Open Graph data is a distribution problem even when classic SEO looks acceptable.
6. Prefer supported structured data aligned to page purpose. Do not recommend schema spam or irrelevant types.
7. Treat AI-answer visibility as an extension of crawlability, metadata clarity, structured facts, and trustworthy content. Do not invent a separate magical “AI SEO” system.

## Reading Guide

| If the task is... | Read |
| --- | --- |
| Full audit from code to implementation handoff | `references/methodology.md`, then `references/fix-prompt-spec.md` |
| Diagnose a rendering, canonical, robots, sitemap, hreflang, or internal-link issue | `references/technical-audit.md` |
| Diagnose bad titles, snippets, link previews, or OG/X metadata | `references/metadata-and-previews.md` |
| Diagnose missing or invalid schema and weak entity markup | `references/structured-data-and-entities.md` |
| Diagnose weak topical targeting, duplication, orphan pages, or anchor text problems | `references/content-and-information-architecture.md` |
| Discuss AI Overviews, citation surfaces, or answer-engine readiness | `references/agentic-search-and-ai-surfaces.md` |
| Avoid overreaching or false positives | `references/gotchas.md` |

## Verified External Baseline

The guidance in this skill was grounded against current primary sources in April 2026, including:

- Google Search Central on SEO basics, helpful content, JavaScript SEO, robots meta directives, canonicalization, snippets, structured data, sitemaps, site names, favicons, and preferred sources.
- The Open Graph protocol specification for required OG fields and image metadata.

Use the references as the first source of truth, then verify live details when the target stack or search surface has materially changed.

## Gotchas

1. **Missing SEO is often a shared abstraction bug**: a single layout, metadata helper, or head component can poison every route.
2. **Do not treat every `noindex` as wrong**: many utility surfaces should stay out of the index.
3. **Do not recommend `robots.txt` for canonicalization**: blocking a duplicate URL in `robots.txt` can prevent crawlers from seeing the canonical signal at all.
4. **Do not assume OG tags equal SEO tags**: search titles, social titles, canonicals, and schema each serve different consumers.
5. **Do not confuse “AI SEO” with hidden hacks**: the durable wins are still crawl access, strong facts, clear metadata, and useful original content.
6. **Do not hand off a fix prompt without evidence**: the second session should receive concrete files, page types, and acceptance criteria, not generic SEO advice.

## Helper Files

- `references/methodology.md` — end-to-end audit workflow and evidence model.
- `references/technical-audit.md` — crawl, rendering, canonicals, robots, sitemaps, hreflang, pagination, internal-link discovery.
- `references/metadata-and-previews.md` — titles, descriptions, OG, X cards, favicons, site names, image previews.
- `references/structured-data-and-entities.md` — JSON-LD strategy and validation priorities.
- `references/content-and-information-architecture.md` — content quality, duplication, template targeting, and link architecture.
- `references/agentic-search-and-ai-surfaces.md` — AI-era search interpretation without hype.
- `references/fix-prompt-spec.md` — exact handoff prompt contract.
- `references/gotchas.md` — high-value traps and anti-patterns.
- `templates/fix-prompt-template.md` — copy-ready handoff prompt shell.
- `scripts/build_fix_prompt.py` — deterministic prompt builder from findings JSON.
- `scripts/probe_seo_analysis.py` — local regression checks for issue normalization and prompt generation.
- `scripts/validate.py` — structural validator for this skill.
- `scripts/test_skill.py` — packaging and deterministic probe test runner.

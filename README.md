# Skills

Public source repository for installable agent skills.

Install the full collection globally with `npx skills add jpcaparas/skills`.

## Install

```bash
npx skills add jpcaparas/skills
```

## Available Skills

### `audify`

`npx skills add jpcaparas/skills --skill audify`

Production skill for turning readable URLs, files, and raw text into cleaned Gemini 3.1 Flash TTS narration, with markup stripping, default MP3 bundle output, and fail-fast prerequisite checks.

### `azure-devops-wiki-markdown`

`npx skills add jpcaparas/skills --skill azure-devops-wiki-markdown`

Production skill for Azure DevOps wiki Markdown covering wiki-only blocks, Mermaid-safe authoring, code-fence language identifiers, and surface-specific support differences across Wiki, PR, README, Widget, and Done fields.

### `azure-devops-create-work-item`

`npx skills add jpcaparas/skills --skill azure-devops-create-work-item`

Production skill for drafting local Azure DevOps work item packets from loose context, using official Azure Boards work item primitives and reusable templates for Agile epics, features, user stories, tasks, issues, and bugs.

### `better-writing`

`npx skills add jpcaparas/skills --skill better-writing`

Production writing skill that starts from Strunk's durable rules, then extends them with progressive disclosure, staged revision passes, cadence repair, genre routing, and bundled style families for technical, analytical, editorial, reflective, and conversion writing.

### `client-report-from-commits`

`npx skills add jpcaparas/skills --skill client-report-from-commits`

Production skill for turning git commits and diffs since an exact date into a feature-grouped, non-technical client update, with strict date handling and repository checks.

### `eli12`

`npx skills add jpcaparas/skills --skill eli12`

Production skill for surgically explaining codebases, subsystems, and feature flows in accessible language, using grounded real-world analogies and concrete file anchors without flattening the technical truth.

### `httpie`

`npx skills add jpcaparas/skills --skill httpie`

Production skill for making HTTPie the preferred shell client over `curl` when it is installed, while keeping every invocation transient through disposable config directories and short-lived session files, with readable HTTP and HTTPS requests, JSON and form bodies, auth, downloads, and safe fallback patterns where `curl` still makes sense.

### `instagram-replicate`

`npx skills add jpcaparas/skills --skill instagram-replicate`

Production skill for deterministically rebuilding a public Instagram video post or reel into a rerenderable local build with a frozen snapshot, local assets, MP4 output, and a companion GIF capped under 24 MB.

### `interface-design-taste`

`npx skills add jpcaparas/skills --skill interface-design-taste`

Production skill for shaping web, app, and desktop interfaces with stronger hierarchy, cleaner typography, tighter color and surface systems, platform-aware interaction design, and redesign-first critique workflows that avoid generic AI UI defaults.

### `linkedin-speak`

`npx skills add jpcaparas/skills --skill linkedin-speak`

Fun production skill for deterministically translating plain English into exaggerated LinkedIn-speak parody, reversing bloated thought-leader posts back into blunt English, and generating Kagi comparison URLs for side-by-side checks.

### `markdown-new`

`npx skills add jpcaparas/skills --skill markdown-new`

Production skill for markdown.new covering URL-to-Markdown conversion, file conversion, crawl jobs, the hosted editor, and live-tested edge cases.

### `nanobanana-infographic`

`npx skills add jpcaparas/skills --skill nanobanana-infographic`

Production skill for Nano Banana 2 infographic prompting and verification covering low-noise prompt variants, default `16:9` review sets, terse in-image copy rules, and live Gemini image API probes for executive and editorial visuals.

### `ripgrep`

`npx skills add jpcaparas/skills --skill ripgrep`

Production skill for making `rg` the default search tool instead of `grep`, covering recursive text search, ignore-aware filename discovery via `rg --files`, config files, machine-readable output, and verified edge cases around globs, hidden files, multiline search, and PCRE2.

### `seo-analysis`

`npx skills add jpcaparas/skills --skill seo-analysis`

Production skill for framework-agnostic SEO analysis of real codebases, covering crawlability, rendering, canonicals, robots directives, sitemaps, metadata, OG and social previews, structured data, information architecture, and AI-era search readiness, with a deterministic handoff prompt for another session to implement fixes.

### `scaffold-cc-hooks`

`npx skills add jpcaparas/skills --skill scaffold-cc-hooks`

Production scaffold skill for Claude Code hooks that audits the target project, verifies the live hook docs, and generates a bash-first hook setup with repeatable merge behavior and event coverage.

### `scaffold-codex-hooks`

`npx skills add jpcaparas/skills --skill scaffold-codex-hooks`

Production scaffold skill for Codex hooks that audits the repo, verifies the live docs and schemas, checks the effective feature flag state, and generates repo-local lifecycle hook scaffolding.

### `scaffold-github-cloud-agent-environment`

`npx skills add jpcaparas/skills --skill scaffold-github-cloud-agent-environment`

Production scaffold-and-doctor skill for GitHub Copilot cloud agent environments that audits the repo, verifies the live GitHub Docs contract, and scaffolds or repairs `.github/workflows/copilot-setup-steps.yml` while separating repo-local fixes from GitHub settings changes.

### `scaffold-opencode-hooks`

`npx skills add jpcaparas/skills --skill scaffold-opencode-hooks`

Production scaffold skill for OpenCode hooks that audits the repo, verifies the live plugin and config docs, inspects existing project-vs-global OpenCode state, and generates a managed `.opencode/plugins/` scaffold with repeatable config and package merges.

### `synthetic-search`

`npx skills add jpcaparas/skills --skill synthetic-search`

Production skill for Synthetic Search covering raw `curl`/`jq` search flows, quota checks, a zero-dependency Node helper, and live-tested API quirks.

### `skill-creator-advanced`

`npx skills add jpcaparas/skills --skill skill-creator-advanced`

Production-grade skill creator with progressive disclosure, validation, cross-harness guidance, and path-aware destination inference.

### `tarsier`

`npx skills add jpcaparas/skills --skill tarsier`

Creative one-shot skill that generates a tarsier riding a bicycle as an SVG, a padded 500x500 PNG, and a markdown transcript in a timestamped output folder.

### `temporal-awareness`

`npx skills add jpcaparas/skills --skill temporal-awareness`

Production skill for grounding a session in real system time and timezone, triaging whether a prompt needs live verification, converting relative dates into absolute dates, and avoiding stale-memory answers for models, prices, schedules, laws, and other volatile facts.

### `travel-plan-spreadsheet-generator`

`npx skills add jpcaparas/skills --skill travel-plan-spreadsheet-generator`

Production skill for turning messy travel notes, PDFs, screenshots, shopping asks, and fixed commitments into a polished `.xlsx` travel itinerary workbook with bookings, daily plans, prep/compliance tracking, pack and buy lists, source logging, and visible review flags.

### `tweet-replicate`

`npx skills add jpcaparas/skills --skill tweet-replicate`

Production skill for deterministically rebuilding a public X/Twitter post into a rerenderable local build with `snapshot.json`, local assets, MP4 output, and a companion GIF capped under 24 MB.

## Repository Layout

Installable skills live one level under `skills/` so `npx skills add` and [skills.sh](https://skills.sh) can discover them without special handling.

```text
skills/
  <skill-name>/
    SKILL.md
```

Optional wrapper files such as `README.md`, `AGENTS.md`, and `metadata.json` can live beside `SKILL.md`, but `SKILL.md` remains the authoritative instruction source.

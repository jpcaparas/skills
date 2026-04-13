# Skills

Public source repository for installable agent skills.

Install the full collection globally with `npx skills add jpcaparas/skills`.

## Install

```bash
npx skills add jpcaparas/skills
```

## Available Skills

### `azure-devops-wiki-markdown`

`npx skills add jpcaparas/skills --skill azure-devops-wiki-markdown`

Production skill for Azure DevOps wiki Markdown covering wiki-only blocks, Mermaid-safe authoring, code-fence language identifiers, and surface-specific support differences across Wiki, PR, README, Widget, and Done fields.

### `better-writing`

`npx skills add jpcaparas/skills --skill better-writing`

Production writing skill that starts from Strunk's durable rules, then extends them with progressive disclosure, staged revision passes, cadence repair, genre routing, and bundled style families for technical, analytical, editorial, reflective, and conversion writing.

### `instagram-replicate`

`npx skills add jpcaparas/skills --skill instagram-replicate`

Production skill for deterministically rebuilding a public Instagram video post or reel into a rerenderable local build with a frozen snapshot, local assets, MP4 output, and a companion GIF capped under 24 MB.

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

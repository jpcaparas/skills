# Skills

Public source repository for installable agent skills.

## Install

```bash
npx skills add jpcaparas/skills
```

```bash
npx skills add https://github.com/jpcaparas/skills
```

## Available Skills

### `markdown-new`

Production skill for markdown.new covering URL-to-Markdown conversion, file conversion, crawl jobs, the hosted editor, and live-tested edge cases.

### `synthetic-search`

Production skill for Synthetic Search covering raw `curl`/`jq` search flows, quota checks, a zero-dependency Node helper, and live-tested API quirks.

### `skill-creator-advanced`

Production-grade skill creator with progressive disclosure, validation, cross-harness guidance, and path-aware destination inference.

### `temporal-awareness`

Production skill for grounding a session in real system time and timezone, triaging whether a prompt needs live verification, converting relative dates into absolute dates, and avoiding stale-memory answers for models, prices, schedules, laws, and other volatile facts.

### `tweet-replicate`

Production skill for deterministically rebuilding a public X/Twitter post into a rerenderable local build with `snapshot.json`, local assets, MP4 output, and a companion GIF capped under 24 MB.

## Repository Layout

Installable skills live one level under `skills/` so `npx skills add` and [skills.sh](https://skills.sh) can discover them without special handling.

```text
skills/
  <skill-name>/
    SKILL.md
```

Optional wrapper files such as `README.md`, `AGENTS.md`, and `metadata.json` can live beside `SKILL.md`, but `SKILL.md` remains the authoritative instruction source.

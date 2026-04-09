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

### `skill-creator-advanced`

Production-grade skill creator with progressive disclosure, validation, cross-harness guidance, and path-aware destination inference.

## Repository Layout

Installable skills live one level under `skills/` so `npx skills add` and [skills.sh](https://skills.sh) can discover them without special handling.

```text
skills/
  <skill-name>/
    SKILL.md
```

Optional wrapper files such as `README.md`, `AGENTS.md`, and `metadata.json` can live beside `SKILL.md`, but `SKILL.md` remains the authoritative instruction source.

# Skill Anatomy — Deep Dive

## Table of Contents

- [File Structure](#file-structure)
- [SKILL.md Requirements](#skillmd-requirements)
- [Frontmatter Specification](#frontmatter-specification)
- [Directory Purposes](#directory-purposes)
- [Naming Conventions](#naming-conventions)
- [Size Budgets](#size-budgets)

---

## File Structure

The Agent Skills standard (agentskills.io) defines a portable format compatible with 12+ agent harnesses including Claude Code, OpenAI Codex, Gemini CLI, Cursor, VS Code, GitHub Copilot, and others.

### Minimum Viable Skill

```
skill-name/
└── SKILL.md
```

Only SKILL.md is required. Everything else is optional but recommended for non-trivial skills.

### Production Skill (this creator's standard)

```
skill-name/
├── SKILL.md              # Entry point — <500 lines
├── README.md             # Optional thin public wrapper
├── AGENTS.md             # Optional thin agent-facing summary
├── metadata.json         # Optional public metadata
├── references/           # On-demand documentation
│   ├── README.md         # or domain-specific files
│   └── ...
├── scripts/              # Executable automation
│   └── ...
├── templates/            # Ready-to-use starter files
│   └── ...
├── evals/                # Test cases
│   └── evals.json
├── assets/               # Static resources
│   └── ...
└── agents/               # Subagent instructions
    └── ...
```

### Public Skills Repository Layout

When publishing skills in a repository meant for `npx skills add owner/repo` or [skills.sh](https://skills.sh), use the top-level public layout:

```text
repo-root/
├── README.md
├── AGENTS.md
├── CLAUDE.md
└── skills/
    └── skill-name/
        ├── SKILL.md
        ├── README.md         # Optional thin wrapper
        ├── AGENTS.md         # Optional thin wrapper
        ├── metadata.json     # Optional public metadata
        └── ...
```

This keeps repo discovery simple while still letting the skill itself stay portable.

### Large Reference Skill (60+ domains)

For skills covering many products/domains (like the Cloudflare skill), each domain gets a subdirectory with a standardized 5-file structure:

```
skill-name/
├── SKILL.md
└── references/
    ├── product-a/
    │   ├── README.md           # Overview, when to use, cross-refs
    │   ├── api.md              # API reference
    │   ├── patterns.md         # Usage patterns and workflows
    │   ├── configuration.md    # Setup and config
    │   └── gotchas.md          # Pitfalls and tribal knowledge
    ├── product-b/
    │   └── ... (same structure)
    └── shared/
        └── ... (cross-cutting concerns)
```

### Skill Composition (multiple skills)

For very large platforms, decompose into a family of skills with a shared foundation:

```
platform-shared/SKILL.md     # Auth, global flags, conventions
platform-action-a/SKILL.md   # One action per skill
platform-action-b/SKILL.md   # Thin wrapper, references shared
```

Each sub-skill's SKILL.md starts with: `> Load {{ skill:platform-shared }} first.`

---

## SKILL.md Requirements

### Structure

1. **YAML frontmatter** (required) — enclosed in `---` fences
2. **Title** — `# Skill Name` (matches the name field)
3. **One-line summary** — what this skill does, in one sentence
4. **Decision tree** — if multiple paths exist, force disambiguation early
5. **Quick reference** — most common operations in a table
6. **Pointers to references** — "Read X when you need Y"
7. **Gotchas** — non-obvious pitfalls (minimum 3 for production skills)

### What Goes in SKILL.md vs References

| SKILL.md (always loaded) | References (loaded on demand) |
|--------------------------|-------------------------------|
| Decision trees | Full API documentation |
| Quick reference tables | Detailed configuration guides |
| 1-2 line examples per operation | Complete code examples |
| Gotchas summary (top 5) | Full gotchas catalog |
| Cross-references to files | Extended patterns & workflows |

### What NOT to Include

- INSTALLATION_GUIDE.md, QUICK_REFERENCE.md, CHANGELOG.md
- Process documentation about how the skill was created
- Redundant content (same info in SKILL.md AND a reference)

For public skill repositories, a thin `README.md`, `AGENTS.md`, or `metadata.json` beside `SKILL.md` is acceptable when it improves repository presentation or marketplace metadata. Keep `SKILL.md` authoritative and avoid copying detailed procedures into the wrappers.

---

## Frontmatter Specification

### Required Fields

```yaml
---
name: skill-name        # [a-z0-9-], 1-64 chars, must match directory name
description: "..."      # Non-empty, max 1024 chars
---
```

### Optional Fields

```yaml
---
name: skill-name
description: "..."
license: MIT                          # License name or file reference
compatibility: "Requires: node >= 18" # Environment requirements
metadata:
  version: "1.0.0"                    # Semantic version
  short-description: "Brief text"     # For UI chips (OpenAI Codex)
  openclaw:                           # Registry metadata
    category: "development"
    requires:
      bins: [some-cli]
    cliHelp: "some-cli --help"
references:                           # Key reference directories (non-standard but useful)
  - domain-a
  - domain-b
---
```

### Description Writing Guide

The description is the primary trigger mechanism. Agents scan descriptions to decide whether to load a skill. Write it to maximize correct triggering:

1. **State what the skill does** — "Wrap the Stripe API for payment processing"
2. **List trigger contexts** — "Use when building payment flows, subscriptions, or marketplace payouts"
3. **Include trigger keywords** — specific terms users would say
4. **Add negative triggers** — "Do NOT trigger for general HTTP requests or non-Stripe payment providers"
5. **Be pushy** — agents undertrigger; err on the side of triggering too often

---

## Directory Purposes

### `references/`

Documentation loaded into context on demand. The agent reads these when SKILL.md points it to them.

**Best practices:**
- One file per topic or domain
- Include a TOC if >300 lines
- Cross-reference related files (one level deep)
- Working examples, not pseudocode

### `scripts/`

Executable code for deterministic or repetitive tasks. Scripts execute without being loaded into context (saving tokens).

**Best practices:**
- Use `#!/usr/bin/env python3` shebang (not `python`)
- Accept arguments via argparse or sys.argv
- Print structured output (JSON preferred)
- Include `--help` with usage examples

### `templates/`

Ready-to-use starter files that can be copied and modified. Unlike scripts (which execute), templates are starting points.

**Examples:** Shell script templates, config file starters, boilerplate code

### `evals/`

Test cases for verifying the skill works correctly. Always contains at least `evals.json`.

### `assets/`

Static files used in the skill's output — HTML templates, icons, fonts, data files.

### `agents/`

Instructions for spawning specialized subagents. Each `.md` file contains the system prompt for one subagent type.

---

## Naming Conventions

| Element | Rule | Example |
|---------|------|---------|
| Skill name | `[a-z0-9-]`, 1-64 chars | `stripe-api` |
| Directory name | Must match `name` field exactly | `stripe-api/` |
| Reference files | Descriptive, lowercase, hyphens | `webhook-patterns.md` |
| Script files | Descriptive, lowercase, underscores | `validate_config.py` |
| Domain directories | Product/domain name, lowercase | `references/payments/` |

Prefer short, verb-led phrases for skill names. Namespace by tool for clarity:
- `gh-review-pr` (GitHub tool)
- `stripe-create-checkout` (Stripe tool)
- `aws-deploy-lambda` (AWS tool)

---

## Size Budgets

| Component | Target | Hard Limit |
|-----------|--------|------------|
| Frontmatter description | 100-300 chars | 1024 chars |
| SKILL.md body | <300 lines | 500 lines |
| Individual reference file | <500 lines | 1000 lines (needs TOC) |
| Total skill (all files) | Varies | No limit, but disclosure must work |
| Script file | <200 lines | No limit |

If approaching any limit, restructure by moving content to references or splitting into sub-skills.

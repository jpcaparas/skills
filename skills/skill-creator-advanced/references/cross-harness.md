# Cross-Harness Compatibility

## Table of Contents

- [Agent Skills Standard Overview](#agent-skills-standard-overview)
- [Supported Platforms](#supported-platforms)
- [Discovery Paths](#discovery-paths)
- [Required vs Optional Frontmatter](#required-vs-optional-frontmatter)
- [Platform-Specific Extensions](#platform-specific-extensions)
- [Installation via npx](#installation-via-npx)
- [What Works Everywhere vs Platform-Specific](#what-works-everywhere-vs-platform-specific)
- [Script Portability](#script-portability)

---

## Agent Skills Standard Overview

The Agent Skills standard (agentskills.io) defines a portable format for packaging instructions, reference documentation, and automation scripts that any AI agent harness can consume.

Core principle: a skill is a directory containing a `SKILL.md` file with YAML frontmatter. Everything else is optional. This minimum viable format works across all supporting harnesses because the contract is simple -- the harness reads frontmatter for metadata and loads the markdown body as instructions.

The standard does NOT specify:
- How the harness decides to load a skill (each harness has its own triggering mechanism)
- How reference files are loaded (Read tool, file inclusion, etc.)
- How scripts are executed (Bash tool, subprocess, etc.)
- How the skill interacts with the user (this is harness-dependent)

What the standard DOES specify:
- Directory structure conventions
- Frontmatter field names and types
- File naming rules
- Portability expectations

---

## Supported Platforms

| Platform | SKILL.md | References | Scripts | Subagents | Notes |
|----------|----------|------------|---------|-----------|-------|
| Claude Code | Full | Full | Full | Full | Primary development target |
| OpenAI Codex | Full | Full | Full | Limited | Add `agents/openai.yaml` for UI |
| Gemini CLI | Full | Full | Full | Limited | Add `metadata.openclaw` for registry |
| Cursor | Full | Full | Full | No | Skills load as context rules |
| VS Code (Copilot) | Full | Full | Partial | No | Markdown-only context |
| GitHub Copilot | Full | Read-only | No | No | No script execution |
| AMP | Full | Full | Full | Yes | Similar capabilities to Claude Code |
| OpenCode | Full | Full | Full | Limited | Open-source harness |

"Full" means the platform can read, load, and act on that component.
"Partial" means the component is loaded but execution may be restricted.
"No" means the component is not supported on that platform.

---

## Discovery Paths

How each platform finds and loads skills.

For public source repositories consumed by `npx skills add owner/repo`, the lowest-friction layout is:

```text
skills/<skill-name>/SKILL.md
```

The installer also searches common project and agent-specific roots such as `.agents/skills/`, `.claude/skills/`, `.codex/skills/`, and related directories.

### Claude Code

Skills are discovered from:
1. `~/.claude/skills/` (user-level)
2. `.claude/skills/` (project-level)
3. Installed via `.skill` files

Triggering: Claude reads all `name` + `description` fields at session start. Decides to load SKILL.md body based on description match to user query.

### OpenAI Codex

Skills are discovered from:
1. `.agents/skills/` (project-level via `skills` CLI conventions)
2. `~/.codex/skills/` (user-level)
3. `.codex/skills/` (seen in some local setups and worth treating as compatible when scanning existing skills)
4. The `agents/` directory (for openai.yaml UI integration)

Triggering: Similar metadata scan. The `agents/openai.yaml` file provides UI display metadata.

### Gemini CLI

Skills are discovered from:
1. `.gemini/skills/` (project-level)
2. `~/.gemini/skills/` (user-level)

Triggering: Metadata scan with `openclaw` fields used for categorization in the Gemini ecosystem.

### Cursor

Skills are discovered from:
1. `.cursor/skills/` (project-level)
2. Cursor rules (`.cursorrules` can reference skills)

Triggering: Skills are loaded as enhanced context. Cursor may load them proactively based on file type or project context.

### VS Code (GitHub Copilot)

Skills are discovered from:
1. `.github/copilot-instructions.md` (can reference skill files)
2. `.vscode/skills/` (project-level)

Triggering: Loaded as workspace context. Limited to markdown instructions -- no script execution.

### AMP

Skills are discovered from:
1. `.amp/skills/` (project-level)
2. `~/.amp/skills/` (user-level)

Triggering: Full skill loading with subagent support.

### OpenCode

Skills are discovered from:
1. `.opencode/skills/` (project-level)
2. `~/.opencode/skills/` (user-level)

Triggering: Metadata-based, similar to Claude Code.

---

## Required vs Optional Frontmatter

### Universal (all platforms)

```yaml
---
name: skill-name          # Required. [a-z0-9-], 1-64 chars.
description: "..."        # Required. Non-empty, max 1024 chars.
---
```

These two fields are the only requirement for cross-platform compatibility. If a skill has valid `name` and `description`, it will work on every platform that supports Agent Skills.

### Commonly Supported Optional Fields

```yaml
---
name: skill-name
description: "..."
license: MIT                              # License identifier
compatibility: "Requires: python3"        # Human-readable requirements
---
```

### Extended Metadata (platform-specific)

```yaml
---
name: skill-name
description: "..."
metadata:
  version: "1.0.0"                        # Semantic version
  short-description: "Brief text"         # UI chip text (Codex, Gemini)
  openclaw:                               # Registry metadata
    category: "development"
    requires:
      bins: [some-cli]                    # Required binaries
    cliHelp: "some-cli --help"            # Help command for validation
  references:                             # Cloudflare-style reference listing
    - domain-a
    - domain-b
---
```

---

## Platform-Specific Extensions

### OpenAI Codex: agents/openai.yaml

For Codex UI integration, add an `agents/openai.yaml` file in the skill directory:

```yaml
# agents/openai.yaml
display_name: "Stripe API Helper"
short_description: "Wrap Stripe API for payments, subscriptions, and Connect"
default_prompt: "Help me integrate Stripe payments into my application"
icon: "credit-card"
```

| Field | Required | Description |
|-------|----------|-------------|
| `display_name` | Yes | Name shown in Codex UI |
| `short_description` | Yes | One-line description for UI card |
| `default_prompt` | No | Pre-filled prompt when user clicks the agent |
| `icon` | No | Icon identifier for UI display |

This file is ignored by non-Codex harnesses. Safe to always include.

### Google Ecosystem: metadata.openclaw

For Gemini CLI and Google ecosystem tools, add `openclaw` fields to the frontmatter metadata:

```yaml
metadata:
  openclaw:
    category: "development"           # Skill category for registry
    subcategory: "api-integration"    # Finer classification
    requires:
      bins: [curl, jq]               # Required CLI tools
      env: [STRIPE_SECRET_KEY]        # Required environment variables
    cliHelp: "curl --version"         # Command to validate installation
    tags: ["payments", "stripe", "api"]
```

| Field | Required | Description |
|-------|----------|-------------|
| `category` | Yes (for registry) | Top-level category |
| `subcategory` | No | Finer classification |
| `requires.bins` | No | CLI tools the skill needs |
| `requires.env` | No | Environment variables needed |
| `cliHelp` | No | Validation command |
| `tags` | No | Searchable tags |

### Cloudflare-Style: references List

Some harnesses use a `references` list in frontmatter to enumerate key reference directories:

```yaml
references:
  - workers
  - pages
  - kv
  - d1
```

This is informational -- it tells the harness what reference domains exist. It does NOT change how files are loaded (that is still driven by SKILL.md pointers).

---

## Installation via npx

Skills can be installed across platforms using the `npx` installer:

```bash
npx skills add owner/repo
npx skills add https://github.com/owner/repo
npx skills add https://github.com/owner/repo/tree/main/skills/skill-name
```

This command:
1. Clones or fetches the source repository (or URL)
2. Discovers `SKILL.md` files in standard locations such as `skills/` and `.agents/skills/`
3. Places selected skills in the platform's skill directory (auto-detected)
4. Validates the `SKILL.md` frontmatter

For local installation (not from registry):

```bash
npx skills add /path/to/skill-repo
npx skills add /path/to/skill-repo --list
npx skills add /path/to/skill-repo --skill my-skill
```

For the least friction, publish skills in a repository with a top-level `skills/` directory and one skill per child folder.

---

## What Works Everywhere vs Platform-Specific

### Universal (safe to include in any skill)

| Component | Works on all platforms |
|-----------|-----------------------|
| SKILL.md with frontmatter | Yes |
| `name` and `description` fields | Yes |
| Markdown body with instructions | Yes |
| `references/` directory with .md files | Yes |
| Decision trees in SKILL.md | Yes |
| Quick reference tables | Yes |
| Cross-references between files | Yes |
| `evals/evals.json` | Yes (ignored if platform doesn't support evals) |

### Platform-Dependent (include but don't rely on)

| Component | Depends on |
|-----------|-----------|
| `scripts/` execution | Platform has Bash/Python execution |
| `agents/` subagent spawning | Platform supports subagents |
| `agents/openai.yaml` | OpenAI Codex only |
| `metadata.openclaw` | Google ecosystem only |
| Live file read from `references/` | Platform has file read tools |

### Design Principle

Write skills that degrade gracefully. The core instructions in SKILL.md should work even if scripts cannot execute and references cannot be read. The skill gets better with those capabilities, but it should not be useless without them.

Example: instead of "Run `scripts/validate.py` to check the config", write "Run `scripts/validate.py` to check the config. If scripts are not available, manually verify: [checklist of things the script checks]."

---

## Script Portability

### Rules

1. **Use `python3`**, not `python`. Some systems only have `python3` on PATH.
2. **Use `#!/usr/bin/env python3`** shebang, not `#!/usr/bin/python3` (path varies).
3. **Use `#!/usr/bin/env bash`** for shell scripts, not `#!/bin/bash`.
4. **No platform-specific paths.** Use `os.path.expanduser("~")` not `/Users/username/`.
5. **No platform-specific tools.** Use `curl` (universal) not `wget` (not on macOS by default).
6. **Standard library only** for Python scripts. No `pip install` requirements unless documented in `compatibility`.
7. **JSON output** for scripts that produce structured data. All platforms can parse JSON.
8. **Exit codes**: 0 for success, 1 for failure. Include `--help` flag.
9. **No interactive input.** Scripts must accept all parameters via arguments or environment variables.
10. **UTF-8 encoding.** Assume UTF-8 everywhere.

### Testing Portability

If you're unsure whether a script is portable:

```bash
# Check shebang
head -1 script.py  # Should be #!/usr/bin/env python3

# Check for platform-specific paths
grep -n '/Users/\|/home/\|C:\\' script.py  # Should find nothing

# Check for non-standard imports
python3 -c "import ast; tree = ast.parse(open('script.py').read()); [print(n.names[0].name) for n in ast.walk(tree) if isinstance(n, ast.Import)]"
```

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

The Agent Skills format provides a portable core recognized by multiple agent harnesses. Verify current platform-specific behavior before promising discovery, script execution, or invocation controls.

### Minimum Viable Skill

```
skill-name/
└── SKILL.md
```

Only `SKILL.md` is universally required. A production release should also have meaningful evals, but every other artifact is earned by behavior rather than created as empty scaffolding.

### Production Skill (earned structure)

```
skill-name/
├── SKILL.md              # Entry point — <500 lines
├── README.md             # Optional thin public wrapper
├── AGENTS.md             # Optional thin agent-facing summary
├── metadata.json         # Optional public metadata
├── references/           # Optional: branch-only documentation
│   ├── README.md         # or domain-specific files
│   └── ...
├── scripts/              # Optional: deterministic automation
│   └── ...
├── templates/            # Optional: copyable starter files
│   └── ...
├── evals/                # Release evidence
│   └── evals.json
├── assets/               # Optional: static output resources
│   └── ...
└── agents/               # Optional: supported specialized roles
    └── ...
```

### Public Skills Repository Layout

When the repository's installer or discovery contract uses a top-level `skills/` directory, keep the canonical packages under that root:

```text
repo-root/
├── README.md
└── skills/
    └── skill-name/
        ├── SKILL.md
        ├── README.md         # Optional thin wrapper
        ├── AGENTS.md         # Optional thin wrapper
        ├── metadata.json     # Optional public metadata
        └── ...
```

This keeps repo discovery simple while still letting the skill itself stay portable.

### Domain-Heavy Reference Skill

When several domains share the same access pattern, a consistent five-file layout can reduce navigation cost. Use only the files each domain earns; do not create empty siblings to satisfy the example:

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

Compose a family when jobs need independent invocation but share a stable prerequisite or reference. Do not split only because the package is large:

```
platform-shared/SKILL.md     # Auth, global flags, conventions
platform-action-a/SKILL.md   # One action per skill
platform-action-b/SKILL.md   # Thin wrapper, references shared
```

Express the prerequisite using a mechanism the target harness actually supports. If symbolic skill references are documented, a sub-skill can say `> Load {{ skill:platform-shared }} first.` Otherwise use a plain instruction such as `> Invoke the installed platform-shared skill first.` and verify name-based discovery. If neither form resolves reliably, keep the shared requirement inline or package it through the repository's documented dependency mechanism.

---

## SKILL.md Requirements

### Structure

1. **YAML frontmatter** (required) — enclosed in `---` fences
2. **Title or immediate purpose** — make the skill's job obvious
3. **Ordered steps** — only when the skill is procedural; give each a checkable completion criterion
4. **Early routing** — only when distinct branches need disambiguation
5. **Quick reference** — only when repeated operations benefit from scanning
6. **Conditional pointers** — name when to load a support file and what decision or action it supports
7. **Evidenced gotchas** — include non-obvious pitfalls that actually exist; do not invent a quota

### What Goes in SKILL.md vs References

| SKILL.md (needed by every branch) | References (branch-only material) |
|--------------------------|-------------------------------|
| Ordered steps and completion criteria | Full API documentation |
| Shared invariants and safety bounds | Detailed configuration guides |
| Early branch routing where needed | Complete branch-specific examples |
| Conditional context pointers | Extended patterns and workflows |

### What NOT to Include

- Extra files that merely rename a section already reachable from `SKILL.md`
- Process documentation about how the skill was created
- Redundant content (same info in SKILL.md AND a reference)

For public skill repositories, a thin `README.md`, `AGENTS.md`, or `metadata.json` beside `SKILL.md` is acceptable when repository policy needs presentation or marketplace metadata. Keep `SKILL.md` authoritative and derive or validate shared fields instead of copying detailed procedures.

---

## Frontmatter Specification

### Required Fields

```yaml
---
name: skill-name        # ^[a-z0-9]+(?:-[a-z0-9]+)*$, 1-64 chars; matches directory
description: "..."      # Non-empty, max 1024 chars
---
```

### Harness-Contract-Specific Optional Fields

Fields beyond `name` and `description` are not uniformly portable. Include an optional field only when the target harness or repository contract documents it, and test that unknown consumers either preserve or safely ignore it.

```yaml
---
name: skill-name
description: "..."
license: MIT                          # When the contract accepts license metadata
compatibility: "Requires: runtime X"  # When the contract exposes requirements
metadata:
  version: "1.0.0"                    # Repository-defined release metadata
  short-description: "Brief text"     # Harness-defined presentation field
  target-harness:                     # Replace with the documented namespace
    category: "development"
    requires:
      bins: [some-cli]
    cliHelp: "some-cli --help"
references:                           # Only when the contract defines this field
  - domain-a
  - domain-b
---
```

### Description Writing Guide

Use the canonical description and invocation rules in `SKILL.md` Phase 2. This anatomy reference adds only the format boundary: `description` is a frontmatter scalar, while manual-only or model-invoked controls belong to documented harness-specific fields and their target-native validation.

---

## Directory Purposes

### `references/`

Documentation intended for conditional loading. The target harness may expose it through file reads, retrieval, or another mechanism; verify the promised behavior.

**Best practices:**
- Organize by a branch's access pattern, not by arbitrary topic count
- Include a TOC if >300 lines
- Use condition-and-purpose pointers; keep navigation shallow
- Match example precision to the intended freedom: keep executable examples syntactically valid and label pseudocode or parameterized forms clearly

### `scripts/`

Executable code for deterministic or repetitive tasks. A capable harness can run a script without reasoning over its full implementation, but do not assume every harness can execute it.

**Best practices:**
- Add a script only when it makes a repeated or fragile operation safer and the consumer has a supported execution path
- Choose a runtime already available in the declared target environment; use its portable launcher convention rather than assuming one language
- Accept explicit arguments through the runtime's conventional parser and avoid hidden machine-local state
- Emit stable, documented output suited to the consumer; use a structured format when another tool must parse it
- Provide help and examples for scripts people or agents are expected to invoke directly

### `templates/`

Ready-to-use starter files that can be copied and modified. Unlike scripts (which execute), templates are starting points.

**Examples:** Shell script templates, config file starters, boilerplate code

### `evals/`

Test cases for structural, behavioral, invocation, disclosure, and near-miss evidence. A release contains a non-empty `evals.json`; a draft may start empty but cannot be promoted that way.

### `assets/`

Static files used in the skill's output — HTML templates, icons, fonts, data files.

### `agents/`

Instructions for spawning specialized subagents. Each `.md` file contains the system prompt for one subagent type.

---

## Naming Conventions

| Element | Rule | Example |
|---------|------|---------|
| Skill name | `^[a-z0-9]+(?:-[a-z0-9]+)*$`, 1-64 chars | `payments-api` |
| Directory name | Must match `name` field exactly | `payments-api/` |
| Reference files | Descriptive, lowercase, hyphens | `webhook-patterns.md` |
| Script files | Descriptive, lowercase, underscores | `validate_config.py` |
| Domain directories | Product/domain name, lowercase | A concrete domain subdirectory under references |

Prefer short, verb-led phrases for skill names. Namespace by tool or domain when it prevents collisions, such as `forge-review-change`, `payments-create-checkout`, or `cloud-deploy-function`.

---

## Size Budgets

| Component | Review signal | Release ceiling |
|-----------|--------|------------|
| Frontmatter description | Every word should improve invocation | 1024 chars or the target harness's lower limit |
| SKILL.md body | Keep the always-loaded path legible | 500 lines for this creator's release profile |
| Individual reference file | Add navigation when scanning becomes costly | 1000 lines for this creator's release profile |
| Total skill (all files) | Varies | No limit, but disclosure must work |
| Script file | One coherent operation | No universal line limit |

Treat size as evidence to inspect the information hierarchy, not as an automatic split rule. Disclose branch-only material first. Split only when a job needs independent invocation or a real context boundary fixes observed premature completion.

## See Also

- `references/curation.md` — invocation ownership, branch ledgers, lifecycle, and publication surfaces
- `references/patterns.md` — context pointers, co-location, granularity, and degrees of freedom
- `references/testing.md` — release evidence for the resulting structure

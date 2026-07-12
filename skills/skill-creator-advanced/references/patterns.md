# Patterns Catalog

## Table of Contents

- [Progressive Disclosure Patterns](#progressive-disclosure-patterns)
- [Branch and Content Ledger](#branch-and-content-ledger)
- [Degrees of Freedom Framework](#degrees-of-freedom-framework)
- [Content Organization Patterns](#content-organization-patterns)
- [The 5-File Reference Structure](#the-5-file-reference-structure)
- [Decision Tree Pattern](#decision-tree-pattern)
- [Completion Criteria](#completion-criteria)
- [Split and Merge Decisions](#split-and-merge-decisions)
- [Cross-Reference Rules](#cross-reference-rules)

---

## Progressive Disclosure Patterns

Skills can place behavior across four authoring layers. On harnesses that document startup metadata and on-demand body loading, the goal is a legible common path rather than token minimization at the expense of reliable behavior. Verify the actual loading contract elsewhere.

### Level 0 — Metadata (startup context when supported)

The `name` and `description` from frontmatter. For discoverable skills, this context pointer must represent each invocation branch once without synonym piles.

### Level 1 — SKILL.md body (loaded through the harness's documented route)

The full `SKILL.md` body after frontmatter. It contains the steps, shared rules, and early routing every invocation needs. A decision tree or quick reference is optional furniture earned by the branch shape.

### Level 2 — References (loaded on demand)

Files in `references/` that `SKILL.md` points to conditionally. Verify actual loading behavior on the target harness.

### Level 3 — Scripts (executed when supported)

Files in `scripts/` carry deterministic or repetitive work. A capable harness can execute them without reasoning over the whole implementation, but script execution is not universal.

### Choosing a Pattern

| Access pattern | Pattern |
|---|---|
| One linear job or one flat peer set of rules | **Flat** — keep the useful material in `SKILL.md` |
| Several branches share a core but need different detail | **Hub and spoke** — route from `SKILL.md` to conditional references |
| Several domains repeat a real setup/API/pattern/gotcha access shape | **Domain directories** — use consistent earned files per domain |
| Jobs need independent invocation but share stable prerequisites | **Skill composition** — separate owners with an explicit dependency contract |

### Pattern: Flat (everything in SKILL.md)

For small, focused skills. No references needed.

```
skill/
└── SKILL.md (all content here, <500 lines)
```

Use for a focused procedure or a reference-only skill whose rules are all needed together. A flat peer set is valid; do not invent branches merely to create disclosure.

### Pattern: Hub and Spoke

`SKILL.md` acts as a router. Each reference file covers a branch-specific decision or action, not merely a topic that was convenient to split.

```
skill/
├── SKILL.md (decision tree + quick ref + pointers)
└── references/
    ├── auth.md
    ├── streaming.md
    ├── tool-use.md
    └── error-codes.md
```

SKILL.md contains a reading guide:

```markdown
## Reading Guide

| Task | Read |
|------|------|
| Basic API call | `references/overview.md` |
| Streaming responses | `references/streaming.md` |
| Function calling | `references/tool-use.md` |
| Error handling | `references/error-codes.md` |
```

### Pattern: Domain Directories

Use when many domains genuinely share a predictable access pattern. A domain gets only the files it needs.

```
skill/
├── SKILL.md (decision trees + product index)
└── references/
    ├── product-a/
    │   ├── README.md
    │   ├── api.md
    │   ├── patterns.md
    │   ├── configuration.md
    │   └── gotchas.md
    └── product-b/
        └── ...
```

SKILL.md contains decision trees that route to the right product, plus a product index table.

### Pattern: Skill Composition

Compose when the parts need independent reachability—not merely because the package is large:

1. **Shared owner** — reusable behavior another skill must reach independently
2. **Action skills** — independently invoked jobs with distinct trigger language
3. **Workflow skills** — orchestration that depends only on reachable skills

```
platform-shared/SKILL.md       # Prerequisites
platform-send/SKILL.md         # Declares a supported dependency on platform-shared
platform-read/SKILL.md
platform-workflow-X/SKILL.md   # Orchestrates send + read
```

Verify the target harness can express each dependency. Two explicit-only skills may need a human router or plain shared reference rather than claiming they can invoke each other.

---

## Branch and Content Ledger

Build the canonical branch-and-artifact ledger from `SKILL.md` Phase 2 before selecting a pattern. This catalog adds two access questions to each branch: how often is the material needed, and can the target harness reliably reach it on demand? Use those answers to choose flat, hub-and-spoke, domain-directory, or composition patterns without copying the placement rules here.

---

## Degrees of Freedom Framework

How tightly should your skill constrain the agent? It depends on how fragile the operation is.

### High Freedom (flexible)

Multiple valid approaches exist. The agent should choose based on context.

**Style:** Text instructions explaining tradeoffs. No specific commands.

**When:**
- Architecture decisions
- Design patterns
- Code organization
- Error handling strategy

**Example:**
```markdown
## Failure Handling
Classify failures using the verified contract. Retry only outcomes the contract
marks retryable, preserve the original error when attempts are exhausted, and
choose the retry mechanism that fits the target stack.
```

### Medium Freedom (guided)

A preferred pattern exists, but alternatives are acceptable.

**Style:** Pseudocode or parameterized examples. Show the recommended approach, mention alternatives.

**When:**
- Common workflows with established patterns
- SDK usage with multiple valid approaches
- Configuration with sensible defaults

**Example:**
```markdown
## Result Encoding
Prefer the tool's documented structured result when another program consumes
the output. Human-readable output is acceptable for interactive inspection.
Preserve the caller's requested encoding when the contract supports it.
```

### Low Freedom (exact)

The operation is fragile. Specific syntax, exact commands, or precise configuration required.

**Style:** Copy-paste commands with exact parameters. No room for interpretation.

**When:**
- API auth headers and token formats
- Config file syntax (YAML, TOML, JSON schemas)
- Version-specific CLI commands
- Database migration commands
- Deployment scripts

**Example:**
```markdown
## Verified Manifest Identifier
For the supported tool version, the manifest key is exactly `artifact-id`.
`artifact_id` and `artifactId` are rejected by that version. Preserve the
hyphenated spelling in generated manifests and validate with the tool's
documented parse-only command.
```

---

## Content Organization Patterns

### Quick Reference First, Deep Dive Second

Use a quick reference when the same operations recur and scanning is faster than prose. Do not add one to a linear procedure or flat rule set that gains nothing from it:

```markdown
## Quick Reference

| Goal | Verified route |
|------|----------------|
| Inspect current state | `records status --format json` |
| Preview a proposed change | `records apply --preview` |
| Apply an authorized change | `records apply --confirm` |

For detailed documentation on each operation, see `references/commands.md`.
```

### Conditional Loading

Load different content based on an observable condition. State the purpose as well as the target:

```markdown
## Stack-Specific Setup

Detect the target stack, then read only its earned route:

- Stack A → read `references/stack-a-setup.md`; use it to choose installation and verification commands
- Stack B → read `references/stack-b-setup.md`; use it to choose installation and verification commands

Add only stacks the skill actually supports; this routing shape is illustrative, not an exhaustive language list.
```

### Centralized Shared Conventions

For skill families, centralize shared behavior only when the dependency is reachable on the target harness. Use that harness's documented dependency mechanism; otherwise identify the installed skill by name and verify name-based discovery:

```markdown
## Prerequisites

> Invoke the installed `platform-shared` skill when authentication or global flags are in scope; use it to establish the request contract before continuing.
```

If neither symbolic nor name-based invocation is reliable, keep the shared rule inline or use the repository's supported dependency metadata instead of claiming composition works.

---

## The 5-File Reference Structure

This is an optional pattern for domains that repeatedly need the same five access surfaces. Omit any file that would be empty or filler, and prefer a flatter layout when the branch map does not justify the structure.

### `README.md` — Overview

- What this product/domain is
- When to use it (and when NOT to)
- "See Also" links to related domains
- Quick start (1-2 commands to get going)

### `api.md` — API Reference

- Endpoints, methods, types
- Request/response formats
- Authentication requirements
- Rate limits and quotas

### `patterns.md` — Usage Patterns

- Common workflows (happy paths)
- Integration examples
- Best practices
- Performance tips

### `configuration.md` — Setup & Config

- Installation steps
- Configuration file formats
- Environment variables
- Binding/integration setup

### `gotchas.md` — Pitfalls & Tribal Knowledge

Use this file for evidenced pitfalls not obvious from the primary reference:

- Hard-to-debug errors and their solutions
- Undocumented limits or behaviors
- Common mistakes (with corrections)
- Version-specific quirks
- "We learned this the hard way" notes

---

## Decision Tree Pattern

Use a decision tree when the skill has genuinely distinct branches that need early disambiguation. A linear procedure or flat peer set does not need one.

### Structure

```
Need to [category]?
├── [criteria A] → product-a/
├── [criteria B] → product-b/
├── [criteria C] → product-c/
└── [criteria D] → product-d/
```

### Rules

1. Start with the user's goal, not the product name
2. Give each branch one owner; state precedence when overlap is unavoidable
3. Leaf nodes point to specific reference files
4. Keep the tree scannable; split the display when it becomes hard to route reliably
5. Put the most common choice first

### Task-to-File Mapping

Add a task-to-file mapping only when it improves on the tree instead of duplicating it:

| Task | Files to Read |
|------|--------------|
| New project setup | `README.md` + `configuration.md` |
| Implement a feature | `README.md` + `api.md` + `patterns.md` |
| Debug an issue | `gotchas.md` |
| Optimize performance | `patterns.md` (performance section) |

---

## Completion Criteria

Every ordered step ends with a condition the agent can observe. Make it exhaustive where partial coverage is the likely failure.

| Weak activity | Strong criterion |
|---|---|
| Review the skill | Every existing behavior is marked preserved, changed, merged, or removed |
| Update the docs | Every governed catalog, wrapper, registry, router, and dependent agrees with the canonical skill |
| Test the examples | Every example has passing evidence or an explicit limitation |

Sharpen the criterion before splitting a sequence. Introduce a real context boundary only when an irreducibly fuzzy phase repeatedly ends early.

## Split and Merge Decisions

Split when:

- a branch has distinct trigger language and must be reached independently
- another skill must reach the behavior independently and the harness supports it
- a real context boundary fixes observed premature completion after sharper criteria failed

Keep together when:

- branches share the same invocation contract and process
- conditional reference can hide branch-only detail
- the only reason to split is line count

Merge when skills compete for the same trigger and follow substantially the same process. Use `references/curation.md` to reconcile their lifecycle and publication surfaces.

## Cross-Reference Rules

1. **Keep answer paths shallow** — a task should not require chasing an accidental chain of references.
2. **Include "See Also" sections** — at the bottom of each reference, list related files
3. **Use relative paths** — `references/cross-harness.md`, not absolute machine paths
4. **Encode condition and purpose** — "Read `references/testing.md` when behavioral evidence is in scope; use it to choose the evaluator and result contract"
5. **Don't duplicate** — information lives in ONE place. Reference it, don't copy it.

## See Also

- `references/curation.md` — invocation ownership, lifecycle, pruning, and publication surfaces
- `references/anatomy.md` — earned package artifacts and release ceilings
- `references/testing.md` — disclosure, invocation, and completion evidence

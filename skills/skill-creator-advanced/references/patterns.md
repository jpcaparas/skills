# Patterns Catalog

## Table of Contents

- [Progressive Disclosure Patterns](#progressive-disclosure-patterns)
- [Degrees of Freedom Framework](#degrees-of-freedom-framework)
- [Content Organization Patterns](#content-organization-patterns)
- [The 5-File Reference Structure](#the-5-file-reference-structure)
- [Decision Tree Pattern](#decision-tree-pattern)
- [Cross-Reference Rules](#cross-reference-rules)

---

## Progressive Disclosure Patterns

Skills use a three-level loading system. The goal: minimize tokens loaded while maximizing usefulness.

### Level 0 — Metadata (always in context)

The `name` + `description` from frontmatter. Approximately 100 tokens. This is all agents see before deciding to load a skill.

### Level 1 — SKILL.md body (loaded on trigger)

The full SKILL.md content after frontmatter. Target <500 lines. Contains: decision trees, quick references, and pointers to deeper content.

### Level 2 — References (loaded on demand)

Files in `references/` that SKILL.md points to. Only loaded when the agent determines it needs deeper information for the current task.

### Level 3 — Scripts (executed, not loaded)

Files in `scripts/` that are executed as commands. Their contents are never loaded into context — only their output is.

### Choosing a Pattern

| Total content size | Pattern | Example skill |
|-------------------|---------|---------------|
| <500 lines | **Flat** — everything in SKILL.md | `gws-gmail-send` |
| 500-2000 lines | **Hub and spoke** — SKILL.md + flat reference files | `claude-api` |
| 2000-10000 lines | **Domain directories** — decision trees + 5-file refs | `cloudflare` |
| >10000 lines | **Skill composition** — family of related skills | `gws-*` family |

### Pattern: Flat (everything in SKILL.md)

For small, focused skills. No references needed.

```
skill/
└── SKILL.md (all content here, <500 lines)
```

When to use: Simple commands, single API endpoints, focused utilities.

### Pattern: Hub and Spoke

SKILL.md acts as a router. Each reference file covers one topic.

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
| Basic API call | `references/README.md` |
| Streaming responses | `references/streaming.md` |
| Function calling | `references/tool-use.md` |
| Error handling | `references/error-codes.md` |
```

### Pattern: Domain Directories

For skills covering many products. Each domain gets its own directory with standardized files.

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

For platforms large enough that a single skill would be unwieldy. Decompose into:

1. **Shared skill** — auth, global flags, conventions (loaded as prerequisite)
2. **Action skills** — one per operation or service (thin, focused)
3. **Workflow skills** — multi-step cross-service recipes (compose action skills)

```
platform-shared/SKILL.md       # Prerequisites
platform-send/SKILL.md         # > Load {{ skill:platform-shared }} first
platform-read/SKILL.md
platform-workflow-X/SKILL.md   # Orchestrates send + read
```

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
## Error Handling
Handle API errors at the boundary. For transient errors (429, 503), implement
exponential backoff. For auth errors (401, 403), surface to the user immediately.
The specific retry library is up to you.
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
## Authentication
Prefer OAuth2 with PKCE flow for web apps. Service accounts are acceptable
for server-to-server communication.

```python
# Recommended: OAuth2 with PKCE
client = AuthClient(flow="pkce", client_id=os.environ["CLIENT_ID"])

# Alternative: Service account (server-to-server only)
client = AuthClient(service_account="/path/to/key.json")
```
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
## API Authentication
Every request requires this exact header format:

```bash
curl -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     https://api.example.com/v1/endpoint
```

The `Bearer` prefix is required. Do not use `Token` or `Basic`.
```

---

## Content Organization Patterns

### Quick Reference First, Deep Dive Second

Lead with the most common operations in a scannable format:

```markdown
## Quick Reference

| Operation | Command |
|-----------|---------|
| List items | `tool list --format json` |
| Create item | `tool create --name "X"` |
| Delete item | `tool delete --id ID` |

For detailed documentation on each operation, see `references/commands.md`.
```

### Conditional Loading

Load different content based on user context:

```markdown
## Language-Specific Setup

Detect the project language, then read the appropriate file:

- Python project → read `references/python.md`
- TypeScript project → read `references/typescript.md`
- Go project → read `references/go.md`
```

### Centralized Shared Conventions

For skill families, centralize common patterns:

```markdown
## Prerequisites

> Read `../shared/SKILL.md` for authentication, global flags, and security rules.
> Everything below assumes you've read the shared reference.
```

---

## The 5-File Reference Structure

For each domain/product in a large skill, use exactly these 5 files:

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

The highest-value content in many skills. Encodes things not obvious from official docs:

- Hard-to-debug errors and their solutions
- Undocumented limits or behaviors
- Common mistakes (with corrections)
- Version-specific quirks
- "We learned this the hard way" notes

---

## Decision Tree Pattern

Decision trees force disambiguation. Instead of listing all options, they mirror how a developer thinks: start with a goal, narrow to a solution.

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
2. Each branch should be mutually exclusive (no overlap)
3. Leaf nodes point to specific reference files
4. Keep trees to 5-10 branches (split into multiple trees if larger)
5. Put the most common choice first

### Task-to-File Mapping

After the decision tree, include a task-to-file mapping:

| Task | Files to Read |
|------|--------------|
| New project setup | `README.md` + `configuration.md` |
| Implement a feature | `README.md` + `api.md` + `patterns.md` |
| Debug an issue | `gotchas.md` |
| Optimize performance | `patterns.md` (performance section) |

---

## Cross-Reference Rules

1. **One level deep only** — SKILL.md can reference files in `references/`. A reference file can reference a sibling. A reference file referencing another reference that references another reference is too deep.
2. **Include "See Also" sections** — at the bottom of each reference, list related files
3. **Use relative paths** — `references/auth.md`, not absolute paths
4. **Explain when to follow the reference** — "Read `references/streaming.md` when building chat UIs that display responses incrementally"
5. **Don't duplicate** — information lives in ONE place. Reference it, don't copy it.

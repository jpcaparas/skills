# Blueprints

## Table of Contents

- [API Wrapper Blueprint](#api-wrapper-blueprint)
- [CLI Tool Blueprint](#cli-tool-blueprint)
- [Progressive Docs Blueprint](#progressive-docs-blueprint)

---

## API Wrapper Blueprint

### When to Use

Use this blueprint when wrapping a REST API, GraphQL API, or SDK into a skill. The skill will help agents make correct API calls with proper auth, request formatting, and error handling.

**Indicators:** The source material is API documentation. There are endpoints, methods, request/response schemas. The skill must produce working HTTP calls or SDK invocations.

### Required Research Phase

Before writing a single line of the skill, gather:

1. **Authentication pattern** -- which one?
   - API key in header (`Authorization: Bearer <key>` or `X-API-Key: <key>`)
   - OAuth2 (client credentials, authorization code, PKCE)
   - Service account / JSON key file
   - Session-based (cookie, CSRF token)
   - Multiple patterns (different for server vs. client)

2. **Base URL and versioning**
   - Is the API versioned in the URL path (`/v1/`, `/v2/`)?
   - Is it versioned via header (`API-Version: 2024-01-01`)?
   - What happens when you call an old version? Does it 404 or silently degrade?
   - Pin the exact version in your skill. Never use "latest" or omit the version.

3. **Endpoint inventory** -- group by domain
   - CRUD operations (create, read, update, delete)
   - Search / list / filter (pagination patterns!)
   - Admin / config / metadata
   - Webhook / event operations
   - Async operations (jobs, polling)

4. **Pagination**
   - Cursor-based (`starting_after`, `ending_before`)
   - Offset-based (`offset`, `limit`)
   - Page-based (`page`, `per_page`)
   - Link header (GitHub-style)
   - What is the default page size? What is the max?

5. **Rate limits and quotas**
   - Requests per second/minute
   - Daily/monthly quotas
   - Per-endpoint limits (some APIs limit writes more than reads)
   - How are limits communicated? (headers, 429 response, error body)
   - Retry-After header support

6. **Error codes**
   - Standard HTTP codes the API actually returns
   - API-specific error codes (Stripe's `card_declined`, etc.)
   - Error response format (JSON with `error.message`? `error.code`?)
   - Idempotency support (safe to retry?)

7. **SDK vs raw HTTP**
   - Does an official SDK exist for the user's language?
   - Is the SDK well-maintained (check last release date)?
   - Does the SDK handle auth, pagination, retries automatically?
   - If the SDK is thin, raw HTTP with clear examples may be better.

8. **Gotchas** -- test at least one real call to discover:
   - Content-Type requirements (some APIs reject `application/json` without charset)
   - Required headers beyond auth (User-Agent, Accept, Idempotency-Key)
   - Field name casing (camelCase vs snake_case)
   - Null vs absent fields (some APIs treat them differently)
   - Expand/include parameters (Stripe-style nested object expansion)

### Directory Structure

```
api-skill/
SKILL.md
references/
  api.md              # Full endpoint reference
  patterns.md         # Common workflows (create-then-poll, pagination loops)
  configuration.md    # Auth setup, environment variables, SDK install
  gotchas.md          # API-specific pitfalls and tribal knowledge
scripts/
  test_connection.sh  # Verify auth works (safe, read-only call)
evals/
  evals.json
agents/
  .gitkeep
templates/
  .gitkeep
assets/
  .gitkeep
```

### SKILL.md Skeleton

```markdown
---
name: {{SKILL_NAME}}
description: "{{DESCRIPTION}}"
---

# {{API_NAME}} API Skill

Wraps the {{API_NAME}} API for [primary use case].

## Authentication

{{AUTH_PATTERN}} -- [1-3 sentences on how to authenticate]

## Quick Reference

| Operation | Method | Endpoint | Notes |
|-----------|--------|----------|-------|
| List X    | GET    | /v1/x    | Paginated, cursor-based |
| Create X  | POST   | /v1/x    | Requires field A, B |
| Get X     | GET    | /v1/x/:id | Expandable |
| Update X  | PATCH  | /v1/x/:id | Partial update |
| Delete X  | DELETE | /v1/x/:id | Irreversible |

## Decision Tree

What do you need to do?

- Create / manage resources -> references/api.md (CRUD section)
- Set up auth or configure -> references/configuration.md
- Build a multi-step workflow -> references/patterns.md
- Debug an error or unexpected behavior -> references/gotchas.md

## Gotchas

1. {{GOTCHA_1}}
2. {{GOTCHA_2}}
3. {{GOTCHA_3}}

## Reading Guide

| Task | Read |
|------|------|
| Endpoint details, request/response formats | references/api.md |
| Pagination, webhooks, async patterns | references/patterns.md |
| Auth setup, env vars, SDK installation | references/configuration.md |
| Known pitfalls and workarounds | references/gotchas.md |
```

### Reference File Organization

- **api.md**: One section per endpoint group. Each endpoint gets method, URL, required params, optional params, response shape, and a working curl/SDK example.
- **patterns.md**: Numbered workflow sections. Each workflow shows the full sequence (create -> poll -> fetch result). Include pagination loop template and retry pattern.
- **configuration.md**: Step-by-step setup. Environment variables table. SDK installation for each language. Config file format if applicable.
- **gotchas.md**: Numbered entries. Each has: symptom, cause, fix. Self-improving -- new discoveries get appended.

### Verification Checklist

- [ ] At least one API call has been executed and returned expected output
- [ ] Auth example includes the exact header format, tested against the real API
- [ ] Every endpoint in the quick reference table exists in api.md with full documentation
- [ ] Pagination pattern includes the loop termination condition
- [ ] Error codes section covers at least: 400, 401, 403, 404, 429, 500
- [ ] Rate limit information is documented with source (docs link or observed behavior)
- [ ] SDK version is pinned if an SDK is recommended
- [ ] All curl examples include required headers (not just auth)

### Example: Stripe API Skill

The `stripe-best-practices` skill follows this pattern. It covers auth (API keys in header), endpoint groups (Checkout Sessions, PaymentIntents, Connect), decision trees for choosing between integration surfaces, and gotchas about deprecated APIs and platform fee handling.

---

## CLI Tool Blueprint

### When to Use

Use this blueprint when wrapping a command-line tool into a skill. The skill will help agents invoke the tool with correct subcommands, flags, and output handling.

**Indicators:** The user mentions a CLI tool by name. The source material is man pages, `--help` output, or CLI documentation. The skill must produce correct shell commands.

### Required Research Phase

1. **Subcommand discovery**
   - Run `tool --help` and capture the full output
   - Run `tool <subcommand> --help` for each major subcommand
   - Identify the subcommand hierarchy (some tools nest: `tool group subcommand`)
   - Group subcommands by function (CRUD, config, debug, info)

2. **Flag documentation**
   - Required vs optional flags per subcommand
   - Short vs long flag forms (`-v` vs `--verbose`)
   - Flags that take arguments vs boolean flags
   - Mutually exclusive flags
   - Global flags vs subcommand-specific flags
   - Default values for optional flags

3. **Version pinning**
   - Run `tool --version` and record the output
   - Check if flag syntax changed between versions (common source of broken examples)
   - Document the minimum supported version
   - If the tool auto-updates, note this in gotchas

4. **Shell compatibility**
   - Does the tool work in bash, zsh, fish?
   - Are there shell-specific quoting issues? (e.g., `!` in bash history expansion)
   - Does it use stdin/stdout/stderr correctly?
   - Pipe compatibility (can output be piped to jq, grep, etc.?)

5. **Output formats**
   - Default output format (text, table, JSON, YAML)
   - How to request JSON output (`--format json`, `--output json`, `-o json`)
   - Is the text output parseable or human-only?
   - Exit codes (0 for success, specific codes for specific errors?)

### Directory Structure

```
cli-skill/
SKILL.md
references/
  commands.md         # Full subcommand reference
  patterns.md         # Common workflows and pipelines
  configuration.md    # Installation, shell setup, config files
  gotchas.md          # Shell quirks, version issues, common mistakes
scripts/
  check_install.sh    # Verify tool is installed and version is correct
evals/
  evals.json
agents/
  .gitkeep
templates/
  .gitkeep
assets/
  .gitkeep
```

### SKILL.md Skeleton

```markdown
---
name: {{SKILL_NAME}}
description: "{{DESCRIPTION}}"
---

# {{TOOL_NAME}} CLI Skill

Wraps the `{{TOOL_NAME}}` command-line tool for [primary use case].

**Version:** {{VERSION}} | **Install:** `{{INSTALL_CMD}}`

## Quick Reference

| Task | Command |
|------|---------|
| List items | `{{TOOL}} list --format json` |
| Create item | `{{TOOL}} create --name "X"` |
| Get details | `{{TOOL}} show ID` |
| Delete item | `{{TOOL}} delete ID --force` |

## Subcommand Groups

What do you need to do?

- Manage resources -> references/commands.md (CRUD section)
- Set up or configure the tool -> references/configuration.md
- Build a multi-step workflow -> references/patterns.md
- Fix an error -> references/gotchas.md

## Gotchas

1. {{GOTCHA_1}}
2. {{GOTCHA_2}}
3. {{GOTCHA_3}}

## Reading Guide

| Task | Read |
|------|------|
| Full command reference | references/commands.md |
| Pipelines, scripting, automation | references/patterns.md |
| Installation, config, shell setup | references/configuration.md |
| Known bugs, version quirks | references/gotchas.md |
```

### Reference File Organization

- **commands.md**: One section per subcommand group. Each subcommand gets: synopsis, flags table, working example, output sample.
- **patterns.md**: Multi-step workflows (deploy pipeline, backup + restore, CI/CD integration). Shell scripting patterns (loops, conditionals on exit codes, output parsing).
- **configuration.md**: Installation methods (brew, apt, npm, cargo). Config file location and format. Shell completions. Environment variables.
- **gotchas.md**: Shell quoting issues. Flag syntax that changed between versions. Undocumented behaviors. Error messages and what they actually mean.

### Verification Checklist

- [ ] `tool --version` output matches the documented version
- [ ] Every command in the quick reference runs without error (or with `--dry-run`)
- [ ] Flag syntax is correct for the documented version (short and long forms)
- [ ] Output format flag is documented and tested
- [ ] Installation command works on the target platform
- [ ] Shell quoting is correct in all examples (especially with spaces, special chars)
- [ ] Exit codes are documented for at least success and the most common error

### Example: `gh` (GitHub CLI) Skill

A `gh-cli` skill would cover: subcommand groups (repo, issue, pr, release, workflow), auth (`gh auth login`), output formats (`--json` flag with `--jq` filtering), and gotchas like `gh api` paginating differently than `gh pr list`.

---

## Progressive Docs Blueprint

### When to Use

Use this blueprint for large reference skills covering many domains, products, or topics. The skill's primary value is organizing knowledge for efficient retrieval rather than wrapping a single API or tool.

**Indicators:** The subject has 10+ distinct topics or products. No single API or CLI -- it's a knowledge domain. The skill needs to route to the right reference file based on the user's question.

### Required Research Phase

1. **Domain mapping**
   - List every product/topic/area that needs coverage
   - Group by category (compute, storage, networking, security, etc.)
   - Identify cross-cutting concerns (auth, billing, monitoring) that span domains
   - Determine the total estimated line count across all topics

2. **Decision trees**
   - How does a user choose between products? (What question do they start with?)
   - Build a tree from the user's goal to the specific product
   - Multiple trees may be needed (by task, by scale, by cost, by feature)

3. **Scale thresholds**

   | Domains | Structure | Example |
   |---------|-----------|---------|
   | 1-5 | Flat references in `references/` | `claude-api` |
   | 6-15 | 5-file structure per domain | `cloudflare` |
   | 16-30 | 5-file structure + shared directory | Large platform |
   | 30+ | Skill composition (multiple skills) | `gws-*` family |

4. **Cross-referencing plan**
   - Which domains reference each other?
   - Map "See Also" links before writing
   - Ensure no circular chains longer than 2 hops (A -> B is OK, A -> B -> C is not)

### Directory Structure

For 6-15 domains:

```
docs-skill/
SKILL.md
references/
  domain-a/
    README.md
    api.md
    patterns.md
    configuration.md
    gotchas.md
  domain-b/
    README.md
    api.md
    patterns.md
    configuration.md
    gotchas.md
  shared/
    auth.md
    conventions.md
evals/
  evals.json
scripts/
  .gitkeep
agents/
  .gitkeep
templates/
  .gitkeep
assets/
  .gitkeep
```

For 30+ domains, decompose into a skill family instead.

### SKILL.md Skeleton

```markdown
---
name: {{SKILL_NAME}}
description: "{{DESCRIPTION}}"
---

# {{PLATFORM_NAME}} Skill

Covers {{DOMAIN_COUNT}} products/services in the {{PLATFORM_NAME}} ecosystem.

## Decision Tree

What are you trying to do?

- Store data
  - Key-value -> references/kv/
  - Relational -> references/database/
  - Object/blob -> references/storage/
- Run code
  - Serverless functions -> references/functions/
  - Containers -> references/containers/
  - Edge/CDN -> references/edge/
- Secure your app
  - Auth -> references/auth/
  - WAF/DDoS -> references/security/
  - Secrets -> references/secrets/

## Product Index

| Product | Category | Reference | When to use |
|---------|----------|-----------|-------------|
| Product A | Storage | references/product-a/ | Storing files and blobs |
| Product B | Compute | references/product-b/ | Running serverless code |
| ... | ... | ... | ... |

## Shared Conventions

Authentication, naming, and global flags apply across all products.
Read `references/shared/auth.md` before using any product reference.

## Reading Guide

| Task | Read |
|------|------|
| Choose a product | This file (decision tree above) |
| Set up auth | references/shared/auth.md |
| Use product X | references/product-x/README.md first |
| Debug an issue | references/product-x/gotchas.md |
```

### The 5-File Reference Structure

Each domain directory contains exactly 5 files (see `references/patterns.md` for details):

1. **README.md** -- overview, when to use, quick start, "See Also" links
2. **api.md** -- API reference (endpoints, methods, types, schemas)
3. **patterns.md** -- common workflows and integration patterns
4. **configuration.md** -- setup, config files, environment variables
5. **gotchas.md** -- pitfalls, limits, tribal knowledge

Not every file needs to be long. A simple product might have a 20-line gotchas.md. But the structure is consistent, so the agent always knows where to look.

### Cross-Referencing

- Every `README.md` ends with a "See Also" section linking related domains
- Cross-references are one level deep only: `README.md -> ../other-domain/README.md`
- Never reference a file that itself references another file to complete its answer
- SKILL.md links to domain directories; domain files link to siblings and adjacent domains

### Verification Checklist

- [ ] Every product in the decision tree has a corresponding reference directory
- [ ] Every reference directory has all 5 files (README, api, patterns, configuration, gotchas)
- [ ] Decision tree branches are mutually exclusive (no product appears in two branches)
- [ ] Cross-references resolve to real files
- [ ] No reference chain goes deeper than 2 hops
- [ ] Shared conventions file exists and is referenced from SKILL.md
- [ ] Product index table is complete and matches the directory structure
- [ ] Total SKILL.md is under 500 lines

### Example: Cloudflare Skill

The `cloudflare` skill covers Workers, Pages, KV, D1, R2, AI, Vectorize, Tunnel, Spectrum, WAF, DDoS, and more. Each product gets a reference directory. SKILL.md contains decision trees organized by task (deploy, store, secure, serve) and a product index. The `references/shared/` directory covers Wrangler CLI and authentication patterns used across all products.

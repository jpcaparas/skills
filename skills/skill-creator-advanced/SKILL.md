---
name: skill-creator-advanced
description: "Advanced skill creator for mission-critical, installable skills — API wrappers, progressively-disclosed technical documentation, CLI tool integrations, and complex multi-reference skills. Use when creating or improving skills that demand rigorous progressive disclosure, verified examples, tested operations, cross-harness compatibility, smart placement into the right repo-local or global skills directory, and self-improvement feedback loops. Triggers on: 'advanced skill', 'create API skill', 'create wrapper skill', 'production skill', 'installable skill', 'improve this skill for progressive disclosure', 'rigorous skill', 'mission-critical skill', or when skill-creator's output needs to be more thorough. Also use when upgrading an existing skill to production quality."
---

# Advanced Skill Creator

Creates and improves mission-critical skills with enforced progressive disclosure, verified operations, self-improving feedback loops, and destination-aware scaffolding. This skill is for advanced use cases where shortcuts are unacceptable.

This skill differs from `{{ skill:skill-creator }}` in four ways: (1) it enforces a structured blueprint phase before writing, (2) it verifies all examples and operations actually work, (3) it produces skills with a complete directory scaffold including tests, and (4) it chooses the destination root intelligently instead of assuming the current working directory.

## When to Use This vs `{{ skill:skill-creator }}`

```
What kind of skill are you building?

├── Quick utility, style guide, simple workflow
│   └── Use `{{ skill:skill-creator }}` (lighter, faster iteration)
│
├── API wrapper, CLI tool integration, SDK reference
│   └── Use THIS skill (operations must be verified)
│
├── Large reference skill (60+ products/domains)
│   └── Use THIS skill (progressive disclosure is critical)
│
├── Upgrading an existing skill to production quality
│   └── Use THIS skill (restructuring for disclosure)
│
└── Anything where "it works on the first try" matters
    └── Use THIS skill
```

---

## Phase 0: Intake

Ask the user ONE question: **"What are you building a skill for?"**

From their answer, infer everything you can. Then present a brief plan (3-5 bullets) and ask for confirmation. Only ask follow-up questions if genuinely ambiguous. The goal is autonomy after the first answer.

Before writing files, determine the destination root:

1. If the user gave an explicit path, use it.
2. Otherwise inspect the current repo, the current installation context, and common global skill roots. Use `scripts/infer_destination.py` or apply the same logic manually.
3. Prefer a repo-local skill root when the current repo already stores skills there.
4. Otherwise prefer the currently installed skill family or the global root with the most existing skills.
5. If nothing is established yet, default to `<repo-root>/.agents/skills/` inside a git repo, or the current harness's global root outside a repo.

Always tell the user where the skill will be created before scaffolding it:

```text
Recommended destination: <skills-root>/<skill-name>
Reason: <one sentence based on existing skills or current install context>
Alternative: <optional fallback path if there is a reasonable second choice>
```

Treat that recommendation as author-time context only. Do not copy it into the generated skill's `SKILL.md`, `README.md`, `AGENTS.md`, or `metadata.json`.

Classify the skill into a blueprint type:

| Blueprint | When to use | Template |
|-----------|-------------|----------|
| API Wrapper | Wrapping an external API or SDK | `templates/api-wrapper/` |
| CLI Tool | Wrapping a command-line tool | `templates/cli-tool/` |
| Progressive Docs | Large reference/documentation skill | `templates/progressive-docs/` |
| Custom | None of the above | Build from anatomy |

Read the relevant template and `references/blueprints.md` for the chosen type. Read `references/placement.md` when the destination is not obvious.

---

## Phase 1: Research & Discovery

Before writing a single line, gather ground truth. This phase is non-negotiable.

### For API Wrappers

1. **Fetch the actual API docs** — use WebFetch, Firecrawl, or context7 MCP to get current documentation
2. **Identify auth patterns** — API key, OAuth, service account, bearer token
3. **List all endpoints/operations** — group by domain (CRUD, admin, analytics, etc.)
4. **Find rate limits, quotas, pricing** — these go in gotchas
5. **Test a real API call** — execute at least one operation to verify the API is reachable and the auth pattern works. Save the working command to `scripts/`

### For CLI Tools

1. **Run `--help`** on the tool and capture output
2. **Identify subcommands** — group by function
3. **Test the most common operation** — execute it and verify output
4. **Find version** — pin the version in the skill

### For Progressive Docs

1. **Map the domain** — list all products/topics that need coverage
2. **Identify the decision tree** — how does a user choose between options?
3. **Estimate reference count** — if >20 references, plan for the 5-file structure (see `references/patterns.md`)

### For Improving Existing Skills

1. **Read the entire existing skill** — SKILL.md + all references, scripts, assets
2. **Run `scripts/validate.py`** against it to get a structural audit
3. **Identify disclosure gaps** — content that should be in references but is inline, or vice versa
4. **Preserve what works** — don't rewrite from scratch unless structurally broken

---

## Phase 2: Architecture

Design the skill structure before writing content. Read `references/anatomy.md` for the full specification.

### Required Directory Structure

Every skill produced by this creator has ALL of these directories, even if some start empty:

```
skill-name/
├── SKILL.md              # Required — <500 lines, progressive disclosure entry point
├── README.md             # Optional — thin public wrapper for marketplace/repo presentation
├── AGENTS.md             # Optional — thin agent-facing summary when publishing in a public repo
├── metadata.json         # Optional — public metadata for repository presentation
├── references/           # On-demand deep-dive documentation
│   └── .gitkeep
├── scripts/              # Executable code for deterministic/repetitive tasks
│   └── .gitkeep
├── templates/            # Ready-to-use starter files (if applicable)
│   └── .gitkeep
├── evals/                # Test cases and assertions
│   └── evals.json
├── assets/               # Static files (images, data, HTML templates)
│   └── .gitkeep
└── agents/               # Subagent instructions (if applicable)
    └── .gitkeep
```

The `.gitkeep` files ensure empty directories are tracked. Remove them when real files are added. If you add public wrapper files, keep `SKILL.md` authoritative and avoid duplicating detailed instructions.

### Frontmatter Rules

```yaml
---
name: skill-name          # Lowercase, hyphens, digits. Must match directory name. Max 64 chars.
description: "..."        # Max 1024 chars. Primary trigger mechanism. Be pushy — see below.
# Optional:
# license: MIT
# compatibility: "Requires: node >= 18, API key for X"
# metadata:
#   version: "1.0.0"
#   openclaw:
#     category: "development"
#     requires:
#       bins: [some-cli]
---
```

**Description writing**: The description is how agents decide to load your skill. Write it like you're convincing someone to open the file. Include: what it does, when to trigger, trigger keywords, and explicit negative triggers (when NOT to use). The Anthropic guidance says to be "pushy" because agents undertrigger.

### Progressive Disclosure Design

Read `references/patterns.md` for the full catalog of patterns. Choose one:

| Content size | Pattern | Example |
|-------------|---------|---------|
| <500 lines total | Everything in SKILL.md | `gws-gmail-send` |
| 500-2000 lines | SKILL.md + flat references | `claude-api` |
| 2000-10000 lines | Decision trees + domain references | `cloudflare` |
| >10000 lines | Skill composition (multiple skills) | `gws-*` family |

Design the disclosure layers:
1. **Layer 0** (always loaded): Frontmatter name + description (~100 tokens)
2. **Layer 1** (on trigger): SKILL.md body — decision trees, quick reference, pointers
3. **Layer 2** (on demand): Reference files — deep dives loaded when needed
4. **Layer 3** (on execute): Scripts — run without loading into context

If the skill is being published in a public source repository for `npx skills add`, place it under `skills/<skill-name>/` whenever that repo already uses the standard public layout.

---

## Phase 3: Write

Write the skill following the architecture from Phase 2. Apply these rules in order:

### SKILL.md Body Rules

1. **Open with a one-line summary** of what this skill does
2. **Decision tree within the first 50 lines** — if there are multiple paths, force disambiguation early
3. **Quick reference table** — the most common operations in a scannable table
4. **Pointers to references** — explicit "Read `references/X.md` when you need Y" guidance
5. **Gotchas section** — at least 3 non-obvious pitfalls. This is the highest-value content
6. **Stay under 500 lines** — if approaching this, move content to references

### Reference File Rules

For skills with >3 reference files, use the 5-file structure per domain:

```
references/<domain>/
├── README.md           # Overview, when to use, cross-references
├── api.md              # API reference (endpoints, methods, types)
├── patterns.md         # Common workflows and usage patterns
├── configuration.md    # Setup, config, environment
└── gotchas.md          # Pitfalls, limits, tribal knowledge
```

For smaller skills, flat files in `references/` are fine. Each reference file should:
- Have a table of contents if >300 lines
- Include cross-references to related files (one level deep only)
- Contain working examples, not pseudocode

### Writing Style

- **Imperative form**: "Run this command" not "You should run this command"
- **Explain the why**: Prefer reasoning over MUST/NEVER directives
- **Add what the agent lacks, omit what it knows**: Don't restate general programming knowledge
- **Match specificity to fragility**: High freedom for flexible tasks, low freedom for brittle operations
- **Working examples over prose**: If you can show it in 5 lines of code, don't explain it in 50 words

### Degrees of Freedom

See the Degrees of Freedom Framework in `references/patterns.md`. Quick version:

| Freedom | When | Style |
|---------|------|-------|
| High | Multiple valid approaches | Text instructions, explain tradeoffs |
| Medium | Preferred pattern exists | Pseudocode or parameterized examples |
| Low | Operations are fragile/exact | Specific scripts, copy-paste commands |

API auth, config file formats, and version-specific syntax are LOW freedom. Design patterns and architecture choices are HIGH freedom.

---

## Phase 4: Verify

This is what separates this skill from `{{ skill:skill-creator }}`. Every operation in the skill must be verified.

### Verification Checklist

Run through this checklist and fix failures before proceeding:

1. **Structure validation** — run `scripts/validate.py <skill-path>` from this skill's directory
2. **Example verification** — for EACH code example or command in the skill:
   - If it's an API call: execute it (or a safe variant) and confirm it returns expected output
   - If it's a CLI command: run it with `--help` or `--dry-run` to confirm syntax is correct
   - If it's a code snippet: write it to a temp file and syntax-check it (parse, don't execute unsafe code)
3. **Cross-reference integrity** — every file path mentioned in SKILL.md must exist
   - For first-class skill or agent mentions in reusable instructions, always use symbolic refs: `{{ skill:<name> }}` and `{{ agent:<name> }}`.
   - Apply the symbolic form even in quick load-order lists, numbered steps, tables, and examples. Do not fall back to plain backticked primitive names if the symbolic form already works.
   - Reserve literal file paths for actual support files, scripts, templates, configs, or data files that must be opened or executed directly.
4. **Disclosure metrics** — SKILL.md must be <500 lines; no reference file >1000 lines without a TOC
5. **Description coverage** — the frontmatter description must mention every major capability

### Automated Validation

Run the validator from this skill's scripts directory:

```bash
python3 /path/to/skill-creator-advanced/scripts/validate.py /path/to/new-skill/
```

This checks: frontmatter format, directory structure, line counts, cross-references, naming conventions.

---

## Phase 5: Test

Create test cases that exercise the skill with realistic prompts.

### Writing Evals

Save to `<skill-name>/evals/evals.json`:

```json
{
  "skill_name": "example-skill",
  "created_by": "skill-creator-advanced",
  "evals": [
    {
      "id": 1,
      "name": "descriptive-test-name",
      "prompt": "Realistic user prompt with specifics — file paths, context, detail",
      "expected_output": "What a correct response looks like",
      "assertions": [
        {
          "text": "Output contains a working API call",
          "type": "functional"
        }
      ],
      "tags": ["smoke", "api-wrapper"]
    }
  ]
}
```

### Test Categories

Every skill needs at least one test from each applicable category:

| Category | What it tests | Minimum |
|----------|--------------|---------|
| Smoke | Basic happy path works | 1 |
| Edge case | Boundary conditions, unusual inputs | 1 |
| Negative | Should-not-trigger or error handling | 1 |
| Disclosure | Correct reference file is loaded for a given query | 1 (if multi-reference) |

### Running Tests

Use the eval infrastructure from `{{ skill:skill-creator }}` (it's compatible):

```bash
# From the skill-creator directory:
python -m scripts.run_eval --skill-path <new-skill> --eval-path <new-skill>/evals/evals.json
```

Or run the lightweight test script from this skill:

```bash
python /path/to/skill-creator-advanced/scripts/test_skill.py <skill-path>
```

---

## Phase 6: Self-Improvement Protocol

This skill learns from feedback. Read `references/self-improvement.md` for the full protocol.

### Feedback Capture

When the user comments on a generated skill's quality ("this is wrong", "you missed X", "this pattern is better"), capture the lesson:

1. **Identify the class of error** — structural, content, disclosure, verification, or style
2. **Extract the generalizable rule** — not "add X to skill Y" but "when wrapping APIs that use pagination, always include a pagination patterns section"
3. **Check for existing rules** — read `references/gotchas.md` to see if this is already covered
4. **If new**: append the rule to `references/gotchas.md` under the appropriate category
5. **If contradicts existing**: update the existing rule and note the date

### Improvement Triggers

After generating a skill, proactively ask: "Want me to run the verification suite, or does this look good?"

If the user provides corrections:
1. Apply the fix to the current skill
2. Update `references/gotchas.md` with the lesson (if generalizable)
3. Re-run `scripts/validate.py` to confirm the fix didn't break structure

---

## Phase 7: Cross-Harness Compatibility

Read `references/cross-harness.md` for the full compatibility matrix. Quick rules:

- **SKILL.md + frontmatter** is universal across Claude Code, OpenAI Codex, Gemini CLI, Cursor, VS Code, and others
- **`name` and `description`** are the only required frontmatter fields
- For OpenAI Codex UI integration, add an openai.yaml file in the agents/ directory (see reference)
- For Google ecosystem integration, add `metadata.openclaw` fields
- For public repositories intended for `skills.sh`, keep installable skills under `skills/<skill-name>/`
- Scripts should use `python3` (not `python`) and avoid platform-specific paths
- For first-class skill and agent references inside reusable instructions, always use `{{ skill:<name> }}` and `{{ agent:<name> }}` instead of harness-specific file paths or plain backticked primitive names
- Reference files work identically across all harnesses

---

## Reference Files

Read these on demand — don't load them all upfront:

| File | When to read |
|------|-------------|
| `references/anatomy.md` | Designing skill structure |
| `references/placement.md` | Choosing the right repo-local or global destination |
| `references/patterns.md` | Choosing disclosure patterns and degrees of freedom |
| `references/blueprints.md` | Using a specific blueprint (API wrapper, CLI tool, progressive docs) |
| `references/testing.md` | Writing thorough evals and assertions |
| `references/self-improvement.md` | Processing user feedback into skill improvements |
| `references/cross-harness.md` | Ensuring compatibility across agent platforms |
| `references/gotchas.md` | Common mistakes and tribal knowledge (self-improving) |

## Agent Instructions

| File | When to use |
|------|------------|
| `agents/reviewer.md` | Spawn a reviewer subagent to audit a generated skill |
| `agents/improver.md` | Spawn an improver subagent to analyze and propose upgrades |

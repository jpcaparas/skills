# Self-Improvement Protocol

## Table of Contents

- [Overview](#overview)
- [Feedback Capture Process](#feedback-capture-process)
- [Error Classification Taxonomy](#error-classification-taxonomy)
- [Rule Storage Format](#rule-storage-format)
- [Contradiction Resolution](#contradiction-resolution)
- [Description Optimization Loop](#description-optimization-loop)
- [Trigger Eval Queries Guidance](#trigger-eval-queries-guidance)
- [When NOT to Save Feedback](#when-not-to-save-feedback)

---

## Overview

This skill learns from mistakes. When a generated skill has a flaw that the user catches, the lesson should be captured in `references/gotchas.md` so the same mistake is never repeated.

The feedback loop:

```
User identifies issue
    |
    v
Classify the error type
    |
    v
Extract a generalizable rule
    |
    v
Check for existing rules in gotchas.md
    |
    +-- New rule -> Append to gotchas.md
    |
    +-- Contradicts existing -> Update existing rule with date
    |
    +-- Already covered -> No action (maybe strengthen wording)
```

---

## Feedback Capture Process

### Step 1: Identify the Signal

User feedback that indicates a learnable mistake:

| Signal | Example |
|--------|---------|
| Direct correction | "This endpoint is wrong, it should be /v2/customers not /v1/customers" |
| Quality complaint | "The examples are pseudocode, they don't actually work" |
| Structural feedback | "Everything is crammed into SKILL.md, split it out" |
| Missing content | "You forgot to mention rate limits" |
| Style feedback | "Stop writing MUST everywhere, explain why instead" |

### Step 2: Extract the Generalizable Rule

The goal is NOT to fix the specific skill. The goal is to capture a rule that prevents the same class of mistake in future skills.

**Bad extraction:** "Add /v2/customers endpoint to the Stripe skill"
**Good extraction:** "When documenting API endpoints, always verify the current API version from official docs. Do not assume /v1/ -- many APIs have migrated to /v2/ or use date-based versioning."

**Bad extraction:** "Add rate limits to the gotchas section"
**Good extraction:** "Every API wrapper skill must include rate limit documentation. Check for: requests per minute, daily quotas, per-endpoint limits, and how limits are communicated (headers vs error response)."

### Step 3: Check for Duplicates

Before appending to gotchas.md:

1. Read the entire `references/gotchas.md` file
2. Search for keywords related to the new rule
3. If a similar rule exists:
   - If the new feedback adds nuance, update the existing rule
   - If the new feedback contradicts it, see [Contradiction Resolution](#contradiction-resolution)
   - If the existing rule fully covers it, no action needed

### Step 4: Append or Update

If the rule is new, append it to the appropriate category in `references/gotchas.md`:

```markdown
- Explaining things the agent already knows
- [NEW] Not verifying API version before documenting endpoints — always fetch
  current docs and confirm the version path (2026-03-27)
```

The date stamp in parentheses tracks when the rule was added.

---

## Error Classification Taxonomy

Every mistake falls into one of five classes. Classify before fixing, because the fix strategy differs by class.

### Structural Errors (highest priority)

Problems with how the skill is organized.

| Error | Fix |
|-------|-----|
| Everything crammed into SKILL.md | Move deep content to references, keep SKILL.md as router |
| SKILL.md too short (just a paragraph) | Add decision tree, quick reference table, gotchas section |
| Missing frontmatter fields | Add name and description at minimum |
| Directory name != skill name | Rename directory to match frontmatter `name` |
| No evals directory | Create evals/ with at least evals.json stub |

### Content Errors

Wrong or missing information in the skill's content.

| Error | Fix |
|-------|-----|
| Pseudocode instead of working examples | Replace with tested, executable code |
| Outdated API versions | Fetch current docs, update all endpoints and examples |
| Missing gotchas section | Add at least 3 non-obvious pitfalls |
| Hallucinated endpoints or flags | Verify against official docs or tool --help output |
| Incomplete auth documentation | Test the auth flow, document the exact header/token format |

### Disclosure Errors

Problems with progressive disclosure -- the wrong content is loaded at the wrong time.

| Error | Fix |
|-------|-----|
| All references loaded upfront | Add conditional loading ("Read X when you need Y") |
| No reading guide | Add a task-to-file mapping table to SKILL.md |
| Reference files without TOC | Add TOC to files over 300 lines |
| Duplicated content | Choose one canonical location, replace duplicates with references |
| Nested cross-references (A -> B -> C) | Flatten: A -> B and A -> C separately |

### Verification Errors

Examples and commands that don't actually work.

| Error | Fix |
|-------|-----|
| curl commands with wrong flags | Run the command, fix the flags |
| API endpoints that 404 | Verify against current API docs |
| Code that doesn't parse | Syntax-check all code blocks |
| Missing auth in examples | Add required headers to every API example |
| Wrong HTTP method | Check API docs for correct method |

### Style Errors (lowest priority)

Tone, formatting, and presentation issues.

| Error | Fix |
|-------|-----|
| Passive voice | Rewrite in imperative ("Run this" not "This should be run") |
| Over-explaining basics | Remove general programming knowledge; add domain-specific knowledge |
| Inconsistent heading levels | Fix hierarchy (# -> ## -> ### only) |
| No "See Also" links | Add cross-references to related files |
| Heavy-handed MUST/NEVER | Replace with reasoning ("X because Y" not "MUST do X") |

---

## Rule Storage Format

Rules are stored in `references/gotchas.md` in this skill's own directory. The file is organized by category with a self-improving header.

### Format

Each rule is a list item under its category heading:

```markdown
**Structural mistakes:**
- Putting everything in SKILL.md instead of using references
- SKILL.md too short (just a paragraph) -- needs decision trees and quick reference
- [NEW] Forgetting to add .gitkeep to empty directories (2026-03-27)
```

### Conventions

- New rules get a `[NEW]` prefix and a date stamp in parentheses
- After a rule has been validated across multiple skills, remove the `[NEW]` prefix
- Each rule is one line (can be long). No multi-line explanations in the gotchas list -- if a rule needs explanation, it belongs in a different reference file.
- Rules are imperative and describe the mistake, not the fix ("Missing gotchas section" not "Add a gotchas section")

---

## Contradiction Resolution

When new feedback contradicts an existing rule:

### Same-Category Contradiction

The new rule directly opposes an existing rule in the same category.

**Process:**
1. Read both rules carefully
2. Determine if the new feedback represents a more recent or authoritative source
3. If the new rule is better: update the existing rule, add a date stamp, note what changed
4. If the existing rule is better: discard the new feedback, optionally add a note explaining why the alternative was considered and rejected

**Example:**

Existing: "Use MUST/NEVER for critical operations"
New feedback: "Stop writing MUST/NEVER, explain reasoning instead"

Resolution: Update the rule. The reasoning-based approach is better because it gives the agent theory of mind to handle edge cases. Update to: "Using MUST/NEVER instead of explaining reasoning -- agents perform better when they understand why (2026-03-27, updated from previous MUST/NEVER guidance)"

### Cross-Category Contradiction

The new rule is valid in one context but contradicts another rule in a different context.

**Process:**
1. Both rules may be correct for their respective contexts
2. Add qualifying context to each rule
3. Add a cross-reference note

**Example:**

Structural rule: "Keep SKILL.md under 500 lines"
Content rule: "Include complete working examples"

Resolution: Both are valid. The structural rule takes precedence -- move complete examples to reference files and keep SKILL.md examples brief (1-2 lines per operation).

---

## Description Optimization Loop

After the skill content is finalized, optimize the frontmatter description for triggering accuracy. This is compatible with skill-creator's `run_loop.py`.

### Prerequisites

- The skill's SKILL.md is complete and verified
- `claude` CLI is available (`claude -p` for programmatic invocation)
- Python 3 is available

### Process

1. Generate trigger eval queries (see next section)
2. Review queries with the user
3. Run the optimization loop:

```bash
python -m scripts.run_loop \
  --eval-set /path/to/trigger-eval.json \
  --skill-path /path/to/skill \
  --model <current-model-id> \
  --max-iterations 5 \
  --verbose
```

4. The loop automatically:
   - Splits eval set into 60% train / 40% test
   - Evaluates current description (3 runs per query for reliability)
   - Proposes improvements based on failures
   - Re-evaluates on both train and test
   - Selects best by test score (avoids overfitting)

5. Apply `best_description` to the skill's frontmatter

### Running from skill-creator directory

The `run_loop.py` script lives in skill-creator's scripts directory. Run it from there:

```bash
cd /path/to/skill-creator
python -m scripts.run_loop \
  --eval-set /path/to/trigger-eval.json \
  --skill-path /path/to/target-skill \
  --model claude-sonnet-4-20250514 \
  --max-iterations 5 \
  --verbose
```

---

## Trigger Eval Queries Guidance

The quality of the description optimization depends on the quality of the eval queries.

### Composition Rules

- **20 total queries**: 10 should-trigger, 10 should-not-trigger
- **60/40 train/test split**: the loop handles this automatically
- **Realistic prompts**: like a real user at their terminal, not abstract test cases
- **Varied formality**: formal requests, casual questions, typos, abbreviations
- **Edge-case focused**: most value comes from hard cases, not obvious ones

### Should-Trigger Queries (10)

Think about coverage:

- **Direct invocation**: user names the tool/API explicitly
- **Implicit need**: user describes a problem that clearly needs this skill
- **Uncommon use case**: rare but valid scenario
- **Competition winner**: query where this skill competes with another but should win
- **Casual phrasing**: "hey can you help me with [thing]"
- **Different languages/frameworks**: if the skill is language-agnostic
- **Error-driven**: user has an error and needs this skill to fix it
- **Migration**: user is moving from one approach to another

### Should-Not-Trigger Queries (10)

The most valuable negatives are near-misses:

- **Keyword overlap**: shares terms with the skill but needs something else
- **Adjacent domain**: related topic but different tool/skill
- **Subset mismatch**: needs a specific part of a larger platform that has its own skill
- **UI vs API**: user wants a frontend component, not backend integration
- **Different provider**: same domain (payments, auth) but different vendor
- **Simple task**: something the agent can handle without any skill
- **Documentation request**: wants to read about X, not implement X
- **Already solved**: user has working code, just wants a review

### Bad vs Good Negative Queries

**Bad:** "Write a fibonacci function" (obviously unrelated, tests nothing)
**Good:** "I need to accept credit card payments on my site using PayPal's checkout SDK" (shares payment domain keywords but needs a different provider's skill)

---

## When NOT to Save Feedback

Not every correction is a generalizable lesson. Skip saving feedback when:

### One-Off Fixes

The mistake was specific to one skill and would not recur elsewhere.

- "The Stripe API key variable should be STRIPE_SECRET_KEY not STRIPE_API_KEY" -- this is a fact about Stripe, not a pattern.
- Exception: if you see the same "one-off" three times, it is a pattern. Save it.

### User-Specific Preferences

The feedback reflects a personal style choice, not a quality issue.

- "I prefer tabs over spaces in code examples"
- "I like shorter descriptions"
- "Can you use TypeScript instead of Python for examples"

### Already Covered

The rule exists in gotchas.md and the current wording is adequate.

### Ambiguous Signal

The user's comment could mean multiple things, or it is unclear whether it applies generally.

- "This feels off" (what specifically?)
- "Not sure about this" (about what?)

Ask for clarification before saving. If the user doesn't clarify, don't save.

### Model Behavior (Not Skill Behavior)

The issue is about how the model executed instructions, not about the instructions themselves.

- "The model took too long" -- a model performance issue, not a skill issue
- "The model didn't read the reference file" -- could be a skill issue (bad pointer) or a model issue (ignored a clear pointer). Investigate before saving.

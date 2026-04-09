# Testing & Eval Methodology

## Table of Contents

- [Test Case Categories](#test-case-categories)
- [evals.json Schema](#evalsjson-schema)
- [Assertion Types](#assertion-types)
- [Writing Realistic Test Prompts](#writing-realistic-test-prompts)
- [Verification Procedures](#verification-procedures)
- [Running Tests with skill-creator Infrastructure](#running-tests-with-skill-creator-infrastructure)
- [Lightweight Test Runner](#lightweight-test-runner)
- [Metrics to Track](#metrics-to-track)

---

## Test Case Categories

Every skill produced by this creator should have at least one test from each applicable category.

### Smoke Tests

Basic happy-path tests that verify the skill works at all. These should pass 100% of the time.

**What they test:** The skill loads, the agent follows its instructions, and the output is structurally correct.

**How to write them:** Pick the single most common use case. Make the prompt specific and realistic. Include file paths, context, and enough detail that there is one obvious correct approach.

**Example:**
```json
{
  "name": "basic-stripe-checkout",
  "prompt": "I need to create a Stripe Checkout Session for a $49.99 subscription plan. The plan is called 'Pro Monthly'. Use the API key from STRIPE_SECRET_KEY env var. Show me the curl command and the expected response shape.",
  "tags": ["smoke"]
}
```

### Edge Case Tests

Boundary conditions, unusual inputs, and less common workflows.

**What they test:** The skill handles non-obvious scenarios correctly -- large inputs, empty inputs, unusual parameter combinations, rare API behaviors.

**How to write them:** Think about what would trip up a naive implementation. What happens at the boundaries? What if a paginated API returns zero results? What if the auth token is expired?

**Example:**
```json
{
  "name": "pagination-empty-result",
  "prompt": "I'm querying the GitHub Issues API for a brand-new repo that has zero issues. The repo is at octocat/empty-repo. Write the code to list all issues, handling the case where there are none. Make sure it doesn't error or loop forever.",
  "tags": ["edge"]
}
```

### Negative Tests

Things the skill should NOT do, or prompts where the skill should not trigger at all.

**What they test:** The skill correctly declines, redirects, or limits its response when given an inappropriate request.

**How to write them:** Create prompts that are plausible but wrong for this skill. Near-misses that share keywords but need a different tool. Requests that exceed the skill's scope.

**Example:**
```json
{
  "name": "not-an-api-wrapper-task",
  "prompt": "Write me a React component that displays a payment form. I don't need any backend integration, just the UI with Tailwind styling.",
  "assertions": [
    {"text": "Does not produce API calls or backend code", "type": "negative"}
  ],
  "tags": ["negative"]
}
```

### Disclosure Tests

Tests that verify the correct reference file is loaded for a given query. Only applicable for multi-reference skills.

**What they test:** Given a specific question, the agent reads the right reference file (not all of them, not the wrong one).

**How to write them:** Create prompts that clearly map to one reference file. Then assert that the agent read that file and did NOT read unrelated ones.

**Example:**
```json
{
  "name": "loads-gotchas-not-api",
  "prompt": "I'm getting a 429 error from the Stripe API when I try to create customers in a loop. What's going on and how do I fix it?",
  "assertions": [
    {"text": "Agent reads references/gotchas.md", "type": "disclosure"},
    {"text": "Response mentions rate limiting and exponential backoff", "type": "functional"}
  ],
  "tags": ["disclosure"]
}
```

---

## evals.json Schema

Compatible with skill-creator's format, with extensions for assertion types and tags.

```json
{
  "skill_name": "example-skill",
  "created_by": "skill-creator-advanced",
  "evals": [
    {
      "id": 1,
      "name": "descriptive-test-name",
      "prompt": "Realistic user prompt with specifics",
      "expected_output": "Human-readable description of what a correct response looks like",
      "files": ["evals/files/input.json"],
      "assertions": [
        {
          "text": "Human-readable assertion statement",
          "type": "functional"
        }
      ],
      "tags": ["smoke", "api-wrapper"]
    }
  ]
}
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `skill_name` | Yes | Must match the skill's frontmatter `name` |
| `created_by` | No | Set to `"skill-creator-advanced"` for traceability |
| `evals[].id` | Yes | Unique integer |
| `evals[].name` | Yes | Descriptive name used in reports and directory names |
| `evals[].prompt` | Yes | The user prompt to test |
| `evals[].expected_output` | Yes | Human description of success |
| `evals[].files` | No | Input files (paths relative to skill root) |
| `evals[].assertions` | No | Machine-checkable assertions (added during grading) |
| `evals[].tags` | No | Categories: smoke, edge, negative, disclosure, plus skill-specific |

---

## Assertion Types

### Functional Assertions

Verify the output is correct. The most common type.

```json
{"text": "Output contains a valid curl command with Authorization header", "type": "functional"}
{"text": "The generated code handles the 429 rate limit error", "type": "functional"}
{"text": "Response includes pagination logic with a termination condition", "type": "functional"}
```

### Structural Assertions

Verify the output has the expected structure, format, or organization.

```json
{"text": "Output is valid JSON", "type": "structural"}
{"text": "Response includes a code block with language annotation", "type": "structural"}
{"text": "Generated skill has SKILL.md with valid YAML frontmatter", "type": "structural"}
```

### Disclosure Assertions

Verify the agent loaded the correct reference files (and not others).

```json
{"text": "Agent reads references/api.md", "type": "disclosure"}
{"text": "Agent does NOT read references/configuration.md (not relevant to this query)", "type": "disclosure"}
```

### Negative Assertions

Verify the output does NOT contain something.

```json
{"text": "Does not produce code for a different API than requested", "type": "negative"}
{"text": "Does not hallucinate endpoints that don't exist", "type": "negative"}
{"text": "Does not recommend deprecated v1 API", "type": "negative"}
```

---

## Writing Realistic Test Prompts

Bad test prompts are abstract and could apply to anything. Good test prompts have the specificity of a real user sitting at their terminal.

### What Makes a Prompt Realistic

1. **Specific file paths and names** -- `~/projects/saas-app/src/billing/checkout.ts`
2. **Concrete data** -- column names, API key variable names, actual error messages
3. **Personal context** -- "my boss wants", "we're migrating from X to Y", "this is for a hackathon"
4. **Implicit skill need** -- the user doesn't say "use the Stripe skill", they describe their problem
5. **Varied formality** -- some formal, some casual, some with typos

### Bad vs Good

**Bad:** "Create an API wrapper for payments"
**Good:** "I need to integrate Stripe Checkout into our Next.js app. The user picks a plan on /pricing (we have 'starter' at $19/mo and 'pro' at $49/mo), clicks 'Subscribe', and should be redirected to Stripe's hosted checkout page. After payment, redirect back to /dashboard?session_id={CHECKOUT_SESSION_ID}. Show me the API route handler at app/api/checkout/route.ts."

**Bad:** "Handle pagination"
**Good:** "I'm pulling all our customers from the Stripe API to build a churn report. We have about 12,000 customers. I need to paginate through all of them and write the results to a CSV at ~/reports/customers.csv with columns: id, email, created_date, subscription_status. The script should show progress (like 'fetched 100/12000')."

**Bad:** "Test error handling"
**Good:** "When I try to create a PaymentIntent with an amount of 0, Stripe returns an error. I need to handle this in my checkout flow -- if the amount is invalid, show the user a message instead of crashing. Here's my current code: [paste actual code]. What's the right error handling pattern?"

---

## Verification Procedures

### API Call Verification

For skills that produce API calls:

1. **Syntax check** -- parse the curl command or code snippet for correct syntax
2. **Header check** -- verify required headers (auth, content-type, accept) are present
3. **Endpoint check** -- confirm the URL path and method match the API docs
4. **Parameter check** -- verify required parameters are included
5. **Live test** (if safe) -- execute a read-only variant of the call

Safe to test live: GET requests, list operations, status checks.
Never test live: POST/PUT/DELETE to production, operations that cost money, operations that send messages.

### CLI Command Verification

For skills that produce shell commands:

1. **Parse check** -- is the command syntactically valid shell?
2. **Flag check** -- do the flags exist in `tool --help` output?
3. **Dry run** -- can we run with `--dry-run` or `--help` to verify?
4. **Output check** -- does the expected output format match reality?

### Code Snippet Verification

For skills that produce code:

1. **Syntax check** -- write to temp file and run language parser (`python -c "import ast; ast.parse(open('f').read())"`)
2. **Import check** -- are the imports valid and available?
3. **Type check** (if applicable) -- does it pass mypy/tsc?
4. **Execution check** (if safe) -- run in a sandbox

---

## Running Tests with skill-creator Infrastructure

This skill's test format is compatible with skill-creator's eval runner.

### Full Eval Run (via skill-creator)

```bash
cd /path/to/skill-creator
python -m scripts.run_eval \
  --skill-path /path/to/new-skill \
  --eval-path /path/to/new-skill/evals/evals.json
```

This spawns subagents for each eval, runs with and without the skill, and produces grading results.

### Generating the Review Viewer

```bash
python /path/to/skill-creator/eval-viewer/generate_review.py \
  /path/to/workspace/iteration-1 \
  --skill-name "my-skill" \
  --benchmark /path/to/workspace/iteration-1/benchmark.json
```

For headless/Cowork environments, add `--static /path/to/output.html`.

### Grading

Run the grader with skill-creator's grader agent. The grading.json must use these exact fields:

```json
{
  "expectations": [
    {"text": "...", "passed": true, "evidence": "..."}
  ]
}
```

The viewer depends on `text`, `passed`, and `evidence` -- not other field names.

---

## Lightweight Test Runner

For quick validation without the full eval infrastructure, use this skill's `scripts/test_skill.py`:

```bash
python3 /path/to/skill-creator-advanced/scripts/test_skill.py /path/to/skill/
```

This does NOT run the skill against prompts. It validates:

1. **Eval existence** -- `evals/evals.json` exists and parses
2. **Eval format** -- each eval has required fields (id, name, prompt, expected_output)
3. **Assertion format** -- assertions have `text` and `type` fields
4. **File references** -- any `files` in evals point to real files
5. **Cross-references** -- file paths mentioned in SKILL.md resolve to real files
6. **Tag coverage** -- reports which test categories are present

Output:

```
Skill: stripe-api
Tests found: 5
  smoke: 1
  edge: 2
  negative: 1
  disclosure: 1
Files verified: 8/8
Cross-references checked: 12/12
Assertion format: 9/9 valid

PASS: all checks passed
```

---

## Metrics to Track

### Pass Rate

The primary metric. What percentage of assertions pass?

| Threshold | Interpretation |
|-----------|---------------|
| 100% | Perfect -- but check if assertions are too easy |
| 80-99% | Good -- investigate failures, they may be flaky |
| 60-79% | Needs work -- systematic issues in the skill |
| <60% | Fundamental problems -- revisit the skill's approach |

### Token Usage

How many tokens does the skill consume per invocation?

- **Baseline** (no skill): typically 1000-3000 tokens for simple tasks
- **With skill**: overhead depends on SKILL.md size and reference files loaded
- **Target**: skill should add <50% token overhead for >50% quality improvement

Track `total_tokens` from the timing.json file captured during eval runs.

### Time

Wall-clock time per invocation.

- Capture `duration_ms` from subagent completion notifications
- Skills that cause significantly longer execution times may have over-broad instructions that send the agent on detours

### Discriminating Power

Not all assertions are useful. Track which assertions:

- **Always pass** (both with and without skill) -- non-discriminating, consider removing
- **Always fail** (even with skill) -- the skill doesn't address this, fix or remove
- **Pass with skill, fail without** -- high-value assertions that prove the skill's worth

### Variance

Run each eval 3+ times. High variance (>20% standard deviation on pass rate) indicates:

- Flaky assertions (hard for the grader to evaluate consistently)
- Ambiguous skill instructions (the agent takes different paths each time)
- Model-dependent behavior (fine on one model, fails on another)

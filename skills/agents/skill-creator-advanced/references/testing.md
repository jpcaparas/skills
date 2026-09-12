# Testing & Eval Methodology

## Table of Contents

- [Test Case Categories](#test-case-categories)
- [Process and Completion Evidence](#process-and-completion-evidence)
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

Basic happy-path tests that verify the skill works at all. They should pass consistently across enough repeated runs to support the release claim; do not impose a universal percentage on stochastic evaluators.

**What they test:** The skill loads, the agent follows its instructions, and the output is structurally correct.

**How to write them:** Pick the single most common use case. Make the prompt specific and realistic. Include file paths, context, and enough detail that there is one obvious correct approach.

**Example:**
```json
{
  "name": "basic-contract-backed-wrapper",
  "prompt": "Create a skill from the attached service contract. It should support the documented asset lookup operation, use the contract's configured credential source, and report the verified success fields without inventing a transport.",
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
  "name": "empty-continuation-result",
  "prompt": "The attached command help says `scan` can return zero records and an empty continuation value. Add that branch to the skill and prove it terminates without treating an empty result as an error.",
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

**How to write them:** Create prompts that clearly map to one reference file. When the harness exposes file access, assert from its captured trace or read log that the relevant file was read and unrelated files were not. Otherwise assert a branch-specific consequence that cannot be produced from the always-loaded instructions alone.

**Example:**
```json
{
  "name": "loads-gotchas-not-api",
  "prompt": "The tool stops a batch with `E_TEMPORARY` and a documented retry delay. Diagnose the failure using the attached skill without changing setup or publishing guidance.",
  "assertions": [
    {"text": "Captured trace records a read of references/gotchas.md and no read of setup or publishing references", "type": "disclosure"},
    {"text": "Response applies the contract's retry condition and delay without inventing a fixed retry policy", "type": "functional"}
  ],
  "tags": ["disclosure"]
}
```

### Invocation Tests

Test description accuracy with three prompt families:

- a direct positive that names the domain
- an implicit positive that needs the skill without naming it
- an adjacent near-miss that shares vocabulary but belongs elsewhere

Treat each genuine invocation branch as one coverage unit. Do not compensate for missing evals by stuffing synonym lists into the description.

### Curation Tests

For library changes, exercise the lifecycle transition and its governed surfaces:

- create, improve, merge, compose, or retire ownership
- draft-to-published promotion
- rename or move with stale-name cleanup
- deprecation or removal with dependent migration
- router, catalog, registry, wrapper, and discovery reconciliation

Use committed fixtures that describe the repository contract; do not depend on ambient home-directory skills.

---

## Process and Completion Evidence

Output assertions alone can miss a rushed or inconsistent process. For procedural skills, assert the observable phase gates:

- every existing behavior is accounted for before restructuring
- every invocation branch maps to one owner
- every claimed operation maps to evidence or an explicit limitation
- every changed publication surface is reconciled
- verification happens before the response declares completion

Run stochastic evals repeatedly and judge process consistency, not identical prose. A creative skill may produce different artifacts while still following the same reliable gates.

For disclosure, pair the positive assertion with a negative one and name the captured evidence:

```json
[
  {"text": "Captured trace records a read of references/gotchas.md for the retry diagnosis", "type": "disclosure"},
  {"text": "Captured trace contains no read of unrelated setup documentation", "type": "negative"}
]
```

---

## evals.json Schema

This package uses an advanced, typed schema for local release preflight. Do not pass it directly to a behavioral or trigger runner without checking that runner's current schema. The adapter rule is simple: preserve each prompt, expected outcome, and fixture, then map each `assertions[].text` value into the evaluator's assertion or expectation field; keep `type` as grading metadata when supported.

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
| `evals[].assertions` | Yes for release | Non-empty, typed success criteria used during grading |
| `evals[].tags` | No | Categories: smoke, edge, negative, disclosure, plus skill-specific |

---

## Assertion Types

### Functional Assertions

Verify the output is correct. The most common type.

```json
{"text": "Output uses the authentication form documented in the attached contract", "type": "functional"}
{"text": "The generated workflow handles the contract's retryable outcome", "type": "functional"}
{"text": "Response includes continuation logic with a verified termination condition", "type": "functional"}
```

### Structural Assertions

Verify the output has the expected structure, format, or organization.

```json
{"text": "Output is valid JSON", "type": "structural"}
{"text": "Response includes a code block with language annotation", "type": "structural"}
{"text": "Generated skill has SKILL.md with valid YAML frontmatter", "type": "structural"}
```

### Disclosure Assertions

Verify from a captured trace, read log, or transcript that the agent loaded the correct reference files and not others. If that evidence is unavailable, replace the load claim with a branch-specific observable consequence rather than guessing about hidden context.

```json
{"text": "Captured trace records a read of references/api.md", "type": "disclosure"}
{"text": "Captured trace contains no read of references/configuration.md", "type": "disclosure"}
```

### Negative Assertions

Verify the output does NOT contain something.

```json
{"text": "Does not produce code for a different API than requested", "type": "negative"}
{"text": "Does not hallucinate endpoints that don't exist", "type": "negative"}
{"text": "Does not recommend deprecated v1 API", "type": "negative"}
```

### Verification Assertions

Verify that the response obtained and reported evidence before declaring completion. Use this type for an observable check, not a restatement of the requested output.

```json
{"text": "Reports the inspected CLI version and relevant help output", "type": "verification"}
{"text": "Runs release validation and distinguishes a blocked live check from a passing check", "type": "verification"}
```

---

## Writing Realistic Test Prompts

Bad test prompts are abstract and could apply to anything. Good test prompts have the specificity of a real user sitting at their terminal.

### What Makes a Prompt Realistic

1. **Specific file paths and names** -- `src/billing/checkout` or the repository's native path form
2. **Concrete data** -- field names, credential variable names, actual error messages
3. **Personal context** -- "my boss wants", "we're migrating from X to Y", "this is for a hackathon"
4. **Implicit skill need** -- the user describes the problem instead of naming the skill
5. **Varied formality** -- some formal, some casual, some with typos

### Bad vs Good

**Bad:** "Create an API wrapper for records"
**Good:** "The attached service contract defines `lookup-record` and `archive-record`. Build a skill for support engineers: lookup is always allowed, archive must require the user's explicit record identifier and use the documented preview mode first. Preserve the contract's field names and report the archive receipt."

**Bad:** "Handle continuation"
**Good:** "The attached CLI help says `records scan` returns at most 200 rows and prints `next_cursor` only when more exist. The skill must collect about 12,000 rows for an audit export, stop when the field is absent, preserve `id`, `owner`, and `state`, and show bounded progress without guessing a total."

**Bad:** "Test error handling"
**Good:** "The supplied SDK contract distinguishes `InvalidInput` from `RetryableLimit` and gives the latter a `retry_after_ms` field. Update the skill so invalid input stops immediately, retryable limits honor that field, and exhausted retries preserve the original error. Here is the current adapter and its failing output: [attached files]."

---

## Verification Procedures

### API Call Verification

For skills that produce API calls, climb the safest applicable verification ladder:

1. **Syntax check** -- parse the request, command, SDK call, or message form with the target contract's tooling
2. **Identity check** -- verify the documented authentication or identity material is present in the required location
3. **Operation check** -- confirm the target, method, procedure, or SDK operation matches current primary evidence
4. **Input check** -- verify required fields and encodings are included
5. **Live test** (when authorized and useful) -- execute a read-only, bounded variant

Prefer read-only status, list, or lookup calls in a non-production account. For writes, messages, spend, destructive actions, or production mutation, stop at documentation/dry-run/sandbox evidence unless the user's request already grants the required authority and scope.

### CLI Command Verification

For skills that produce CLI invocations:

1. **Parse check** -- is the invocation valid for the documented target shell, process API, or command environment?
2. **Option check** -- do the command, options, arguments, and defaults exist in current primary help or reference output?
3. **Safe probe** -- use the tool's documented help, parse-only, preview, or dry-run facility when one exists; do not invent a conventional flag.
4. **Result check** -- do output, status, and exit semantics match the verified tool contract?

### Code Snippet Verification

For skills that produce code:

1. **Syntax check** -- write to a temporary file and run the target language's parser or compiler in parse-only mode.
2. **Dependency check** -- confirm imports, packages, modules, or linked libraries exist for the stated environment.
3. **Static check** -- run the project's configured type, lint, or compile checks when applicable.
4. **Execution check** -- run the smallest safe example in a disposable sandbox when useful and authorized.

---

## Running Tests with skill-creator Infrastructure

Behavioral output evaluation and invocation evaluation are separate workflows. Do not use a trigger runner to claim that generated artifacts were correct, and do not infer trigger accuracy from successful behavioral runs.

Before interpreting scores, prove the harness itself works:

1. Confirm the evaluator's model/CLI is authenticated.
2. Run one known-positive query that must invoke a test skill and one known-negative query that must not.
3. Preserve subprocess errors and distinguish infrastructure failure from a genuine non-trigger.
4. Treat uniform results—especially every positive and negative returning the same trigger state—as a failed health probe until disproved.

### Behavioral Output Workflow

Inspect the installed evaluator's `SKILL.md` and schema reference first; its fields and commands are the executable contract. Then:

1. Create a workspace outside the skill package. For an improvement, capture a recoverable baseline there before the first target write. If work already began without one, recover the old package from an immutable version-control revision or stop rather than comparing against the edited package.
2. For every behavioral case, launch the with-skill run and its baseline in the same batch. The baseline is no skill for a new package and the preserved old version for an improvement.
3. Copy committed fixtures into a separate `inputs/` directory for every run, then give both configurations the same prompt, fixture contents, output contract, and authority boundaries. Never let an eval edit the canonical package or `evals/files/` tree. When an assertion claims a file was or was not loaded, also capture the harness tool trace, read log, or transcript. If the harness exposes no such evidence, rewrite the assertion around a branch-specific observable consequence.
4. Translate this package's typed assertion texts to the evaluator's current assertion or expectation field. Do not discard the type; retain it in metadata or the grader brief.
5. Grade both outputs with evidence, aggregate the benchmark, and inspect assertions that pass equally well without the skill.

Use the exact directory contract consumed by the installed aggregator. For a new package, use `with_skill` and `without_skill` as shown. For an improvement, substitute `new_skill` and `old_skill` for those two configuration directory names; keep every nested path unchanged.

```text
iteration-N/
└── eval-<id>/
    ├── eval_metadata.json
    ├── with_skill/
    │   └── run-1/
    │       ├── inputs/              # isolated fixture copy
    │       ├── outputs/
    │       ├── grading.json
    │       ├── timing.json          # when available
    │       └── trace.jsonl          # when disclosure claims need it
    └── without_skill/
        └── run-1/
            ├── inputs/              # independent copy of the same fixtures
            ├── outputs/
            ├── grading.json
            ├── timing.json
            └── trace.jsonl
```

Each `grading.json` sits at the `run-*` root and contains both `expectations` and a `summary` with passed, failed, total, and pass rate. After aggregation, reject the result if either configuration is absent, an expected eval/run pair was skipped, or the benchmark contains zero graded assertions.

When the installed package exposes the standard aggregation module, run it from that package root after the paired outputs and grades exist:

```bash
python3 -m scripts.aggregate_benchmark /path/to/workspace/iteration-N \
  --skill-name <skill-name>
```

There is intentionally no claimed one-command behavioral runner here: the paired executions are performed by the current agent/subagent harness, and the installed evaluator's documented workflow governs their workspace shape.

### Invocation Workflow

Store invocation queries separately from behavioral cases, for example in a file named `trigger-evals.json` inside the skill's eval directory:

```json
[
  {"query": "A realistic implicit request that needs the skill", "should_trigger": true},
  {"query": "A realistic adjacent request owned elsewhere", "should_trigger": false}
]
```

The installed `skill-creator` trigger runner is Claude-specific in the version documented here; it cannot establish invocation behavior for Codex, Gemini, Copilot, OpenCode, or another harness. Use it only for a Claude target. For every other target, use that harness's native evaluator and preserve the same query/expected-outcome contract.

Before accepting any trigger score, run and save separate raw health probes that preserve exit status, stdout, and stderr:

1. invoke the evaluator backend directly with a harmless authenticated request
2. verify the temporary skill is present in the target's discovery output
3. run one known-positive and one known-negative control

The installed runner can collapse worker or subprocess failures into non-trigger results, so its score is invalid unless those raw probes pass. Then run it with its trigger schema:

```bash
cd /path/to/installed/skill-creator
python3 -m scripts.run_eval \
  --eval-set /path/to/skill/evals/trigger-evals.json \
  --skill-path /path/to/skill \
  --runs-per-query 3
```

This command measures Claude invocation only. Keep the raw health-probe artifacts beside its report, and treat authentication errors, discovery failures, missing controls, and uniform all-zero/all-one results as evaluator-health failures rather than skill scores.

### Generating the Review Viewer

```bash
python3 /path/to/skill-creator/eval-viewer/generate_review.py \
  /path/to/workspace/iteration-1 \
  --skill-name "my-skill" \
  --benchmark /path/to/workspace/iteration-1/benchmark.json
```

For headless environments, add `--static /path/to/output.html`.

### Grading

Run the grader with skill-creator's grader agent. The grading.json must use these exact fields:

```json
{
  "expectations": [
    {"text": "...", "passed": true, "evidence": "..."}
  ],
  "summary": {"passed": 1, "failed": 0, "total": 1, "pass_rate": 1.0}
}
```

The viewer depends on `text`, `passed`, and `evidence` -- not other field names.

---

## Lightweight Test Runner

For quick validation without the full eval infrastructure, use this skill's `scripts/test_skill.py`:

```bash
python3 /path/to/skill-creator-advanced/scripts/test_skill.py /path/to/skill/
```

This does **not** run the skill against prompts and cannot prove behavior. It is a release preflight that validates:

1. **Eval existence** -- `evals/evals.json` exists and parses
2. **Eval format** -- each eval has required fields (id, name, prompt, expected_output)
3. **Assertion format** -- assertions have `text` and `type` fields
4. **File references** -- any `files` in evals point to real files
5. **Path safety** -- eval fixtures remain inside the skill package
6. **Cross-references** -- local package pointers resolve without escaping the package
7. **Tag coverage** -- reports which test categories are present

Output:

```
Skill: example-skill
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

Track the proportion of applicable assertions that pass, but interpret it against the release claim, baseline, variance, and consequence of each failure. A single failed safety assertion can block release while several low-value wording assertions may deserve removal. Set acceptance criteria before running the suite instead of applying universal quality bands afterward.

### Context Cost

Compare the always-loaded description, loaded `SKILL.md`, and branch-specific references against the improvement they produce. Track tokens when the evaluator exposes them, but avoid universal percentage targets: models, harnesses, and task sizes differ.

### Time

Wall-clock time per invocation.

- Capture wall time or duration metadata only when the current harness exposes it reliably
- Skills that cause significantly longer execution times may have over-broad instructions that send the agent on detours

### Discriminating Power

Not all assertions are useful. Track which assertions:

- **Always pass** (both with and without skill) -- non-discriminating, consider removing
- **Always fail** (even with skill) -- the skill doesn't address this, fix or remove
- **Pass with skill, fail without** -- high-value assertions that prove the skill's worth

### Variance

Run each stochastic eval multiple times. Material variance indicates:

- Flaky assertions (hard for the grader to evaluate consistently)
- Ambiguous skill instructions (the agent takes different paths each time)
- Model-dependent behavior (fine on one model, fails on another)

### Evaluator Health

Track authentication, model availability, tool discovery, timeouts, and subprocess errors separately from assertion failures. A score produced while the evaluator is logged out or cannot discover the temporary skill is not evidence about the skill.

## See Also

- `references/curation.md` — invocation ownership, lifecycle transitions, and publication-surface gates
- `references/patterns.md` — branch-based disclosure and completion criteria
- `references/self-improvement.md` — using failing evals to curate feedback

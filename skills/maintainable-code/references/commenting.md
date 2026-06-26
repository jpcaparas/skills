# Commenting for Maintainers

Use this reference when code is operational, dense, cross-language, generated, security-sensitive, asynchronous, or likely to be maintained by someone who understands programming fundamentals but not this system's history.

## Table of Contents

- [Principle](#principle)
- [Comment Placement](#comment-placement)
- [Comment Scope](#comment-scope)
- [Source-Backed Claims](#source-backed-claims)
- [Junior-Friendly Structure](#junior-friendly-structure)
- [GitHub Actions, YAML, and Shell](#github-actions-yaml-and-shell)
- [TypeScript and JavaScript](#typescript-and-javascript)
- [Python](#python)
- [Go](#go)
- [Rust](#rust)
- [Java, Kotlin, and C#](#java-kotlin-and-c)
- [SQL](#sql)
- [HTML, CSS, and UI Markup](#html-css-and-ui-markup)
- [Terraform, Kubernetes, and Infrastructure Config](#terraform-kubernetes-and-infrastructure-config)
- [Review Checklist](#review-checklist)

## Principle

Comments are part of the interface between today's implementer and tomorrow's maintainer. They should reduce the amount of hidden context a reader must reconstruct.

Do not optimize for line count at the cost of hidden context. A short phase comment is cheaper than making the next maintainer reverse-engineer a dense block.

Prefer comments that explain:

- Why this approach exists.
- What invariant must stay true.
- Which external service, file format, or runtime quirk forced the shape.
- What phase a dense block is performing.
- What would break if a future maintainer "simplifies" it.
- Where generated or copied code begins and how to refresh it.

Avoid comments that merely translate syntax:

- Bad: `# Loop over prefixes`
- Better: `# Artifact names are prefixed by matrix job; scan every requested prefix before downloading.`

## Comment Placement

Use comments where the reader is about to pay a context cost:

1. Before a multi-step block, name the phase.
2. Above a surprising condition, explain the rule or invariant.
3. Next to a magic value, name the source or contract.
4. At external boundaries, document API quirks, retries, pagination, auth, rate limits, and data shape assumptions.
5. In generated files, explain generation source and the command to refresh when that is stable.

Do not hide bad names behind comments. Rename first when a better name can carry the intent.

## Comment Scope

Do not concentrate all documentation at the class or module header. Put context at the smallest level that will help the next maintainer make the right change.

Use this placement ladder:

1. **Module or class docblock**: explain the responsibility, lifecycle, ownership boundary, or public contract.
2. **Method or function docblock**: explain inputs, outputs, side effects, thrown errors, idempotency, retries, or framework hooks.
3. **Property or field docblock**: explain units, nullability, persisted format, cache lifetime, serialization name, or why a weak type is safe.
4. **Branch or block comment**: explain a local invariant, surprising condition, multi-step phase, workaround, or external contract.
5. **Inline trailing comment**: use sparingly for short source notes such as a protocol constant, status code, or required version.

Prefer adding the useful comments first and letting the user or reviewer prune them. It is easier to remove a comment that repeats obvious structure than to recover missing context about why a block exists.

Example property and method docblocks:

```ts
interface RetryPolicy {
  /** Maximum extra attempts after the first request; excludes the initial try. */
  maxRetries: number;
}

/**
 * Sends a request with per-call retry state so concurrent requests cannot
 * consume each other's retry budget.
 */
async function requestWithRetry(policy: RetryPolicy): Promise<Response> {
  // Retry only server-side failures; client errors usually mean the request
  // shape is wrong and should surface immediately.
  return send(policy);
}
```

## Source-Backed Claims

When a comment, docblock, review note, or final answer makes a claim about a language, framework, runtime, or official convention, check whether official documentation can back it. Link the official source when the claim affects maintainability, correctness, security, or future upgrades.

Good source-backed comments:

- Link to the official documentation for a framework convention that looks magical locally.
- Paraphrase what the docs say; do not paste long excerpts.
- Prefer versioned docs for frameworks when the project is pinned to a version.
- Use a stable official page for language syntax or docstring/comment behavior.
- If no official source exists, say the claim comes from local codebase evidence, a dependency source file, or observed behavior.

Verified official source examples:

| Ecosystem | Use when backing claims about | Official source |
|---|---|---|
| PHP | Comment syntax and parser behavior | `https://www.php.net/manual/en/language.basic-syntax.comments.php` |
| Python | Function docstring conventions | `https://docs.python.org/3/tutorial/controlflow.html#documentation-strings` |
| Laravel | Eloquent accessors, mutators, casts, and method docblock examples | `https://laravel.com/docs/13.x/eloquent-mutators` |
| Laravel | Route behavior and routing conventions | `https://laravel.com/docs/13.x/routing` |
| Next.js | App Router route handler file conventions | `https://nextjs.org/docs/app/api-reference/file-conventions/route` |
| Next.js | App Router data fetching behavior | `https://nextjs.org/docs/app/getting-started/fetching-data` |

Avoid source-shaped decoration. Do not add a link just because a source exists; add it when it helps a maintainer verify a non-obvious rule without searching from scratch.

## Junior-Friendly Structure

Write comments for a junior developer with solid fundamentals and limited system context. Keep the wording concrete, local, and scan-friendly.

Use this shape for longer comments:

1. Start with the constraint or reason.
2. Name the moving parts in the order the code uses them.
3. Use bullets or numbered lists when the comment explains multiple concepts.
4. End with the invariant a future change must preserve.

Example:

```py
# The export keeps database values as strings until validation finishes:
# - Decimal avoids binary rounding drift for money.
# - Empty strings mean "missing" in the vendor CSV, not zero.
# - The final quantize step is the only place we round for display.
amount = parse_export_amount(row["amount"])
```

Keep comments digestible:

- Prefer two or three short sentences over one dense paragraph.
- Use bullet points when explaining multiple reasons, phases, or failure modes.
- Name domain concepts directly instead of using vague words like "stuff", "things", or "logic".
- Avoid unexplained acronyms unless the surrounding code already defines them.

## GitHub Actions, YAML, and Shell

Dense CI and shell code needs more comments than application code because it combines YAML, shell quoting, command-line tools, environment variables, and remote service behavior.

Weak:

```yaml
- name: Download matching artifacts
  shell: bash
  run: |
    set -euo pipefail
    prefixes=("web-" "api-")
    artifacts_json="$(
      gh api --paginate "/repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/artifacts?per_page=100" |
      jq -s '{artifacts: map(.artifacts[])}'
    )"

    for prefix in "${prefixes[@]}"; do
      jq -r --arg prefix "$prefix" \
        '.artifacts[] | select(.name | startswith($prefix)) | [.id, .name] | @tsv' \
        <<< "$artifacts_json"
    done | sort -u | while IFS=$'\t' read -r artifact_id artifact_name; do
      printf 'Downloading %s (%s)\n' "$artifact_name" "$artifact_id"
      gh run download "$GITHUB_RUN_ID" --name "$artifact_name"
    done
```

Better:

```yaml
- name: Download matching artifacts
  shell: bash
  run: |
    set -euo pipefail

    # Keep this list aligned with the matrix jobs that upload artifacts. The
    # download step intentionally accepts multiple prefixes because some runs
    # publish both service-specific and shared bundles.
    prefixes=("web-" "api-")

    # Fetch all artifact pages once, then normalize the paginated responses
    # into one JSON shape. The rest of this step can stay local and testable
    # with jq instead of making one GitHub API call per prefix.
    artifacts_json="$(
      gh api --paginate "/repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/artifacts?per_page=100" |
      jq -s '{artifacts: map(.artifacts[])}'
    )"

    # Emit id/name pairs for every requested prefix, then de-duplicate before
    # downloading. One artifact can match more than one prefix when a shared
    # bundle name is intentionally broad.
    for prefix in "${prefixes[@]}"; do
      jq -r --arg prefix "$prefix" \
        '.artifacts[] | select(.name | startswith($prefix)) | [.id, .name] | @tsv' \
        <<< "$artifacts_json"
    done | sort -u | while IFS=$'\t' read -r artifact_id artifact_name; do
      # A blank line from an upstream filter should not become a download
      # request. Check both fields because gh downloads by artifact name.
      if [ -z "$artifact_id" ] || [ -z "$artifact_name" ]; then
        continue
      fi

      printf 'Downloading %s (%s)\n' "$artifact_name" "$artifact_id"
      gh run download "$GITHUB_RUN_ID" --name "$artifact_name"
    done
```

Shell comment guidelines:

- Comment pipeline stages when `jq`, `awk`, `sed`, `sort`, process substitution, heredocs, or nested command substitution changes data shape.
- Explain quoting choices when word splitting, globbing, or newline preservation matters.
- Explain why `set -e`, `pipefail`, or `|| true` is safe in this context.
- Prefer comments above the block over trailing comments on long commands.

YAML/config comment guidelines:

- Explain permission minimization, concurrency keys, matrix exclusions, cache keys, version pins, and artifact naming contracts.
- Keep comments close to the field they justify.
- Avoid repeating the key name in prose.

Example:

```yaml
permissions:
  # This job only reads workflow metadata and artifacts; keep contents write
  # disabled so a compromised dependency cannot push to the repository.
  actions: read
  contents: read

concurrency:
  # One preview per branch is useful; multiple previews for the same branch
  # waste runner minutes and make artifact names ambiguous.
  group: preview-${{ github.ref }}
  cancel-in-progress: true
```

## TypeScript and JavaScript

Weak:

```ts
// Check if user can retry.
if (attempts < maxAttempts && error.status >= 500) {
  return retry();
}
```

Better:

```ts
// Only retry server-side failures. Client errors usually mean the request
// shape is invalid, so retrying would hide the real bug from the caller.
if (attempts < maxAttempts && error.status >= 500) {
  return retry();
}
```

Use comments for:

- Browser/server boundaries, hydration assumptions, and feature detection.
- Why a weak type or cast is safe after validation.
- Retry, caching, debounce, throttling, and cancellation behavior.
- Compatibility shims and third-party library quirks.

Prefer types and names for:

- Data shape.
- Valid states.
- Mode names.
- Public function intent.

## Python

Weak:

```py
# Iterate through rows.
for row in rows:
    total += Decimal(row["amount"])
```

Better:

```py
# Amounts arrive as strings from the export; Decimal avoids binary rounding
# drift before we compare totals with the accounting system.
for row in rows:
    total += Decimal(row["amount"])
```

Use comments for:

- Numeric precision, timezone, locale, encoding, and path assumptions.
- Regular expressions whose domain grammar is not obvious.
- Resource lifetime choices around files, sockets, subprocesses, and locks.
- Compatibility branches for different Python or dependency versions.

Prefer docstrings for public modules, classes, and functions when they explain contract, side effects, or exceptions. Python's official tutorial documents docstring conventions for functions; use that source when a code review or handoff needs to justify docstring shape.

## Go

Weak:

```go
// Start goroutines.
for _, job := range jobs {
    go runJob(ctx, job)
}
```

Better:

```go
// All workers share the request context so cancellation stops queued work
// after the first fatal validation error.
for _, job := range jobs {
    go runJob(ctx, job)
}
```

Use comments for:

- Goroutine ownership, cancellation, channel closing responsibility, and lock ordering.
- Public exported identifiers, following Go's documentation convention.
- Error wrapping decisions and when callers should inspect errors.

Prefer simple names and small interfaces before explanatory comments.

## Rust

Weak:

```rust
// Unsafe code.
let value = unsafe { ptr.as_ref().unwrap() };
```

Better:

```rust
// SAFETY: ptr comes from the arena allocated above and remains valid until
// the arena is dropped after this traversal.
let value = unsafe { ptr.as_ref().unwrap() };
```

Use comments for:

- `unsafe` preconditions and why they are upheld.
- Lifetime or ownership constraints that are enforced by a surrounding protocol instead of the type system.
- Performance tradeoffs around allocation, borrowing, and synchronization.

Prefer types, enums, and pattern matching for state explanations.

## Java, Kotlin, and C#

Weak:

```java
// Validate order.
if (!order.isSubmitted()) {
    throw new InvalidOrderException(order.id());
}
```

Better:

```java
// Fulfillment only consumes submitted orders; accepting drafts here would
// bypass inventory reservation and create negative stock later.
if (!order.isSubmitted()) {
    throw new InvalidOrderException(order.id());
}
```

Kotlin variant:

```kotlin
// Suspended accounts can still own projects, but project access must stay
// blocked until Billing clears the account hold.
when (account.status) {
    AccountStatus.Suspended -> denyAccess(account.id)
    AccountStatus.Active -> allowAccess(account.id)
}
```

C# variant:

```csharp
// The export contract expects UTC calendar dates; using local time would shift
// rows around midnight for customers outside the server timezone.
var exportDate = DateOnly.FromDateTime(clock.UtcNow);
```

Use comments for:

- Public API compatibility, serialization formats, dependency injection boundaries, and framework lifecycle hooks.
- Method/property docblocks when framework conventions make behavior implicit, such as Laravel Eloquent accessors, mutators, casts, route model binding, or serialization hooks. Link Laravel's versioned official docs when citing those conventions.
- Threading assumptions, transaction boundaries, and idempotency.
- Why an annotation or reflection hook is required.

Prefer expressive method names, domain exceptions, and typed value objects when they make the rule explicit.

## SQL

Weak:

```sql
-- Get orders.
WITH orders AS (
  SELECT * FROM order_events
)
SELECT customer_id, count(*) FROM orders GROUP BY customer_id;
```

Better:

```sql
-- Collapse event rows to submitted orders before joining payments; joining
-- raw events would over-count retries and webhook replays.
WITH submitted_orders AS (
  SELECT DISTINCT order_id, customer_id
  FROM order_events
  WHERE event_type = 'submitted'
)
SELECT customer_id, count(*) FROM submitted_orders GROUP BY customer_id;
```

Use comments for:

- Why a CTE exists, especially when it de-duplicates or changes grain.
- Assumptions about indexes, locks, transaction isolation, and data volume.
- Migration reversibility and backfill safety.

Prefer descriptive CTE names over comments that restate table names.

## HTML, CSS, and UI Markup

Weak:

```html
<!-- Button -->
<button type="submit">Save</button>
```

Better:

```html
<!-- type=submit is intentional: this button must trigger native form
validation before the React submit handler runs. -->
<button type="submit">Save</button>
```

Weak:

```css
/* Header style */
.header {
  position: sticky;
}
```

Better:

```css
/* Keep the command bar visible while long tables scroll; rows underneath use
z-index 0, so this layer only needs to beat table content. */
.header {
  position: sticky;
  z-index: 1;
}
```

Use comments for:

- Accessibility relationships that are not obvious from markup.
- Layout invariants, stacking contexts, container queries, and browser workarounds.
- Why a rule is duplicated for print, dark mode, reduced motion, or legacy support.

Prefer semantic elements, ARIA only when needed, and component names that carry domain meaning.

## Terraform, Kubernetes, and Infrastructure Config

Weak:

```hcl
# Set lifecycle.
lifecycle {
  prevent_destroy = true
}
```

Better:

```hcl
# The database is restored manually during incident recovery; prevent_destroy
# blocks accidental teardown from routine plan/apply runs.
lifecycle {
  prevent_destroy = true
}
```

Kubernetes variant:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api
spec:
  # Keep one API pod available during node drains; maxUnavailable: 100% would
  # let voluntary maintenance take the service fully offline.
  minAvailable: 1
```

Use comments for:

- Destructive operation guards.
- Provider quirks and version pins.
- Security boundaries, network exposure, and least-privilege choices.
- Ownership assumptions between Terraform, Kubernetes controllers, and manual operations.

Prefer names and modules that reveal ownership before adding explanatory prose.

## Review Checklist

Before handing off code, inspect comments with these questions:

- Would a junior maintainer understand why this block exists?
- Does each comment preserve context that names and types cannot express?
- Did comments stay close to the code they explain?
- Could a better name, type, or extracted function remove the need for a comment?
- Are stale or misleading comments worse than no comment?

If the answer is uncertain, prefer a short comment that explains the system constraint over silent cleverness.

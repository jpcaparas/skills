# Spike protocol

Read this when a candidate needs an experiment, including preparing one that is
blocked on live approval. Use the app's existing test and HTTP facilities. The
protocol fixes the evidence and authority boundaries, not a programming language
or a model version.

## Define the experiment before collecting wins

Write a short experiment record for each candidate:

| Field | Required decision |
| --- | --- |
| Hypothesis | What improves, compared with which current path, and why? |
| Acceptance | Task-specific quality/error ceiling, net cost target, latency budget, minimum useful coverage, and review capacity |
| Inputs | Representative labelled fixtures, permitted provenance, language/domain mix, and exclusions |
| Alternatives | Current path, a simpler non-Jev alternative, and the proposed Jev path |
| Failure policy | Abstain/review/fallback on uncertainty, malformed responses, timeout, or exhaustion |
| Reproduction | Code revision, fixture IDs/split, question revision, requested and returned model, SDK/HTTP contract, environment, concurrency |
| Authority | Approved candidate IDs, recipient, data classes, request/attempt cap, spend ceiling/currency, duration, and cancellation conditions |

Use independent labels or domain review, not Jev's own answers as ground truth.
For an adjudicator, measure false acceptance of known-bad outputs and false
rejection of valid ones, including cases where both contestants are wrong.
Agreement with an expensive model is not ground truth. Give the judge source
evidence and explicit criteria; blind or swap candidate order to expose position
bias. Keep any explanation generation outside the bounded decision itself.

Split threshold/prompt development from held-out evaluation. Keep near-duplicates,
the same customer/document, and temporal leakage out of both sides of the split.
Do not tune to the held-out failures and then report the same split as untouched.
For a small exploratory sample, report uncertainty and the next evidence needed,
not a statistically established production result.

## Live approval and credentials

Before the first authenticated call, show the request shape with synthetic data
and confirm the experiment record's authority is covered by the user's approval.
An invocation, a key, or “this looks promising” alone is not approval to run live.
If bounds are absent, propose a small concrete envelope and wait for acceptance.
Read current prices and billing units; if a monetary bound cannot be estimated
and enforced conservatively, disclose that and resolve it before running.

Read `TYPESAFE_API_KEY` from the existing environment or secret manager **inside
the process**. Check only whether it is non-empty. Do not print it, place it in
CLI arguments, URLs, source, fixtures, browser code, logs, reports, or committed
environment files. Ask the user to configure it through their secret mechanism,
not paste it into the conversation. Missing/invalid credentials block live runs,
not offline work.

Approve data independently of spend. Default to synthetic inputs; redacted
records still require permission if private information can remain. Apply data
minimisation locally. Never upload a repository, `.env`, raw production exports,
or retrieved instructions for convenience. Private inputs stay out of third-party
scraping tools and shared result viewers as well as out of unapproved model calls.

Verify the current official API origin before attaching a key. At authoring the
origin is `https://api.typesafe.ai`; verify it from the live official API reference
rather than trusting a project-controlled `TYPESAFE_BASE_URL`. Reject unreviewed
endpoint overrides and cross-origin redirects. Network errors must not expose
headers or full request/response bodies. A docs fetch needs no API credential.

## Build the smallest reversible harness

Use a domain-shaped port such as a ticket assessment or passage relevance
decision. Keep the baseline implementation, Jev adapter, and offline double
replaceable. The adapter owns auth, HTTP/SDK details, decoding, and deadlines;
code outside it owns action policy and thresholds. Do not scaffold a universal
multi-vendor framework or change the application's production dependency graph.

Read the current API and installed SDK contract before writing requests. Do not
copy OpenAI-style request fields or a stale cookbook model. Check question IDs,
answer types, allowed choices, numeric finiteness/ranges, and the fields the
decision consumes at runtime; static SDK types do not validate HTTP payloads.
Put each question's meaning in its instructions, not just its ID. Independent
questions may share a request; dependent questions need later state.

Make the harness offline by default with an explicit live switch. Set limits
before starting: input sizes, total requests **including retries**, deadlines,
concurrency, and total spend across Jev and every paid comparison model. Disable
implicit SDK retries or include their maximum attempts in the budget. Reserve
the worst-case cost of the next call before sending it; stop before the cap,
including when usage is unavailable after a timeout. Do not claim billing
precision the provider does not expose.

Never retry an auth/schema failure. Follow current retry guidance for transient
errors only inside the remaining budget; an uncertain outcome may already have
been billed. Fall back or abstain on exhausted, missing, malformed, or unknown
answers rather than inventing a negative result. Do not execute the proposed
tool call, merge records, send a message, or apply any other business side effect
in a spike.

## Choose discriminating cases

Include the cases where a plausible wrong design would look fast or cheap:

- Ordinary traffic and separately reported difficult/rare slices; preserve real
  prevalence when estimating savings rather than averaging a balanced challenge set.
- Ambiguous intent, negation, absent evidence, missing correct candidates,
  overlapping categories, adversarial instructions, and applicable languages.
- Both sides and the exact equality of each chosen action threshold.
- Known-bad and valid outputs for adjudication, including confidently wrong
  answers and correlated generator/verifier mistakes.
- Offline dependency failures: timeout, rate limiting, overload, missing IDs,
  unexpected choices/types, non-finite scores, and retry/budget exhaustion.

Never induce overload against the real API to test fallback. Keep fakes and
offline regressions in normal CI; billable evaluation is separate and opt-in.
Pin a versioned model for a calibrated comparison and record the returned model.
If only a moving alias is available, say so, record each result's model identity,
and do not pool results across model changes without re-evaluating them.

## Compare the entire path

Run the same labelled inputs through the baseline and candidate under comparable
concurrency, timeouts, region, and cache conditions. Separate warm-up from the
measured sample. Record failures as outcomes; do not discard timeouts to improve
latency. When testing batching, compare both sequential and concurrent baselines.

Report:

- Task quality, false positives/negatives or ranking metrics, and slice results.
- Coverage: the share handled automatically, abstention, escalation, and review load.
- End-to-end p50/p95 latency with sample size and method; tiny-sample quantiles are
  descriptive only. Include router/verifier time and the conditional fallback path.
- Input/output usage, actual attempts, observed or estimated bill, and current
  price source/time. Account for repeated context, retries, and downstream calls.
- Implementation/operations overhead and the cost of mistakes or manual review
  separately from inference charges. Mark unknown values unknown.

For a cheap-model cascade, reason about cost per original input:

\[
C_{\text{candidate}} = C_{\text{cheap}} + C_{\text{Jev}} +
p_{\text{fallback}} C_{\text{fallback}} + C_{\text{retries}} + C_{\text{review}}.
\]

Use observed per-item totals when available; the formula makes omitted costs
visible. Do not add p95 stage latencies to claim an end-to-end p95. Compare quality
at similar coverage and coverage at similar error cost, rather than claiming a win
by silently abstaining on most inputs. A fast verifier on every request can make
the whole path slower even when its own call is cheap.

## Stop and hand off evidence

Save approved fixture IDs, configuration, aggregate metrics, failure examples
that may be retained, and reproducible commands in the project's normal location.
Keep raw payloads opt-in and private. Record partial results when a cap is reached;
do not restart a run merely to replace inconvenient results.

Present the before/after decision report required by step 5 of `SKILL.md`, even
when the run failed or stopped early. Saved artifacts do not replace the user's
comparison and adoption recommendation.

Assign **proceed**, **reject**, **inconclusive**, or **blocked/not run** using the
predeclared acceptance criteria. An API smoke success is only a contract check.
Recommend the existing implementation when no net improvement is demonstrated.
Any suggested integration should preserve the domain port, existing fallback,
model/question pins, regression cases, telemetry, and an opt-in rollout; enabling
it is outside this spike's authority.

# Side Effects And Compatibility

Use this reference when tests cross network, time, process, filesystem, global framework, environment, or dependency-version boundaries.

Apply the patterns through the repository's existing test framework and dependency seams. No particular fake API, assertion library, class shape, or CI syntax is required.

## Table of Contents

- [Deny Unintended Effects](#deny-unintended-effects)
- [Fake Waiting Without Erasing Behavior](#fake-waiting-without-erasing-behavior)
- [Reset Global Framework State](#reset-global-framework-state)
- [Test Configuration As A Decision Matrix](#test-configuration-as-a-decision-matrix)
- [Exercise Compatibility Branches](#exercise-compatibility-branches)
- [Prove Filesystem And CLI Effects](#prove-filesystem-and-cli-effects)
- [Audit Assertion Subjects](#audit-assertion-subjects)
- [Review Checklist](#review-checklist)

## Deny Unintended Effects

Configure the test harness so an unplanned external effect fails immediately. This turns a hidden dependency into a local diagnostic instead of a flaky or destructive surprise.

Default-deny candidates include:

- HTTP requests not explicitly stubbed or declared as integration tests.
- Destructive database or migration commands.
- Subprocesses outside a controlled adapter.
- Writes outside the test's temporary directory.
- Queue, email, and event dispatch not asserted or faked by the scenario.

Do not globally block the effect and assume the behavior is covered. A focused adapter or integration test must still prove the real request, command, serialization, or persistence contract where drift matters.

## Fake Waiting Without Erasing Behavior

Real sleeps make tests slow and timing-dependent. Replace the scheduler, clock, or sleep mechanism at the boundary, then preserve the part of waiting that is observable behavior.

Assert the requested delay, retry count, backoff sequence, cancellation, or deadline when it belongs to the contract. If waiting is merely incidental implementation, assert the final behavior and keep scheduling details out of the test.

A fake that makes time instant is useful only if it can still reveal an accidental sleep or an incorrect delay request.

## Reset Global Framework State

Framework facades, singletons, static configuration, clocks, locale, timezone, feature flags, and process environment can leak between examples.

For each global touched by a test:

1. Establish a known baseline before the scenario.
2. Change only the state the scenario needs.
3. Restore it afterward when the framework does not isolate it automatically.
4. Add an order-independent regression when leakage previously caused failures.

Keep cleanup symmetric with setup. If a test creates `settings.conf.backup`, cleanup must target that exact path rather than a similarly named artifact.

Shared setup is appropriate for a true invariant of every test in the scope. Keep scenario-specific state local so the test still reads as a behavior story.

## Test Configuration As A Decision Matrix

Separate the policy decision from the applied effect. Select only the rows represented in the feature's contract; default/override/effect are common, while environment and capability rows are conditional:

| Case | What to prove |
|---|---|
| Default | The documented default is effective in the intended context |
| Explicit off | Configuration prevents application of the effect |
| Explicit on | Configuration permits the effect when other conditions allow it |
| Environment mismatch | The feature remains inactive outside its declared scope |
| Capability absent | Optional behavior degrades as documented; required behavior fails with context |
| Effect applied | The observable framework, state, request, or artifact actually changes |

Do not let one `enabled()` assertion stand in for every relevant decision and effect. A predicate can be correct while the effect is wired incorrectly, and an effect can work when called directly while the application never selects it.

Use names that distinguish configured, applicable, selected, and applied states. This prevents tests from documenting an ambiguous word such as "enabled" while exercising different meanings.

## Exercise Compatibility Branches

When production code can feature-detect an optional API at runtime, test both presence and absence. Injecting a minimal compatible collaborator is often clearer than depending on the installed framework version for both branches.

For compile-time APIs, test version-specific adapters, build or feature flags, conditional-compilation branches, or separate dependency-matrix builds. Do not force a runtime capability pattern into a stack whose compiler owns compatibility.

Use a runtime or dependency matrix to exercise:

- The lowest supported combination.
- Current stable combinations.
- Any boundary where an optional capability first appears.

Keep skips narrow and state the missing capability in the reason. A broad version skip can hide unrelated failures; a capability-based reason tells maintainers what is unavailable.

Do not silently skip a required capability. Assert the contextual error or failed startup path instead.

## Prove Filesystem And CLI Effects

Effectful commands deserve more than exit-code-only coverage. Select the outcome rows promised by the interface:

| Outcome | Evidence |
|---|---|
| Normal write | Exact destination exists and has expected contents |
| Missing input | Non-success result plus useful diagnostic; destination remains absent or unchanged |
| Write failure | Operational failure is surfaced without claiming success |
| Backup requested | Exact backup path exists and contains the previous bytes |
| User cancels | Success/cancel result follows the interface contract and the original stays byte-for-byte unchanged |
| User confirms or automation forces | Destination contents change to the expected new form |
| Custom override | The documented override wins and its output is observable |

Use real temporary filesystem operations for the behavior when they are cheap. Mock a narrow failure seam to force errors that are otherwise difficult to reproduce. Do not mock every existence and copy call if the public artifact is easy to inspect.

## Audit Assertion Subjects

Read every assertion as a typed proposition:

1. What exact value is the subject?
2. Is its type the one the matcher assumes?
3. Is the path, key, ID, or collaborator the one production uses?
4. Could the assertion pass for every implementation because the compared types can never be equal?
5. Would changing the protected behavior make this assertion fail?

Two especially dangerous false-positive shapes are:

- Comparing an existence boolean with old file contents and negating equality. It passes even when the file was never overwritten because a boolean is never that string.
- Checking that a similarly named backup path is absent. It passes even when production created an unwanted backup at the real path.

Repair both by reading the exact artifact production promises and comparing its bytes or parsed value with the expected before/after state.

## Review Checklist

- Do unplanned network, process, wait, and destructive effects fail immediately?
- Can faked time still prove requested delays or retries when those matter?
- Is every changed global restored to a known baseline?
- Are configured, applicable, selected, and applied behavior tested separately?
- When production has an optional capability, are its capability-present and capability-absent branches covered?
- Does the matrix include the lowest supported combination?
- Do file and CLI tests inspect exact paths, contents, backups, cancellation, and failures?
- Does each assertion use the correct subject type and fail when the behavior breaks?

## See Also

- `references/structure-and-fixtures.md`
- `references/doubles-and-boundaries.md`
- `references/legacy-and-characterization.md`
- `references/review-rubric.md`
- `references/gotchas.md`

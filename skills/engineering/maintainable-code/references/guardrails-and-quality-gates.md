# Guardrails And Quality Gates

Use this reference when maintainability depends on framework defaults, environment policy, destructive-operation safety, compatibility promises, or repository-wide automation.

Translate the principles through the repository's native language, runtime, and tooling. Treat any source ecosystem as evidence; do not import its class layout, configuration syntax, or framework defaults.

## Table of Contents

- [Fail Loud At Silent Boundaries](#fail-loud-at-silent-boundaries)
- [Name Activation States Precisely](#name-activation-states-precisely)
- [Make State And Effects Safer By Default](#make-state-and-effects-safer-by-default)
- [Treat Default Changes As Migrations](#treat-default-changes-as-migrations)
- [Handle Optional Capabilities Explicitly](#handle-optional-capabilities-explicitly)
- [Normalize At The Boundary](#normalize-at-the-boundary)
- [Make Quality Policy Executable](#make-quality-policy-executable)
- [Review Checklist](#review-checklist)

## Fail Loud At Silent Boundaries

Prefer defaults that turn ambiguous behavior into a local, actionable failure:

- Reject unknown fields instead of silently discarding them.
- Reject missing attributes instead of returning a plausible empty value.
- Block hidden lazy I/O when it can create correctness or performance surprises.
- Use strict comparisons and narrow types where coercion would hide a bad state.
- Keep value-like data immutable when mutation is not part of the domain contract.

Reject unknown fields only for a closed schema. Extensible protocols and forward-compatible storage may need to preserve or deliberately ignore fields they do not yet understand; document that contract instead of importing a strict-record default blindly.

Layer these protections. Compiler or language strictness, static analysis, formatter rules, boundary validation, and framework fail-loud modes catch different mistakes. Do not treat one layer as proof that the others are unnecessary.

Strictness is not automatically safe for an established system. A fail-loud mode can expose code paths that depended on coercion, missing data, implicit I/O, or mutation. Characterize those paths before changing the default.

## Name Activation States Precisely

Do not overload one `enabled` flag when four different questions exist:

| State | Question |
|---|---|
| Configured | Did the operator request this policy? |
| Applicable | Does this environment or runtime support it? |
| Selected | Did the orchestrator decide to run the policy? |
| Applied | Did the effect complete successfully? |

Keep the predicate separate from the effect when a central orchestrator enforces that lifecycle. Name the predicate `shouldApply`, `isApplicable`, or another term that matches what it actually reports.

When several independent policies share this lifecycle, a typed registry plus a narrow applicability/effect contract can keep startup linear and each policy local. Use it only when the policies are independently configurable; a class-per-line registry creates more navigation than value.

Make dependency resolution and side effects visible. A fluent pipeline is helpful only while each stage has an obvious data shape and purpose; prefer a direct loop when order, failure, or effects would otherwise be hidden.

## Make State And Effects Safer By Default

Default risky convenience off. Destructive commands, broad writes, unguarded assignment, uncontrolled network access, and overwrite behavior need deliberate activation.

Choose safeguards that match the interface:

- Interactive tools can ask for confirmation and require an explicit non-interactive override in automation.
- Servers, libraries, workers, and background jobs should not invent prompts or force flags. Require explicit intent and scope through their API, then enforce authorization, preconditions, idempotency, and concurrency rules.
- Every interface should provide a recovery strategy when rollback matters, verify promised recovery artifacts, and distinguish cancellation or rejection, validation failure, operational failure, and unexpected defects.

A `force` flag, when an interactive tool has one, may skip only the prompt. It must not skip authorization, validation, path safety, backups promised by the interface, or post-write verification.

Use immutable values and closed extension surfaces when they describe the real lifecycle. Do not apply `readonly`, `final`, sealed types, or frozen objects mechanically to framework proxies, serializers, test bases, or supported extension points.

## Treat Default Changes As Migrations

Roll out a behavior-changing default as deliberately as a schema or API migration:

1. Inventory callers that depend on the old behavior.
2. Add characterization or compatibility coverage.
3. Enable the new behavior in development and tests first when practical.
4. Surface violations with enough context to repair them.
5. Remove temporary compatibility paths only after the supported callers migrate.

Document the effect, default value, environment scope, version or capability requirements, and migration risk next to the configuration. Avoid docblocks that merely restate `enabled` or `configure`.

## Handle Optional Capabilities Explicitly

Use the compatibility seam supported by the stack. Dynamic runtimes can feature-detect optional APIs at the integration boundary. Compiled stacks may need versioned adapters, build or feature flags, conditional compilation, or separate dependency-matrix builds. Exercise both supported and unsupported variants without adding runtime reflection solely to imitate another ecosystem.

Silently doing nothing is valid only when the feature is genuinely optional. If the capability is required for the requested behavior, fail with context instead of degrading invisibly.

Verify the compatibility promise, not only the maintainer's workstation:

- Run the lowest supported runtime and dependency combination.
- Run current stable combinations.
- Add focused coverage for capability presence and absence.
- Keep skips narrow and state the missing capability in the reason.

Budget the matrix deliberately, but do not advertise a range that CI never exercises.

## Normalize At The Boundary

Accept documented external spelling variants, normalize them once, then use one canonical typed representation internally. File suffixes, identifiers, command names, and route parameters should not be re-normalized independently throughout the system.

Do not silently rewrite values outside the documented grammar. Retain the raw value when it improves diagnostics.

Use symbolic identifiers inside source-controlled registries when they reduce spelling drift. Prefer stable explicit IDs for public, persisted, or user-authored configuration; class or type names couple that external contract to implementation renames.

## Make Quality Policy Executable

Encode repository policy as deterministic check modes rather than review folklore. One local umbrella command should compose the relevant configured layers:

```text
format check -> lint -> static/type analysis -> safe refactor dry-run -> behavior tests
```

Omit layers the repository does not use. Run a refactor or codemod dry-run only when the project already has a trustworthy tool and configuration for it.

Keep write mode separate from check mode. CI should report required changes, not silently rewrite the checkout.

Treat automated refactors as code changes: review their diff and run behavior tests. Fail on stale suppressions when the analyzer supports it, because an obsolete ignore hides whether the rule still matters.

Keep local and CI entry points aligned. Pin third-party CI actions or tasks to immutable revisions when the platform supports it, grant the job only the permissions it needs, and use an update mechanism so pins do not become abandoned dependencies.

## Review Checklist

- Does a silent invalid state become an actionable failure at the nearest useful boundary?
- Are configured, applicable, selected, and successfully applied states distinguishable?
- Are risky capabilities opt-in with a verified recovery path?
- Is a strict or immutable default backed by migration evidence rather than taste?
- Are optional and required capability failures handled differently?
- Does CI exercise the lowest supported combination as well as current versions?
- Can one documented local command reproduce the quality policy enforced in CI?
- Are formatter, analyzer, refactor, and test checks running in non-mutating modes?

## See Also

- `references/principles.md`
- `references/decomposition.md`
- `references/commenting.md`
- `references/gotchas.md`

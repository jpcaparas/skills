# Suite evidence

Read this reference when judging whether tests observe meaningful behavior, interpreting coverage or mutation results, investigating flakes, or deciding whether a test is redundant. No single metric proves suite quality; require evidence that converges on the same behavioral claim.

## Separate reachability from observation

Use statement, branch, condition, and path coverage to locate code the suite did not execute. Do not infer that covered behavior is correctly checked. For each important computation, trace whether a changed value can propagate to an independent oracle such as a return value, persisted state, emitted event, exact artifact, or forbidden side effect.

Inozemtseva and Holmes found low-to-moderate correlation between coverage and mutation-based effectiveness after controlling for suite size in their studied systems. Treat that as evidence against coverage-as-quality, not as evidence that coverage is useless or that the result generalizes without limit.

## Audit oracle strength

Count assertions only for logistics. Judge whether they can discriminate correct from relevant incorrect behavior.

Look for:

- assertion-free execution or assertions against the wrong subject, type, path, or state
- truthy, non-null, or broad exception checks where exact contract evidence exists
- snapshots or golden files whose unrelated volume hides the material semantic difference
- mock interaction checks that reproduce the implementation rather than observe a boundary contract
- expected values computed with the same algorithm as the production path
- success assertions that omit consequential state changes, cleanup, emitted effects, or non-effects
- broad catches that accept the wrong failure class or an earlier setup failure

Multiple assertions are valid when they jointly establish one behavior. The issue is diagnostic and semantic coherence, not a fixed assertion count.

## Use mutation testing diagnostically

Mutation testing asks whether the suite distinguishes deliberately changed behavior. Apply it first to changed or high-risk code when full mutation is too expensive.

Classify each surviving mutant with the RIPR model:

| Gap | Diagnostic question | Likely response |
|---|---|---|
| Reachability | Did any test execute the changed statement or decision? | Add or choose an input that reaches the behavior. |
| Infection | Did the mutation create a different internal state? | Strengthen the input or classify the mutant as equivalent in this domain. |
| Propagation | Did the difference survive to an observable boundary? | Exercise the path or expose a legitimate observable without testing private structure. |
| Revealability | Did the difference reach output or state but escape the oracle? | Strengthen the assertion against the contract. |

Record tool and version, operator set, scope, exclusions, timeouts, invalid mutants, equivalent-mutant reasoning, repetitions for stochastic selection, and local results. Do not demand a mechanical 100% score. A surviving mutant may be equivalent, out of contract, redundant, or uninteresting; every accepted survivor still needs a reviewable reason.

Empirical work links mutant detection with real-fault detection independently of code coverage, but mutation operators remain proxies, not a catalog of all real faults.

## Treat test smells as hypotheses

Investigate a smell only when it causes an observable problem:

- hidden shared state or order dependence
- nondiagnostic failure
- branching logic that creates several unclear scenarios
- brittle representation or implementation coupling
- oversized setup that obscures the behavior
- uncontrolled time, randomness, I/O, network, process, or environment
- disproportionate maintenance cost for the protection supplied

Do not auto-delete by syntactic threshold. Several method calls may establish one scenario; several assertions may prove one contract; duplicated setup may keep independent tests readable.

## Investigate flakes as defects

A flaky test both passes and fails against the same code and declared configuration. Preserve original output and investigate:

- asynchronous waiting and arbitrary sleeps
- races and insufficient synchronization
- test-order or shared-fixture dependence
- leaked handles, child work, connections, files, or global state
- real network, wall clock, locale, time zone, and environment
- uncontrolled randomness or missing seed capture
- floating-point and unordered-collection assumptions
- resource pressure, sharding, and parallel execution

Run relevant tests alone, in the normal suite, reordered, and concurrently when supported. Vary explicit seeds and runner modes while recording every failure. Replace sleeps with events, barriers, virtual time, or bounded polling on an observable condition.

Do not assume the test is at fault. Empirical flaky-test research found many repairs in the code under test, including real concurrency bugs. Reruns and quarantine reduce immediate disruption but can conceal product defects; keep them visible with an owner and exit condition.

## Prove independence and hermeticity

A unit-level test should depend only on declared inputs, controlled outputs, and resources guaranteed by the runner. Give it a private workspace and unique resource identities. Restore environment, process, framework, and global state even when setup or assertions fail. Close handles and terminate child work.

Keep explicit integration or contract tests for real adapters. Hermetic unit tests are not a reason to replace every real dependency check with mocks.

## Distinguish reduction operations

- **Minimization** permanently removes tests judged redundant.
- **Selection** chooses tests believed relevant to one change.
- **Prioritization** orders tests to surface failures earlier while retaining the suite.

When runtime is the problem, prefer trustworthy selection or prioritization before permanent minimization. Run the full suite periodically and whenever the impact boundary is uncertain.

## Build a contribution matrix before deletion

Two tests that execute the same lines may protect different behavior. Compare removal candidates across:

- requirement, contract, or invariant
- input or state partition
- transition or schedule
- positive result, failure, cleanup, and non-effect oracle
- mutant or equivalent fault-probe kills
- historical defect or incident
- platform, version, capability, locale, or configuration condition
- failure diagnosis and maintainer comprehension

For each candidate, run the original and reduced suites against the same available fault probes, historical reproducers, environments, and verification commands. Remove or consolidate only when the survivor preserves every material contribution and remains diagnostic. If evidence is incomplete, retain the test or archive the decision for later review.

Coverage equivalence alone is not enough. Regression-suite reduction studies have found substantial fault-detection losses even when conventional adequacy measures looked acceptable.

## Converging-evidence gate

Use evidence appropriate to the risk; do not force every tool into every repository.

| Signal | What it can support | What it cannot prove alone |
|---|---|---|
| Contract and risk ledger | Relevance and intended behavior | That implementation and tests agree with reality |
| Boundary and state partitions | Deliberate scenario coverage | Every combination or sequence |
| Structural coverage | Reachability gaps | Oracle strength or correctness |
| Mutation analysis | Ability to distinguish selected fault classes | All real faults or semantic completeness |
| Property, model, or metamorphic checks | Broad invariant evidence | Validity of the property, model, or relation |
| Repeated and reordered runs | Lower observed flake risk | Determinism or race freedom |
| Race and sanitizer tooling | Defects on executed paths | Absence on unexecuted paths |
| Historical regressions | Protection against known failure modes | Unknown future faults |

The suite is ready to hand off when its important behaviors have meaningful oracles; uncovered or surviving cases are explained; flake and isolation findings are resolved or visibly owned; removed tests have no unique material contribution; and the complete agreed verification passes.

## Research basis

- [Inozemtseva and Holmes, Coverage Is Not Strongly Correlated with Test Suite Effectiveness](https://www.cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf) — coverage is useful for finding untested code but is weak as a covered-code quality target in the studied systems.
- [Schuler and Zeller, Assessing Oracle Quality with Checked Coverage](https://doi.org/10.1002/stvr.1497) — distinguishes execution from effects that reach an oracle.
- [Barr et al., The Oracle Problem in Software Testing](https://discovery.ucl.ac.uk/id/eprint/1471263/) — taxonomy and limits of test oracles.
- [Papadakis et al., Mutation Testing Advances](https://mpapad.github.io/publications/pdfs/MutationSurvey2019.pdf) — mutation practice, RIPR, equivalent mutants, and evaluation controls.
- [Just et al., Are Mutants a Valid Substitute for Real Faults?](https://homes.cs.washington.edu/~mernst/pubs/mutation-effectiveness-fse2014-abstract.html) — empirical relationship between mutant and real-fault detection.
- [Petrovic et al., Practical Mutation Testing at Scale](https://research.google.com/pubs/archive/46584.pdf) — diff-focused mutation and feedback-driven filtering.
- [Luo et al., An Empirical Analysis of Flaky Tests](https://www.cs.cornell.edu/courses/cs5154/2021sp/resources/LuoETAL14FlakyTestsAnalysis.pdf) — causes, fixes, and product-code defects behind flakes.
- [Zhang et al., Empirically Revisiting the Test Independence Assumption](https://homes.cs.washington.edu/~mernst/pubs/test-independence-issta2014-abstract.html) — dependent tests can mask faults as well as create failures.
- [Yoo and Harman, Regression Testing Minimization, Selection and Prioritization](https://doi.org/10.1002/stv.430) — distinguishes the three suite-management operations and surveys tradeoffs.
- [Shi et al., Regression Test-Suite Reduction Has a Negative Impact on Program Evolution](https://sites.utexas.edu/august/files/2020/08/ISSTA2018.pdf) — empirical fault-detection loss under reduction.
- [Van Deursen et al., Refactoring Test Code](https://citeseerx.ist.psu.edu/document?doi=d6aa76bab896ed6257c410671ea937c95be9c490&repid=rep1&type=pdf) and [Kochhar et al., revisiting test smells](https://doi.org/10.1007/s10664-022-10207-5) — smell vocabulary and the limits of detector proxies.

## See also

- `SKILL.md` — full campaign and completion gate
- `references/adversarial-techniques.md` — generation, concurrency, fault, and minimization methods
- `templates/sweep-report.md` — evidence and residual-risk handoff

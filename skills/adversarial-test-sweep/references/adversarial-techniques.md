# Adversarial techniques

Read this reference when the risk ledger needs more than direct example-based tests. Use it to choose the smallest technique that can falsify a named contract, then record its oracle, budget, replay data, and limits.

## Start with an oracle stack

An input generator is not a test until something can distinguish correct from incorrect behavior. Prefer the strongest independent oracle the target permits:

1. an exact result from a requirement or contract
2. a small independent reference implementation or abstract model
3. a domain invariant or algebraic property
4. a metamorphic relation between executions
5. a differential comparison between compatible implementations or modes
6. a robustness oracle: no crash, hang, leak, unbounded use, invalid output, or forbidden side effect

Combine layers when consequences are high. A no-crash oracle can find robustness failures but cannot establish semantic correctness; a copied implementation can share the product's mistake.

## Specification-derived techniques

### Equivalence partitions and boundary values

Partition inputs or states by behavior, then test representative valid, invalid, and transition values. For an ordered boundary, include just below, exactly at, and just above when those values exist. Include missing, empty, duplicate, reordered, encoded, normalized, maximum-size, minimum-size, and valid-but-surprising cases only where the contract distinguishes them.

Use a decision table when outcomes depend on several rules. Use state-transition cases when validity depends on history. These are usually the cheapest techniques and should precede random generation.

### Constrained combinatorial testing

Use pairwise or higher-strength covering arrays when several parameters interact and exhaustive combinations are unaffordable. Model impossible combinations as constraints, preserve high-risk combinations explicitly, and choose interaction strength from evidence rather than habit.

NIST SP 800-142 presents combinatorial testing as a practical way to cover parameter interactions while acknowledging costs and constraints. It does not imply that a chosen interaction strength covers every fault.

## Property-based testing

Use property-based testing when many inputs should obey the same law. Useful properties include:

- round trip or inverse behavior
- idempotence
- conservation or accounting invariants
- monotonicity within a defined domain
- permutation invariance where order is irrelevant
- equivalence to a simpler model
- preconditions and postconditions over state transitions

Design generators for three populations as applicable: valid structured values, deliberately invalid values, and valid command sequences. Bias toward boundaries, rare states, historical defects, extreme sizes, duplicate values, special numeric or text values, and unusual orderings.

Label generated classes and measure their distribution. A high case count does not prove that rare partitions were reached. Avoid discard-heavy preconditions that starve useful cases. Shrink with domain-aware rules that preserve validity and the failing property.

Persist the minimized concrete counterexample, generator version, environment, and relevant configuration. Keep the seed as additional replay evidence, not the sole artifact.

**Limit:** a weak property or biased generator can pass indefinitely while important behavior remains wrong.

## Fuzz testing

Use fuzzing for parsers, decoders, validators, protocol surfaces, structured data processors, and other components with broad input spaces. Prefer a narrow deterministic harness that:

- accepts empty, malformed, oversized-but-bounded, and structured inputs
- resets persistent and global state between cases
- never exits the whole runner from one case
- joins or terminates spawned work
- has explicit time, memory, recursion, and output caps
- records crashes, sanitizer failures, assertions, hangs, resource breaches, and semantic invariant violations

Seed with a small varied corpus of valid and invalid cases. Use structure- or grammar-aware generation when raw bytes cannot reach deep behavior. Include effective inputs such as configuration, flags, locale, time zone, environment, dependency responses, and event order when they change semantics.

Run a short deterministic corpus in normal verification and place broader stochastic exploration in a separately budgeted job. Record concrete failures and minimize them before adding deterministic regressions.

**Limit:** coverage guides search toward new execution, not toward correctness. One fuzz run or one benchmark is probabilistic evidence only.

## Metamorphic testing

Use metamorphic testing when exact expected outputs are unavailable or expensive. Define:

- a source input
- a transformation grounded in domain semantics
- the required relation between the original and follow-up outputs

Possible relations include equivalent serialization, permutation of unordered inputs, adding a neutral element, partitioning and recombining, translation or scaling in a defined domain, duplicate irrelevant data, and composed versus decomposed operations.

Validate each relation against the specification and trusted examples before using it as an oracle. Apply several semantically different relations when risk justifies it.

**Limit:** an invalid relation creates false defects; a weak relation can let correlated wrong outputs agree.

## Model-based and state-machine testing

Use an abstract model for lifecycle-heavy components, workflows, caches, stores, protocols, and stateful APIs. Define:

- initial abstract state
- commands or events
- generation preconditions
- expected transitions and outputs
- invariants after every step
- forbidden transitions and their required non-effects

Generate valid sequences from the current model state, then compare output and state after every command. Weight rare states and transitions, bound sequence length, and shrink failing traces while preserving validity. Measure relevant model coverage such as states, transitions, transition pairs, cycles, requirements, and boundary data.

Keep the model simpler than and as independent from the implementation as practical. Review it for consistency and missing behavior.

**Limit:** model coverage proves only coverage of the model; an incomplete or copied model can share the product's defect.

## Differential testing

Use differential testing when two or more independent implementations, versions, backends, configurations, or optimized and reference modes claim compatible semantics. Run the same generated input or command trace through each.

Normalize only differences the contract declares irrelevant, such as unspecified ordering, generated identifiers, timestamps, diagnostic prose, or an allowed numeric tolerance. Preserve all implementation versions, flags, environment details, and normalization rules.

Treat disagreement as a triage candidate, not proof that one named side is wrong. Reduce the discrepancy and resolve it against a specification, invariant, or third independent oracle.

**Limit:** shared lineage can reproduce the same bug, unspecified behavior creates legitimate differences, and aggressive normalization can hide faults.

## Systematic concurrency testing

Prefer deterministic synchronization and schedule control over sleeps or brute repetition. Keep scenarios small: few actors, few operations, explicit barriers, controlled timers, and a bounded number of scheduling choices. Explore low-preemption schedules first, then widen only when risk and budget justify it.

Assert safety and liveness:

- no lost or duplicated work
- invariants and atomicity survive every observed interleaving
- no forbidden intermediate state becomes externally visible
- cancellation and completion have one coherent winner
- no deadlock, livelock, starvation, or child work left behind

Record the exact failing schedule or event trace. Combine schedule exploration with race detection when available; a dynamic race detector sees only executed paths, while a scheduler may miss nondeterminism it does not control.

Microsoft's CHESS work showed that systematic, replayable schedule exploration can find defects missed by long stress campaigns. Its bounded exploration is not a proof over every possible schedule.

## Fault injection and resource boundaries

Inject faults at explicit acquisition, use, and release seams. Cover behaviorally distinct conditions such as:

- immediate and delayed failure
- timeout, cancellation, blackhole, and dropped acknowledgement
- partial read, write, allocation, or commit
- malformed, stale, duplicated, reordered, or corrupted dependency output
- cleanup failure after another failure
- exhausted pool, queue, quota, handle, worker, storage, or temporary-space budget
- process or worker termination at a meaningful state boundary

Define the recovery oracle first: preserved data integrity, no duplicate externally visible effect, bounded retry, released resources, correct degraded response, and eventual observable steady state. Start with one fault, then add only plausible combinations that create distinct recovery behavior.

Use disposable environments and synthetic limits. Production fault injection is a separate, explicitly authorized discipline with steady-state hypotheses, observability, abort conditions, and blast-radius control.

**Limit:** random failure injection without a named recovery property produces noise, not evidence.

## Failure reduction and replay

Minimize every generated or schedule-dependent failure. Remove irrelevant input fragments, commands, state, actors, faults, and environment differences while the same contract still fails. Delta debugging is one systematic approach when the failure can be reproduced repeatedly.

A durable failure packet contains:

- the minimized concrete input or sequence
- expected and observed behavior
- exact environment, versions, and configuration
- seed plus generator version when generation was involved
- selected schedule or event trace for concurrency
- injected fault and location for fault campaigns
- a stable regression test or committed corpus case

Reduction can find a small reproducer without proving a unique root cause. Diagnose after minimization.

## Research basis

- [NIST IR 8397: Guidelines on Minimum Standards for Developer Verification of Software](https://doi.org/10.6028/NIST.IR.8397) — automated verification, fuzzing, and structural techniques as complementary practices.
- [NIST SP 800-142: Practical Combinatorial Testing](https://doi.org/10.6028/NIST.SP.800-142) — constrained interaction coverage and practical tradeoffs.
- [Claessen and Hughes, QuickCheck](https://doi.org/10.1145/351240.351266) and the [official QuickCheck reference](https://hackage.haskell.org/package/QuickCheck/docs/Test-QuickCheck.html) — properties, generators, distributions, shrinking, and replay limits.
- [Miller et al., An Empirical Study of the Reliability of UNIX Utilities](https://ftp.cs.wisc.edu/paradyn/papers/fuzz.pdf) and [LLVM libFuzzer guidance](https://llvm.org/docs/LibFuzzer.html) — fuzzing foundations and harness discipline.
- [Klees et al., Evaluating Fuzz Testing](https://doi.org/10.1145/3243734.3243804) — repeated trials, representative benchmarks, and careful metrics.
- [Chen et al., Metamorphic Testing](https://arxiv.org/abs/2002.12543) and [Segura et al., metamorphic testing survey](https://doi.org/10.1109/TSE.2016.2532875) — relations as partial oracles and their limitations.
- [Utting, Pretschner, and Legeard, A Taxonomy of Model-Based Testing Approaches](https://doi.org/10.1002/stvr.456) — models, selection criteria, and abstraction limits.
- [McKeeman, Differential Testing for Software](https://www.cs.tufts.edu/comp/150FP/archive/bill-mckeeman/DifferentailTesting.pdf) — structured cross-implementation comparison and ambiguity.
- [Musuvathi et al., CHESS](https://www.microsoft.com/en-us/research/publication/chess-a-systematic-testing-tool-for-concurrent-software/) — deterministic systematic schedule exploration and replay.
- [Gunawi et al., FATE and DESTINI](https://www.usenix.org/conference/nsdi11/fate-and-destini-framework-cloud-recovery-testing) — systematic multi-failure recovery testing.
- [Zeller and Hildebrandt, Simplifying and Isolating Failure-Inducing Input](https://doi.org/10.1109/32.988498) — automated failure minimization.

## See also

- `SKILL.md` — campaign workflow and safety boundaries
- `references/suite-evidence.md` — coverage, mutation, flakes, redundancy, and pruning
- `templates/risk-ledger.md` — technique, oracle, budget, and disposition record

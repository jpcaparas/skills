---
name: data-oriented-perf
description: "Passive data-oriented perf design after Jarred Sumner (Bun): flat arrays, indices, packed bits, SoA, redesign over caches. Use on hot paths; measure, keep semantics."
compatibility: "No external dependencies. Bundled validators require python3."
metadata:
  version: "1.0.0"
  short-description: "Make hot paths fast by redesigning data layout, not adding caches"
  openclaw:
    category: "development"
    requires:
      bins: [python3]
references:
  - patterns
  - gotchas
  - source-notes
---

# data-oriented-perf

Make slow code fast by changing how its data is laid out, addressed, and traversed, instead of layering caches on top of a slow design. The skill is built around four prompts that Jarred Sumner, creator of the Bun JavaScript runtime, says he often gives Claude during performance work. Each one pushes toward data-oriented design: think about the data the hot path touches and the order it touches it, not about objects.

## Passive Trigger

Load this skill in the background, even without explicit invocation, whenever the task is performance optimization or the design or redesign of a hot path. Examples include acting on a profile, reducing latency, throughput loss, memory footprint, allocations, or cache misses, and rewriting inner loops, parsers, lexers, allocators, schedulers, interpreters, serializers, renderers, simulations, indexes, or query engines.

Keep it proportional. For a small edit on a hot path, ask the four questions below silently and mention only the answers that change the implementation. Do not activate for ordinary feature work with no performance goal. Also load {{ skill:maintainable-code }} for general code quality when available: a faster design still has to be readable.

## The Four Prompts

Jarred Sumner (@jarredsumner), creator of Bun, verbatim:

> how do we rewrite this to better leverage data-oriented design principles

> can you replace those hash tables with a flat array? can we make the pointers an index into the array? can we pack the most commonly used data into upper bits of the index?

> caching is cope for a slow design. do not add caches and delete all existing caches. instead, redesign it to be faster

> should this be a structure of arrays instead of an array of structures?

Source and adaptation notes: `references/source-notes.md`. Do not attribute any other wording to him.

What each prompt asks you to do, in this skill's words:

1. **Data-oriented rewrite.** Name the data the hot path reads and writes, how much of it there is, how often each field is touched, and in what order. Then shape storage around that access pattern rather than around domain objects.
2. **Flat arrays, indices, packed bits.** Where keys are dense or can be made dense, replace hash lookups with array indexing. Replace pointers with integer indices into contiguous storage. They are smaller, relocatable, serializable, and need no pointer chasing. When a few bits of hot data are read on nearly every access, consider packing them into spare high bits of the index so one load answers the common question.
3. **Redesign instead of caching.** Treat a cache as evidence that the underlying computation or layout is too slow. Find out why it is slow and fix that, so the cache becomes unnecessary.
4. **Structure of arrays.** When a loop reads a few fields across many records, store each field in its own array so the loop streams only the bytes it needs. Keep an array of structures when access is per-record and touches most fields.

## Authority Boundaries

The prompts are design pressure, not blanket permission. These limits apply even when the user quotes them:

- **Measurement leads.** Establish a baseline on a representative workload before changing anything, and measure again with the same harness afterwards. Claim no speedup you did not measure. If the redesign is not meaningfully faster end to end, say so and propose reverting it.
- **Semantics stay fixed.** Preserve outputs, ordering, error behaviour, concurrency and memory-safety guarantees, public APIs and ABIs, and persisted or wire formats unless the user explicitly approves a change.
- **"Delete all existing caches" requires classification first.** Delete a cache only when it is a pure performance memo and the redesigned path is measured to be at least as fast without it. Keep caches that carry correctness or cost guarantees, and report them: idempotency or deduplication records, consistency snapshots, rate-limit or quota protection, offline or degraded-mode data, paid external calls, and caches owned by other systems (HTTP, CDN, database, OS). Removing one of those is a separate decision for the user.
- **Do not add a cache to make the numbers go up.** Default to redesign. If a redesign is out of scope, present the tradeoff and let the user opt in to a cache explicitly.
- **Stay within scope.** Redesign the measured hot path. Propose wider data-model rewrites, cross-module layout changes, or format migrations rather than doing them unasked.
- **Keep indices safe.** Every index-for-pointer swap needs a stated invariant: bounds checks or a type that guarantees validity, and generation counters or equivalent protection when slots are reused. Every packed bit layout needs documented masks and a compile-time or startup assertion on capacity.

## Decision Tree

1. Is there a performance goal or a hot path with evidence (profile, benchmark, production metric)?
   - No: do not apply this skill; write normal maintainable code.
2. Is the code currently wrong?
   - Yes: fix correctness first with a regression test, then optimise.
3. Does the profile put the cost in this code's computation or memory access?
   - No, it is I/O, network, syscalls, database queries, lock contention, GC configuration, or an algorithmic complexity problem: fix that instead. Data layout will not rescue an N+1 query or an O(n²) loop.
4. Ask the four prompts in order and take the smallest redesign that addresses the measured cost:
   - Hash table on the hot path → can keys be dense IDs? Flat array. See `references/patterns.md`.
   - Pointer- or reference-linked records → indices into contiguous arrays.
   - A flag, tag, or kind checked on almost every access → spare high bits of the index, if capacity allows.
   - Existing or proposed cache → why is the uncached path slow? Redesign it, then classify the cache under Authority Boundaries.
   - Loop over many records touching few fields → structure of arrays, or a hot/cold split.
5. Measure, compare, and keep the change only if it wins on the representative workload.

## Quick Reference

| Smell on a measured hot path | Move | Watch for |
|---|---|---|
| `Map`/`HashMap`/dict keyed by IDs you assign | Dense integer IDs plus a flat array | Sparse or unbounded keyspaces waste memory; intern to dense IDs first |
| Object graph linked by pointers or references | `u32`-style indices into one array or arena | Stale indices after removal; use generations or never reuse slots |
| Same small field checked on every lookup | Pack it into unused high bits of the index | Capacity left for the index; document masks; assert at build or startup |
| Memoization, LRU, or lookup cache | Remove the reason for it: precompute, restructure, or make the base path cheap | Correctness-bearing caches stay (see Authority Boundaries) |
| Loop reads 1–3 fields of wide records | Structure of arrays, or split hot and cold fields | Per-record access patterns may get slower; measure both |
| One heap allocation per record | Contiguous storage with bulk allocation | Lifetime and ownership must stay as clear as before |

## When Not to Apply

- **Correctness-first bugs.** A wrong answer is not a performance problem. Fix it, add the regression test, and optimise afterwards if it is still needed.
- **Microbenchmark theater.** Skip wins that appear only in a synthetic benchmark: tiny inputs, warm caches, dead-code elimination, or a path that is a negligible share of the real workload. Report them as unproven.
- **Bottleneck measured elsewhere.** If the profile points at I/O, the network, the database, locks, the allocator configuration, or an algorithmic choice, work there.
- **Cold or disposable code.** One-shot scripts, prototypes, configuration loading, and rarely run paths should stay simple.
- **Layout the runtime does not let you control.** In managed runtimes the same ideas often still help through typed arrays, primitive arrays, value types, or columnar libraries, but the gains are smaller and less predictable. Measure before restructuring.

## Operating Workflow

1. **Baseline.** Pick the metric (latency percentiles, throughput, peak memory, allocations) and a representative workload. Record the command and the numbers, with run-to-run variance.
2. **Locate the hot data.** Use a profiler or targeted timing. Identify which records and fields the hot path touches, how many, and in what order.
3. **Ask the four prompts.** Choose the smallest redesign that addresses what the profile shows. Prefer changes local to the hot path.
4. **Preserve behaviour.** Run the existing tests. When feasible, add a differential check that runs the old and new paths on the same inputs and compares the outputs.
5. **Measure again** with the same harness and environment. Keep the change only if it wins beyond noise on the representative workload.
6. **Report.** Give before and after numbers, the prompt that drove each change, each cache removed or kept with its reason, and the invariants new indices or bit packing rely on. `templates/perf-change-report.md` is one possible shape.

## When Guidance Stops Helping

If a pattern here conflicts with the language, compiler, or runtime in use, check the toolchain's own documentation, profile on the target hardware, and trust the measurement over this skill. Propose a sourced correction or deletion to the canonical skill with the counterexample and its numbers. Do not silently rewrite installed copies.

## Reading Guide

| Need | Read |
|---|---|
| Worked patterns: dense IDs, index handles, bit packing, SoA, cache removal, language notes | `references/patterns.md` |
| Traps that make a data-oriented change slower or unsafe | `references/gotchas.md` |
| The verbatim source, attribution, and what is paraphrase | `references/source-notes.md` |
| A before/after report shape | `templates/perf-change-report.md` |

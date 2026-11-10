---
name: data-oriented-perf
description: "Passive data-oriented performance design for hot paths: flat arrays, integer indices, packed bits, structure of arrays, redesign over caches. Use when optimizing against a profile; not for work with no performance goal."
---

# data-oriented-perf

Make slow code fast by changing how its data is laid out, addressed and traversed, not by layering caches on a slow design. For a small edit on a hot path, ask the four questions below silently and mention only the answers that change the implementation. Pair with `maintainable-code` when available: a faster design must stay readable.

## The four prompts

Jarred Sumner (@jarredsumner, creator of Bun) posted these as things he often says to Claude during perf work (https://x.com/jarredsumner/status/2117037940031496252, 2026-11-01). Keep them verbatim and attribute no other wording to him:

> how do we rewrite this to better leverage data-oriented design principles

> can you replace those hash tables with a flat array? can we make the pointers an index into the array? can we pack the most commonly used data into upper bits of the index?

> caching is cope for a slow design. do not add caches and delete all existing caches. instead, redesign it to be faster

> should this be a structure of arrays instead of an array of structures?

Read them as design pressure on the data the hot path touches and the order it touches it:

1. Name what the path reads and writes, how much, how often per field, in what order; shape storage around that.
2. Dense or densifiable keys: array indexing instead of hash lookups (intern external keys to dense IDs once at the boundary). Pointers become integer indices into contiguous storage. If a few bits are read on nearly every access, consider packing them into spare high bits of the index.
3. A cache is evidence the underlying path is slow. Find out why and fix that so the cache is unnecessary.
4. Loops that read few fields across many records: structure of arrays or a hot/cold split. Keep array of structures when access is per-record and touches most fields.

## Limits that hold even when the user quotes the prompts

- Profile first and measure with the same harness before and after, on a representative workload (realistic sizes, results consumed so the optimizer cannot delete the loop, repeated runs for variance). Claim no speedup you did not measure; if the redesign does not win end to end, say so and propose reverting.
- If the profile puts the cost in I/O, network, database queries, locks, GC configuration or an algorithmic problem (N+1, O(n²)), fix that instead; layout will not rescue it. Fix correctness bugs first with a regression test.
- Keep outputs, ordering, error behaviour, concurrency and memory-safety guarantees, public APIs and ABIs, and persisted or wire formats unless the user approves a change. Index-based layouts tempt direct serialization; that changes formats and needs a migration plan.
- "Delete all existing caches" needs classification first. Delete a cache only if it is a pure performance memo and the redesigned path measures at least as fast without it. Keep and report caches that carry correctness or cost: idempotency or dedup records, consistency snapshots, rate-limit or quota protection, offline data, paid or rate-limited external calls, and caches owned elsewhere (HTTP, CDN, database, OS). Removing those is the user's decision. Do not add a cache to make numbers go up; if a redesign is out of scope, present the tradeoff and let the user opt in.
- Redesign the measured hot path only. Propose wider data-model rewrites or cross-module layout changes instead of doing them.

## Gotchas

- Indices drop the language's lifetime checks. If slots are reused, pair indices with generation counters; append-only structures need none. Silent wrong-record reads are worse than crashes.
- Packed layouts need named mask/shift helpers and a construction-time or compile-time capacity assertion (28 bits works until the 29th is needed). In JavaScript, bitwise operators are signed 32-bit; use `>>> 0`.
- Parallel arrays drift if appended or removed separately; one owning type does every mutation (or use Zig `MultiArrayList`, Arrow, an ECS).
- Flat arrays indexed by raw external IDs allocate for the largest ID. Intern first.
- Swap-remove changes other elements' indices; use tombstones or a free list when indices must stay stable.
- SoA slows code that handles whole records at a time. Measure both layouts.
- Deleting a memo without fixing the computation behind it is a regression.
- Managed runtimes: typed arrays, primitive arrays or value-type structs give contiguity, but gains are smaller and less predictable; measure before restructuring. In Go, pointer-free hot structs and slice indices reduce GC scanning.

## Done

Report before/after numbers with variance, which of the four prompts drove each change, each cache removed or kept and why, and the invariants new indices or bit layouts depend on.

# Gotchas

Ways a data-oriented change ends up slower, wrong, or unmaintainable.

1. **Optimising without a profile.** A layout change in code that takes 2% of the runtime can save at most 2%. Find the hot data first.
2. **Benchmarking the wrong thing.** Tiny inputs fit in L1 whatever the layout, warm caches hide misses, and an optimiser may delete a loop whose result is unused. Use representative sizes, consume the results, and repeat runs to see variance.
3. **Treating "delete all caches" as literal.** Removing an idempotency cache, a rate-limit guard, or a cache in front of a paid API changes behaviour or cost, not just speed. Classify every cache first, as `SKILL.md` describes.
4. **Silently trading a cache for a slower path.** Deleting a performance memo without redesigning the computation behind it is a regression. The cache goes only when the redesign makes it unnecessary, and the measurement shows that.
5. **Stale indices.** Indices remove the language's lifetime checks. Reused slots without generation checks produce silent wrong-record reads, which are worse than crashes.
6. **Bit packing without capacity checks.** A 28-bit index works until a record needs a 29th bit. Enforce capacity at construction, not in a comment.
7. **SoA for per-record code.** If most code handles one whole record at a time, splitting it across arrays touches more cache lines. The access pattern decides, not the trend.
8. **Columns falling out of sync.** Parallel arrays that are appended or removed separately drift. One owning type must do every mutation.
9. **Flat arrays over sparse keys.** Indexing by raw external IDs allocates for the largest ID, not the number of records. Intern to dense IDs first.
10. **Unreadable results.** Bit tricks and parallel arrays need names. Wrap masks, shifts, and column access behind small, named functions so the next maintainer can follow the design. Pair with maintainable-code guidance.
11. **Changing formats as a side effect.** Index-based layouts are attractive to serialize directly. Doing that changes persisted or wire formats, which needs explicit approval and a migration plan.

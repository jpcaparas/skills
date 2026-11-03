# Source Notes

## Primary source

- **Author:** Jarred Sumner (@jarredsumner), creator of the Bun JavaScript runtime
- **Post:** https://x.com/jarredsumner/status/2117037940031496252
- **Published:** 2026-11-01T23:35:52Z

Full text, verbatim:

```text
some things I often say to claude when doing perf optimization work:

> how do we rewrite this to better leverage data-oriented design principles

> can you replace those hash tables with a flat array? can we make the pointers an index into the array? can we pack the most commonly used data into upper bits of the index?

> caching is cope for a slow design. do not add caches and delete all existing caches. instead, redesign it to be faster

> should this be a structure of arrays instead of an array of structures?
```

The four quoted prompts are the only words this skill attributes to him. Keep them verbatim, including lowercase and punctuation. Do not add, merge, or reword attributed quotes. Write new guidance in the skill's own voice instead.

## Adaptation choices

- **Quotes and paraphrase stay separate.** `SKILL.md` quotes the four prompts exactly, then explains each in the skill's own words. All operational guidance, patterns, and gotchas are this skill's interpretation, not his.
- **Passive, not literal.** The post describes prompts a person gives an agent during performance work. The skill turns them into questions the agent asks itself whenever it is doing that kind of work.
- **Authority boundaries added.** The post is terse and aimed at an expert driving the work. "do not add caches and delete all existing caches" is read as design pressure toward faster base paths. It is not a license to remove caches that carry correctness or cost guarantees, or to change program semantics. Measurement decides what ships.
- **When-not-to-apply added.** Correctness bugs, unmeasured microbenchmark gains, and bottlenecks elsewhere (I/O, databases, locks, algorithms) are excluded so the prompts are not applied where layout cannot help.

## Background on data-oriented design

These are widely cited introductions to the approach the prompts draw on. They are listed as further reading only; nothing from them is quoted here.

- Mike Acton, "Data-Oriented Design and C++", CppCon 2014.
- Andrew Kelley, "Practical Data Oriented Design (DoD)", Handmade Seattle 2021, about applying these techniques in the Zig compiler.
- Richard Fabian, *Data-Oriented Design* (book).

## Provenance

This skill was requested by the repository owner after reading the post above. If the post becomes unavailable, the verbatim text in this file is the record. Do not reconstruct or extend it from memory.

# data-oriented-perf

Installable passive skill that applies Jarred Sumner's (Bun) performance-optimization prompts during hot-path work. It covers data-oriented rewrites, flat arrays and indices instead of hash tables and pointers, hot data packed into index bits, structure of arrays, and redesigning slow paths instead of adding caches. Measurement and preserved semantics stay in charge.

## Install

```bash
npx skills add jpcaparas/skills --skill data-oriented-perf
```

## Includes

- `SKILL.md` as the canonical workflow: passive trigger, the four verbatim prompts, authority boundaries, decision tree, quick reference, and when not to apply
- `references/patterns.md` for dense IDs, index handles, bit packing, SoA, cache redesign, and language notes
- `references/gotchas.md` for traps that make a data-oriented change slower or unsafe
- `references/source-notes.md` for the verbatim source post and adaptation choices
- `templates/perf-change-report.md` as an optional before/after report shape

Use this when an agent is optimising performance or redesigning a hot path, even if nobody asks for it by name.

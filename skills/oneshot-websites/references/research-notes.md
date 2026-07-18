# Research Notes

Read this file when expanding the prompt catalogue or revisiting benchmark provenance. These notes explain the evidence behind the package without constraining how a lead implements an experiment.

## Public One-Shot Showcase Pattern

The supplied July 2026 X examples span far more than landing pages:

- [Max Weinbach](https://x.com/mweinbach/status/2077827886149439547) describes a browser recreation of a desktop operating system with a coherent material system and native-feeling apps.
- [JUMPERZ](https://x.com/jumperz/status/2077841331037094042) highlights a single-prompt motion experience through scroll pacing, oversized type reveals, number transitions, layout shifts, and colour inversions.
- [shirish](https://x.com/shiri_shh/status/2078213686481895812) compares an explorable stylised 3D city scene across two builders.
- [am.will](https://x.com/LLMJunky/status/2078267563511787532) shows a playable car-and-ball arena experience with a vehicle, ball, pickups, goals, and game-state UI.
- [mr.bruce](https://x.com/sharkydev001/status/2078025345417294325) compares playable and inspectable 3D submarine experiences made from the same stated prompt.
- [aditya](https://x.com/adxtyahq/status/2077836136630943999) shows a first-person action scene with world rendering, weapons, minimap, and status UI.

The posts expose artifact descriptions and demonstrations, but not their complete literal prompts. Treat the concepts as evidence of breadth, not as prompt quotations or reproducible benchmark inputs.

Across the examples, the strongest artifact has a recognisable subject and one legible hero capability: an operating system, choreographed motion sequence, explorable world, simulation, or game loop. This informed the catalogue’s emphasis on concrete experiences rather than technology recipes.

## Benchmark Lessons

- [WebDev Arena](https://arena.ai/blog/webdev-arena/) reports substantial prompt volume in website design, game development, and clone development. Its fixed application stack is useful for its own comparison but should not become a restriction in this general skill.
- [WebGen-Bench](https://arxiv.org/abs/2505.03733) evaluates multi-file websites through operation-and-expected-result test cases. This supports preserving functional evidence independently from visual polish.
- [Design2Code](https://github.com/NoviScl/Design2Code) reports direct, text-augmented, and self-revision prompting separately. The distinction supports honest run classification rather than presenting different workflows as equivalent.
- [ArtifactsBench](https://github.com/Tencent-Hunyuan/ArtifactsBenchmark) covers games, web applications, simulations, data work, multimedia editing, and quick tools, and evaluates rendered behavior through temporal screenshots and task-specific checklists. Its breadth helped shape the catalogue taxonomy.
- [CSS Design Awards](https://www.cssdesignawards.com/blog/2025-website-of-the-year-winners/430/), [Apple Design Awards](https://developer.apple.com/design/awards/2025/), and [Core77 Interaction](https://designawards.core77.com/interaction) provide additional evidence that interactive storytelling, creative tools, data experiences, sound, and playful systems belong in a web-artifact repertoire.

## Static Handoff Research

- [Cloudflare Drop](https://www.cloudflare.com/drop/) accepts a static folder or ZIP containing HTML, CSS, and JavaScript and requires a root `index.html`. Cloudflare’s current [temporary-account contract](https://developers.cloudflare.com/workers/platform/claim-deployments/#supported-resources) supports up to 1,000 static files at 5 MiB per asset; the live Drop preflight also caps a folder at 100 MiB total.
- [Vercel Drop](https://vercel.com/docs/drop) accepts a file, folder, or ZIP. It serves static sites and can also detect framework projects, so the portable no-build artifact contains the exported browser files rather than source manifests, filtered framework state, or server and provider configuration.

These are July 2026 provider observations, not timeless benchmark rules. Keep the final compatibility constants easy to revise and recheck first-party sources when maintaining the skill.

## Package Consequences

The research led to five durable choices:

1. Preserve the actual prompt and run identity instead of reconstructing them afterward.
2. Separate fresh lead contexts so sibling results cannot bias one another.
3. Record the workflow honestly without imposing a time, model-call, framework, dependency, or source-project-shape limit.
4. Standardize only the handoff: exact `PROMPT.md` plus a built root `index.html` in a drop-ready static folder.
5. Keep the prompt catalogue broad and appendable, with deterministic checks for identity and accidental implementation constraints.

## See Also

- `references/catalogue-authoring.md` — catalogue schema and extension rules
- `references/execution-protocol.md` — autonomous worker and provenance contract

# nanobanana

Production skill for generating and editing images with Google's Nano Banana, pinned to Gemini Nano Banana 2.1 (`gemini-nano-banana-2.1`).

## What It Covers

- A natural-language workflow: "use Nano Banana to make X" becomes a scene prompt, the right ratio, size and thinking level, a checked image, and a cost estimate
- Generation, edits (including ink and mask edits), up to 14 references, multi-turn refinement, web and image search grounding, and half-price batch jobs
- Live-measured behaviour from 2026-10-18: sizes from 512 to 4K, JPEG-only output, thinking-level cost and latency, where search works, and docs that disagree with the API
- Known failure modes (handedness, clock hands, added text) and deterministic fixes (flip, composite, chroma key)
- A standard-library Python helper with local validation, cost estimates, batch support, and a free API drift check

## Key Files

- `SKILL.md` - authoritative instructions
- `references/prompting.md` - prompt rules and templates
- `references/workflows.md` - helper recipes and post-processing
- `references/api.md` - REST contracts, sizes, pricing, errors
- `references/gotchas.md` - quirks and recovery
- `references/evidence.md` - dated live-probe ledger
- `scripts/nanobanana.py` - generation, batch, and contract helper
- `scripts/test_helper.py` - offline helper regressions

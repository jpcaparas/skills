# Evidence and Verification Limits

A **2026-10-18 UTC snapshot** from one paid Gemini API key. It is evidence from that day, not a promise about future releases.

Sources: Google's [image generation guide](https://ai.google.dev/gemini-api/docs/image-generation) (updated 2026-10-09), its [generateContent variant](https://ai.google.dev/gemini-api/docs/generate-content/image-generation), the [Nano Banana 2.1 model page](https://ai.google.dev/gemini-api/docs/models/gemini-nano-banana-2.1) (updated 2026-10-06), [pricing](https://ai.google.dev/gemini-api/docs/pricing), the [Interactions API overview](https://ai.google.dev/gemini-api/docs/interactions-overview), [batch](https://ai.google.dev/gemini-api/docs/batch-api), [Files](https://ai.google.dev/gemini-api/docs/files), and live `GET /v1beta/models/gemini-nano-banana-2.1`.

## Executed probes

About 150 generations (roughly $6.50 at list prices, estimated from returned usage), plus about 30 free validation probes. Images were judged by a vision model against per-task checklists and spot-checked by eye. Two samples per cell is small; treat single-digit differences as indicative.

| Probe | Result |
| --- | --- |
| Parameter matrix (sizes, 16 ratios, 6 thinking values, 3 MIME types, store, text-only format) | See `references/api.md`; 512 works on Interactions only, JPEG only, lowercase `minimal`/`medium`/`high` only, `9:21` and `7:5` rejected |
| Sampling (`seed` ×2, `temperature: 0` ×2, `top_k`, `top_p`, `max_output_tokens`) | All accepted; same seed gave different images; `max_output_tokens: 100` → HTTP 500 |
| Image count | "Three separate images" → one image; `candidateCount: 2` rejected |
| Multi-turn (3 turns stored; `store: false` then chain) | Identity and additions kept across turns; chain after `store: false` silently lost context |
| Edits (replace object, ink circle, mask image, PNG/WebP input, PDF, 3 s video) | All succeeded; regions outside the edit at about 38 dB PSNR; PDF text reproduced exactly with macrons |
| References (14, 15, 20 numbered swatches; product label) | All accepted and all swatches placed; jar label exact in 2 of 2 scenes |
| Search on Interactions (web ×5, image ×4, `visual_search` ×2, combinations) | Web search skipped 2 of 4; image search always `requires_action`; combinations stalled |
| Search on generateContent (web ×3, image ×2, web+image ×1) | Searched every time; takahē and tūī cards accurate with macrons |
| Thinking benchmark: 7 tasks × 3 levels × 2 samples at 1K | Charts, counting, planets solved at all levels; left hand 0/6; clock 7:20 2/6; sign copy exact 2/6 overall; medium/high added extra diagram text |
| Knowledge: capitals map and film timeline × 3 levels × 2 | Map 6/6; timeline wrong years in 1 of 2 at minimal, 4/4 at medium and high |
| Latency and cost (42 benchmark calls at 1K) | Median 9.0 / 14.8 / 23.8 s; mean $0.037 / $0.043 / $0.049 for minimal / medium / high |
| Techniques (2 samples each) | Strict copy instruction: sign exact 2/2. Viewer-relative handedness: 0/2. Drawn clock reference: 0/2 |
| Small print at 1K, 2K, 4K | Legible at all sizes; recased to capitals at 1K and 2K; one 2K sample added gibberish logos; 4K kept casing |
| Output sizes (extreme ratios at 1K and 2K; 4K at 1:1, 2:3, 16:9) | Extreme ratios differ from the docs table |
| Input tokens (256 px to 4096 px images) | 1,120 tokens per image regardless of size |
| Concurrency (6 and 12 parallel 512 requests) | All HTTP 200, 6–13 s, no rate-limit headers |
| Background and streaming | Both work; streaming delivers the image at the end |
| Batch (2 inline requests) | `BATCH_STATE_SUCCEEDED` after about 2.6 minutes |
| Files API | 4K image uploaded and referenced by `uri` |
| Safety | Banknote scan blocked with HTTP 400; historical-figure watercolour allowed |
| Transparency | "Transparent background" draws a checkerboard; magenta key on basil clean; green key on glossy apple left a faint rim |
| Helper live checks | `generate` (512, continue, mask edit, image search), `--dry-run`, `contract` (no drift) |

## Rerun these probes

- `python3 scripts/nanobanana.py contract` — free; confirms ratios, sizes, thinking levels and output MIME types, and prints model metadata. Exit 4 means drift.
- One cheap live call: `python3 scripts/nanobanana.py generate --size 512 --thinking minimal --ratio 1:4 --no-store --out probe.jpg "A lighthouse"`, then compare the dimensions with `references/api.md`.
- Search routing: run the same `--image-search` prompt through the helper and through a raw Interactions request; if Interactions now completes with `google_search_call` steps, propose moving search back to it.

## Not tested

- Vertex AI / Google Cloud (its docs say sampling parameters error there).
- 4K output at extreme ratios, and 2K or 4K at every ratio.
- Long multi-turn chains (more than three turns) and when identity drift starts.
- Four-character consistency and ten-object fidelity at the documented limits.
- Non-Latin scripts beyond French and German accents and Māori macrons (Arabic right-to-left order in particular).
- Free-tier behaviour (this model has none) and actual billed amounts; costs here are estimates from usage at list prices.
- Whether Google bills the ~300 unexplained non-image output tokens.
- File-input batches (JSONL through the Files API) and batch turnaround under load.
- The undocumented `visual_search` search type beyond two calls.

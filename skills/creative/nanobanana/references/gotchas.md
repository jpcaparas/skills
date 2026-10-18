# Gotchas

Surprises seen live on 2026-10-18, with the fix for each.

## The output looks right but is wrong

Failures are silent and plausible: a right hand where the brief said left, a clock at 7:00 instead of 7:20, an extra "Sun" label, a title recased to capitals, an airplane icon on a sign. Inspect every image against the brief before reporting it, word by word for any copy.

## More thinking does not fix everything

`high` costs about a third more than `minimal` and takes about 2.5 times as long (median 24 s against 9 s at 1K, with a 56 s outlier), yet it did not fix handedness, clock hands, or extra labels. It also added more unrequested text on diagrams. Its value is factual recall: `minimal` got film release years wrong, while `medium` and `high` did not. Use `medium` by default and raise it for dense facts.

## Requests that look valid but are not

- `image_size` needs an uppercase K (`1K`); `1k` and `0.5K` are rejected.
- `thinking_level` on the Interactions API must be lowercase; `low` and `none` are rejected.
- `9:21` and other unlisted ratios are rejected.
- PNG, WebP and GIF output are rejected; output is always JPEG.
- The `512` size works on the Interactions API but not on generateContent or in batch.
- `candidateCount` above 1 is rejected, and prompts asking for several images return one.

## Settings that do nothing useful

- `seed` and `temperature` are accepted, but the same seed gave a different image. Do not promise reproducibility.
- `response_format: {"type": "text"}` and `responseModalities: ["TEXT"]` still return an image.
- `max_output_tokens: 100` caused HTTP 500 instead of a clean error.

## Conversations that quietly lose context

- `store: false` (`--no-store`) cannot be continued. Passing its ID as `previous_interaction_id` still returns HTTP 200, but the model starts from scratch (a "make it red" follow-up to a blue cube produced an unrelated red room).
- Per-turn settings reset: send ratio, size and thinking on every turn. A turn without them came back at 1K.
- Every earlier image is billed again as input on each turn (about 1,150 tokens each).

## Search on the Interactions API

Image search on the Interactions API ended with `status: requires_action` and a `function_call` named `google:image_search` that a client cannot execute; resuming it produced an ungrounded image. Web search there was skipped in 2 of 4 runs, and combining `web_search` with the undocumented `visual_search` also stalled. The helper therefore routes `--search` and `--image-search` to generateContent, which searched every time.

## The docs' size table is wrong for extreme ratios

1:4 at 1K came back as 512×2064 (docs: 512×2048), 1:8 as 352×2928 (docs: 384×3072), and 8:1 at 2K as 5856×704 (docs: 6144×768). Use the width and height in the helper's summary.

## Default aspect ratio

With no input image and no ratio, the output was 16:9 (1376×768), not the documented 1:1. Always pass `--ratio` for new images.

## Transparency

Asking for a transparent background draws a grey checkerboard into the JPEG. Use a flat key colour that is absent from the subject and key it locally (`references/workflows.md`). A green leaf on a green key was wrongly removed; glossy subjects keep a faint rim.

## Reference limits

The API accepted 20 references without error and placed all of them, but Google documents 14 (4 characters, 10 objects). The helper enforces 14. Each image costs 1,120 input tokens however small it is, so downscaling references saves bandwidth, not money.

## Usage numbers

On generateContent, `candidatesTokenCount` was sometimes smaller than the image tokens it should include (314 against 1,120). Compute cost from the per-modality details. A PDF reference was counted as 0 input tokens even though its text was used.

## Safety blocks

A request for a full-detail banknote scan returned HTTP 400 "Image generation blocked due to safety violations". It is deterministic for that prompt, so rephrase or decline rather than retry. A watercolour of a historical public figure was generated normally.

## Response size

Thought signatures make full responses several megabytes even for a 512 image. Do not log raw responses or paste them into context; the helper saves the image and prints a short summary.

## Model churn

Nano Banana 2 (`gemini-3.1-flash-image`) shuts down on 2026-10-29, Imagen is already gone, and Google's pages disagree on 2.1's token limits (model page 131,072 input; `ListModels` 65,536). Never switch to another model to work around a failure. Run `contract`, read the current docs, and report.

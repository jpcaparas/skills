# API Reference

Raw contracts for `gemini-nano-banana-2.1`, recorded live on 2026-10-18. Official sources: [image generation](https://ai.google.dev/gemini-api/docs/image-generation), [legacy generateContent variant](https://ai.google.dev/gemini-api/docs/generate-content/image-generation), [model page](https://ai.google.dev/gemini-api/docs/models/gemini-nano-banana-2.1), [Interactions API](https://ai.google.dev/gemini-api/docs/interactions), [pricing](https://ai.google.dev/gemini-api/docs/pricing), [batch](https://ai.google.dev/gemini-api/docs/batch-api), and [Files API](https://ai.google.dev/gemini-api/docs/files).

All requests use `https://generativelanguage.googleapis.com` with the header `x-goog-api-key: $GEMINI_API_KEY`.

## Which API to use

| Need | API | Why |
| --- | --- | --- |
| Generate, edit, references, multi-turn | Interactions `POST /v1beta/interactions` | Google's recommended API; server-side conversation state; accepts `512` |
| Web or image search grounding | `POST /v1beta/models/gemini-nano-banana-2.1:generateContent` | Searched in 3 of 3 runs and returns `groundingMetadata`. On Interactions, web search was skipped in 2 of 4 runs, and image search always stopped with `status: requires_action` and a client-side `function_call` (`google:image_search`) |
| Many images, half price | `POST /v1beta/models/gemini-nano-banana-2.1:batchGenerateContent` | Batch runs on generateContent requests |

## Interactions API

### Request

```json
{
  "model": "gemini-nano-banana-2.1",
  "input": [
    {"type": "image", "mime_type": "image/png", "data": "<base64>"},
    {"type": "text", "text": "Replace the mint with a lemon slice. Keep everything else the same."}
  ],
  "response_format": {"type": "image", "aspect_ratio": "4:3", "image_size": "1K"},
  "generation_config": {"thinking_level": "medium"},
  "store": true,
  "previous_interaction_id": "v1_...",
  "system_instruction": "House style: ..."
}
```

| Field | Values and behaviour |
| --- | --- |
| `input` | A string, or blocks of `text`, `image`, `video`, `document` (PDF) with `mime_type` plus `data` (base64) or `uri` (Files API) |
| `response_format` | `{"type": "image", ...}` returns only the image. A list such as `[{"type": "text"}, {"type": "image"}]` adds a caption. Omitted: text plus image at 16:9 1K. `{"type": "text"}` alone still produced an image |
| `aspect_ratio` | `1:1 2:3 3:2 3:4 4:3 4:5 5:4 9:16 16:9 21:9 1:4 4:1 1:8 8:1`; others, including `9:21`, are rejected |
| `image_size` | `512`, `1K`, `2K`, `4K`; `0.5K` and lowercase `1k` are rejected |
| `mime_type` (in `response_format`) | only `image/jpeg` |
| `thinking_level` | `minimal`, `medium` (default), `high`, lowercase only. The schema lists `low`, but the model rejects it |
| `temperature`, `seed`, `top_k`, `top_p` | Accepted but not reproducible: identical seeds gave different images. `max_output_tokens: 100` caused HTTP 500 |
| `store` | Default `true`; retained 55 days on the paid tier, 1 day on free. With `false`, a later `previous_interaction_id` pointing at it is **silently ignored** (HTTP 200, no context) |
| `previous_interaction_id` | Continues a stored conversation. `response_format`, `generation_config`, `tools` and `system_instruction` apply per turn and must be resent; without `response_format` the size reverted to 1K |
| `background` | `true` returns `status: in_progress` at once; poll `GET /v1beta/interactions/{id}` |
| `stream` | `true` with `?alt=sse` streams events (`interaction.created`, `step.start`, ..., `done`); the image arrives whole at the end |
| `tools` | `google_search` (with `search_types` such as `web_search`, `image_search`) works unreliably here (see above); `url_context` is rejected |

### Response

```json
{
  "id": "v1_...", "status": "completed", "object": "interaction", "model": "gemini-nano-banana-2.1",
  "steps": [
    {"type": "thought", "signature": "<large base64>"},
    {"type": "model_output", "content": [{"type": "image", "mime_type": "image/jpeg", "data": "<base64 jpeg>"}]}
  ],
  "usage": {
    "total_input_tokens": 1155, "input_tokens_by_modality": [{"modality": "image", "tokens": 1120}, {"modality": "text", "tokens": 35}],
    "total_output_tokens": 1425, "output_tokens_by_modality": [{"modality": "image", "tokens": 1120}],
    "total_thought_tokens": 599, "total_cached_tokens": 0, "total_tool_use_tokens": 0, "total_tokens": 3179
  }
}
```

- Take images from `model_output` steps only. Thought steps carry signatures of up to about 1 MB of base64 each, so a full response can be several megabytes.
- `total_output_tokens` includes about 250–350 non-image tokens even when no caption is returned; thought tokens are counted separately.
- Search on this API adds `google_search_call` (`arguments.queries`) and `google_search_result` (`search_suggestions` HTML) steps.
- `GET /v1beta/interactions/{id}` returns the stored interaction with its `user_input` steps; `DELETE` removes it.

## generateContent (search grounding and batch)

```json
{
  "contents": [{"role": "user", "parts": [{"text": "Use image search for ..., then create ..."}]}],
  "tools": [{"googleSearch": {"searchTypes": {"webSearch": {}, "imageSearch": {}}}}],
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"],
    "imageConfig": {"aspectRatio": "3:4", "imageSize": "1K"},
    "thinkingConfig": {"thinkingLevel": "medium", "includeThoughts": false}
  }
}
```

- `imageSize` here accepts `1K`, `2K`, `4K`; `512` returns "Image size 512 is not supported for this model" even though the error text lists `512`.
- `thinkingLevel` is case-insensitive here (`MINIMAL` and `minimal` both work).
- There is no output MIME option (`outputMimeType` and `imageOutputOptions` are rejected); output is JPEG.
- `candidateCount: 2` returns "Multiple candidates is not enabled for this model".
- `responseModalities: ["TEXT"]` still returned an image.
- Images arrive in `candidates[0].content.parts[].inlineData`; skip parts with `thought: true`. The image part carries a `thoughtSignature`; send the whole model turn back unchanged when continuing a stateless conversation on this API (the helper avoids this by continuing on the Interactions API instead).
- `groundingMetadata` holds `webSearchQueries`, `imageSearchQueries`, `groundingChunks` (`web.uri`/`image.sourceUri` redirect links with titles), `groundingSupports`, and `searchEntryPoint.renderedContent` (the HTML widget Google's terms require you to display).
- `usageMetadata.candidatesTokensDetails` gives image tokens. `candidatesTokenCount` was sometimes lower than the image tokens alone (314 against 1,120), so cost from the per-modality details, not the total.

## Batch

```json
POST /v1beta/models/gemini-nano-banana-2.1:batchGenerateContent
{"batch": {"display_name": "shots", "input_config": {"requests": {"requests": [
  {"metadata": {"key": "boat"}, "request": {"contents": [{"parts": [{"text": "A paper boat"}]}],
    "generation_config": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "1:1", "imageSize": "1K"}, "thinkingConfig": {"thinkingLevel": "minimal"}}}}
]}}}}
```

Poll `GET /v1beta/batches/{id}`. States are `BATCH_STATE_PENDING`, `BATCH_STATE_RUNNING`, then `BATCH_STATE_SUCCEEDED` (the docs show `JOB_STATE_*` names). Results are in `metadata.output.inlinedResponses.inlinedResponses[]`, each with `metadata.key` and a generateContent `response` or an `error`. Use a JSONL file uploaded through the Files API for anything over 20 MB.

## Files API

Resumable upload: `POST /upload/v1beta/files` with headers `X-Goog-Upload-Protocol: resumable`, `X-Goog-Upload-Command: start`, `X-Goog-Upload-Header-Content-Length`, `X-Goog-Upload-Header-Content-Type`; then send the bytes to the returned `X-Goog-Upload-URL` with `X-Goog-Upload-Command: upload, finalize`. Reference the result as `{"type": "image", "uri": "<file.uri>", "mime_type": "image/jpeg"}` (Interactions) or `{"fileData": {"fileUri": ..., "mimeType": ...}}` (generateContent). Files last 48 hours, 2 GB each, 20 GB per project. Use it when a request would exceed 100 MB inline (50 MB for PDFs).

## Output sizes (measured)

| Ratio | 512 | 1K | 2K | 4K |
| --- | --- | --- | --- | --- |
| 1:1 | 512×512 | 1024×1024 | 2048×2048 | 4096×4096 |
| 16:9 | — | 1376×768 | — | 5504×3072 |
| 4:3 | 592×448 | 1200×896 | — | — |
| 2:3 | — | 848×1264 | 1696×2528 | 3392×5056 |
| 21:9 | — | 1584×672 | — | — |
| 1:4 / 4:1 | — | 512×2064 / 2064×512 | 1024×4128 | — |
| 1:8 / 8:1 | — | 352×2928 / 2928×352 | 5856×704 (8:1) | — |

The other standard ratios at 1K matched the docs table (2:3 848×1264, 3:4 896×1200, 4:5 928×1152, 5:4 1152×928, 9:16 768×1376). The extreme ratios do **not** match the docs (which list 512×2048, 384×3072 and 6144×768). Read the real size from the helper's summary instead of assuming.

## Tokens and pricing (list, USD)

| Meter | Price | Measured |
| --- | --- | --- |
| Input (text, image, video, PDF) | $1.50 / 1M | each input image 1,120 tokens at any resolution (256 px to 4096 px); 3 s video 210 tokens; a PDF was counted as 0 document tokens |
| Text and thinking output | $7.50 / 1M | thought tokens: 0 at minimal, ~830 median at medium, ~1,300 at high (up to 3,640) |
| Image output | $30 / 1M | 747 (512), 1,120 (1K), 1,680 (2K), 3,780 (4K) tokens at every ratio |
| Batch | half of the above | |
| Google Search grounding | 5,000 queries free per month across Gemini 3+ models, then $14 / 1,000 | one request can run several queries (up to 4 seen) |

Estimated cost = input × 1.5e-6 + image × 30e-6 + (other output + thought) × 7.5e-6. The helper prints this as `estimated_cost_usd`; Google's billing is authoritative. There is no free tier for this model.

## Errors

| Response | Meaning | Action |
| --- | --- | --- |
| 400 "The value 'X' is not supported for '...'. Supported values: ..." | Invalid enum value | Fix the value; the list is the live contract (free to trigger; `contract` uses it) |
| 400 "Thinking level THINKING_LEVEL_LOW is not supported for this model" | `low` | Use `minimal`, `medium` or `high` |
| 400 "Image generation blocked due to safety violations. Please modify your input and retry." | Policy block | Rephrase; do not retry unchanged |
| 400 "Url Context as tool is not enabled for this model" | Unsupported tool | Remove it |
| 404 "Model '...' not found. Did you mean 'gemini-nano-banana-2.1'?" | Wrong ID | Use the pinned ID; never substitute another model |
| 429 / 500 / 503 | Throttle or transient | Retry with backoff (the helper retries twice) |
| 200 with `status: requires_action` | The model emitted a client-side tool call (search on Interactions) | Use generateContent for search |
| 200 with text but no image | The model answered in words | Rephrase as an explicit image request |

No rate-limit headers were returned. Twelve concurrent 512 requests all succeeded (6–13 s each).

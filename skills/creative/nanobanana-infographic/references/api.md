# Nano Banana 2.1 Gemini API Reference For Infographics

## Table of Contents

- [Overview](#overview)
- [Model Policy](#model-policy)
- [Base URL and Headers](#base-url-and-headers)
- [Request Shape](#request-shape)
- [Image And Thinking Settings](#image-and-thinking-settings)
- [Response Handling](#response-handling)
- [Cost](#cost)
- [Common Failures](#common-failures)

## Overview

This skill renders through Gemini `generateContent` with the model `gemini-nano-banana-2.1` (public name Nano Banana 2.1). The facts below were measured live on 2026-10-18.

- Script preset aspect ratio: `16:9` (overridable)
- Script preset size: `1K` (overridable to `2K` or `4K`)
- Script preset thinking level: `medium` (overridable)
- Workflow: one request per intended image; concurrent batches only for an authorized multi-image pack

The `nanobanana` skill, when installed, owns the full model mechanics: the Interactions API, edits, references, multi-turn refinement, search grounding, the Batch API, and its drift check. Use it for anything beyond rendering an infographic prompt.

Official sources for disputed details: [image generation](https://ai.google.dev/gemini-api/docs/image-generation), [model page](https://ai.google.dev/gemini-api/docs/models/gemini-nano-banana-2.1), [generateContent reference](https://ai.google.dev/api/generate-content), and [pricing](https://ai.google.dev/gemini-api/docs/pricing). Ordinary prompt drafting does not need a fresh lookup.

## Model Policy

Use `gemini-nano-banana-2.1` only. The bundled scripts hard-code it and have no `--model` flag.

- Nano Banana 2 (`gemini-3.1-flash-image`; this skill previously called `gemini-3.1-flash-image-preview`) shuts down on 2026-10-29.
- Nano Banana Pro, Nano Banana 2 Lite, `gemini-2.5-flash-image`, and Imagen cost more for worse results or are gone.
- If 2.1 fails, diagnose and report. Do not fall back to another model.
- When Google ships a newer Nano Banana, confirm it from official documentation and `ListModels`, then propose a sourced update to the canonical skill rather than editing an installed copy.

Check what your key can call without printing the key:

```bash
curl -sS "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  | jq -r '.models[]?.name' | rg 'nano-banana'
```

## Base URL and Headers

```text
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-nano-banana-2.1:generateContent
x-goog-api-key: $GEMINI_API_KEY
Content-Type: application/json
```

## Request Shape

A paid live call; use it only within the user's authorized scope:

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-nano-banana-2.1:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "Create a 16:9 executive infographic about cloud cost control on a white background. Exact title, copied character for character: \"Cost discipline\". Exactly three sections labelled \"Measure\", \"Own\", \"Optimise\". No other text. Minimal palette, flat editorial design."
          }
        ]
      }
    ],
    "generationConfig": {
      "responseModalities": ["TEXT", "IMAGE"],
      "imageConfig": {
        "aspectRatio": "16:9",
        "imageSize": "1K"
      },
      "thinkingConfig": {"thinkingLevel": "medium"}
    }
  }'
```

Notes:

- `responseModalities` must include `IMAGE`. Even `["TEXT"]` alone returned an image, so do not rely on it to get a text-only answer.
- Describe one coherent composition, including mixed styles when requested, rather than offering conflicting alternatives in one prompt.

## Image And Thinking Settings

Aspect ratios accepted by `imageConfig.aspectRatio`:

```text
1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9, 1:4, 4:1, 1:8, 8:1
```

`imageConfig.imageSize` accepts `1K`, `2K`, and `4K` on `generateContent`. `512` is rejected here ("Image size 512 is not supported for this model"), even though the error lists it; only the Interactions API accepts `512`. Measured 1K sizes: 16:9 is 1376×768, 4:5 is 928×1152, 9:16 is 768×1376, 1:1 is 1024×1024. Extreme ratios differ from Google's table (1:4 at 1K came back 512×2064), so read the saved file's dimensions instead of assuming.

`thinkingConfig.thinkingLevel` accepts `minimal`, `medium`, and `high`.

| Level | Use for infographics |
| --- | --- |
| `minimal` | Cheap layout drafts with no facts to get right. It got a factual detail wrong in 1 of 2 tests |
| `medium` | Default. Good typography and exact copy when the prompt quotes it |
| `high` | Dense facts, many labels, or data the model must reason about. Costs more thinking tokens |

Medium and high both tend to add labels nobody asked for. When the visible copy must be exact, quote it, say to copy it character for character, and end with "No other text."

Output is always JPEG. There is no MIME option, no transparency (a "transparent background" request draws a checkerboard), and one image per request (`candidateCount` above 1 is rejected).

## Response Handling

Images arrive in the first candidate:

```text
candidates[0].content.parts[]
```

- Skip parts with `thought: true`.
- If a part has `text`, save it as supporting notes.
- If a part has `inlineData`, base64-decode `inlineData.data` and save it. The MIME type is `image/jpeg`.

`scripts/probe_gemini_image_api.py` is a portable reference implementation.

## Cost

List prices, USD: image output $30 per million tokens, text and thinking output $7.50 per million, input $1.50 per million. A 1K image is 1,120 output tokens; 2K is 1,680 and 4K is 3,780. Measured mean cost of one 1K image was about $0.04 at medium thinking (thinking adds roughly 800–1,300 tokens). There is no free tier. Google's billing is authoritative.

## Common Failures

Diagnose before retrying and keep further paid calls within the authorized scope. Never print credentials or switch models to resolve an error.

| Status | Likely cause | Fix |
|---|---|---|
| `400` "not supported ... Supported values: ..." | Invalid ratio, size, or thinking level | Use a value from the returned list |
| `400` "blocked due to safety violations" | Prompt or content refused | Rephrase the request; do not retry unchanged |
| `401` | Missing or invalid API key | Set `GEMINI_API_KEY` from the secret store |
| `403` | Key lacks access or billing | Check the project's billing and model access |
| `404` | Wrong model ID or path | Use `gemini-nano-banana-2.1` exactly |
| `429` | Quota or rate limit | Slow down, lower `--max-concurrency`, retry later |
| `500`, `503`, `504` | Transient backend or capacity issue | Retry with backoff within the authorized budget |

## See Also

- `references/patterns.md` for custom compositions and optional presets
- `references/configuration.md` for the local scripts
- `references/gotchas.md` for text and clutter pitfalls

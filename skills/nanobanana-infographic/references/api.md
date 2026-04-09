# Nano Banana 2 Gemini API Reference For Infographics

## Table of Contents

- [Overview](#overview)
- [Verified Models](#verified-models)
- [Base URL and Headers](#base-url-and-headers)
- [Request Shape](#request-shape)
- [ImageConfig](#imageconfig)
- [Response Handling](#response-handling)
- [Common Failures](#common-failures)

## Overview

This skill targets Nano Banana 2 through Gemini `generateContent`.

- Public product name: `Nano Banana 2`
- Public model family name: `Gemini 3.1 Flash Image`
- Callable Developer API model verified on April 9, 2026: `gemini-3.1-flash-image-preview`
- Default aspect ratio: `16:9`
- Default verification size: `1K`
- Default workflow: one render pass per variant

Google's February 26, 2026 launch post identifies Nano Banana 2 as `Gemini 3.1 Flash Image`. A live `ListModels` call on April 9, 2026 exposed `models/gemini-3.1-flash-image-preview` as the callable Developer API model for this key. Use that callable ID in scripts and raw HTTP requests.

## Verified Models

Nano Banana 2 guidance for this skill is intentionally narrow:

- preferred public name: `Nano Banana 2`
- preferred API target: `gemini-3.1-flash-image-preview`

If you need to confirm what your own key can call today, list the models directly:

```bash
curl -sS "https://generativelanguage.googleapis.com/v1beta/models" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  | jq -r '.models[]?.name' | rg 'flash-image|image'
```

## Base URL and Headers

Developer API endpoint:

```text
https://generativelanguage.googleapis.com/v1beta/models/<model>:generateContent
```

Required headers:

```text
x-goog-api-key: $GEMINI_API_KEY
Content-Type: application/json
```

## Request Shape

Minimal raw HTTP request for a single infographic render:

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "Create a sleek executive infographic about cloud cost control. White background. Title text: Cost discipline. Three disciplined sections. Minimal palette. Flat editorial design."
          }
        ]
      }
    ],
    "generationConfig": {
      "responseModalities": ["TEXT", "IMAGE"],
      "imageConfig": {
        "aspectRatio": "16:9",
        "imageSize": "1K"
      }
    }
  }'
```

Notes:

- `responseModalities` must include `IMAGE` to ask for image output.
- `TEXT` is useful because Gemini often returns a short text part alongside the image.
- For review loops, keep the prompt focused on one composition, not a list of styles.

## ImageConfig

The Gemini API reference documents these `ImageConfig` options:

- `aspectRatio`
- `imageSize`

Supported aspect ratios documented by Google:

```text
1:1, 1:4, 4:1, 1:8, 8:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9
```

Supported image sizes documented by Google:

```text
512, 1K, 2K, 4K
```

If `imageSize` is omitted, Google documents a default of `1K`.

For this skill:

- Use `1K` as the default review size.
- Use `512` for quick previews when you want lower-cost iteration. A live Nano Banana 2 probe on April 9, 2026 accepted both `512` and `1K`.
- Use `2K` or `4K` only after the composition is already working.

## Response Handling

Gemini returns a `candidates` array. The actual image bytes arrive in `inlineData` parts inside the first candidate:

```text
candidates[0].content.parts[]
```

Typical handling pattern:

- If `part.text` exists, save it as supporting notes.
- If `part.inlineData` exists, base64-decode `part.inlineData.data` and save it to disk.

Use `scripts/probe_gemini_image_api.py` for a portable reference implementation.

## Common Failures

These are practical HTTP failures to expect when operating the API:

| Status | Likely Cause | Fix |
|---|---|---|
| `400` | bad request shape, unsupported config, malformed JSON | check `responseModalities`, `imageConfig`, and JSON syntax |
| `401` | missing or invalid API key | export `GEMINI_API_KEY` and retry |
| `403` | key is valid but lacks access | check project, billing, or model availability |
| `404` | wrong model ID or endpoint path | verify the exact model string |
| `429` | quota or rate limit pressure | slow the loop and retry later |
| `500` or `503` | transient backend or capacity issue | retry with backoff; drop to `512` or `1K` while testing |

## See Also

- `references/patterns.md` for the three-variant workflow
- `references/configuration.md` for the local scripts
- `references/gotchas.md` for text and clutter pitfalls

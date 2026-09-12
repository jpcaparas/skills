# audify Configuration & Setup

## Table of Contents

- [Requirements](#requirements)
- [Authentication](#authentication)
- [Environment variables](#environment-variables)
- [Prerequisite checks](#prerequisite-checks)
- [Troubleshooting](#troubleshooting)

## Requirements

`audify` is intentionally small and dependency-light. It requires:

- `python3`
- `ffmpeg`
- `GEMINI_API_KEY`

Optional but useful:

- `jq` when you want to inspect raw REST responses

## Authentication

This skill uses a Gemini API key, not `gcloud` ADC, OAuth, or a service-account flow.

Get the key from Google AI Studio, then export it:

```bash
export GEMINI_API_KEY="your-key-here"
```

`scripts/audify.py` and `scripts/probe_gemini_tts.py` both stop immediately when `GEMINI_API_KEY` is missing.

## Environment Variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | Yes | Authenticates model discovery and speech generation |

## Prerequisite Checks

Check that `ffmpeg` exists:

```bash
command -v ffmpeg
```

Check that the key exposes Gemini TTS models:

```bash
python3 scripts/probe_gemini_tts.py --mode models
```

Run a short end-to-end smoke test:

```bash
python3 scripts/probe_gemini_tts.py --mode smoke
```

If you want to inspect the raw model listing yourself:

```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200" \
  -H "x-goog-api-key: $GEMINI_API_KEY" | jq -r '.models[].name'
```

## Troubleshooting

### `GEMINI_API_KEY` is missing

The wrapper exits before touching the source. Set the environment variable first.

### `gemini-3.1-flash-tts-preview` is not listed

Treat that as unavailable access and bail. Do not silently switch models unless the user asked for a fallback.

### `ffmpeg` is missing

The default MP3 path cannot succeed without local conversion. Either install `ffmpeg` or run `--format wav`.

### The server returns `403`

Treat this as "API unavailable for this key or project" and bail with the concrete response body. Do not keep retrying `403`.

### The server returns `500`

`audify` retries transient failures automatically because Google documents rare random `500` failures for Gemini 3.1 Flash TTS. If retries still fail, stop and surface the server body.

## See Also

- `references/api.md` for exact request and response shapes
- `references/patterns.md` for the recommended wrapper commands
- `references/gotchas.md` for non-obvious failure cases

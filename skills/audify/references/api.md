# Gemini TTS API Reference For audify

## Table of Contents

- [Overview](#overview)
- [Endpoints audify uses](#endpoints-audify-uses)
- [Common headers](#common-headers)
- [Verified wrapper call](#verified-wrapper-call)
- [Supported models](#supported-models)
- [Voice options](#voice-options)
- [Response handling](#response-handling)
- [Error handling](#error-handling)

## Overview

`audify` targets the Gemini API TTS surface exposed through `generativelanguage.googleapis.com`, authenticated with `GEMINI_API_KEY`.

Base URL:

```text
https://generativelanguage.googleapis.com/v1beta
```

Primary model:

```text
gemini-3.1-flash-tts-preview
```

The verified live model list in this environment also exposed:

- `models/gemini-2.5-flash-preview-tts`
- `models/gemini-2.5-pro-preview-tts`
- `models/gemini-3.1-flash-tts-preview`

## Endpoints audify uses

### Discover available models

```text
GET /models?pageSize=200
```

Use this to confirm that `gemini-3.1-flash-tts-preview` is reachable before synthesis. `scripts/probe_gemini_tts.py --mode models` wraps this check.

### Synthesize speech

```text
POST /models/gemini-3.1-flash-tts-preview:generateContent
```

This is the endpoint that `scripts/audify.py` calls for each cleaned transcript chunk.

## Common Headers

Every request in this skill uses:

```text
x-goog-api-key: $GEMINI_API_KEY
Content-Type: application/json
Accept: application/json
```

## Verified Wrapper Call

This raw call matches the wrapper's live-tested request shape:

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-tts-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [{
        "text": "Synthesize speech only.\n### DIRECTOR NOTES\nPerformance: Clear, neutral narrator.\n### TRANSCRIPT\nSkill validation is working."
      }]
    }],
    "generationConfig": {
      "responseModalities": ["AUDIO"],
      "speechConfig": {
        "voiceConfig": {
          "prebuiltVoiceConfig": {
            "voiceName": "Kore"
          }
        }
      }
    },
    "model": "gemini-3.1-flash-tts-preview"
  }'
```

Run the production-safe probe instead of hand-parsing the response:

```bash
python3 scripts/probe_gemini_tts.py --mode smoke
```

## Supported Models

Google's speech generation docs list these Gemini API TTS models:

| Model | Single speaker | Multi-speaker |
| --- | --- | --- |
| `gemini-3.1-flash-tts-preview` | Yes | Yes |
| `gemini-2.5-flash-preview-tts` | Yes | Yes |
| `gemini-2.5-pro-preview-tts` | Yes | Yes |

`audify` defaults to `gemini-3.1-flash-tts-preview` because that is the newest documented Gemini API TTS model as of April 16, 2026.

## Voice Options

Google documents these 30 prebuilt voices for Gemini TTS:

| Voice | Style |
| --- | --- |
| `Zephyr` | Bright |
| `Puck` | Upbeat |
| `Charon` | Informative |
| `Kore` | Firm |
| `Fenrir` | Excitable |
| `Leda` | Youthful |
| `Orus` | Firm |
| `Aoede` | Breezy |
| `Callirrhoe` | Easy-going |
| `Autonoe` | Bright |
| `Enceladus` | Breathy |
| `Iapetus` | Clear |
| `Umbriel` | Easy-going |
| `Algieba` | Smooth |
| `Despina` | Smooth |
| `Erinome` | Clear |
| `Algenib` | Gravelly |
| `Rasalgethi` | Informative |
| `Laomedeia` | Upbeat |
| `Achernar` | Soft |
| `Alnilam` | Firm |
| `Schedar` | Even |
| `Gacrux` | Mature |
| `Pulcherrima` | Forward |
| `Achird` | Friendly |
| `Zubenelgenubi` | Casual |
| `Vindemiatrix` | Gentle |
| `Sadachbia` | Lively |
| `Sadaltager` | Knowledgeable |
| `Sulafat` | Warm |

Use `Kore` as the safe default when the user does not care. Ask when the request clearly depends on a particular persona.

## Response Handling

The Gemini API returns audio in `candidates[0].content.parts[0].inlineData.data` as base64 PCM.

`audify` assumes the same format shown in the official docs and verified live output:

- signed 16-bit little-endian PCM
- mono
- 24 kHz

The wrapper concatenates PCM chunks first, then converts once with `ffmpeg`:

```bash
ffmpeg -y -f s16le -ar 24000 -ac 1 -i input.pcm audio.mp3
```

Use `--format wav` when you want a WAV output instead of MP3.

## Error Handling

| Status | Meaning in practice | audify behavior |
| --- | --- | --- |
| `400` | Bad request, malformed payload, or unsuitable content | Bail with the server message |
| `401` | Invalid or missing key | Bail and tell the user to fix `GEMINI_API_KEY` |
| `403` | API not enabled or access blocked | Bail and tell the user the Gemini API surface is unavailable |
| `404` | Model name not found | Bail and report the missing model explicitly |
| `429` | Rate limiting | Retry with backoff, then bail if exhausted |
| `500` | Transient server failure or rare audio/token mismatch | Retry with backoff, then bail if exhausted |

## See Also

- `references/configuration.md` for key setup and prerequisite checks
- `references/patterns.md` for voice-selection and output-bundle workflows
- `references/gotchas.md` for Google-documented TTS quirks

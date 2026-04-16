---
name: audify
description: "Turn a readable resource into cleaned Gemini TTS audio. Use when the user wants to audify a URL, markdown note, HTML page, DOCX, or raw text into an MP3 while stripping markup, HTML, code fences, and bare URLs before synthesis. Triggers on: '/audify', 'read this aloud', 'turn this page into audio', 'make an mp3 narration', 'text to speech this resource', or when Gemini 3.1 Flash TTS with `GEMINI_API_KEY` is the right path. Do NOT trigger for music generation, live voice chat, or binary/media sources that are not meant to be narrated."
compatibility: "Requires: `python3`, `ffmpeg`, and `GEMINI_API_KEY`; optional `jq` for raw REST debugging"
---

# audify

Clean a readable resource into narration-safe prose, synthesize it with Gemini 3.1 Flash TTS, and write a timestamped output folder that contains an MP3, the cleaned transcript, and a manifest.

Verified against the Gemini API speech generation docs updated April 15, 2026 and the Google Cloud blog post published April 16, 2026.

## Decision Tree

What kind of input are you handling?

- A URL, markdown file, HTML file, DOCX, plain text file, or raw text that should be listened to
  - Run `python3 scripts/audify.py ...`

- A resource that is mostly code, logs, tables, minified JSON, or other content that is not meant to be narrated
  - Bail instead of forcing TTS. Explain why it is not a good narration target.

- A request where voice or nuance is materially ambiguous
  - Ask one short question before synthesis.
  - Use: "Which voice and delivery should I use? If you do not care, I will use `Kore` with a clear neutral narrator style."

- A request where the user does not care about style details
  - Default to `Kore` plus a clear neutral narrator nuance.

- A longer job with multiple chunks or a large cleaned transcript
  - Tell the user up front that multi-chunk TTS can take a few minutes and that quiet periods are normal.
  - Do not keep narrating every short poll. Prefer one expectation-setting update, then wait for chunk progress or completion.

- Missing `GEMINI_API_KEY`, unavailable `gemini-3.1-flash-tts-preview`, missing `ffmpeg`, or exhausted read attempts
  - Bail with the concrete failed prerequisite.

## Quick Reference

| Task | Command | Read |
| --- | --- | --- |
| URL to MP3 bundle | `python3 scripts/audify.py "https://example.com/"` | `references/patterns.md` |
| Local file to MP3 bundle | `python3 scripts/audify.py --file templates/sample-input.md --voice Kore --nuance "Warm documentary narrator"` | `references/patterns.md` |
| Raw text from stdin | `cat templates/sample-input.md \| python3 scripts/audify.py --stdin` | `references/patterns.md` |
| Clean-only suitability check | `python3 scripts/audify.py --url "https://example.com/" --check-only` | `references/patterns.md` |
| Live model and synthesis probe | `python3 scripts/probe_gemini_tts.py --mode all` | `references/api.md` |

## Reading Guide

| If the user needs... | Read |
| --- | --- |
| Raw Gemini REST shape, supported models, voices, and failure codes | `references/api.md` |
| Env vars, key setup, `ffmpeg`, and prerequisite checks | `references/configuration.md` |
| URL/file/text workflows, output bundle layout, and question-asking rules | `references/patterns.md` |
| Failure handling, retries, and why audify should bail | `references/gotchas.md` |

## Operational Rules

1. Treat `SKILL.md` as the entry point and keep the tool choice narrow: `scripts/audify.py` for production runs, `scripts/probe_gemini_tts.py` for live verification.
2. Clean first, synthesize second. Strip markup, HTML, code fences, and bare URLs before TTS so the spoken transcript stays close to the readable text instead of the transport format.
3. Preserve human text whenever possible. Keep visible anchor text, headings, paragraph content, and inline prose; drop boilerplate that is structural rather than spoken.
4. Stop when the source is not narration-friendly. Do not read code dumps, logs, stack traces, raw tables, or binary blobs aloud just because they decoded as text.
5. Stop when read attempts are exhausted. Do not silently fall back from a bad fetch or undecodable file to a hallucinated summary.
6. Set runtime expectations before long runs. For multi-chunk TTS, tell the user a realistic range such as "often 2-6 minutes" and that silence between chunk completions is normal.
7. Do not badger the user with polling updates. After the initial expectation-setting message, only report meaningful state changes such as chunk progress, retries, or final completion.
8. Auto-split large transiently failing chunks before giving up. Keep the same voice, nuance, model, and output format while retrying with smaller chunk boundaries.

## Output Contract

By default `scripts/audify.py` creates `audify-output/<timestamp>-<slug>/` under the current working directory.

The folder contains:

- `audio.mp3` by default
- `cleaned.txt` with the final spoken transcript
- `manifest.json` with source, voice, nuance, chunking, and retry metadata
- runtime expectations in both the wrapper output JSON and the status stream
- fallback chunk-split metadata when a large chunk had to be retried in smaller pieces

Use `--format wav` when MP3 conversion is not wanted.

## Gotchas

1. **Gemini TTS returns PCM, not MP3**: The Gemini API returns base64 PCM audio. This skill converts it locally with `ffmpeg`, so missing `ffmpeg` is a hard stop for the default MP3 path.
2. **Gemini 3.1 Flash TTS can throw transient `500` errors**: Google documents rare cases where the model emits text tokens instead of audio tokens. The wrapper retries transient failures with backoff.
3. **Vague prompts can get rejected or spoken aloud**: The wrapper uses an explicit "synthesize speech only" preamble and a labeled `TRANSCRIPT` section so instructions do not become narration.
4. **Voice and prompt can clash**: Google warns that strong speaker mismatches can sound wrong. When the user asks for a very specific persona, make sure the selected voice and nuance point in the same direction.
5. **HTML extraction is best-effort**: Blog chrome, nav text, or legal footer text can still leak through on messy pages. If the cleaned preview looks wrong, stop and ask for a narrower source.
6. **Long silence is not the same as failure**: A multi-chunk run can spend a couple of minutes inside Gemini calls and local MP3 conversion. Do not treat every quiet 30-second interval as a problem.
7. **A single large chunk can still fail transiently**: When that happens, the wrapper should split just that chunk into smaller pieces and continue with the same voice, nuance, model, and format instead of forcing a full manual rerun.

## Helper Scripts

- `scripts/audify.py` is the production wrapper for URL, file, stdin, and raw text inputs.
- `scripts/probe_gemini_tts.py` runs safe live probes against model discovery and short synthesis.
- `scripts/test_audify_unit.py` covers cleaner, chunking, DOCX extraction, and bail heuristics.
- `scripts/validate.py` checks structure, cross-references, and leftover template placeholders.
- `scripts/test_skill.py` runs structural checks, unit tests, and a live smoke probe when `GEMINI_API_KEY` is present.

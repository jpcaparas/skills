# audify

Production skill for turning readable resources into cleaned Gemini TTS narration with a timestamped MP3 output bundle.

## What It Covers

- URL, file, stdin, and raw-text inputs
- Markup, HTML, code-fence, and bare-URL stripping before TTS
- Voice and nuance selection with a neutral default
- Bail behavior for unreadable resources and missing prerequisites
- Live Gemini model discovery and safe smoke probes

## Key Files

- `SKILL.md` - authoritative instructions
- `references/api.md` - Gemini REST contract, models, and voices
- `references/configuration.md` - `GEMINI_API_KEY`, `ffmpeg`, and setup checks
- `references/patterns.md` - production wrapper commands and output layout
- `references/gotchas.md` - retries, bail rules, and preview-model caveats
- `scripts/audify.py` - production wrapper
- `scripts/probe_gemini_tts.py` - live verification helper

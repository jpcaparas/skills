# YouTube Transcript Dossier

Convert supplied or fetched YouTube transcripts into scoped summaries, notes, exports, or full dossiers with source timestamps.

## Fetching Requirements

Supplied transcripts need none of these tools.

- `python3`
- `yt-dlp` — for video metadata (`brew install yt-dlp` or `pip install yt-dlp`)
- `youtube-transcript-api` — for transcript fetching (`pip install youtube-transcript-api`)
- Restricted-content access is not guaranteed; see `references/fetching.md` for the upstream baseline and authorized-file boundary.

## Quick Start

```bash
# Fetch transcript + metadata as JSON
python3 scripts/fetch_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Get raw timestamped text
python3 scripts/fetch_transcript.py "VIDEO_ID" --format text

# Prefer Spanish, fall back to English
python3 scripts/fetch_transcript.py "https://youtu.be/VIDEO_ID" --lang es en
```

Then produce the requested summary or notes; `templates/dossier.md` is an optional scaffold for a full dossier.

## Install

```bash
npx skills add jpcaparas/skills --skill youtube-transcript-dossier
```

See `SKILL.md` for full instructions.

# YouTube Transcript Dossier

Convert a YouTube video transcript into a structured dossier with metadata, executive summary, timestamped key topics, notable quotes, takeaways, and follow-up items.

## Requirements

- `python3`
- `yt-dlp` — for video metadata (`brew install yt-dlp` or `pip install yt-dlp`)
- `youtube-transcript-api` — for transcript fetching (`pip install youtube-transcript-api`)
- Optional: cookie file for age-restricted videos

## Quick Start

```bash
# Fetch transcript + metadata as JSON
python3 scripts/fetch_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Get raw timestamped text
python3 scripts/fetch_transcript.py "VIDEO_ID" --format text

# Prefer Spanish, fall back to English
python3 scripts/fetch_transcript.py "https://youtu.be/VIDEO_ID" --lang es en
```

Then use the output to build a dossier following `templates/dossier.md`.

## Install

```bash
npx skills add jpcaparas/skills --skill youtube-transcript-dossier
```

See `SKILL.md` for full instructions.

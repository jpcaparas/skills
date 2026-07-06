---
name: youtube-transcript-dossier
description: "Convert a YouTube video transcript into a structured dossier: metadata, executive summary, timestamped key topics, notable quotes, takeaways, follow-ups. Trigger on: YouTube dossier, video to notes, transcript to summary, summarize YouTube video. Do NOT trigger for non-YouTube video, audio transcription, or downloading video files."
compatibility: "Requires: python3, yt-dlp, youtube-transcript-api (pip install youtube-transcript-api). Optional: cookie file for age-restricted videos."
metadata:
  version: "1.0.0"
  short-description: "Turn YouTube transcripts into structured dossiers with timestamps"
  openclaw:
    category: "productivity"
    subcategory: "summarization"
    requires:
      bins: [python3, yt-dlp]
    cliHelp: "python3 scripts/fetch_transcript.py --help"
    tags: ["youtube", "transcript", "dossier", "summary", "notes", "video"]
---

# YouTube Transcript Dossier

Fetch a YouTube video transcript and metadata, then synthesize a structured dossier with timestamped topics, quotes, takeaways, and follow-ups.

## Decision Tree

What does the user want?

- A full dossier from a YouTube video URL or ID
  Run `python3 scripts/fetch_transcript.py "<url>"`, then build the dossier using `templates/dossier.md`.

- Just the raw transcript (JSON, text, or VTT) without synthesis
  Run `python3 scripts/fetch_transcript.py "<url>" --format json|text|vtt` and return the output directly.

- Transcript for a non-English video
  Add `--lang <code>` (e.g. `--lang es fr en` for Spanish-first with fallback).

- Age-restricted or members-only video
  Export a cookie file from the browser, then add `--cookie-file cookies.txt`.

- The video has no captions at all
  Read `references/gotchas.md` for fallback strategies and what to tell the user.

- The user wants to save or export the dossier
  Produce the dossier first, then ask whether they want Markdown, PDF, or DOCX.

## Quick Reference

| Task | Command | Read |
| --- | --- | --- |
| Fetch transcript + metadata (JSON) | `python3 scripts/fetch_transcript.py "<url>"` | `references/fetching.md` |
| Fetch transcript only (skip metadata) | `python3 scripts/fetch_transcript.py "<url>" --no-metadata` | `references/fetching.md` |
| Fetch with language preference | `python3 scripts/fetch_transcript.py "<url>" --lang es en` | `references/fetching.md` |
| Fetch text format | `python3 scripts/fetch_transcript.py "<url>" --format text` | `references/fetching.md` |
| Fetch VTT format | `python3 scripts/fetch_transcript.py "<url>" --format vtt` | `references/fetching.md` |
| Build the dossier | Use `templates/dossier.md` as skeleton | `references/dossier-format.md` |
| Handle edge cases | — | `references/gotchas.md` |
| Validate the skill package | `python3 scripts/validate.py skills/youtube-transcript-dossier` | — |
| Run packaging tests | `python3 scripts/test_skill.py skills/youtube-transcript-dossier` | — |

## Default Workflow

1. **Extract the video ID.** Accept any YouTube URL format (watch, youtu.be, embed, shorts, m.youtube.com) or a bare 11-character ID. The script handles parsing automatically.
2. **Fetch metadata and transcript.** Run `scripts/fetch_transcript.py` to get video metadata (title, channel, duration, description, stats) and the best available transcript (manual captions preferred over auto-generated).
3. **Assess transcript quality.** Auto-generated captions are lower quality and may mishear words, names, and technical terms. Note the transcript `source` field (`manual` vs `auto-generated`) and adjust confidence accordingly.
4. **Synthesize the dossier.** Use the transcript snippets (which include `start` timestamps) and metadata to build a structured document. Copy `templates/dossier.md` as the starting skeleton.
5. **Anchor claims with timestamps.** Every topic, quote, and key point should reference the timestamp where it appears so the user can jump to the exact moment.
6. **Separate fact from inference.** The transcript is evidence; the dossier is interpretation. Mark uncertain items instead of smoothing them into confident statements.
7. **Return the dossier in Markdown** unless the user requested another format.

## Output Contract

The dossier follows `templates/dossier.md`. Omit empty sections, but keep these core sections when the source supports them:

- **Header**: video title, channel, URL, duration, upload date, transcript source
- **Executive Summary**: 2-3 sentence overview
- **Key Topics**: major themes with timestamp ranges
- **Notable Quotes**: verbatim quotes with timestamps
- **Key Takeaways**: distilled points worth remembering
- **Follow-Ups**: concrete action items (read, verify, compare, try, watch)
- **References Mentioned**: people, tools, books, papers, links

## Reading Guide

| If the user needs... | Read |
| --- | --- |
| Transcript fetching details, yt-dlp metadata, language fallback, cookie setup | `references/fetching.md` |
| Dossier section definitions, formatting rules, and quality bar | `references/dossier-format.md` |
| Handling missing captions, auto-gen quality, restricted videos, common failures | `references/gotchas.md` |
| A reusable output skeleton | `templates/dossier.md` |

## Gotchas

1. **Auto-generated captions are unreliable for names and jargon.** YouTube speech-to-text frequently mishears proper nouns, technical terms, and numbers. When `source` is `auto-generated`, flag low-confidence sections and do not treat transcribed names as verified.
2. **Manual captions may be incomplete.** Some channels upload partial or edited caption tracks. If the transcript ends abruptly or skips sections, note the gap rather than assuming the video ended.
3. **Timestamps drift from visual content.** The transcript reflects spoken audio, not slides, demos, or visual overlays. If the user references something they saw, the timestamp may not align with the visual moment.
4. **Music and sound effects clutter the transcript.** YouTube captions include `[♪♪♪]`, `[Applause]`, `[Music]`, and similar non-speech markers. Filter these out of quotes and takeaways, but note when a section is primarily music.
5. **Long videos produce very long transcripts.** A 2-hour lecture can yield 1000+ snippets. Chunk the synthesis by timestamp range or topic rather than trying to process the entire transcript at once.
6. **Some videos have captions disabled.** The creator must enable captions. If transcripts are disabled, the script returns exit code 2. Tell the user and offer alternatives (see `references/gotchas.md`).
7. **Cookie files are required for age-restricted videos.** Without a valid cookie file, `youtube-transcript-api` cannot access age-restricted content. Export cookies from a logged-in browser session.

## Helper Scripts

- `scripts/fetch_transcript.py` — fetches video metadata (via yt-dlp) and transcript (via youtube-transcript-api), outputs JSON, text, or VTT.
- `scripts/validate.py` — checks skill structure, frontmatter, and cross-references.
- `scripts/test_skill.py` — runs structural validation, eval format checks, and cross-reference integrity.

---
name: youtube-transcript-dossier
description: "Convert YouTube transcripts into summaries, notes, raw exports, or structured dossiers with timestamps. Use for YouTube dossier, video to notes, transcript to summary, or summarize YouTube video. Do NOT use for non-YouTube video, audio transcription, or downloading video files."
compatibility: "Supplied transcripts need no fetching tools. Fetching requires python3 and youtube-transcript-api; yt-dlp adds metadata. Authorized user-provided cookie files are usable only where upstream supports them."
metadata:
  version: "1.0.0"
  short-description: "Turn YouTube transcripts into structured dossiers with timestamps"
  openclaw:
    category: "productivity"
    subcategory: "summarization"
    cliHelp: "python3 scripts/fetch_transcript.py --help"
    tags: ["youtube", "transcript", "dossier", "summary", "notes", "video"]
---

# YouTube Transcript Dossier

Turn a supplied or fetched YouTube transcript into the answer the user requested. Match its length and sections to the task; a full dossier is available, not mandatory for every summary.

## Decision Tree

What does the user want?

- A short summary, selected topics, or an answer from a supplied transcript
  Use the supplied text directly. Do not refetch unless missing context or a requested verification makes it necessary.

- A full dossier from a YouTube video URL or ID
  If no transcript is supplied, run `python3 scripts/fetch_transcript.py "<url>"`. Use `templates/dossier.md` as an optional skeleton and omit unsupported or unhelpful sections.

- Just the raw transcript (JSON, text, or VTT) without synthesis
  Return the supplied transcript or fetch with `--format json|text|vtt`. Preserve transcript wording; JSON preserves snippet text and numeric timing, while text output normalizes whitespace and rounds display timestamps. Use JSON or the original supplied file when exact preservation matters.

- Transcript for a non-English video
  Add `--lang <code>` (e.g. `--lang es fr en` for Spanish-first with fallback).

- Age-restricted or members-only video
  Do not promise access. Read `references/fetching.md`; use only a user-provided authorized cookie file if the installed upstream version supports it. Never extract browser session credentials automatically or bypass access controls.

- The video has no captions at all
  Read `references/gotchas.md` for fallback strategies and what to tell the user.

- The user wants to save or export the dossier
  Produce the requested format directly with available tooling. Ask only if a missing format choice is consequential; do not ask whether they want an export they already requested. Report unavailable export tooling honestly.

## Quick Reference

| Task | Command | Read |
| --- | --- | --- |
| Fetch transcript + metadata (JSON) | `python3 scripts/fetch_transcript.py "<url>"` | `references/fetching.md` |
| Fetch transcript only (skip metadata) | `python3 scripts/fetch_transcript.py "<url>" --no-metadata` | `references/fetching.md` |
| Fetch with language preference | `python3 scripts/fetch_transcript.py "<url>" --lang es en` | `references/fetching.md` |
| Fetch text format | `python3 scripts/fetch_transcript.py "<url>" --format text` | `references/fetching.md` |
| Fetch VTT format | `python3 scripts/fetch_transcript.py "<url>" --format vtt` | `references/fetching.md` |
| Build a full dossier | Optionally adapt `templates/dossier.md` | `references/dossier-format.md` |
| Handle edge cases | — | `references/gotchas.md` |
| Validate the skill package | From the skill directory: `python3 scripts/validate.py .` | — |
| Run packaging tests | From the skill directory: `python3 scripts/test_skill.py .` | — |

## Default Workflow

1. **Use the available source.** Start with supplied transcript text. When fetching is needed, accept supported YouTube URLs (watch, youtu.be, embed, shorts, m.youtube.com) or a bare 11-character ID.
2. **Fetch only missing evidence.** Run `scripts/fetch_transcript.py` for transcript and metadata, or add `--no-metadata` when metadata is unnecessary. Manual captions are preferred by the helper, but are not guaranteed accurate.
3. **Assess transcript quality.** Note known source/language, auto-caption errors, gaps, and coverage limits. If source information is missing, say it is unknown rather than inventing metadata.
4. **Synthesize to scope.** Return the requested summary, notes, answer, or dossier. Choose chunking by transcript size, context capacity, and requested coverage, not video duration alone. Do not invent quotes or follow-ups to fill sections.
5. **Anchor claims with timestamps.** Preserve available timestamps for topics, quotes, and key points. Never invent timestamps for untimed text. Quotes must match the actual transcript; flag suspected errors outside the quotation or use a labeled paraphrase.
6. **Separate fact from inference.** The transcript is evidence; the dossier is interpretation. Mark uncertain items instead of smoothing them into confident statements.
7. **Deliver the requested format.** Use Markdown when none is specified and no consequential format decision is missing.

## Output Contract

For a full dossier, select useful sections from `templates/dossier.md`. Short summaries and targeted answers need no dossier headings. Do not force a sentence count, quotes, or follow-ups:

- **Header**: video title, channel, URL, duration, upload date, transcript source
- **Executive Summary**: overview sized to the user's request
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
4. **Music and sound effects clutter summaries.** Omit irrelevant non-speech markers from synthesis, not from raw exports. If quoting a passage containing markers, preserve it or mark omissions explicitly.
5. **Long videos may need chunking.** Use timestamp ranges or topics when context limits or coverage warrant it; a focused answer need not summarize every chunk.
6. **Some videos have captions disabled.** The creator must enable captions. If transcripts are disabled, the script returns exit code 2. Tell the user and offer alternatives (see `references/gotchas.md`).
7. **Restricted-content access is not guaranteed.** Cookie support depends on upstream behavior; a flag in the helper is not proof of working authentication. Prefer a user-provided transcript when access is unavailable.

## Keeping Guidance Current

API and cookie behavior are version-sensitive; the helper's documented behavior is a baseline, not a promise of restricted-content support. When failures, gaps, or suspected staleness affect the task, consult current official upstream docs or trusted source evidence. Skip routine browsing for sufficient supplied transcripts. If verification is unavailable, state the gap and propose a sourced correction plus an example or check in the canonical package; never automatically edit installed copies.

## Helper Scripts

- `scripts/fetch_transcript.py` — fetches video metadata (via yt-dlp) and transcript (via youtube-transcript-api), outputs JSON, text, or VTT.
- `scripts/validate.py` — checks skill structure, frontmatter, and cross-references.
- `scripts/test_skill.py` — runs structural validation, eval format checks, and cross-reference integrity.

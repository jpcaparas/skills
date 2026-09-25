# Transcript Fetching

How `scripts/fetch_transcript.py` acquires video metadata and transcript data.

Use it only when transcript or metadata evidence is missing and needed. A supplied transcript can support a summary directly without tool installation, network calls, or metadata enrichment.

## Architecture

The script uses two tools in sequence:

1. **yt-dlp** — fetches video metadata (title, channel, duration, description, stats) via `--dump-json --skip-download`. This is a read-only operation that does not download the video file.
2. **youtube-transcript-api** — fetches the transcript with timestamped snippets. Prefers manually created captions over auto-generated ones.

Both tools are called independently. If yt-dlp fails, transcript fetching can still succeed; if transcript fetching fails, available metadata can still be returned in JSON. Either or both may fail. Metadata is not evidence of the video's spoken content.

## Input Formats

The script accepts any of these YouTube URL formats:

| Format | Example |
| --- | --- |
| Watch URL | `https://www.youtube.com/watch?v=VIDEO_ID` |
| Short URL | `https://youtu.be/VIDEO_ID` |
| Embed URL | `https://www.youtube.com/embed/VIDEO_ID` |
| Shorts URL | `https://www.youtube.com/shorts/VIDEO_ID` |
| Mobile URL | `https://m.youtube.com/watch?v=VIDEO_ID` |
| Bare ID | `VIDEO_ID` (11 characters) |

URL parameters like `&t=42s` or `&list=...` are ignored. Only the 11-character video ID is extracted.

## Language Preference

Use `--lang` to specify preferred languages in priority order:

```bash
# Spanish first, fall back to English
python3 scripts/fetch_transcript.py "<url>" --lang es en

# Multiple English variants
python3 scripts/fetch_transcript.py "<url>" --lang en-US en-GB en
```

The script tries languages in this order:

1. Manually created transcript in the first matching language
2. Manually created in any remaining preferred languages
3. Auto-generated transcript in the first matching language
4. Auto-generated in any remaining preferred languages
5. Any available transcript matching the preference list

If no transcript matches any preferred language, the script lists what IS available and exits with code 2.

## Output Formats

### JSON (default)

Full structured output with metadata, transcript source info, and all snippets:

JSON preserves fetched snippet text, line breaks, and numeric timestamps. Keep raw output unchanged; annotate or paraphrase in a separate synthesis rather than editing the evidence.

```json
{
  "video_id": "dQw4w9WgXcQ",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "metadata": { "title": "...", "channel": "...", "duration": 213 },
  "transcript": {
    "source": "manual",
    "language": "English",
    "language_code": "en",
    "snippet_count": 61,
    "snippets": [{ "start": 1.4, "duration": 1.68, "text": "..." }]
  },
  "warnings": []
}
```

The `source` field is the most important quality indicator:
- `"manual"` — human-written or channel-uploaded captions (preferred by the helper, not guaranteed accurate)
- `"auto-generated"` — YouTube speech-to-text (may mishear terms)

### Text

Timestamped plain text suitable for reading or piping to other tools. The helper collapses snippet whitespace and rounds display timestamps to seconds; use JSON or the original supplied transcript when exact text/timing preservation matters:

```text
# Video Title
# Channel: Channel Name
# Duration: 03:33

Transcript: English (manual)

[00:01] First line of transcript
[00:19] Second line of transcript
```

### VTT

WebVTT subtitle format compatible with video players and subtitle editors:

```vtt
WEBVTT

1
00:00:01.360 --> 00:00:03.040
First line of transcript

2
00:00:18.640 --> 00:00:21.880
Second line of transcript
```

## Metadata Fields

When yt-dlp is available, these fields are extracted:

| Field | Description |
| --- | --- |
| `title` | Video title |
| `channel` | Channel name |
| `uploader` | Uploader name (may differ from channel) |
| `duration` | Duration in seconds |
| `upload_date` | Upload date as YYYYMMDD |
| `view_count` | View count |
| `like_count` | Like count |
| `description` | Full video description |
| `tags` | Channel-assigned tags |
| `categories` | YouTube categories |
| `availability` | "public", "unlisted", "private", etc. |
| `live_status` | "not_live", "is_live", "was_live", etc. |
| `channel_url` | Channel URL |

Not all fields are present for every video. Check for null/missing before using.

## Cookie File Support

The [official upstream README's Cookie Authentication section](https://github.com/jdepoix/youtube-transcript-api#cookie-authentication), checked on September 25, 2026, reports cookie authentication unavailable after YouTube API changes. This is a verified documentation baseline, not a permanent version claim; a cookie flag or CLI example alone does not establish working support.

The bundled helper attempts `YouTubeTranscriptApi(cookie_path=...)`. If that constructor argument is unsupported, it falls back to an unauthenticated client. It does not pass the cookie file to the separate yt-dlp metadata call. Do not promise age-restricted, members-only, private, or region-locked access.

If current official upstream documentation and the installed version establish support for the needed operation, use only an authorized cookie file the user supplied:

```bash
python3 scripts/fetch_transcript.py "<url>" --cookie-file /path/to/user-provided-cookies.txt
```

Never automatically export browser cookies or extract session credentials. Treat the file as secret: do not print its contents, commit it, or include it in a dossier. Do not bypass access controls. If access is unavailable, request an authorized transcript instead of assuming an upgrade will fix authentication.

For version/API failures, check the installed version and [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) or [yt-dlp](https://github.com/yt-dlp/yt-dlp) official docs as relevant. State unresolved support gaps and propose a sourced canonical-package correction with a check; do not silently patch an installed copy.

## Exit Codes

| Code | Meaning |
| --- | --- |
| 0 | Success — transcript fetched |
| 1 | Usage error — bad URL or invalid arguments |
| 2 | Transcript unavailable — no captions, video removed, or language not found |
| 3 | Dependency missing — `youtube-transcript-api` is not installed |

## See Also

- `references/dossier-format.md` — how to structure the synthesized dossier
- `references/gotchas.md` — troubleshooting transcript quality and availability

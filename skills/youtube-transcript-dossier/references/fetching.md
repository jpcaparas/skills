# Transcript Fetching

How `scripts/fetch_transcript.py` acquires video metadata and transcript data.

## Architecture

The script uses two tools in sequence:

1. **yt-dlp** — fetches video metadata (title, channel, duration, description, stats) via `--dump-json --skip-download`. This is a read-only operation that does not download the video file.
2. **youtube-transcript-api** — fetches the transcript with timestamped snippets. Prefers manually created captions over auto-generated ones.

Both tools are called independently. If yt-dlp fails, the transcript is still fetched. If youtube-transcript-api fails, the metadata is still returned. This graceful degradation ensures partial results are always available.

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
- `"manual"` — human-written or channel-uploaded captions (highest quality)
- `"auto-generated"` — YouTube speech-to-text (lower quality, may mishear terms)
- `"yt-dlp-fallback"` — not currently used, reserved for future fallback

### Text

Timestamped plain text suitable for reading or piping to other tools:

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

For age-restricted, members-only, or region-locked videos:

```bash
# Export cookies from a logged-in browser session
# (use a browser extension like "Get cookies.txt" or yt-dlp's --cookies-from-browser)

python3 scripts/fetch_transcript.py "<url>" --cookie-file cookies.txt
```

The cookie file should be in Netscape format (the same format yt-dlp uses). If the installed version of youtube-transcript-api does not support `cookie_path`, the script warns and continues without cookies.

## Exit Codes

| Code | Meaning |
| --- | --- |
| 0 | Success — transcript fetched |
| 1 | Usage error — bad URL or invalid arguments |
| 2 | Transcript unavailable — no captions, video removed, or language not found |
| 3 | Dependency missing — youtube-transcript-api not installed |

## See Also

- `references/dossier-format.md` — how to structure the synthesized dossier
- `references/gotchas.md` — troubleshooting transcript quality and availability

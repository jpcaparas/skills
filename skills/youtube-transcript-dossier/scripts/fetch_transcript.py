#!/usr/bin/env python3
"""
fetch_transcript.py — Fetch YouTube video metadata and transcript as structured JSON.

Usage:
    python3 fetch_transcript.py <youtube-url-or-id> [options]

Examples:
    python3 fetch_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    python3 fetch_transcript.py dQw4w9WgXcQ --lang en --format json
    python3 fetch_transcript.py "https://youtu.be/dQw4w9WgXcQ" --format text
    python3 fetch_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --cookie-file cookies.txt

Output:
    JSON (default): video metadata + transcript snippets with timestamps
    text:           timestamped plain text ([MM:SS] text)
    vtt:            WebVTT subtitle format

Exit codes:
    0 = success
    1 = usage error (bad input)
    2 = transcript unavailable (no captions, video removed, etc.)
    3 = dependency missing (yt-dlp or youtube-transcript-api)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

YOUTUBE_ID_RE = re.compile(
    r"(?:v=|/embed/|/shorts/|youtu\.be/)"
    r"([a-zA-Z0-9_-]{11})"
    r"(?:[&?].*)?$"
)
BARE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")

YTDLP_FIELDS = [
    "id", "title", "channel", "uploader", "duration",
    "upload_date", "view_count", "like_count",
    "description", "tags", "categories",
    "availability", "live_status", "channel_url",
]


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class Snippet:
    start: float
    duration: float
    text: str


@dataclass
class TranscriptInfo:
    source: str
    language: str
    language_code: str
    snippet_count: int
    snippets: list[Snippet] = field(default_factory=list)


@dataclass
class FetchResult:
    video_id: str
    url: str
    metadata: dict[str, Any]
    transcript: TranscriptInfo | None
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_video_id(input_str: str) -> str | None:
    """Extract an 11-character YouTube video ID from a URL or bare ID."""
    input_str = input_str.strip()
    if BARE_ID_RE.match(input_str):
        return input_str
    m = YOUTUBE_ID_RE.search(input_str)
    if m:
        return m.group(1)
    return None


def format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_vtt_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS.mmm (WebVTT cue timestamp)."""
    total_ms = int(round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


# ---------------------------------------------------------------------------
# Metadata fetching (yt-dlp)
# ---------------------------------------------------------------------------

def fetch_metadata(video_id: str) -> tuple[dict[str, Any], list[str]]:
    """Fetch video metadata via yt-dlp --dump-json.

    Returns (metadata_dict, warnings). If yt-dlp is unavailable or fails,
    metadata is empty and a warning is added.
    """
    warnings: list[str] = []
    if shutil.which("yt-dlp") is None:
        warnings.append("yt-dlp not found on PATH - skipping metadata fetch")
        return {}, warnings

    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--skip-download", url],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        warnings.append("yt-dlp timed out after 60s - skipping metadata fetch")
        return {}, warnings
    except Exception as exc:
        warnings.append(f"yt-dlp failed: {exc} - skipping metadata fetch")
        return {}, warnings

    if result.returncode != 0:
        stderr = result.stderr.strip()
        warnings.append(f"yt-dlp exited {result.returncode}: {stderr[:200]}")
        return {}, warnings

    try:
        raw = json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        warnings.append(f"Could not parse yt-dlp JSON: {exc}")
        return {}, warnings

    metadata = {k: raw.get(k) for k in YTDLP_FIELDS if k in raw}
    return metadata, warnings


# ---------------------------------------------------------------------------
# Transcript fetching (youtube-transcript-api)
# ---------------------------------------------------------------------------

def _import_ytt_api():
    """Import YouTubeTranscriptApi, returning (class, error_string)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        return YouTubeTranscriptApi, None
    except ImportError:
        return None, "youtube-transcript-api not installed - run: pip install youtube-transcript-api"


def _import_errors():
    """Import youtube-transcript-api exception types."""
    try:
        from youtube_transcript_api._errors import (
            VideoUnavailable,
            NoTranscriptFound,
            TranscriptsDisabled,
            NoTranscriptAvailable,
            NotTranslatable,
            TranslationLanguageNotFound,
        )
        return {
            "VideoUnavailable": VideoUnavailable,
            "NoTranscriptFound": NoTranscriptFound,
            "TranscriptsDisabled": TranscriptsDisabled,
            "NoTranscriptAvailable": NoTranscriptAvailable,
            "NotTranslatable": NotTranslatable,
            "TranslationLanguageNotFound": TranslationLanguageNotFound,
        }
    except ImportError:
        return {}


def fetch_transcript(
    video_id: str,
    lang_pref: list[str],
    cookie_file: str | None,
) -> tuple[TranscriptInfo | None, list[str]]:
    """Fetch transcript via youtube-transcript-api.

    Prefers manually created captions over auto-generated. Falls back
    through the language preference list. Returns (info, warnings).
    Returns (None, warnings) if no transcript is available.
    """
    warnings: list[str] = []
    YTTApi, err = _import_ytt_api()
    if YTTApi is None:
        return None, [err]

    errors = _import_errors()
    VideoUnavailable = errors.get("VideoUnavailable", Exception)
    NoTranscriptFound = errors.get("NoTranscriptFound", Exception)
    TranscriptsDisabled = errors.get("TranscriptsDisabled", Exception)

    try:
        if cookie_file:
            ytt_api = YTTApi(cookie_path=cookie_file)
        else:
            ytt_api = YTTApi()
    except TypeError:
        if cookie_file:
            warnings.append(
                "cookie-file not supported by this youtube-transcript-api version "
                "- ignoring cookies (age-restricted videos may fail)"
            )
        ytt_api = YTTApi()

    try:
        transcript_list = ytt_api.list(video_id)
    except VideoUnavailable as exc:
        return None, [f"Video unavailable: {exc}"]
    except TranscriptsDisabled:
        return None, ["Transcripts are disabled for this video"]
    except Exception as exc:
        return None, [f"Could not list transcripts: {type(exc).__name__}: {exc}"]

    # Try manually created transcripts first, then auto-generated
    transcript = None
    source_label = ""
    for finder, label in [
        (transcript_list.find_manually_created_transcript, "manual"),
        (transcript_list.find_generated_transcript, "auto-generated"),
    ]:
        for lang in lang_pref:
            try:
                transcript = finder([lang])
                source_label = label
                break
            except NoTranscriptFound:
                continue
            except Exception:
                continue
        if transcript:
            break

    if transcript is None:
        try:
            transcript = transcript_list.find_transcript(lang_pref)
            source_label = "auto-generated"
        except NoTranscriptFound:
            available = []
            for t in transcript_list:
                kind = "auto" if t.is_generated else "manual"
                available.append(f"{t.language} ({t.language_code}, {kind})")
            avail_str = ", ".join(available) if available else "none"
            return None, [
                f"No transcript found for languages {lang_pref}. "
                f"Available: {avail_str}"
            ]
        except Exception as exc:
            return None, [f"Could not find any transcript: {exc}"]

    try:
        fetched = transcript.fetch()
    except Exception as exc:
        return None, [f"Transcript fetch failed: {type(exc).__name__}: {exc}"]

    snippets = []
    for s in fetched:
        snippets.append(Snippet(
            start=float(s.start),
            duration=float(getattr(s, "duration", 0.0) or 0.0),
            text=s.text,
        ))

    info = TranscriptInfo(
        source=source_label,
        language=transcript.language,
        language_code=transcript.language_code,
        snippet_count=len(snippets),
        snippets=snippets,
    )
    return info, warnings


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def to_json(result: FetchResult) -> str:
    """Serialize FetchResult to JSON string."""
    data = asdict(result)
    return json.dumps(data, indent=2, ensure_ascii=False)


def to_text(result: FetchResult) -> str:
    """Format as timestamped plain text."""
    lines = []
    meta = result.metadata
    if meta:
        lines.append(f"# {meta.get('title', result.video_id)}")
        if meta.get("channel"):
            lines.append(f"# Channel: {meta['channel']}")
        if meta.get("duration"):
            lines.append(f"# Duration: {format_timestamp(meta['duration'])}")
        lines.append("")
    else:
        lines.append(f"# {result.video_id}")
        lines.append("")

    if result.transcript is None:
        lines.append("[No transcript available]")
        return "\n".join(lines)

    lines.append(f"Transcript: {result.transcript.language} ({result.transcript.source})")
    lines.append("")
    for s in result.transcript.snippets:
        lines.append(f"[{format_timestamp(s.start)}] {s.text}")
    return "\n".join(lines)


def to_vtt(result: FetchResult) -> str:
    """Format as WebVTT."""
    lines = ["WEBVTT", ""]
    if result.transcript is None:
        return "\n".join(lines)
    for i, s in enumerate(result.transcript.snippets, 1):
        start = format_vtt_timestamp(s.start)
        end = format_vtt_timestamp(s.start + s.duration)
        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(s.text)
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch YouTube video metadata and transcript.",
        usage="%(prog)s <youtube-url-or-id> [options]",
    )
    parser.add_argument(
        "url",
        help="YouTube URL or 11-character video ID",
    )
    parser.add_argument(
        "--lang", "-l",
        nargs="+",
        default=["en"],
        help="Preferred language codes in priority order (default: en). "
             "Example: --lang en en-US en-GB",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "text", "vtt"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--cookie-file",
        default=None,
        help="Path to a cookie file (Netscape or yt-dlp format) for "
             "age-restricted or members-only videos",
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Skip yt-dlp metadata fetch (transcript only)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)

    video_id = extract_video_id(args.url)
    if not video_id:
        print(f"Error: could not extract a YouTube video ID from: {args.url}", file=sys.stderr)
        print("Expected a YouTube URL or an 11-character video ID.", file=sys.stderr)
        return 1

    metadata: dict[str, Any] = {}
    warnings: list[str] = []
    if not args.no_metadata:
        metadata, warnings = fetch_metadata(video_id)

    transcript, t_warnings = fetch_transcript(video_id, args.lang, args.cookie_file)
    warnings.extend(t_warnings)

    result = FetchResult(
        video_id=video_id,
        url=f"https://www.youtube.com/watch?v={video_id}",
        metadata=metadata,
        transcript=transcript,
        warnings=warnings,
    )

    if args.format == "json":
        print(to_json(result))
    elif args.format == "text":
        print(to_text(result))
    elif args.format == "vtt":
        print(to_vtt(result))

    if transcript is None:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

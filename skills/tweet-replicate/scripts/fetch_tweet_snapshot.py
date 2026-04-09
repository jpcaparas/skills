#!/usr/bin/env python3
"""Fetch a frozen snapshot of a public X/Twitter status for local rerenders."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


USER_AGENT = "tweet-replicate/1.0 (+https://x.com)"
STATUS_ID_RE = re.compile(r"/status/(?P<id>\d+)")


def fetch_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urlopen(request) as response:
        return json.load(response)


def extract_status_id(url: str) -> str:
    match = STATUS_ID_RE.search(url)
    if not match:
        raise ValueError(f"Could not find a status ID in {url!r}")
    return match.group("id")


def download_file(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)
    return destination


def safe_extension(url: str, fallback: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix or fallback


def probe_media(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=codec_type,width,height:format=duration,size",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    payload = json.loads(result.stdout)
    streams = payload.get("streams") or []
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
    format_data = payload.get("format", {})
    duration = format_data.get("duration")
    size = format_data.get("size")
    return {
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "duration_seconds": float(duration) if duration is not None else None,
        "size_bytes": int(size) if size is not None else None,
        "has_audio": audio_stream is not None,
    }


def download_with_ytdlp(status_url: str, asset_dir: Path, stem: str = "media") -> Path:
    output_template = asset_dir / f"{stem}.%(ext)s"
    command = [
        "yt-dlp",
        "--no-playlist",
        "-f",
        "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b/best",
        "-o",
        str(output_template),
        status_url,
    ]
    subprocess.run(command, check=True)
    candidates = sorted(asset_dir.glob(f"{stem}.*"))
    if not candidates:
        raise RuntimeError("yt-dlp succeeded but did not leave a media file behind")
    return candidates[0]


def pick_primary_media(status: dict[str, Any]) -> dict[str, Any] | None:
    media_field = status.get("media") or []
    if isinstance(media_field, dict):
        media_items = media_field.get("all") or media_field.get("videos") or media_field.get("photos") or []
    else:
        media_items = media_field
    if not media_items:
        return None
    primary = media_items[0]
    media_type = primary.get("type") or "unknown"
    if media_type in {"video", "gif"}:
        formats = primary.get("formats") or []
        mp4_formats = [item for item in formats if item.get("container") == "mp4" and item.get("url")]
        if mp4_formats:
            primary["download_url"] = max(mp4_formats, key=lambda item: item.get("bitrate") or 0)["url"]
        elif primary.get("url"):
            primary["download_url"] = primary["url"]
    elif primary.get("url"):
        primary["download_url"] = primary["url"]
    return primary


def build_author_snapshot(
    author: dict[str, Any] | None,
    output_path: Path,
    asset_dir: Path,
    prefix: str = "",
) -> dict[str, Any]:
    author = author or {}
    avatar_url = author.get("avatar_url")
    local_avatar_path = None
    if avatar_url:
        avatar_extension = safe_extension(avatar_url, ".jpg")
        avatar_destination = asset_dir / f"{prefix}avatar{avatar_extension}"
        download_file(avatar_url, avatar_destination)
        local_avatar_path = os.path.relpath(avatar_destination, output_path.parent)
    return {
        "name": author.get("name") or "",
        "handle": author.get("screen_name") or "",
        "avatar_url": avatar_url,
        "local_avatar_path": local_avatar_path,
        "verified": bool((author.get("verification") or {}).get("verified")),
        "profile_url": author.get("url"),
    }


def build_media_snapshot(
    post: dict[str, Any],
    fallback_url: str,
    output_path: Path,
    asset_dir: Path,
    prefix: str = "",
) -> dict[str, Any] | None:
    primary_media = pick_primary_media(post)
    if not primary_media:
        return None

    media_type = primary_media.get("type") or "unknown"
    remote_url = primary_media.get("download_url")
    media_destination = None
    stem = f"{prefix}media" if prefix else "media"
    if remote_url:
        try:
            media_extension = safe_extension(remote_url, ".bin")
            media_destination = asset_dir / f"{stem}{media_extension}"
            download_file(remote_url, media_destination)
        except Exception:
            media_destination = None
    if media_destination is None and media_type in {"video", "gif"}:
        media_destination = download_with_ytdlp(post.get("url") or fallback_url, asset_dir, stem=stem)

    local_media_path = None
    local_media_probe: dict[str, Any] = {}
    if media_destination is not None and media_destination.exists():
        local_media_path = os.path.relpath(media_destination, output_path.parent)
        local_media_probe = probe_media(media_destination)

    return {
        "kind": media_type,
        "remote_url": remote_url,
        "thumbnail_url": primary_media.get("thumbnail_url"),
        "width": primary_media.get("width") or local_media_probe.get("width"),
        "height": primary_media.get("height") or local_media_probe.get("height"),
        "duration_seconds": primary_media.get("duration") or local_media_probe.get("duration_seconds"),
        "size_bytes": local_media_probe.get("size_bytes"),
        "has_audio": local_media_probe.get("has_audio", False),
        "local_path": local_media_path,
    }


def build_post_snapshot(
    post: dict[str, Any],
    output_path: Path,
    asset_dir: Path,
    fallback_url: str,
    prefix: str = "",
) -> dict[str, Any]:
    return {
        "canonical_url": post.get("url") or fallback_url,
        "status_id": str(post.get("id") or ""),
        "created_at": post.get("created_at"),
        "text": post.get("text") or "",
        "author": build_author_snapshot(post.get("author"), output_path, asset_dir, prefix=prefix),
        "counts": {
            "reply_count": int(post.get("replies") or 0),
            "repost_count": int(post.get("reposts") or 0),
            "like_count": int(post.get("likes") or 0),
            "bookmark_count": int(post.get("bookmarks") or 0),
            "quote_count": int(post.get("quotes") or 0),
            "view_count": int(post.get("views") or 0),
        },
        "media": build_media_snapshot(post, fallback_url, output_path, asset_dir, prefix=prefix),
    }


def create_snapshot(status_url: str, output_path: Path, asset_dir: Path) -> dict[str, Any]:
    status_id = extract_status_id(status_url)
    payload = fetch_json(f"https://api.fxtwitter.com/2/status/{status_id}")
    status = payload["status"]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    asset_dir.mkdir(parents=True, exist_ok=True)

    top_snapshot = build_post_snapshot(status, output_path, asset_dir, status_url)

    snapshot = {
        "schema_version": 1,
        "source_url": status_url,
        "snapshot_created_at": datetime.now().astimezone().isoformat(),
        "source_method": "api.fxtwitter.com/2/status",
        **top_snapshot,
    }
    if status.get("quote"):
        snapshot["quote"] = build_post_snapshot(
            status["quote"],
            output_path,
            asset_dir,
            status["quote"].get("url") or status_url,
            prefix="quote-",
        )
    output_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("status_url", help="Public X/Twitter status URL")
    parser.add_argument("--output", required=True, help="Path to write snapshot.json")
    parser.add_argument(
        "--asset-dir",
        required=True,
        help="Directory that should receive the local avatar and primary media files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output).resolve()
    asset_dir = Path(args.asset_dir).resolve()
    snapshot = create_snapshot(args.status_url, output_path, asset_dir)
    json.dump(snapshot, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

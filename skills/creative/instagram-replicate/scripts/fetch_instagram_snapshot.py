#!/usr/bin/env python3
"""Fetch a frozen snapshot of one public Instagram post or reel for local rerenders."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from playwright.async_api import async_playwright


USER_AGENT = "instagram-replicate/1.0 (+https://www.instagram.com)"
SHORTCODE_RE = re.compile(r"/(?P<kind>p|reel|tv)/(?P<shortcode>[A-Za-z0-9_-]+)")
OG_IMAGE_RE = re.compile(r'og:image"\s+content="([^"]+)"')


def fetch_json_via_ytdlp(url: str) -> dict[str, Any]:
    result = subprocess.run(
        ["yt-dlp", "--dump-single-json", "--no-warnings", url],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def extract_shortcode(url: str) -> str:
    match = SHORTCODE_RE.search(url)
    if not match:
        raise ValueError(f"Could not find an Instagram shortcode in {url!r}")
    return match.group("shortcode")


def download_file(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(unescape(url), headers={"User-Agent": USER_AGENT})
    with urlopen(request) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)
    return destination


def safe_extension(url: str, fallback: str) -> str:
    suffix = Path(urlparse(unescape(url)).path).suffix.lower()
    return suffix or fallback


def probe_media(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,width,height:format=duration,size",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    streams = payload.get("streams") or []
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
    format_data = payload.get("format") or {}
    duration = format_data.get("duration")
    size = format_data.get("size")
    return {
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "duration_seconds": float(duration) if duration is not None else None,
        "size_bytes": int(size) if size is not None else None,
        "has_audio": audio_stream is not None,
    }


def fetch_profile_html(handle: str) -> str:
    request = Request(
        f"https://www.instagram.com/{handle}/",
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    with urlopen(request) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_profile_avatar_url(profile_html: str) -> str | None:
    match = OG_IMAGE_RE.search(profile_html)
    if not match:
        return None
    return unescape(match.group(1))


async def detect_profile_verified(profile_url: str) -> bool:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        try:
            await page.goto(profile_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            selectors = [
                "main header svg[aria-label='Verified']",
                "svg[aria-label='Verified'][height='18']",
            ]
            for selector in selectors:
                if await page.locator(selector).count():
                    return True
            return False
        finally:
            await browser.close()


def download_media(post_url: str, asset_dir: Path, stem: str = "media") -> Path:
    output_template = asset_dir / f"{stem}.%(ext)s"
    subprocess.run(
        [
            "yt-dlp",
            "--force-overwrites",
            "--no-playlist",
            "--no-warnings",
            "--merge-output-format",
            "mp4",
            "-f",
            "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b[ext=mp4]/b/best",
            "-o",
            str(output_template),
            post_url,
        ],
        check=True,
    )
    candidates = sorted(
        path
        for path in asset_dir.glob(f"{stem}.*")
        if path.suffix.lower() not in {".part", ".json", ".info.json"}
    )
    if not candidates:
        raise RuntimeError("yt-dlp succeeded but did not leave a media file behind")
    return candidates[0]


def pick_best_thumbnail(payload: dict[str, Any]) -> str | None:
    thumbnails = payload.get("thumbnails") or []
    if thumbnails:
        sorted_thumbnails = sorted(
            thumbnails,
            key=lambda item: (
                int(item.get("width") or 0),
                int(item.get("height") or 0),
            ),
        )
        url = sorted_thumbnails[-1].get("url")
        if url:
            return url
    return payload.get("thumbnail")


def canonical_author_name(payload: dict[str, Any]) -> str:
    if payload.get("uploader"):
        return str(payload["uploader"])
    title = str(payload.get("title") or "")
    if title.startswith("Video by "):
        return title.removeprefix("Video by ").strip()
    return str(payload.get("channel") or payload.get("uploader_id") or "Instagram")


def relpath(path: Path, parent: Path) -> str:
    return os.path.relpath(path, parent)


def iso_timestamp_from_unix(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value).astimezone().isoformat()


def build_comment_snapshot(comment: dict[str, Any] | None) -> dict[str, Any] | None:
    if not comment:
        return None
    author = str(comment.get("author") or "").strip()
    text = str(comment.get("text") or "").strip()
    if not author and not text:
        return None
    return {
        "author_name": author,
        "author_handle": author,
        "text": text,
        "created_at": iso_timestamp_from_unix(comment.get("timestamp")),
    }


def create_snapshot(post_url: str, output_path: Path, asset_dir: Path) -> dict[str, Any]:
    payload = fetch_json_via_ytdlp(post_url)
    shortcode = extract_shortcode(post_url)
    handle = str(payload.get("channel") or "").strip()
    profile_url = f"https://www.instagram.com/{handle}/" if handle else None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    asset_dir.mkdir(parents=True, exist_ok=True)

    profile_html = fetch_profile_html(handle) if handle else ""
    avatar_url = extract_profile_avatar_url(profile_html) if profile_html else None
    verified = asyncio.run(detect_profile_verified(profile_url)) if profile_url else False

    local_avatar_path = None
    if avatar_url:
        avatar_destination = asset_dir / f"avatar{safe_extension(avatar_url, '.jpg')}"
        download_file(avatar_url, avatar_destination)
        local_avatar_path = relpath(avatar_destination, output_path.parent)

    poster_url = pick_best_thumbnail(payload)
    poster_local_path = None
    if poster_url:
        poster_destination = asset_dir / f"poster{safe_extension(poster_url, '.jpg')}"
        download_file(poster_url, poster_destination)
        poster_local_path = relpath(poster_destination, output_path.parent)

    media_destination = download_media(post_url, asset_dir)
    media_probe = probe_media(media_destination)

    snapshot = {
        "schema_version": 1,
        "source_url": post_url,
        "snapshot_created_at": datetime.now().astimezone().isoformat(),
        "source_method": "yt-dlp Instagram extractor + public profile page",
        "canonical_url": str(payload.get("webpage_url") or post_url),
        "shortcode": shortcode,
        "created_at": iso_timestamp_from_unix(payload.get("timestamp")),
        "caption": str(payload.get("description") or ""),
        "audio_label": "Original audio",
        "author": {
            "name": canonical_author_name(payload),
            "handle": handle,
            "avatar_url": avatar_url,
            "local_avatar_path": local_avatar_path,
            "verified": verified,
            "profile_url": profile_url,
        },
        "counts": {
            "like_count": int(payload.get("like_count") or 0),
            "comment_count": int(payload.get("comment_count") or 0),
        },
        "media": {
            "kind": "video" if payload.get("duration") else "image",
            "remote_url": str(payload.get("webpage_url") or post_url),
            "poster_url": poster_url,
            "poster_local_path": poster_local_path,
            "width": payload.get("width") or media_probe.get("width"),
            "height": payload.get("height") or media_probe.get("height"),
            "duration_seconds": payload.get("duration") or media_probe.get("duration_seconds"),
            "size_bytes": media_probe.get("size_bytes"),
            "has_audio": media_probe.get("has_audio", False),
            "local_path": relpath(media_destination, output_path.parent),
        },
        "top_comment": build_comment_snapshot((payload.get("comments") or [None])[0]),
    }

    output_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("post_url", help="Public Instagram post or reel URL")
    parser.add_argument("--output", required=True, help="Path to write snapshot.json")
    parser.add_argument(
        "--asset-dir",
        required=True,
        help="Directory that should receive the local avatar, poster frame, and primary media files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    create_snapshot(
        args.post_url,
        Path(args.output).expanduser().resolve(),
        Path(args.asset_dir).expanduser().resolve(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

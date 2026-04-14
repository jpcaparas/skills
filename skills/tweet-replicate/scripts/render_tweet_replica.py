#!/usr/bin/env python3
"""Render a frozen public X/Twitter status snapshot to MP4 and GIF."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fetch_tweet_snapshot import (
    create_snapshot,
    download_file,
    download_with_ytdlp,
    extract_status_id,
    probe_media,
    safe_extension,
)
from record_tweet_replica import record_html_to_webm


CANVAS_WIDTH = 594
CONTENT_WIDTH = 562
MEDIA_MAX_WIDTH = 506
MEDIA_MAX_HEIGHT = 606
QUOTE_MEDIA_MAX_WIDTH = 506
QUOTE_MEDIA_MAX_HEIGHT = 606
DEFAULT_SAVE_ROOT = "pieces"
DEFAULT_GIF_MAX_BYTES = 24 * 1024 * 1024
DEFAULT_CAPTURE_DEVICE_SCALE_FACTOR = 2
MP4_CRF = 14
MP4_PRESET = "slow"
GIF_PRESETS = [
    {"fps": 10, "width": 480, "colors": 96},
    {"fps": 8, "width": 420, "colors": 80},
    {"fps": 8, "width": 360, "colors": 64},
    {"fps": 6, "width": 320, "colors": 48},
    {"fps": 5, "width": 280, "colors": 40},
    {"fps": 4, "width": 240, "colors": 32},
    {"fps": 3, "width": 200, "colors": 24},
    {"fps": 2, "width": 160, "colors": 16},
]


def compact_count(value: int) -> str:
    if value < 1000:
        return str(value)
    if value < 1_000_000:
        scaled = value / 1000
        if scaled < 100:
            scaled = math.floor(scaled * 10) / 10
            text = f"{scaled:.1f}".rstrip("0").rstrip(".")
        else:
            text = str(int(round(scaled)))
        return f"{text}K"
    scaled = value / 1_000_000
    scaled = math.floor(scaled * 10) / 10
    text = f"{scaled:.1f}".rstrip("0").rstrip(".")
    return f"{text}M"


def format_timestamp(created_at: str | None, view_count: int) -> str:
    if not created_at:
        return f"{compact_count(view_count)} Views"
    dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y").astimezone()
    hour = dt.strftime("%I").lstrip("0") or "0"
    month = dt.strftime("%b")
    return f"{hour}:{dt:%M %p} · {month} {dt.day}, {dt.year} · {compact_count(view_count)} Views"


def compute_media_size_for_bounds(
    media: dict[str, Any] | None,
    max_width: int,
    max_height: int,
) -> tuple[int, int]:
    if not media:
        return 0, 0
    width = int(media.get("width") or max_width)
    height = int(media.get("height") or max_height)
    if width <= 0 or height <= 0:
        return max_width, max_height
    scale = min(max_width / width, max_height / height)
    return max(1, int(round(width * scale))), max(1, int(round(height * scale)))


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "tweet"


def default_piece_workdir(source: str, save_root: Path) -> Path:
    status_id = extract_status_id(source)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder_name = f"tweet-replicate-status-{status_id}-{timestamp}"
    return save_root / slugify(folder_name)


def normalize_output_path(path_text: str | None, default_path: Path) -> Path:
    if not path_text:
        return default_path
    output_path = Path(path_text).expanduser().resolve()
    if output_path.suffix:
        return output_path
    return output_path.with_suffix(".mp4")


def resolve_paths(args: argparse.Namespace, source_path: Path) -> tuple[Path, Path]:
    if args.workdir:
        workdir = Path(args.workdir).expanduser().resolve()
        output_path = normalize_output_path(args.output, workdir / "tweet-replica.mp4")
        return workdir, output_path

    if args.output:
        output_path = normalize_output_path(args.output, Path(args.output).expanduser().resolve())
        return output_path.with_suffix(""), output_path

    if source_path.exists() and source_path.suffix.lower() == ".json":
        workdir = source_path.resolve().parent
        return workdir, workdir / "tweet-replica.mp4"

    save_root = Path(args.save_root).expanduser().resolve() if args.save_root else (Path.cwd() / DEFAULT_SAVE_ROOT).resolve()
    workdir = default_piece_workdir(args.source, save_root)
    return workdir, workdir / "tweet-replica.mp4"


def load_snapshot(snapshot_path: Path) -> dict[str, Any]:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    base_dir = snapshot_path.parent

    def resolve_post_paths(post: dict[str, Any] | None) -> None:
        if not post:
            return
        author = post.get("author") or {}
        media = post.get("media")
        if author.get("local_avatar_path"):
            author["local_avatar_path"] = str((base_dir / author["local_avatar_path"]).resolve())
        if media and media.get("local_path"):
            media["local_path"] = str((base_dir / media["local_path"]).resolve())

    resolve_post_paths(snapshot)
    resolve_post_paths(snapshot.get("quote"))
    return snapshot


def ensure_local_assets(snapshot: dict[str, Any], snapshot_path: Path) -> dict[str, Any]:
    base_dir = snapshot_path.parent

    def ensure_post_assets(post: dict[str, Any] | None) -> None:
        if not post:
            return
        author = post.get("author") or {}
        if author.get("avatar_url") and author.get("local_avatar_path"):
            avatar_path = Path(author["local_avatar_path"])
            if not avatar_path.is_absolute():
                avatar_path = (base_dir / avatar_path).resolve()
            if not avatar_path.exists():
                download_file(author["avatar_url"], avatar_path)
            author["local_avatar_path"] = str(avatar_path)

        media = post.get("media")
        if media and media.get("local_path") and (media.get("remote_url") or media.get("source_status_url")):
            media_path = Path(media["local_path"])
            if not media_path.is_absolute():
                media_path = (base_dir / media_path).resolve()
            if not media_path.exists():
                restored_path = None
                if media.get("kind") in {"video", "gif"} and media.get("source_status_url"):
                    try:
                        restored_path = download_with_ytdlp(media["source_status_url"], media_path.parent, stem=media_path.stem)
                    except Exception:
                        restored_path = None
                if restored_path is None and media.get("remote_url"):
                    restored_path = media_path.with_suffix(safe_extension(media["remote_url"], media_path.suffix or ".bin"))
                    download_file(media["remote_url"], restored_path)
                if restored_path is not None:
                    media_path = restored_path.resolve()
            if media_path.exists():
                details = probe_media(media_path)
                media["local_path"] = str(media_path)
                media["width"] = media.get("width") or details.get("width")
                media["height"] = media.get("height") or details.get("height")
                media["duration_seconds"] = media.get("duration_seconds") or details.get("duration_seconds")
                media["size_bytes"] = details.get("size_bytes")
                media["has_audio"] = details.get("has_audio", False)

    ensure_post_assets(snapshot)
    ensure_post_assets(snapshot.get("quote"))
    return snapshot


def build_media_payload(
    media: dict[str, Any] | None,
    max_width: int,
    max_height: int,
) -> dict[str, Any] | None:
    if not media or not media.get("local_path"):
        return None
    media_local_path = Path(media["local_path"]).resolve()
    media_uri = media_local_path.as_uri()
    media_width, media_height = compute_media_size_for_bounds(media, max_width, max_height)
    return {
        "kind": media.get("kind"),
        "uri": media_uri,
        "width": media_width,
        "height": media_height,
    }


def format_relative_short(created_at: str | None, snapshot_created_at: str | None) -> str:
    if not created_at or not snapshot_created_at:
        return ""
    created_dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
    snapshot_dt = datetime.fromisoformat(snapshot_created_at)
    delta = snapshot_dt - created_dt.astimezone(snapshot_dt.tzinfo)
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 3600:
        minutes = max(seconds // 60, 1)
        return f"{minutes}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


def active_media_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    return snapshot.get("media") or (snapshot.get("quote") or {}).get("media")


def build_replica_payload(snapshot: dict[str, Any], still_duration_ms: int) -> dict[str, Any]:
    counts = snapshot.get("counts") or {}
    media = snapshot.get("media")
    quote = snapshot.get("quote")
    active_media = active_media_from_snapshot(snapshot)
    avatar_path = snapshot.get("author", {}).get("local_avatar_path")
    avatar_uri = Path(avatar_path).resolve().as_uri() if avatar_path else None
    duration_ms = still_duration_ms
    if active_media and active_media.get("kind") in {"video", "gif"}:
        duration_ms = int(round((active_media.get("duration_seconds") or 0) * 1000)) or still_duration_ms

    quote_payload = None
    if quote:
        quote_avatar_path = quote.get("author", {}).get("local_avatar_path")
        quote_avatar_uri = Path(quote_avatar_path).resolve().as_uri() if quote_avatar_path else None
        quote_payload = {
            "text": quote.get("text") or "",
            "author": {
                "name": quote.get("author", {}).get("name") or "",
                "handle": quote.get("author", {}).get("handle") or "",
                "verified": bool(quote.get("author", {}).get("verified")),
                "avatarUri": quote_avatar_uri,
            },
            "subline": f"@{quote.get('author', {}).get('handle') or ''} · {format_relative_short(quote.get('created_at'), snapshot.get('snapshot_created_at'))}".strip(),
            "media": build_media_payload(quote.get("media"), QUOTE_MEDIA_MAX_WIDTH, QUOTE_MEDIA_MAX_HEIGHT),
        }

    return {
        "canonicalUrl": snapshot.get("canonical_url"),
        "layout": {
            "canvasWidth": CANVAS_WIDTH,
            "contentWidth": CONTENT_WIDTH,
        },
        "post": {
            "text": snapshot.get("text") or "",
            "author": {
                "name": snapshot.get("author", {}).get("name") or "",
                "handle": snapshot.get("author", {}).get("handle") or "",
                "verified": bool(snapshot.get("author", {}).get("verified")),
                "avatarUri": avatar_uri,
            },
            "timestampLine": format_timestamp(snapshot.get("created_at"), int(counts.get("view_count") or 0)),
            "counts": {
                "reply": compact_count(int(counts.get("reply_count") or 0)),
                "repost": compact_count(int(counts.get("repost_count") or 0)),
                "like": compact_count(int(counts.get("like_count") or 0)),
                "bookmark": compact_count(int(counts.get("bookmark_count") or 0)),
            },
        },
        "media": build_media_payload(media, MEDIA_MAX_WIDTH, MEDIA_MAX_HEIGHT),
        "quote": quote_payload,
        "recordDurationMs": duration_ms,
    }


def render_html(template_path: Path, output_path: Path, payload: dict[str, Any]) -> None:
    template = template_path.read_text(encoding="utf-8")
    html = template.replace("__REPLICA_JSON__", json.dumps(payload, ensure_ascii=False))
    output_path.write_text(html, encoding="utf-8")


def transcode_to_mp4(recording_path: Path, output_path: Path, media: dict[str, Any] | None) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(recording_path),
        "-c:v",
        "libx264",
        "-preset",
        MP4_PRESET,
        "-crf",
        str(MP4_CRF),
        "-pix_fmt",
        "yuv420p",
    ]
    use_audio = bool(media and media.get("local_path") and media.get("kind") in {"video", "gif"} and media.get("has_audio"))
    if use_audio:
        command.extend(
            [
                "-i",
                str(Path(media["local_path"]).resolve()),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                "-shortest",
                str(output_path),
            ]
        )
    else:
        command.extend(
            [
                "-an",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )
    subprocess.run(command, check=True)


def render_gif_variant(source_video: Path, output_path: Path, fps: int, width: int, colors: int) -> int:
    palette_fd, palette_name = tempfile.mkstemp(prefix="tweet-replicate-palette-", suffix=".png")
    os.close(palette_fd)
    palette_path = Path(palette_name)
    palettegen_filter = (
        f"fps={fps},scale={width}:-2:flags=lanczos,"
        f"palettegen=max_colors={colors}:reserve_transparent=0:stats_mode=diff"
    )
    paletteuse_filter = (
        f"fps={fps},scale={width}:-2:flags=lanczos[x];"
        "[x][1:v]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle"
    )
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(source_video), "-vf", palettegen_filter, str(palette_path)],
            check=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source_video),
                "-i",
                str(palette_path),
                "-lavfi",
                paletteuse_filter,
                "-loop",
                "0",
                str(output_path),
            ],
            check=True,
        )
    finally:
        if palette_path.exists():
            palette_path.unlink()
    return output_path.stat().st_size


def create_gif_under_limit(source_video: Path, output_path: Path, max_bytes: int) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for preset in GIF_PRESETS:
        size_bytes = render_gif_variant(source_video, output_path, preset["fps"], preset["width"], preset["colors"])
        attempt = {**preset, "size_bytes": size_bytes}
        attempts.append(attempt)
        if size_bytes <= max_bytes:
            return {
                "path": str(output_path),
                "size_bytes": size_bytes,
                "max_bytes": max_bytes,
                "preset": preset,
                "attempts": attempts,
            }
    raise RuntimeError(
        f"Could not render a GIF under {max_bytes} bytes. "
        f"Last attempt was {attempts[-1]['size_bytes']} bytes with {attempts[-1]}."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        help="Public X/Twitter status URL or a previously saved snapshot.json path",
    )
    parser.add_argument(
        "--output",
        help="Output MP4 path. If omitted, save under ./pieces by default, or alongside the snapshot.json source.",
    )
    parser.add_argument(
        "--workdir",
        help="Directory for snapshot, local assets, rendered HTML, and WebM capture",
    )
    parser.add_argument(
        "--save-root",
        help="Root directory for auto-generated build folders when the source is a live status URL.",
    )
    parser.add_argument(
        "--still-duration-ms",
        type=int,
        default=4000,
        help="Recording duration for text-only or image-only posts",
    )
    parser.add_argument(
        "--tail-hold-ms",
        type=int,
        default=450,
        help="Extra hold after playback to avoid cutting the final frame",
    )
    parser.add_argument(
        "--gif-max-bytes",
        type=int,
        default=DEFAULT_GIF_MAX_BYTES,
        help="Hard byte ceiling for the generated GIF",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = Path(args.source).expanduser()
    workdir, output_path = resolve_paths(args, source_path)
    workdir.mkdir(parents=True, exist_ok=True)
    asset_dir = workdir / "assets"
    snapshot_path = workdir / "snapshot.json"

    if source_path.exists() and source_path.suffix.lower() == ".json":
        snapshot = ensure_local_assets(load_snapshot(source_path.resolve()), source_path.resolve())
        snapshot_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        snapshot = create_snapshot(args.source, snapshot_path, asset_dir)
        snapshot = ensure_local_assets(load_snapshot(snapshot_path), snapshot_path)
        snapshot_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    payload = build_replica_payload(snapshot, args.still_duration_ms)
    skill_root = Path(__file__).resolve().parent.parent
    template_path = skill_root / "templates" / "tweet_replica.html"
    html_path = workdir / "tweet-replica.html"
    render_html(template_path, html_path, payload)

    webm_path = workdir / "capture.webm"
    asyncio.run(
        record_html_to_webm(
            html_path,
            webm_path,
            CANVAS_WIDTH,
            args.tail_hold_ms,
            DEFAULT_CAPTURE_DEVICE_SCALE_FACTOR,
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    transcode_to_mp4(webm_path, output_path, active_media_from_snapshot(snapshot))

    gif_path = output_path.with_suffix(".gif")
    gif_result = create_gif_under_limit(output_path, gif_path, args.gif_max_bytes)
    mp4_probe = probe_media(output_path)
    gif_probe = probe_media(gif_path)
    gif_size_bytes = gif_probe.get("size_bytes") or gif_path.stat().st_size

    summary = {
        "output_mp4": str(output_path),
        "output_gif": str(gif_path),
        "workdir": str(workdir),
        "save_root": str(workdir.parent),
        "snapshot": str(snapshot_path),
        "html": str(html_path),
        "recording": str(webm_path),
        "mp4_duration_seconds": mp4_probe.get("duration_seconds"),
        "mp4_size_bytes": mp4_probe.get("size_bytes"),
        "gif_duration_seconds": gif_probe.get("duration_seconds"),
        "gif_size_bytes": gif_size_bytes,
        "gif_max_bytes": args.gif_max_bytes,
        "gif_preset": gif_result["preset"],
    }
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

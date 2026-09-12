#!/usr/bin/env python3
"""Render a frozen public Instagram post snapshot to MP4 and GIF."""

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

from fetch_instagram_snapshot import create_snapshot, download_file, extract_shortcode, probe_media
from record_instagram_replica import record_html_to_webm


CANVAS_WIDTH = 1492
PAGE_PADDING_X = 70
POST_MEDIA_MAX_WIDTH = 678
POST_MEDIA_MAX_HEIGHT = 1204
SIDEBAR_WIDTH = 674
DEFAULT_SAVE_ROOT = "pieces"
DEFAULT_GIF_MAX_BYTES = 24 * 1024 * 1024
GIF_PRESETS = [
    {"fps": 10, "width": 640, "colors": 96},
    {"fps": 8, "width": 560, "colors": 80},
    {"fps": 8, "width": 480, "colors": 72},
    {"fps": 6, "width": 420, "colors": 64},
    {"fps": 5, "width": 360, "colors": 48},
    {"fps": 4, "width": 320, "colors": 40},
    {"fps": 3, "width": 280, "colors": 32},
    {"fps": 2, "width": 240, "colors": 24},
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
    return slug or "instagram"


def default_piece_workdir(source: str, save_root: Path) -> Path:
    shortcode = extract_shortcode(source)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder_name = f"instagram-replicate-post-{shortcode}-{timestamp}"
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
        output_path = normalize_output_path(args.output, workdir / "instagram-replica.mp4")
        return workdir, output_path

    if args.output:
        output_path = normalize_output_path(args.output, Path(args.output).expanduser().resolve())
        return output_path.with_suffix(""), output_path

    if source_path.exists() and source_path.suffix.lower() == ".json":
        workdir = source_path.resolve().parent
        return workdir, workdir / "instagram-replica.mp4"

    save_root = Path(args.save_root).expanduser().resolve() if args.save_root else (Path.cwd() / DEFAULT_SAVE_ROOT).resolve()
    workdir = default_piece_workdir(args.source, save_root)
    return workdir, workdir / "instagram-replica.mp4"


def load_snapshot(snapshot_path: Path) -> dict[str, Any]:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    base_dir = snapshot_path.parent
    author = snapshot.get("author") or {}
    media = snapshot.get("media") or {}

    if author.get("local_avatar_path"):
        author["local_avatar_path"] = str((base_dir / author["local_avatar_path"]).resolve())
    if media.get("local_path"):
        media["local_path"] = str((base_dir / media["local_path"]).resolve())
    if media.get("poster_local_path"):
        media["poster_local_path"] = str((base_dir / media["poster_local_path"]).resolve())
    return snapshot


def ensure_local_assets(snapshot: dict[str, Any], snapshot_path: Path) -> dict[str, Any]:
    base_dir = snapshot_path.parent
    author = snapshot.get("author") or {}
    if author.get("avatar_url") and author.get("local_avatar_path"):
        avatar_path = Path(author["local_avatar_path"])
        if not avatar_path.is_absolute():
            avatar_path = (base_dir / avatar_path).resolve()
        if not avatar_path.exists():
            download_file(author["avatar_url"], avatar_path)
        author["local_avatar_path"] = str(avatar_path)

    media = snapshot.get("media") or {}
    if media.get("poster_url") and media.get("poster_local_path"):
        poster_path = Path(media["poster_local_path"])
        if not poster_path.is_absolute():
            poster_path = (base_dir / poster_path).resolve()
        if not poster_path.exists():
            download_file(media["poster_url"], poster_path)
        media["poster_local_path"] = str(poster_path)

    if media.get("remote_url") and media.get("local_path"):
        media_path = Path(media["local_path"])
        if not media_path.is_absolute():
            media_path = (base_dir / media_path).resolve()
        if media_path.exists():
            details = probe_media(media_path)
            media["local_path"] = str(media_path)
            media["width"] = media.get("width") or details.get("width")
            media["height"] = media.get("height") or details.get("height")
            media["duration_seconds"] = media.get("duration_seconds") or details.get("duration_seconds")
            media["size_bytes"] = details.get("size_bytes")
            media["has_audio"] = details.get("has_audio", False)
    return snapshot


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def format_relative_short(created_at: str | None, snapshot_created_at: str | None) -> str:
    created_dt = parse_iso_datetime(created_at)
    snapshot_dt = parse_iso_datetime(snapshot_created_at)
    if not created_dt or not snapshot_dt:
        return ""
    delta = snapshot_dt - created_dt.astimezone(snapshot_dt.tzinfo)
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 3600:
        return f"{max(seconds // 60, 1)}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    if seconds < 604800:
        return f"{seconds // 86400}d"
    return created_dt.strftime("%b %-d") if os.name != "nt" else created_dt.strftime("%b %#d")


def format_relative_long(created_at: str | None, snapshot_created_at: str | None) -> str:
    created_dt = parse_iso_datetime(created_at)
    snapshot_dt = parse_iso_datetime(snapshot_created_at)
    if not created_dt or not snapshot_dt:
        return ""
    delta = snapshot_dt - created_dt.astimezone(snapshot_dt.tzinfo)
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 3600:
        minutes = max(seconds // 60, 1)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if seconds < 604800:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"
    day = created_dt.day
    return f"{created_dt.strftime('%B')} {day}, {created_dt.year}"


def build_media_payload(media: dict[str, Any] | None) -> dict[str, Any] | None:
    if not media or not media.get("local_path"):
        return None
    media_local_path = Path(media["local_path"]).resolve()
    poster_path = media.get("poster_local_path")
    media_width, media_height = compute_media_size_for_bounds(media, POST_MEDIA_MAX_WIDTH, POST_MEDIA_MAX_HEIGHT)
    return {
        "kind": media.get("kind"),
        "uri": media_local_path.as_uri(),
        "posterUri": Path(poster_path).resolve().as_uri() if poster_path else None,
        "width": media_width,
        "height": media_height,
        "hasAudio": bool(media.get("has_audio")),
    }


def build_replica_payload(snapshot: dict[str, Any], still_duration_ms: int) -> dict[str, Any]:
    counts = snapshot.get("counts") or {}
    media = snapshot.get("media")
    active_media = media or {}
    avatar_path = snapshot.get("author", {}).get("local_avatar_path")
    avatar_uri = Path(avatar_path).resolve().as_uri() if avatar_path else None
    duration_ms = still_duration_ms
    if active_media and active_media.get("kind") == "video":
        duration_ms = int(round((active_media.get("duration_seconds") or 0) * 1000)) or still_duration_ms

    comment = snapshot.get("top_comment")
    media_payload = build_media_payload(media)
    return {
        "canonicalUrl": snapshot.get("canonical_url"),
        "layout": {
            "canvasWidth": CANVAS_WIDTH,
            "pagePaddingX": PAGE_PADDING_X,
            "mediaWidth": media_payload["width"] if media_payload else POST_MEDIA_MAX_WIDTH,
            "mediaHeight": media_payload["height"] if media_payload else POST_MEDIA_MAX_HEIGHT,
            "sidebarWidth": SIDEBAR_WIDTH,
        },
        "post": {
            "caption": snapshot.get("caption") or "",
            "audioLabel": snapshot.get("audio_label") or "Original audio",
            "author": {
                "name": snapshot.get("author", {}).get("name") or "",
                "handle": snapshot.get("author", {}).get("handle") or "",
                "verified": bool(snapshot.get("author", {}).get("verified")),
                "avatarUri": avatar_uri,
            },
            "counts": {
                "like": compact_count(int(counts.get("like_count") or 0)),
                "comment": compact_count(int(counts.get("comment_count") or 0)),
            },
            "timestampShort": format_relative_short(snapshot.get("created_at"), snapshot.get("snapshot_created_at")),
            "timestampLong": format_relative_long(snapshot.get("created_at"), snapshot.get("snapshot_created_at")),
            "comment": {
                "authorName": comment.get("author_name") or "",
                "authorHandle": comment.get("author_handle") or "",
                "text": comment.get("text") or "",
                "relative": format_relative_short(comment.get("created_at"), snapshot.get("snapshot_created_at")),
            }
            if comment
            else None,
            "media": media_payload,
            "recordDurationMs": duration_ms,
        },
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
    ]
    use_audio = bool(media and media.get("local_path") and media.get("kind") == "video" and media.get("has_audio"))
    if use_audio:
        command.extend(
            [
                "-i",
                str(Path(media["local_path"]).resolve()),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                "-shortest",
                str(output_path),
            ]
        )
    else:
        command.extend(
            [
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-an",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )
    subprocess.run(command, check=True)


def render_gif_variant(source_video: Path, output_path: Path, fps: int, width: int, colors: int) -> int:
    palette_fd, palette_name = tempfile.mkstemp(prefix="instagram-replicate-palette-", suffix=".png")
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
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source_video),
                "-vf",
                palettegen_filter,
                "-frames:v",
                "1",
                "-update",
                "1",
                str(palette_path),
            ],
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
        help="Public Instagram post/reel URL or a previously saved snapshot.json path",
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
        help="Root directory for auto-generated build folders when the source is a live Instagram URL.",
    )
    parser.add_argument(
        "--still-duration-ms",
        type=int,
        default=4000,
        help="Recording duration for image-only posts",
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
    template_path = skill_root / "templates" / "instagram_replica.html"
    html_path = workdir / "instagram-replica.html"
    render_html(template_path, html_path, payload)

    webm_path = workdir / "capture.webm"
    asyncio.run(record_html_to_webm(html_path, webm_path, CANVAS_WIDTH, args.tail_hold_ms))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    transcode_to_mp4(webm_path, output_path, snapshot.get("media"))

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

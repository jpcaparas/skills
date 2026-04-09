#!/usr/bin/env python3
"""Run live end-to-end checks against tweet-replicate."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_GIF_MAX_BYTES = 24 * 1024 * 1024


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=True)


def probe_duration_seconds(path: Path) -> float:
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nokey=1:noprint_wrappers=1",
            str(path),
        ]
    )
    return float(result.stdout.strip())


def verify_artifact(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else None,
    }


def run_probe(source: str, save_root: Path, cleanup: bool, gif_max_bytes: int) -> dict[str, Any]:
    script_path = Path(__file__).resolve().parent / "render_tweet_replica.py"
    command = [
        sys.executable,
        str(script_path),
        source,
        "--save-root",
        str(save_root),
        "--gif-max-bytes",
        str(gif_max_bytes),
    ]
    completed = run_command(command)
    summary = json.loads(completed.stdout)

    snapshot_path = Path(summary["snapshot"])
    workdir = Path(summary["workdir"])
    mp4_path = Path(summary["output_mp4"])
    gif_path = Path(summary["output_gif"])
    html_path = Path(summary["html"])
    webm_path = Path(summary["recording"])

    with snapshot_path.open("r", encoding="utf-8") as handle:
        snapshot = json.load(handle)

    result = {
        "source": source,
        "workdir": str(workdir),
        "snapshot_source_url": snapshot.get("source_url"),
        "artifacts": {
            "snapshot": verify_artifact(snapshot_path),
            "html": verify_artifact(html_path),
            "recording": verify_artifact(webm_path),
            "mp4": verify_artifact(mp4_path),
            "gif": verify_artifact(gif_path),
        },
        "mp4_duration_seconds": probe_duration_seconds(mp4_path),
        "gif_duration_seconds": probe_duration_seconds(gif_path),
        "gif_within_limit": gif_path.stat().st_size <= gif_max_bytes,
        "gif_limit_bytes": gif_max_bytes,
        "gif_preset": summary.get("gif_preset"),
    }

    if cleanup and workdir.exists():
        shutil.rmtree(workdir)
        result["cleaned_up"] = True
    else:
        result["cleaned_up"] = False

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", help="Public X/Twitter status URLs to test")
    parser.add_argument(
        "--save-root",
        required=True,
        help="Directory that should receive temporary build folders during the probe",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete each generated workdir after verification succeeds",
    )
    parser.add_argument(
        "--gif-max-bytes",
        type=int,
        default=DEFAULT_GIF_MAX_BYTES,
        help="Hard GIF size limit to enforce during the probe",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    save_root = Path(args.save_root).expanduser().resolve()
    save_root.mkdir(parents=True, exist_ok=True)
    results = [
        run_probe(source, save_root, cleanup=args.cleanup, gif_max_bytes=args.gif_max_bytes)
        for source in args.sources
    ]
    payload = {
        "probe_count": len(results),
        "all_gifs_within_limit": all(item["gif_within_limit"] for item in results),
        "results": results,
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

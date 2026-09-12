#!/usr/bin/env python3
"""
Fetch the official isitagentready.com scan JSON for a deployed site.

Usage:
    python3 scripts/scan_site.py --url https://example.com
    python3 scripts/scan_site.py --url https://example.com --output ./scan-results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib import error, request


SCAN_URL = "https://isitagentready.com/api/scan"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch the official isitagentready.com scan JSON for a deployed URL."
    )
    parser.add_argument(
        "--url",
        required=True,
        help="HTTP(S) URL to scan.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON file path to write the full scan response.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds for the HTTP request. Default: 120.",
    )
    return parser.parse_args()


def validate_url(url: str) -> None:
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")


def fetch_scan(url: str, timeout: int) -> dict:
    payload = json.dumps({"url": url}).encode("utf-8")
    req = request.Request(
        SCAN_URL,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "isitagentready-skill/1.0 (+https://isitagentready.com/)",
        },
    )
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    args = parse_args()
    try:
        validate_url(args.url)
        data = fetch_scan(args.url, args.timeout)
    except (ValueError, error.HTTPError, error.URLError, TimeoutError) as exc:
        print(f"scan_site.py error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        summary = {
            "url": data.get("url", args.url),
            "level": data.get("level"),
            "levelName": data.get("levelName"),
            "output": str(output_path),
        }
        print(json.dumps(summary, indent=2))
        return 0

    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

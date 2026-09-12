#!/usr/bin/env python3
"""Record a prepared local Instagram replica HTML page to WebM with Playwright."""

from __future__ import annotations

import argparse
import asyncio
import shutil
import tempfile
from pathlib import Path

from playwright.async_api import async_playwright


async def measure_page(playwright, html_path: Path, width: int) -> tuple[int, int]:
    browser = await playwright.chromium.launch(
        headless=True,
        args=["--autoplay-policy=no-user-gesture-required"],
    )
    page = await browser.new_page(viewport={"width": width, "height": 1600})
    await page.goto(html_path.as_uri(), wait_until="load")
    await page.wait_for_function("window.__replicaReady === true")
    height = await page.evaluate(
        """
        () => {
          const root = document.querySelector('.instagram-root');
          if (root) {
            return Math.ceil(root.getBoundingClientRect().height);
          }
          return Math.ceil(document.documentElement.scrollHeight);
        }
        """
    )
    duration_ms = await page.evaluate(
        "window.__getRecordDurationMs ? window.__getRecordDurationMs() : 4000"
    )
    await browser.close()
    return int(height), int(duration_ms)


async def record_html_to_webm(html_path: Path, output_path: Path, width: int, tail_hold_ms: int) -> Path:
    async with async_playwright() as playwright:
        height, duration_ms = await measure_page(playwright, html_path, width)
        record_dir = Path(tempfile.mkdtemp(prefix="instagram-replicate-record-"))
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--autoplay-policy=no-user-gesture-required"],
        )
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=str(record_dir),
            record_video_size={"width": width, "height": height},
        )
        page = await context.new_page()
        await page.goto(html_path.as_uri(), wait_until="load")
        await page.wait_for_function("window.__replicaReady === true")
        await page.evaluate("window.__startPlayback && window.__startPlayback()")
        await page.wait_for_timeout(duration_ms + tail_hold_ms)
        video = page.video
        await context.close()
        await browser.close()

        recorded_path = None
        if video is not None:
            recorded_path = Path(await video.path())
        if recorded_path is None or not recorded_path.exists():
            candidates = sorted(record_dir.glob("*.webm"))
            if not candidates:
                raise RuntimeError("Playwright recording completed without a WebM output")
            recorded_path = candidates[0]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(recorded_path, output_path)
        return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html_path", help="Prepared local HTML file")
    parser.add_argument("output_path", help="Output WebM path")
    parser.add_argument("--width", type=int, default=1492, help="Viewport width in pixels")
    parser.add_argument(
        "--tail-hold-ms",
        type=int,
        default=450,
        help="Extra hold after playback to avoid truncating the final frame",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    asyncio.run(
        record_html_to_webm(
            Path(args.html_path).resolve(),
            Path(args.output_path).resolve(),
            args.width,
            args.tail_hold_ms,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Rasterize an SVG to a 500x500 PNG with 16px padding on a white background.

Usage:
    python3 rasterize.py <input.svg> <output.png>

Dependencies:
    rsvg-convert (from librsvg). Install with:
      macOS:  brew install librsvg
      Debian: apt install librsvg2-bin
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile


CANVAS = 500
PADDING = 16  # 1em on a 16px base
INNER = CANVAS - 2 * PADDING  # 468


def die(msg: str, code: int = 1) -> None:
    print(f"rasterize: {msg}", file=sys.stderr)
    sys.exit(code)


def main() -> None:
    if len(sys.argv) != 3:
        die(f"usage: {os.path.basename(sys.argv[0])} <input.svg> <output.png>", 2)

    input_svg = sys.argv[1]
    output_png = sys.argv[2]

    if not os.path.isfile(input_svg):
        die(f"input SVG not found: {input_svg}")

    if shutil.which("rsvg-convert") is None:
        die(
            "rsvg-convert not found on PATH. Install librsvg:\n"
            "  macOS:  brew install librsvg\n"
            "  Debian: apt install librsvg2-bin"
        )

    with open(input_svg, "r", encoding="utf-8") as f:
        svg = f.read()

    # Extract viewBox, falling back to width/height attributes
    vb = re.search(r'viewBox=["\']([^"\']+)["\']', svg)
    if vb:
        viewbox = vb.group(1).strip()
    else:
        w = re.search(r'\bwidth=["\']?([\d.]+)', svg)
        h = re.search(r'\bheight=["\']?([\d.]+)', svg)
        viewbox = f"0 0 {w.group(1) if w else 100} {h.group(1) if h else 100}"

    # Extract everything inside the root <svg> tag
    inner = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.DOTALL)
    content = inner.group(1) if inner else svg

    wrapper = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink"\n'
        f'     width="{CANVAS}" height="{CANVAS}" '
        f'viewBox="0 0 {CANVAS} {CANVAS}">\n'
        f'  <rect width="{CANVAS}" height="{CANVAS}" fill="white"/>\n'
        f'  <svg x="{PADDING}" y="{PADDING}" '
        f'width="{INNER}" height="{INNER}" viewBox="{viewbox}">\n'
        f"{content}\n"
        f"  </svg>\n"
        f"</svg>\n"
    )

    fd, tmp = tempfile.mkstemp(suffix=".svg")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(wrapper)
        try:
            subprocess.run(
                [
                    "rsvg-convert",
                    "-w",
                    str(CANVAS),
                    "-h",
                    str(CANVAS),
                    "-o",
                    output_png,
                    tmp,
                ],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            die(f"rsvg-convert failed with exit code {e.returncode}")
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

    if not os.path.isfile(output_png):
        die(f"expected output file was not produced: {output_png}")

    size = os.path.getsize(output_png)
    print(f"OK {size} bytes -> {output_png}")


if __name__ == "__main__":
    main()

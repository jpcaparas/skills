#!/usr/bin/env python3
"""Generate README skill-card prompts and optional Nano Banana raster images."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


CARD_FILENAME = "skill-card.png"
PROMPT_FILENAME = "skill-card.prompt.md"
CARD_WIDTH = "640"
FINAL_WIDTH = 1024
FINAL_HEIGHT = 576
DEFAULT_MODEL = "gemini-3.1-flash-image-preview"
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_IMAGE_SIZE = "1K"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
NO_TEXT_RULE = (
    "No visible text, no letters, no numbers, no typography, no captions, "
    "no labels, no logos, no watermarks, no pseudo-text, no glyph-like marks, "
    "no UI copy, no code characters, no punctuation, no checkmarks, no question marks."
)

SKILL_SCENES = {
    "audify": "headphones catching flowing sound ribbons, waveform crystals, and a small studio mixer made of blank blocks",
    "azure-devops-create-work-item": "a quest-token forge where a hammer stamps a blank glowing slab into a task gem",
    "azure-devops-wiki-markdown": "a knowledge temple linking clean geometric blocks through glowing connector paths",
    "better-writing": "a quill-shaped tool smoothing a jagged ribbon into a clean luminous ribbon",
    "client-report-from-commits": "commit stones merging into a polished crystal stack for a stakeholder path",
    "eli12": "a lantern revealing a simple route through a tangled brass machine",
    "google-search-ai-optimization": "a search tower sending clear signals to crawler fireflies and answer crystals",
    "implicit-token-savings": "a compact token backpack moving through a narrow efficient corridor",
    "instagram-replicate": "a camera portal rebuilding a scene into film reels, snapshot tiles, and local asset crates",
    "interface-design-taste": "a refined workbench arranging blank layout panels, color swatches, and spacing rails",
    "isitagentready": "a checkpoint scanner testing a website gate with robot-readable path beacons",
    "linkedin-speak": "a megaphone transforming a small plain block into an overbright beam of geometric confetti",
    "markdown-new": "a cloud portal turning raw fragments into neatly stacked blank content blocks",
    "nanobanana-infographic": "abstract chart-like towers, simple icon gems, and one bright banana-shaped spark",
    "oneshot-websites": "tiny blank world portals spawning different complete website landscapes",
    "reading-notes": "a reading desk collecting bookmarks, highlight bars, and task gems around a glowing source",
    "repo-intent-documenter": "a compass room connecting repository clue gems into a clear route line",
    "repository-readme-writer": "a project book shrine assembled from setup tools, blank blocks, and guide rails",
    "ripgrep": "a magnifying beam racing through file shelves and lighting up matching pixels",
    "scaffold-cc-hooks": "a Claude hook switchboard with event levers connected to reusable script cartridges",
    "scaffold-codex-hooks": "a Codex hook switchboard with event levers connected to reusable script cartridges",
    "scaffold-github-cloud-agent-environment": "a cloud runner factory wiring setup pipes into a safe agent workspace",
    "scaffold-opencode-hooks": "an OpenCode plugin switchboard with lifecycle levers connected to reusable script cartridges",
    "secure-ai-agent-coding": "a guarded agent workbench behind shields, permission gates, and safe tool lanes",
    "seo-analysis": "a crawl-path garden where sitemap nodes glow under search spotlights",
    "skill-creator-advanced": "a skill forge crafting a reusable instruction cartridge from blank parts and test gems",
    "synthetic-search": "a zero-retention radar scanning the web through clean privacy lanes",
    "tarsier": "a tiny bicycle courier carrying an art packet through a pixel side-scroller lane",
    "temporal-awareness": "a numeral-free clock tower aligning blank date blocks and live verification beacons",
    "travel-plan-spreadsheet-generator": "a travel desk arranging route tiles, luggage, blank tickets, and grid gems",
    "tweet-replicate": "a social portal frame being rebuilt into a local video reel, snapshot tile, and asset crate",
    "zoom-out": "a camera lifting above a code city to reveal modules, routes, and call paths",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root. Default: current directory.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model ID. Default: {DEFAULT_MODEL}")
    parser.add_argument("--aspect-ratio", default=DEFAULT_ASPECT_RATIO, help="Gemini image aspect ratio.")
    parser.add_argument("--image-size", default=DEFAULT_IMAGE_SIZE, help="Gemini image size.")
    parser.add_argument("--max-concurrency", type=int, default=4, help="Concurrent render jobs. Default: 4.")
    parser.add_argument("--passes", type=int, default=1, help="Render attempts per skill. Default: 1.")
    parser.add_argument("--force", action="store_true", help="Regenerate existing PNG files.")
    parser.add_argument("--prompts-only", action="store_true", help="Only write prompt files and README blocks.")
    parser.add_argument(
        "--normalize-only",
        action="store_true",
        help="Normalize existing PNG cards with ImageMagick without calling Gemini.",
    )
    parser.add_argument(
        "--output-dir",
        default="/tmp/skills-nanobanana-art",
        help="Directory for non-committed API request and response artifacts.",
    )
    return parser.parse_args()


def skill_names(skills_root: Path) -> list[str]:
    return sorted(path.parent.name for path in skills_root.glob("*/SKILL.md") if path.is_file())


def prompt_for_skill(name: str) -> str:
    scene = SKILL_SCENES[name]
    return f"""Nano Banana 2 image generation prompt for the `{name}` README skill badge.

Create a polished rectangular raster badge for a GitHub README.
Aspect ratio: 16:9.
Style: consistent side-scrolling 16-bit pixel game art, crisp pixel edges, low-noise, premium editorial composition, layered parallax background, simple geometric props, restrained detail.
Subject: {scene}.
Composition: one central readable illustration, a few supporting environmental elements, generous negative space, no crowded UI, no poster collage, no photorealism, no mockup frame.
Forbidden objects unless unavoidable: pages, documents, signs, posters, terminal windows, dashboard windows, browser windows, charts with axes, speech bubbles, calendars with grids, spreadsheets, tickets with markings, maps with markings, and social media post mockups.
Blank-surface rule: any paper, book, ticket, screen, terminal, dashboard, chart, browser, sign, speech bubble, social post, calendar, spreadsheet, map, or interface surface must be visually blank or represented only by solid unlabeled rectangles, bars, dots, connectors, and simple icons. Do not draw interior strokes that resemble writing.
Palette: deep midnight navy background, cool teal and blue shadows, one warm amber accent, limited saturated highlights, cohesive with the rest of a 32-card skill collection.
Lighting: soft game-like glow, clear silhouette separation, no blur, no grain, no lens effects.
{NO_TEXT_RULE}
Return only the image.
"""


def readme_image_block(name: str) -> str:
    return (
        '<p align="center">\n'
        f'  <img src="skills/{name}/{CARD_FILENAME}" '
        f'alt="16-bit side-scrolling pixel art badge for {name}" '
        f'width="{CARD_WIDTH}">\n'
        '</p>\n\n'
    )


def update_readme_cards(readme_path: Path, names: list[str]) -> None:
    readme = readme_path.read_text(encoding="utf-8")
    block_pattern = re.compile(
        r'(?:<p align="center">\n'
        r'  <img src="skills/[^"]+/skill-card\.(?:svg|png)" '
        r'alt="16-bit side-scrolling pixel art badge for [^"]+" '
        r'width="\d+">\n'
        r'</p>\n\n)?'
        r'(### `([^`]+)`)',
        re.MULTILINE,
    )

    def replace(match: re.Match[str]) -> str:
        name = match.group(2)
        if name not in names:
            return match.group(0)
        return readme_image_block(name) + match.group(1)

    updated = block_pattern.sub(replace, readme)
    readme_path.write_text(updated, encoding="utf-8")


def build_request_body(prompt: str, aspect_ratio: str, image_size: str) -> dict:
    return {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": image_size,
            },
        },
    }


def run_request(model: str, request_body: dict, api_key: str) -> dict:
    request = urllib.request.Request(
        url=API_URL.format(model=model),
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            "User-Agent": "skills-readme-nanobanana-art/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def first_inline_image(payload: dict) -> tuple[str, bytes] | None:
    candidate = ((payload.get("candidates") or [{}])[0]) if payload else {}
    parts = ((candidate.get("content") or {}).get("parts") or [])
    for part in parts:
        inline_data = part.get("inlineData") or part.get("inline_data")
        if not inline_data:
            continue
        data = inline_data.get("data")
        if not data:
            continue
        mime_type = inline_data.get("mimeType") or inline_data.get("mime_type") or "application/octet-stream"
        return mime_type, base64.b64decode(data)
    return None


def image_magick_binary() -> str:
    binary = shutil.which("magick")
    if binary:
        return binary
    raise RuntimeError("ImageMagick `magick` is required to normalize generated skill-card PNGs.")


def normalize_png(source_path: Path, target_path: Path) -> None:
    normalized_path = target_path.with_suffix(".normalized.png")
    subprocess.run(
        [
            image_magick_binary(),
            str(source_path),
            "-strip",
            "-filter",
            "Lanczos",
            "-resize",
            f"{FINAL_WIDTH}x{FINAL_HEIGHT}!",
            "-define",
            "png:compression-level=9",
            str(normalized_path),
        ],
        check=True,
    )
    normalized_path.replace(target_path)


def normalize_to_png(source_path: Path, mime_type: str, payload: bytes, target_path: Path) -> None:
    ext = mimetypes.guess_extension(mime_type) or ".bin"
    source_path = source_path.with_suffix(ext)
    source_path.write_bytes(payload)

    normalize_png(source_path, target_path)


def normalize_existing_cards(repo_root: Path, names: list[str]) -> list[dict]:
    results: list[dict] = []
    for name in names:
        target_path = repo_root / "skills" / name / CARD_FILENAME
        if not target_path.is_file():
            results.append({"skill": name, "status": "missing", "image": str(target_path)})
            continue
        normalize_png(target_path, target_path)
        results.append({"skill": name, "status": "normalized", "image": str(target_path)})
    return results


def render_skill(
    *,
    repo_root: Path,
    output_root: Path,
    name: str,
    prompt: str,
    model: str,
    aspect_ratio: str,
    image_size: str,
    passes: int,
    force: bool,
    api_key: str,
) -> dict:
    target_path = repo_root / "skills" / name / CARD_FILENAME
    if target_path.is_file() and not force:
        normalize_png(target_path, target_path)
        return {"skill": name, "status": "normalized", "image": str(target_path)}

    skill_output = output_root / name
    skill_output.mkdir(parents=True, exist_ok=True)
    last_error = ""
    for pass_index in range(1, max(1, passes) + 1):
        request_body = build_request_body(prompt, aspect_ratio, image_size)
        request_path = skill_output / f"request-{pass_index:02d}.json"
        request_path.write_text(json.dumps(request_body, indent=2) + "\n", encoding="utf-8")

        try:
            payload = run_request(model, request_body, api_key)
            response_path = skill_output / f"response-{pass_index:02d}.json"
            response_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            image = first_inline_image(payload)
            if image is None:
                last_error = "response did not contain inline image data"
                continue
            mime_type, data = image
            normalize_to_png(skill_output / f"returned-{pass_index:02d}", mime_type, data, target_path)
            return {
                "skill": name,
                "status": "rendered",
                "image": str(target_path),
                "mime_type": mime_type,
                "request_file": str(request_path),
                "response_file": str(response_path),
            }
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            error_path = skill_output / f"response-{pass_index:02d}.error.txt"
            error_path.write_text(body, encoding="utf-8")
            last_error = f"HTTP {exc.code}; see {error_path}"
        except Exception as exc:  # pragma: no cover - defensive network/tooling boundary
            last_error = str(exc)

    return {"skill": name, "status": "error", "error": last_error}


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    skills_root = repo_root / "skills"
    names = skill_names(skills_root)
    missing = sorted(set(names) - set(SKILL_SCENES))
    if missing:
        print(f"Missing skill-art scene descriptions: {', '.join(missing)}", file=sys.stderr)
        return 2

    for name in names:
        skill_dir = skills_root / name
        (skill_dir / PROMPT_FILENAME).write_text(prompt_for_skill(name), encoding="utf-8")

    update_readme_cards(repo_root / "README.md", names)

    if args.prompts_only:
        print(f"Wrote {len(names)} skill-card prompts and updated README.md.")
        return 0

    if args.normalize_only:
        results = normalize_existing_cards(repo_root, names)
        for result in results:
            print(f"{result['skill']}: {result['status']}")
        failures = [result for result in results if result["status"] == "missing"]
        if failures:
            print(f"Missing {len(failures)} skill-card PNG(s); render them before normalizing.", file=sys.stderr)
            return 2
        print(f"Normalized {len(results)} existing Nano Banana skill-card PNGs.")
        return 0

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("GEMINI_API_KEY is required to render Nano Banana skill-card PNGs.", file=sys.stderr)
        return 2

    output_root = Path(args.output_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    started = time.time()
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_concurrency)) as pool:
        futures = [
            pool.submit(
                render_skill,
                repo_root=repo_root,
                output_root=output_root,
                name=name,
                prompt=prompt_for_skill(name),
                model=args.model,
                aspect_ratio=args.aspect_ratio,
                image_size=args.image_size,
                passes=args.passes,
                force=args.force,
                api_key=api_key,
            )
            for name in names
        ]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{result['skill']}: {result['status']}")

    results.sort(key=lambda item: item["skill"])
    manifest = {
        "model": args.model,
        "aspect_ratio": args.aspect_ratio,
        "image_size": args.image_size,
        "duration_seconds": round(time.time() - started, 3),
        "results": results,
    }
    (output_root / "batch-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    failures = [result for result in results if result["status"] == "error"]
    if failures:
        print(f"Failed to render {len(failures)} skill card(s). See {output_root / 'batch-manifest.json'}.", file=sys.stderr)
        return 2

    print(f"Rendered or confirmed {len(results)} Nano Banana skill-card PNGs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

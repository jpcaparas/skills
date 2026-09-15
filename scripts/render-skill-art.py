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
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from skill_catalog import Skill, discover_skills

CARD_FILENAME = "skill-card.png"
PROMPT_FILENAME = "skill-card.prompt.md"
CARD_WIDTH = "480"
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
    "adhd-friendly": "a focused pathway where scattered task fragments converge through a calm priority gate into one bright next-step tile, with completed progress gems behind and optional paths parked nearby",
    "adversarial-test-sweep": "a testing gauntlet where bug-shaped hazard sprites, boundary gates, race lanes, fault sparks, and resource barriers confront a shielded formation of distinct test gems",
    "azure-devops-create-work-item": "a quest-token forge where a hammer stamps a blank glowing slab into a task gem",
    "azure-devops-wiki-markdown": "a knowledge temple linking clean geometric blocks through glowing connector paths",
    "better-chezmoi": "a dotfile workbench separating a source vault and home directory through a glowing preview gate, with template gems, a shielded secret capsule, and reversible sync rails",
    "better-writing": "a quill-shaped tool smoothing a jagged ribbon into a clean luminous ribbon",
    "bootstrap-agents-md": "a repository observatory distilling many project signal paths into one durable guidance beacon with a smaller companion beacon linked beside it",
    "client-report-from-commits": "commit stones merging into a polished crystal stack for a stakeholder path",
    "devils-advocate": "two opposing debate champions facing each other across a glowing balance arena, with one mirrored argument shield, pressure-test sparks, and a central evidence gem",
    "eli12": "a lantern revealing a simple route through a tangled brass machine",
    "google-search-ai-optimization": "a search tower sending clear signals to crawler fireflies and answer crystals",
    "heuristic-to-deterministic": "a workshop converting fuzzy clue clouds into locked gears, check rails, and repeatable test gems",
    "implicit-token-savings": "a compact token backpack moving through a narrow efficient corridor",
    "interface-design-taste": "a refined workbench arranging blank layout panels, color swatches, and spacing rails",
    "isitagentready": "a checkpoint scanner testing a website gate with robot-readable path beacons",
    "maintainable-code": "a code workshop arranging clear modular blocks, typed connector rails, test gems, and simple responsibility lanes",
    "maintainable-tests": "a testing garden of clear scenario tiles, boundary markers, legacy anchors, and readable assertion gems",
    "markdown-new": "a cloud portal turning raw fragments into neatly stacked blank content blocks",
    "nanobanana-infographic": "abstract chart-like towers, simple icon gems, and one bright banana-shaped spark",
    "oneshot-timeline": "a winding trail of evenly separated story beacons untangling a knot of pathways, with small framed silhouette gems alternating beside the trail and a warm lantern illuminating the next moment",
    "oneshot-websites": "tiny blank world portals spawning different complete website landscapes",
    "product-question": "a side-scrolling path of user-flow tiles and glowing inquiry gems leading toward a code city skyline, with simple unlabeled connectors and no screens or papers",
    "repository-readme-writer": "a project book shrine assembled from setup tools, blank blocks, and guide rails",
    "ripgrep": "a magnifying beam racing through file shelves and lighting up matching pixels",
    "scaffold-hooks": "a universal agent hook switchboard routing four harness cables into one shared script rail",
    "scaffold-github-cloud-agent-environment": "a cloud runner factory wiring setup pipes into a safe agent workspace",
    "secure-ai-agent-coding": "a guarded agent workbench behind shields, permission gates, and safe tool lanes",
    "seo-analysis": "a crawl-path garden where sitemap nodes glow under search spotlights",
    "skill-creator-advanced": "a skill forge crafting a reusable instruction cartridge from blank parts and test gems",
    "simplified-technical-english": "a precision language workshop where tangled instruction paths pass through a calibration gate into short clear action rails, with terminology gems, a hazard shield, and separate procedure and description lanes",
    "strong-types": "a foundry casting loose shape-shifting blobs into crisp interlocking typed blocks along guarded connector rails with shield gates rejecting misfit pieces",
    "synthetic-search": "a zero-retention radar scanning the web through clean privacy lanes",
    "temporal-awareness": "a numeral-free clock tower aligning blank date blocks and live verification beacons",
    "to-diagram": "a tangled maze of process rails entering a clarity prism and emerging as one clean branching flow with phase gates and an image crystal",
    "travel-plan-spreadsheet-generator": "a travel desk arranging route tiles, luggage, blank tickets, and grid gems",
    "zoom-out": "a camera lifting above a code city to reveal modules, routes, and call paths",
    "youtube-transcript-dossier": "a play portal unfolding a ribbon of caption gems into a tidy dossier with bookmark rails and topic tiles",
}


def prepare_output_root(output_dir: str | None) -> Path:
    """Return a safe directory for non-committed API artifacts.

    With no explicit directory, create a fresh private mkdtemp directory so no
    other local user can pre-create it. With an explicit directory, refuse a
    symlink or a directory owned by another user: a predictable shared path
    such as the old /tmp default could otherwise be planted to redirect writes.
    """

    if output_dir is None:
        return Path(tempfile.mkdtemp(prefix="skills-nanobanana-art-"))

    output_root = Path(output_dir).expanduser()
    if output_root.is_symlink():
        raise SystemExit(f"--output-dir must not be a symlink: {output_root}")
    if output_root.exists() and not output_root.is_dir():
        raise SystemExit(f"--output-dir exists and is not a directory: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    stat = output_root.stat()
    if stat.st_uid != os.getuid():
        raise SystemExit(f"--output-dir is not owned by the current user: {output_root}")
    if stat.st_mode & 0o077:
        output_root.chmod(0o700)
    return output_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root. Default: current directory.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model ID. Default: {DEFAULT_MODEL}")
    parser.add_argument("--aspect-ratio", default=DEFAULT_ASPECT_RATIO, help="Gemini image aspect ratio.")
    parser.add_argument("--image-size", default=DEFAULT_IMAGE_SIZE, help="Gemini image size.")
    parser.add_argument("--max-concurrency", type=int, default=4, help="Concurrent render jobs. Default: 4.")
    parser.add_argument("--passes", type=int, default=1, help="Render attempts per skill. Default: 1.")
    parser.add_argument("--skill", action="append", default=[], help="Render only this skill. Repeat for multiple skills.")
    parser.add_argument("--force", action="store_true", help="Regenerate existing PNG files.")
    parser.add_argument("--prompts-only", action="store_true", help="Only write prompt files and README blocks.")
    parser.add_argument(
        "--normalize-only",
        action="store_true",
        help="Normalize existing PNG cards with ImageMagick without calling Gemini.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Directory for non-committed API request and response artifacts. "
            "Default: a fresh private tempfile.mkdtemp directory, so no other local "
            "user can pre-create or redirect it."
        ),
    )
    return parser.parse_args()


def prompt_for_skill(name: str) -> str:
    scene = SKILL_SCENES[name]
    blank_surface_subjects = (
        "paper, book, ticket, screen, terminal, dashboard, chart, browser, sign, "
        "speech bubble, social post, calendar, spreadsheet, map, or interface surface"
    )
    return f"""Nano Banana 2 image generation prompt for the `{name}` README skill badge.

Create a polished rectangular raster badge for a GitHub README.
Aspect ratio: 16:9.
Style: consistent side-scrolling 16-bit pixel game art, crisp pixel edges, low-noise, premium editorial composition, layered parallax background, simple geometric props, restrained detail.
Subject: {scene}.
Composition: one central readable illustration, a few supporting environmental elements, generous negative space, no crowded UI, no poster collage, no photorealism, no mockup frame.
Forbidden objects unless unavoidable: pages, documents, signs, posters, terminal windows, dashboard windows, browser windows, charts with axes, speech bubbles, calendars with grids, spreadsheets, tickets with markings, maps with markings, and social media post mockups.
Blank-surface rule: any {blank_surface_subjects} must be visually blank or represented only by solid unlabeled rectangles, bars, dots, connectors, and simple icons. Do not draw interior strokes that resemble writing.
Palette: deep midnight navy background, cool teal and blue shadows, one warm amber accent, limited saturated highlights, cohesive with the rest of the README skill-card collection.
Lighting: soft game-like glow, clear silhouette separation, no blur, no grain, no lens effects.
{NO_TEXT_RULE}
Return only the image.
"""


def readme_image_block(skill: Skill) -> str:
    return (
        '<p align="center">\n'
        f'  <img src="{skill.repo_path}/{CARD_FILENAME}" '
        f'alt="16-bit side-scrolling pixel art badge for {skill.name}" '
        f'width="{CARD_WIDTH}">\n'
        '</p>\n\n'
    )


def update_readme_cards(readme_path: Path, skills: list[Skill]) -> None:
    readme = readme_path.read_text(encoding="utf-8")
    by_name = {skill.name: skill for skill in skills}
    card_block_pattern = re.compile(
        r'<p align="center">\n'
        r'  <img src="skills/[^"]+/skill-card\.(?:svg|png)" '
        r'alt="16-bit side-scrolling pixel art badge for [^"]+" '
        r'width="\d+">\n'
        r'</p>\n\n',
        re.MULTILINE,
    )
    readme = card_block_pattern.sub("", readme)

    section_pattern = re.compile(
        r"(#### `([^`]+)`\n\n"
        r"`npx skills add jpcaparas/skills --skill ([^`]+)`\n\n)",
        re.MULTILINE,
    )

    def replace(match: re.Match[str]) -> str:
        name = match.group(2)
        command_name = match.group(3)
        if name not in by_name or command_name != name:
            return match.group(0)
        return match.group(1) + readme_image_block(by_name[name])

    updated = section_pattern.sub(replace, readme)
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


def normalize_existing_cards(skills: list[Skill]) -> list[dict]:
    results: list[dict] = []
    for skill in skills:
        name = skill.name
        target_path = skill.directory / CARD_FILENAME
        if not target_path.is_file():
            results.append({"skill": name, "status": "missing", "image": str(target_path)})
            continue
        normalize_png(target_path, target_path)
        results.append({"skill": name, "status": "normalized", "image": str(target_path)})
    return results


def render_skill(
    *,
    skill: Skill,
    output_root: Path,
    prompt: str,
    model: str,
    aspect_ratio: str,
    image_size: str,
    passes: int,
    force: bool,
    api_key: str,
) -> dict:
    name = skill.name
    target_path = skill.directory / CARD_FILENAME
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
    try:
        skills = discover_skills(skills_root)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    by_name = {skill.name: skill for skill in skills}
    all_names = sorted(by_name)
    requested_names = sorted(set(args.skill))
    unknown = sorted(set(requested_names) - set(all_names))
    if unknown:
        print(f"Unknown skill name(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    names = requested_names if requested_names else all_names
    missing = sorted(set(all_names) - set(SKILL_SCENES))
    if missing:
        print(f"Missing skill-art scene descriptions: {', '.join(missing)}", file=sys.stderr)
        return 2

    for name in names:
        skill_dir = by_name[name].directory
        (skill_dir / PROMPT_FILENAME).write_text(prompt_for_skill(name), encoding="utf-8")

    update_readme_cards(repo_root / "README.md", skills)

    if args.prompts_only:
        print(f"Wrote {len(names)} skill-card prompts and updated README.md.")
        return 0

    if args.normalize_only:
        results = normalize_existing_cards([by_name[name] for name in names])
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

    output_root = prepare_output_root(args.output_dir)
    started = time.time()
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_concurrency)) as pool:
        futures = [
            pool.submit(
                render_skill,
                skill=by_name[name],
                output_root=output_root,
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

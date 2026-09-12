#!/usr/bin/env python3
"""Run a live Gemini image-generation probe and save the outputs locally."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_MODEL = "gemini-3.1-flash-image-preview"
DEFAULT_IMAGE_SIZE = "1K"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Submit a text prompt to Gemini image generation and save the raw "
            "request, response, and decoded image files."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--prompt", help="Inline prompt text.")
    source.add_argument("--prompt-file", help="Path to a UTF-8 text file containing the prompt.")
    parser.add_argument("--output-dir", required=True, help="Directory to write outputs into.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model ID. Default: {DEFAULT_MODEL}")
    parser.add_argument("--aspect-ratio", default="16:9", help="Aspect ratio to request.")
    parser.add_argument(
        "--image-size",
        default=DEFAULT_IMAGE_SIZE,
        help=f"Requested image size. Default: {DEFAULT_IMAGE_SIZE}",
    )
    parser.add_argument("--passes", type=int, default=1, help="How many separate requests to make.")
    parser.add_argument("--sleep-seconds", type=float, default=0.0, help="Sleep between passes.")
    return parser.parse_args()


def load_prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        return args.prompt.strip()
    path = Path(args.prompt_file).expanduser().resolve()
    return path.read_text(encoding="utf-8").strip()


def build_request_body(prompt: str, aspect_ratio: str, image_size: str) -> dict:
    return {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": image_size,
            },
        },
    }


def extension_for_mime(mime_type: str) -> str:
    guess = mimetypes.guess_extension(mime_type or "")
    if guess:
        return guess
    return ".bin"


def save_inline_images(parts: list[dict], output_dir: Path, pass_index: int) -> list[str]:
    image_paths: list[str] = []
    image_counter = 0
    for part in parts:
        inline_data = part.get("inlineData") or part.get("inline_data")
        if not inline_data:
            continue
        payload = inline_data.get("data")
        if not payload:
            continue
        mime_type = inline_data.get("mimeType") or inline_data.get("mime_type") or "application/octet-stream"
        image_counter += 1
        ext = extension_for_mime(mime_type)
        filename = f"pass-{pass_index:02d}-image-{image_counter:02d}{ext}"
        path = output_dir / filename
        path.write_bytes(base64.b64decode(payload))
        image_paths.append(str(path))
    return image_paths


def run_request(model: str, request_body: dict, api_key: str) -> dict:
    url = API_URL.format(model=model)
    request = urllib.request.Request(
        url=url,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            "User-Agent": "nanobanana-infographic-probe/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def main() -> None:
    args = parse_args()
    prompt = load_prompt(args)
    if not prompt:
        raise SystemExit("Prompt is empty.")

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY is required for live probes.")

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "model": args.model,
        "aspect_ratio": args.aspect_ratio,
        "image_size": args.image_size,
        "passes": [],
    }
    image_count = 0

    for index in range(1, max(1, args.passes) + 1):
        request_body = build_request_body(prompt, args.aspect_ratio, args.image_size)
        request_path = output_dir / f"request-{index:02d}.json"
        request_path.write_text(json.dumps(request_body, indent=2) + "\n", encoding="utf-8")

        try:
            payload = run_request(args.model, request_body, api_key)
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            (output_dir / f"response-{index:02d}.error.txt").write_text(error_body, encoding="utf-8")
            print(f"HTTP {exc.code} on pass {index}: see response-{index:02d}.error.txt", file=sys.stderr)
            raise SystemExit(2) from exc
        except urllib.error.URLError as exc:
            print(f"Network error on pass {index}: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc

        response_path = output_dir / f"response-{index:02d}.json"
        response_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

        candidate = ((payload.get("candidates") or [{}])[0]) if payload else {}
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        text_parts = [part.get("text", "") for part in parts if part.get("text")]
        saved_images = save_inline_images(parts, output_dir, index)
        image_count += len(saved_images)

        manifest["passes"].append(
            {
                "index": index,
                "request_file": str(request_path),
                "response_file": str(response_path),
                "text_parts": text_parts,
                "image_files": saved_images,
            }
        )

        if args.sleep_seconds and index < args.passes:
            time.sleep(max(0.0, args.sleep_seconds))

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if image_count == 0:
        print(f"No images were returned. See {manifest_path}", file=sys.stderr)
        raise SystemExit(3)

    print(f"Saved {image_count} image(s) to {output_dir}")


if __name__ == "__main__":
    main()

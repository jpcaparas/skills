#!/usr/bin/env python3
"""Render every prompt in a variant pack concurrently."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import probe_gemini_image_api as probe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read a variant-pack.json file and render all variants concurrently "
            "through the Gemini image API."
        )
    )
    parser.add_argument("--variant-pack", required=True, help="Path to variant-pack.json.")
    parser.add_argument("--output-dir", required=True, help="Directory for batch outputs.")
    parser.add_argument("--model", default=probe.DEFAULT_MODEL, help=f"Model ID. Default: {probe.DEFAULT_MODEL}")
    parser.add_argument("--aspect-ratio", help="Override the aspect ratio from the pack.")
    parser.add_argument(
        "--image-size",
        default=probe.DEFAULT_IMAGE_SIZE,
        help=f"Requested image size. Default: {probe.DEFAULT_IMAGE_SIZE}",
    )
    parser.add_argument("--passes", type=int, default=1, help="How many passes per variant.")
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=0,
        help="Maximum concurrent jobs. Default: all jobs in the batch.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Write the batch plan without calling the API.")
    return parser.parse_args()


def load_pack(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data.get("variants"), list) or not data["variants"]:
        raise SystemExit("variant-pack.json is missing a non-empty 'variants' array.")
    return data


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def render_job(
    *,
    variant: dict,
    pass_index: int,
    output_root: Path,
    model: str,
    aspect_ratio: str,
    image_size: str,
    api_key: str,
) -> dict:
    variant_dir = output_root / variant["id"]
    variant_dir.mkdir(parents=True, exist_ok=True)

    request_body = probe.build_request_body(variant["prompt"], aspect_ratio, image_size)
    request_path = variant_dir / f"request-{pass_index:02d}.json"
    write_json(request_path, request_body)

    try:
        payload = probe.run_request(model, request_body, api_key)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        error_path = variant_dir / f"response-{pass_index:02d}.error.txt"
        error_path.write_text(error_body, encoding="utf-8")
        return {
            "variant_id": variant["id"],
            "variant_name": variant["name"],
            "pass_index": pass_index,
            "status": "error",
            "error_file": str(error_path),
            "error": f"HTTP {exc.code}",
        }
    except Exception as exc:  # pragma: no cover - defensive catch for network/runtime issues
        error_path = variant_dir / f"response-{pass_index:02d}.error.txt"
        error_path.write_text(str(exc), encoding="utf-8")
        return {
            "variant_id": variant["id"],
            "variant_name": variant["name"],
            "pass_index": pass_index,
            "status": "error",
            "error_file": str(error_path),
            "error": str(exc),
        }

    response_path = variant_dir / f"response-{pass_index:02d}.json"
    write_json(response_path, payload)

    candidate = ((payload.get("candidates") or [{}])[0]) if payload else {}
    content = candidate.get("content") or {}
    parts = content.get("parts") or []
    saved_images = probe.save_inline_images(parts, variant_dir, pass_index)
    text_parts = [part.get("text", "") for part in parts if part.get("text")]

    return {
        "variant_id": variant["id"],
        "variant_name": variant["name"],
        "pass_index": pass_index,
        "status": "ok",
        "request_file": str(request_path),
        "response_file": str(response_path),
        "image_files": saved_images,
        "text_parts": text_parts,
    }


def main() -> None:
    args = parse_args()
    variant_pack_path = Path(args.variant_pack).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pack = load_pack(variant_pack_path)
    brief = pack.get("brief") or {}
    aspect_ratio = args.aspect_ratio or brief.get("aspect_ratio") or "16:9"
    variants = pack["variants"]
    jobs = [
        {"variant": variant, "pass_index": pass_index}
        for variant in variants
        for pass_index in range(1, max(1, args.passes) + 1)
    ]

    batch_manifest = {
        "variant_pack": str(variant_pack_path),
        "model": args.model,
        "aspect_ratio": aspect_ratio,
        "image_size": args.image_size,
        "variant_count": len(variants),
        "passes_per_variant": max(1, args.passes),
        "job_count": len(jobs),
        "max_concurrency": args.max_concurrency or len(jobs),
        "results": [],
    }

    if args.dry_run:
        write_json(output_dir / "batch-manifest.json", batch_manifest)
        print(f"Wrote dry-run plan to {output_dir / 'batch-manifest.json'}")
        return

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY is required for batch rendering.")

    start = time.time()
    max_workers = max(1, args.max_concurrency or len(jobs))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(
                render_job,
                variant=job["variant"],
                pass_index=job["pass_index"],
                output_root=output_dir,
                model=args.model,
                aspect_ratio=aspect_ratio,
                image_size=args.image_size,
                api_key=api_key,
            )
            for job in jobs
        ]

        for future in as_completed(futures):
            batch_manifest["results"].append(future.result())

    batch_manifest["results"].sort(key=lambda item: (item["variant_id"], item["pass_index"]))
    batch_manifest["duration_seconds"] = round(time.time() - start, 3)
    write_json(output_dir / "batch-manifest.json", batch_manifest)

    by_variant: dict[str, list[dict]] = {}
    for result in batch_manifest["results"]:
        by_variant.setdefault(result["variant_id"], []).append(result)

    for variant_id, results in by_variant.items():
        write_json(output_dir / variant_id / "manifest.json", {"variant_id": variant_id, "results": results})

    failures = [result for result in batch_manifest["results"] if result["status"] != "ok"]
    if failures:
        print(f"Completed with {len(failures)} failed job(s). See {output_dir / 'batch-manifest.json'}")
        raise SystemExit(2)

    print(f"Rendered {len(batch_manifest['results'])} job(s) to {output_dir}")


if __name__ == "__main__":
    main()

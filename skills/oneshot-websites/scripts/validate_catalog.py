#!/usr/bin/env python3
"""Validate an output directory generated with the oneshot-websites skill."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REMOTE_IMAGE_RE = re.compile(r"<(?:img|source)\b[^>]*\bsrc=[\"']https?://", re.I)
REMOTE_SCRIPT_RE = re.compile(r"<script\b[^>]*\bsrc=[\"']https?://", re.I)
FRAMEWORK_HINT_RE = re.compile(r"(react|vue|svelte|alpine|cdn\.tailwindcss)\b", re.I)


def load_manifest(root: Path) -> dict | None:
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def infer_items(root: Path) -> list[dict]:
    items: list[dict] = []
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        if (child / "index.html").exists() and (child / "PROMPT.md").exists():
            items.append(
                {
                    "path": f"{child.name}/",
                    "prompt": f"{child.name}/PROMPT.md",
                    "type": child.name,
                    "status": "OK",
                    "summary": "Inferred route without manifest entry.",
                }
            )
    return items


def check_route_html(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    stripped = text.strip()
    if not stripped.lower().startswith("<!doctype html>"):
        errors.append(f"{path}: does not start with <!DOCTYPE html>")
    if not stripped.lower().endswith("</html>"):
        errors.append(f"{path}: does not end with </html>")
    if REMOTE_IMAGE_RE.search(text):
        errors.append(f"{path}: contains remote image URL")
    if REMOTE_SCRIPT_RE.search(text):
        errors.append(f"{path}: contains remote script URL")
    if FRAMEWORK_HINT_RE.search(text):
        errors.append(f"{path}: contains framework/CDN hint")
    return errors


def normalize_rel(value: str) -> str:
    return value.strip().lstrip("/")


def validate(root: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    manifest = load_manifest(root)
    items = manifest.get("items", []) if manifest else infer_items(root)

    if manifest is None:
        warnings.append("manifest.json missing; inferred routes from directories")
    elif not isinstance(items, list):
        errors.append("manifest.json items field must be an array")
        items = []

    if not items:
        errors.append("no route items found")

    root_index = root / "index.html"
    root_index_text = ""
    if not root_index.exists():
        errors.append("root index.html missing")
    else:
        root_index_text = root_index.read_text(encoding="utf-8", errors="replace")
        if "Fairness Note" not in root_index_text:
            errors.append("root index.html missing Fairness Note")
        if "PROMPT.md" not in root_index_text:
            errors.append("root index.html does not expose PROMPT.md")

    required_fields = {"path", "prompt", "type", "status", "summary"}
    checked_routes = 0
    for item in items:
        missing = sorted(field for field in required_fields if not item.get(field))
        if missing:
            errors.append(f"manifest item missing fields {missing}: {item}")
            continue

        rel_path = normalize_rel(str(item["path"]))
        rel_prompt = normalize_rel(str(item["prompt"]))
        route_dir = root / rel_path
        route_index = route_dir / "index.html"
        prompt = root / rel_prompt

        if not route_dir.is_dir():
            errors.append(f"route directory missing: {rel_path}")
            continue
        if not prompt.exists():
            errors.append(f"prompt missing: {rel_prompt}")
        if not route_index.exists():
            errors.append(f"route index missing: {rel_path}index.html")
        else:
            checked_routes += 1
            errors.extend(check_route_html(route_index))

        if root_index_text:
            for needle in [rel_path, rel_prompt, str(item["type"])]:
                if needle and needle not in root_index_text:
                    errors.append(f"root index.html missing {needle}")

    return {
        "valid": not errors,
        "root": str(root),
        "routes": len(items),
        "checked_routes": checked_routes,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="Generated catalog directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")

    result = validate(root)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

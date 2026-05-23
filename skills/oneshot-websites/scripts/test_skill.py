#!/usr/bin/env python3
"""Run lightweight tests for the oneshot-websites skill."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def assert_ok(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def write_sample_catalog(root: Path) -> Path:
    route = root / "restaurant"
    route.mkdir(parents=True)
    (route / "PROMPT.md").write_text(
        "# One-Shot Prompt\n\nRestaurant prompt for a single-pass route.\n",
        encoding="utf-8",
    )
    (route / "index.html").write_text(
        "<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><title>Restaurant</title></head><body><main><h1>Maison Vorieux</h1></main></body></html>\n",
        encoding="utf-8",
    )
    manifest = {
        "catalogTitle": "Oneshot Websites Test",
        "harness": "test",
        "generated": "2026-05-23",
        "mode": "single-pass",
        "selection": "test",
        "items": [
            {
                "path": "restaurant/",
                "title": "Maison Vorieux",
                "prompt": "restaurant/PROMPT.md",
                "type": "restaurant",
                "typeLabel": "Elegant Restaurant",
                "status": "OK",
                "summary": "Fine dining storefront with candlelit course reveals.",
            }
        ],
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1

    skill = Path(sys.argv[1]).resolve()
    errors: list[str] = []

    evals_path = skill / "evals" / "evals.json"
    try:
        evals = json.loads(evals_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"failed to read evals: {exc}", file=sys.stderr)
        return 1

    tags = {tag for item in evals.get("evals", []) for tag in item.get("tags", [])}
    for required in ["smoke", "edge", "negative", "disclosure", "verification"]:
        assert_ok(required in tags, f"missing eval tag: {required}", errors)

    for item in evals.get("evals", []):
        assert_ok("prompt" in item, f"eval missing prompt: {item}", errors)
        assert_ok("expected_output" in item, f"eval missing expected_output: {item}", errors)
        for assertion in item.get("assertions", []):
            assert_ok("text" in assertion, f"assertion missing text: {assertion}", errors)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest_path = write_sample_catalog(root)
        build = run(
            [
                sys.executable,
                str(skill / "scripts" / "build_catalog_index.py"),
                "--manifest",
                str(manifest_path),
                "--out",
                str(root / "index.html"),
            ]
        )
        assert_ok(build.returncode == 0, f"build_catalog_index.py failed: {build.stderr}", errors)

        validate = run([sys.executable, str(skill / "scripts" / "validate_catalog.py"), str(root)])
        assert_ok(validate.returncode == 0, f"validate_catalog.py failed: {validate.stdout}\n{validate.stderr}", errors)

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS: eval metadata, catalog builder, and catalog validator checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

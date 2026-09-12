#!/usr/bin/env python3

"""List published fixture skills without reading or writing real install roots."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture_root", type=Path)
    args = parser.parse_args()

    root = args.fixture_root.resolve()
    payload = json.loads((root / "registry.json").read_text(encoding="utf-8"))
    published = payload.get("published")
    if not isinstance(published, list) or not all(isinstance(item, str) for item in published):
        raise SystemExit("registry.json must contain a string array named published")

    for name in published:
        skill_file = root / "skills" / "stable" / name / "SKILL.md"
        if not skill_file.is_file():
            raise SystemExit(f"published skill is missing: {name}")
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

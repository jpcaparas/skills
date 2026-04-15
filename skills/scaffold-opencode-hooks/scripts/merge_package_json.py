#!/usr/bin/env python3
"""
merge_package_json.py

Merge dependency requirements into an OpenCode config-dir package.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_package_json(path: Path) -> dict:
    if not path.exists():
        return {
            "name": "opencode-config",
            "private": True,
            "type": "module",
            "dependencies": {},
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-file", required=True)
    parser.add_argument("--dependencies-json", required=True)
    args = parser.parse_args()

    package_path = Path(args.package_file).expanduser().resolve()
    package_path.parent.mkdir(parents=True, exist_ok=True)

    data = load_package_json(package_path)
    requested = json.loads(args.dependencies_json)
    if not isinstance(requested, dict):
        raise ValueError("--dependencies-json must be a JSON object")

    deps = data.get("dependencies", {})
    if not isinstance(deps, dict):
        deps = {}

    for name, version in requested.items():
        deps[name] = version

    data.setdefault("name", "opencode-config")
    data.setdefault("private", True)
    data.setdefault("type", "module")
    data["dependencies"] = dict(sorted(deps.items()))

    package_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"package_file": str(package_path), "dependencies": data["dependencies"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


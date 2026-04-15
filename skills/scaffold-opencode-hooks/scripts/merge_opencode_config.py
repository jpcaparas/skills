#!/usr/bin/env python3
"""
merge_opencode_config.py

Merge npm plugin package names into an OpenCode config file.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def strip_jsonc(text: str) -> str:
    result: list[str] = []
    i = 0
    in_string = False
    string_char = ""
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_string:
            result.append(ch)
            if ch == "\\" and i + 1 < len(text):
                result.append(text[i + 1])
                i += 2
                continue
            if ch == string_char:
                in_string = False
            i += 1
            continue
        if ch in {'"', "'"}:
            in_string = True
            string_char = ch
            result.append(ch)
            i += 1
            continue
        if ch == "/" and nxt == "/":
            i += 2
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        result.append(ch)
        i += 1
    stripped = "".join(result)
    return re.sub(r",(\s*[}\]])", r"\1", stripped)


def load_config(path: Path) -> dict:
    if not path.exists():
        return {"$schema": "https://opencode.ai/config.json"}
    raw = path.read_text(encoding="utf-8")
    cleaned = strip_jsonc(raw)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-file", required=True)
    parser.add_argument("--plugins", nargs="+", required=True)
    args = parser.parse_args()

    config_path = Path(args.config_file).expanduser().resolve()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = load_config(config_path)
    existing = data.get("plugin", [])
    if not isinstance(existing, list):
        existing = []
    merged = list(existing)
    for plugin in args.plugins:
        if plugin not in merged:
            merged.append(plugin)
    data["plugin"] = merged
    data.setdefault("$schema", "https://opencode.ai/config.json")

    config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"config_file": str(config_path), "plugins": merged}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


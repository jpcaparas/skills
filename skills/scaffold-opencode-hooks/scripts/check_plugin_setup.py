#!/usr/bin/env python3
"""
check_plugin_setup.py

Inspect project and global OpenCode plugin-related state.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PLUGIN_SUFFIXES = {".js", ".ts", ".mjs", ".cjs", ".jsx", ".tsx"}


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


def load_jsonc(path: Path) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    if not path.exists():
        return {}, warnings
    try:
        raw = path.read_text(encoding="utf-8")
        cleaned = strip_jsonc(raw)
        data = json.loads(cleaned)
        if path.suffix == ".jsonc":
            warnings.append(
                f"{path} uses JSONC comments; deterministic merges will rewrite normalized JSON."
            )
        return data if isinstance(data, dict) else {}, warnings
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Failed to parse {path}: {exc}")
        return {}, warnings


def choose_config_path(root: Path, base_name: str) -> Path:
    json_path = root / f"{base_name}.json"
    jsonc_path = root / f"{base_name}.jsonc"
    if json_path.exists():
        return json_path
    if jsonc_path.exists():
        return jsonc_path
    return json_path


def list_plugin_files(plugin_dir: Path) -> list[str]:
    if not plugin_dir.is_dir():
        return []
    return sorted(
        str(path.relative_to(plugin_dir))
        for path in plugin_dir.rglob("*")
        if path.is_file() and path.suffix in PLUGIN_SUFFIXES
    )


def package_dependencies(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    deps = data.get("dependencies", {})
    return deps if isinstance(deps, dict) else {}


def inspect_scope(root: Path, config_root: Path) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    config_path = choose_config_path(config_root, "opencode")
    config_data, config_warnings = load_jsonc(config_path)
    warnings.extend(config_warnings)

    plugin_entries = config_data.get("plugin", [])
    if not isinstance(plugin_entries, list):
        plugin_entries = []
        warnings.append(f"{config_path} has a non-array 'plugin' field; ignoring it.")

    plugin_dir = config_root / "plugins"
    package_file = config_root / "package.json"

    return (
        {
            "config_file": str(config_path),
            "config_exists": config_path.exists(),
            "config_format": config_path.suffix[1:] if config_path.exists() else "json",
            "plugin_entries": plugin_entries,
            "plugin_dir": str(plugin_dir),
            "local_plugin_files": list_plugin_files(plugin_dir),
            "package_file": str(package_file),
            "package_exists": package_file.exists(),
            "package_dependencies": package_dependencies(package_file),
        },
        warnings,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--home")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project).resolve()
    home = Path(args.home).expanduser().resolve() if args.home else Path.home().resolve()
    global_root = home / ".config" / "opencode"
    project_config_root = project_root
    project_runtime_root = project_root / ".opencode"

    project_state, project_warnings = inspect_scope(project_root, project_config_root)
    project_plugins = list_plugin_files(project_runtime_root / "plugins")
    if project_plugins and project_state["local_plugin_files"] != project_plugins:
        project_state["local_plugin_files"] = project_plugins
        project_state["plugin_dir"] = str(project_runtime_root / "plugins")

    project_state["package_file"] = str(project_runtime_root / "package.json")
    project_state["package_exists"] = (project_runtime_root / "package.json").exists()
    project_state["package_dependencies"] = package_dependencies(project_runtime_root / "package.json")

    global_state, global_warnings = inspect_scope(global_root, global_root)

    is_git_repo = False
    current = project_root
    for candidate in [project_root, *project_root.parents]:
        if (candidate / ".git").exists():
            is_git_repo = True
            break

    scope_recommendation = "project" if (
        is_git_repo
        or project_state["config_exists"]
        or bool(project_state["local_plugin_files"])
        or project_state["package_exists"]
    ) else "global"

    deployment_recommendation = "hybrid" if (
        project_state["plugin_entries"] or global_state["plugin_entries"]
    ) else "local-files"

    warnings = project_warnings + global_warnings

    result = {
        "project_root": str(project_root),
        "home": str(home),
        "scope_recommendation": scope_recommendation,
        "deployment_recommendation": deployment_recommendation,
        "recommended_module_format": "js",
        "project": project_state,
        "global": global_state,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


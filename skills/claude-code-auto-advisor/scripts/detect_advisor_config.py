#!/usr/bin/env python3
"""Conservatively inspect visible Claude Code advisor configuration."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any


TRUTHY = {"1", "true", "yes", "on"}
FALSY = {"", "0", "false", "no", "off"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=".", help="Directory used to find project .claude settings.")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format.")
    return parser.parse_args()


def env_truthy(name: str) -> bool:
    value = os.environ.get(name)
    if value is None:
        return False
    return value.strip().lower() in TRUTHY


def env_falsey(name: str) -> bool:
    value = os.environ.get(name)
    if value is None:
        return False
    return value.strip().lower() in FALSY


def claude_code_signals() -> list[str]:
    signals = []
    for name in [
        "CLAUDE_CODE_SESSION_ID",
        "CLAUDE_CODE_REMOTE",
        "CLAUDE_CODE_REMOTE_SESSION_ID",
        "CLAUDECODE",
    ]:
        if os.environ.get(name):
            signals.append(f"env:{name}")
    return signals


def managed_settings_paths() -> list[Path]:
    system = platform.system().lower()
    if system == "darwin":
        return [Path("/Library/Application Support/ClaudeCode/managed-settings.json")]
    if system == "windows":
        roots = [
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramData"),
        ]
        return [Path(root) / "ClaudeCode" / "managed-settings.json" for root in roots if root]
    return [Path("/etc/claude-code/managed-settings.json")]


def project_settings_paths(cwd: Path) -> list[Path]:
    paths: list[Path] = []
    try:
        current = cwd.resolve()
    except OSError:
        current = cwd.absolute()

    for parent in [current, *current.parents]:
        claude_dir = parent / ".claude"
        paths.append(claude_dir / "settings.local.json")
        paths.append(claude_dir / "settings.json")
    return paths


def settings_paths(cwd: Path) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    for path in managed_settings_paths():
        candidates.append(("managed", path))
    for path in project_settings_paths(cwd):
        candidates.append(("project-or-local", path))
    candidates.append(("user", Path.home() / ".claude" / "settings.json"))

    seen: set[Path] = set()
    unique: list[tuple[str, Path]] = []
    for scope, path in candidates:
        try:
            key = path.resolve()
        except OSError:
            key = path.absolute()
        if key in seen:
            continue
        seen.add(key)
        unique.append((scope, path))
    return unique


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "settings root is not an object"
    return data, None


def inspect(cwd: Path) -> dict[str, Any]:
    signals = claude_code_signals()
    disabled = env_truthy("CLAUDE_CODE_DISABLE_ADVISOR_TOOL")
    disabled_explicitly_false = env_falsey("CLAUDE_CODE_DISABLE_ADVISOR_TOOL")

    files = []
    first_model: str | None = None
    for scope, path in settings_paths(cwd):
        data, error = read_json(path)
        entry: dict[str, Any] = {
            "scope": scope,
            "path": str(path),
            "exists": path.is_file(),
        }
        if error:
            entry["error"] = error
        if data is not None and "advisorModel" in data:
            value = data.get("advisorModel")
            entry["advisorModel"] = value
            if first_model is None and isinstance(value, str) and value.strip():
                first_model = value.strip()
        files.append(entry)

    if disabled:
        status = "disabled_by_environment"
    elif first_model:
        status = "configured_in_visible_settings"
    elif signals:
        status = "no_visible_settings_model_found"
    else:
        status = "not_claude_code_or_unknown"

    return {
        "status": status,
        "advisor_model": first_model,
        "claude_code_signals": signals,
        "advisor_disabled_env": disabled,
        "advisor_disable_env_explicitly_false": disabled_explicitly_false,
        "settings_files": files,
        "limitations": [
            "Does not detect a session-only claude --advisor flag.",
            "Does not detect server-managed settings delivered after sign-in.",
            "Does not verify model pairing, organization allowlists, provider support, or actual tool attachment.",
            "The current Claude Code callable advisor tool is a stronger signal than this filesystem preflight.",
        ],
    }


def print_text(result: dict[str, Any]) -> None:
    print(f"status: {result['status']}")
    print(f"advisor_model: {result['advisor_model'] or '(none found in visible settings)'}")
    signals = ", ".join(result["claude_code_signals"]) or "(none)"
    print(f"claude_code_signals: {signals}")
    print(f"advisor_disabled_env: {result['advisor_disabled_env']}")
    visible = [
        item for item in result["settings_files"] if item.get("exists") or "advisorModel" in item or item.get("error")
    ]
    if visible:
        print("visible_settings:")
        for item in visible:
            suffix = ""
            if "advisorModel" in item:
                suffix = f" advisorModel={item['advisorModel']!r}"
            if item.get("error"):
                suffix += f" error={item['error']}"
            print(f"  - {item['scope']}: {item['path']}{suffix}")
    else:
        print("visible_settings: (none)")
    print("limitations:")
    for note in result["limitations"]:
        print(f"  - {note}")


def main() -> int:
    args = parse_args()
    result = inspect(Path(args.cwd))
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

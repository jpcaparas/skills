#!/usr/bin/env python3
"""Conservative local preflight for Codex subagent readiness.

This helper is intentionally modest: it can find local Codex CLI/config files,
but it cannot prove that the current conversation is running in the Codex app
or that subagent tools are attached to this exact session.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback
    tomllib = None  # type: ignore[assignment]


def find_project_root(start: Path) -> Path | None:
    """Return the nearest ancestor that looks like a project root."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def read_toml(path: Path) -> dict[str, Any]:
    """Read TOML when the runtime supports tomllib; otherwise return empty."""
    if tomllib is None or not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive settings boundary
        return {"_error": str(exc)}


def codex_version(codex_path: str | None) -> str | None:
    """Return `codex --version` output when the CLI is available."""
    if not codex_path:
        return None
    try:
        result = subprocess.run(
            [codex_path, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    output = (result.stdout or result.stderr).strip()
    return output or None


def summarize_agents_config(config: dict[str, Any]) -> dict[str, Any]:
    agents = config.get("agents")
    if not isinstance(agents, dict):
        return {}
    allowed = {
        "max_threads",
        "max_depth",
        "job_max_runtime_seconds",
    }
    return {key: agents.get(key) for key in sorted(allowed) if key in agents}


def build_report(cwd: Path) -> dict[str, Any]:
    codex_path = shutil.which("codex")
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    project_root = find_project_root(cwd)
    project_codex_dir = project_root / ".codex" if project_root else None

    user_config_path = codex_home / "config.toml"
    project_config_path = project_codex_dir / "config.toml" if project_codex_dir else None
    user_config = read_toml(user_config_path)
    project_config = read_toml(project_config_path) if project_config_path else {}

    report: dict[str, Any] = {
        "cwd": str(cwd.resolve()),
        "project_root": str(project_root) if project_root else None,
        "codex_cli": {
            "found": codex_path is not None,
            "path": codex_path,
            "version": codex_version(codex_path),
        },
        "codex_home": str(codex_home),
        "user_config": {
            "path": str(user_config_path),
            "exists": user_config_path.is_file(),
            "agents": summarize_agents_config(user_config),
            "parse_error": user_config.get("_error"),
        },
        "project_config": {
            "path": str(project_config_path) if project_config_path else None,
            "exists": bool(project_config_path and project_config_path.is_file()),
            "agents": summarize_agents_config(project_config),
            "parse_error": project_config.get("_error"),
        },
        "custom_agent_dirs": [
            {
                "scope": "user",
                "path": str(codex_home / "agents"),
                "exists": (codex_home / "agents").is_dir(),
            },
            {
                "scope": "project",
                "path": str(project_codex_dir / "agents") if project_codex_dir else None,
                "exists": bool(project_codex_dir and (project_codex_dir / "agents").is_dir()),
            },
        ],
        "limits": {
            "can_prove_current_surface": False,
            "can_prove_subagent_tools_attached": False,
        },
    }

    if codex_path:
        report["recommendation"] = (
            "Codex CLI is installed locally. Use the current session tool list and "
            "user prompt authorization as the source of truth before spawning."
        )
    else:
        report["recommendation"] = (
            "Codex CLI was not found on PATH. This does not disprove Codex app use, "
            "but it is not enough evidence to apply Codex-only subagent behavior."
        )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cwd",
        default=".",
        help="Directory to inspect for project-scoped Codex config. Default: current directory.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format. Default: json.",
    )
    args = parser.parse_args()

    report = build_report(Path(args.cwd))
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Codex CLI found: {report['codex_cli']['found']}")
        print(f"Codex CLI version: {report['codex_cli']['version'] or 'unknown'}")
        print(f"Project root: {report['project_root'] or 'not found'}")
        print(f"User agents config: {report['user_config']['agents'] or 'none detected'}")
        print(f"Project agents config: {report['project_config']['agents'] or 'none detected'}")
        print(report["recommendation"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

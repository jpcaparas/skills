#!/usr/bin/env python3
"""
check_hooks_feature.py

Inspect or enable the Codex `hooks` feature in user or project config.

Usage:
    python3 check_hooks_feature.py --project /path/to/project
    python3 check_hooks_feature.py --project /path/to/project --json
    python3 check_hooks_feature.py --project /path/to/project --enable --scope project
    python3 check_hooks_feature.py --project /path/to/project --enable --scope user
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


FEATURE_NAME = "hooks"
LEGACY_FEATURE_NAMES = ("codex_hooks",)
ALL_FEATURE_NAMES = (FEATURE_NAME, *LEGACY_FEATURE_NAMES)

SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
FEATURE_LINE_RE = re.compile(
    rf"^(\s*)({'|'.join(re.escape(name) for name in ALL_FEATURE_NAMES)})(\s*=\s*)(true|false)(\s*(?:#.*)?)$"
)
FEATURE_LIST_RE = re.compile(
    rf"^({'|'.join(re.escape(name) for name in ALL_FEATURE_NAMES)})\s+.+?\s+(true|false)\s*$"
)


def canonical_dir(path: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"project path is not a directory: {resolved}")
    return resolved


def resolve_home(home_arg: str | None) -> Path:
    if home_arg:
        return Path(home_arg).expanduser().resolve()
    return Path(os.environ.get("HOME", str(Path.home()))).expanduser().resolve()


def default_user_config(home: Path) -> Path:
    return home / ".codex" / "config.toml"


def default_project_config(project: Path) -> Path:
    return project / ".codex" / "config.toml"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def parse_feature_values(content: str) -> dict[str, bool]:
    values: dict[str, bool] = {}
    current_section: str | None = None
    for raw_line in content.splitlines():
        section_match = SECTION_RE.match(raw_line)
        if section_match:
            current_section = section_match.group(1).strip()
            continue
        if current_section != "features":
            continue
        feature_match = FEATURE_LINE_RE.match(raw_line)
        if feature_match:
            values[feature_match.group(2)] = feature_match.group(4) == "true"
    return values


def parse_feature_value(content: str, feature_name: str = FEATURE_NAME) -> bool | None:
    return parse_feature_values(content).get(feature_name)


def upsert_feature_value(path: Path, value: bool) -> bool:
    desired = "true" if value else "false"
    original = read_text(path)
    lines = original.splitlines(keepends=True)

    section_start: int | None = None
    section_end = len(lines)
    for idx, raw_line in enumerate(lines):
        section_match = SECTION_RE.match(raw_line)
        if not section_match:
            continue

        section_name = section_match.group(1).strip()
        if section_start is None and section_name == "features":
            section_start = idx
            continue

        if section_start is not None:
            section_end = idx
            break

    changed = False

    if section_start is not None:
        canonical_idx: int | None = None
        legacy_idx: int | None = None
        for idx in range(section_start + 1, section_end):
            feature_match = FEATURE_LINE_RE.match(lines[idx].rstrip("\n"))
            if feature_match:
                if feature_match.group(2) == FEATURE_NAME:
                    canonical_idx = idx
                    break
                if legacy_idx is None:
                    legacy_idx = idx

        target_idx = canonical_idx if canonical_idx is not None else legacy_idx
        if target_idx is not None:
            feature_match = FEATURE_LINE_RE.match(lines[target_idx].rstrip("\n"))
            if feature_match is None:
                raise AssertionError("target feature line did not match")
            replacement = (
                f"{feature_match.group(1)}{FEATURE_NAME}"
                f"{feature_match.group(3)}{desired}{feature_match.group(5)}"
            )
            if lines[target_idx].endswith("\n"):
                replacement += "\n"
            if lines[target_idx] != replacement:
                lines[target_idx] = replacement
                changed = True
        else:
            insertion = f"{FEATURE_NAME} = {desired}\n"
            lines.insert(section_end, insertion)
            changed = True
    else:
        block = []
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        if lines and lines[-1].strip():
            block.append("\n")
        block.extend(["[features]\n", f"{FEATURE_NAME} = {desired}\n"])
        lines.extend(block)
        changed = True

    new_content = "".join(lines)
    if new_content != original:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_content, encoding="utf-8")
        changed = True

    return changed


def run_codex(project: Path, home: Path, codex_bin: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["CODEX_HOME"] = str(home / ".codex")
    return subprocess.run(
        [codex_bin, "-C", str(project), *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def inspect_effective_feature(project: Path, home: Path, codex_bin: str) -> tuple[bool | None, list[str]]:
    warnings: list[str] = []
    try:
        result = run_codex(project, home, codex_bin, "features", "list")
    except FileNotFoundError:
        return None, [f"codex binary not found: {codex_bin}"]

    if result.returncode != 0:
        stderr = result.stderr.strip()
        warnings.append(
            "failed to inspect effective feature state"
            + (f": {stderr}" if stderr else "")
        )
        return None, warnings

    legacy_effective: bool | None = None
    for raw_line in result.stdout.splitlines():
        match = FEATURE_LIST_RE.match(raw_line.strip())
        if not match:
            continue
        value = match.group(2) == "true"
        if match.group(1) == FEATURE_NAME:
            return value, warnings
        legacy_effective = value

    if legacy_effective is not None:
        warnings.append(
            "`codex features list` reported the legacy `codex_hooks` key; prefer canonical `hooks`."
        )
        return legacy_effective, warnings

    warnings.append("could not find hooks in `codex features list` output")
    return None, warnings


def inspect_codex_version(home: Path, codex_bin: str) -> tuple[str | None, list[str]]:
    warnings: list[str] = []
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["CODEX_HOME"] = str(home / ".codex")
    try:
        result = subprocess.run(
            [codex_bin, "--version"],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
    except FileNotFoundError:
        return None, [f"codex binary not found: {codex_bin}"]

    if result.returncode != 0:
        stderr = result.stderr.strip()
        warnings.append(
            "failed to inspect codex version"
            + (f": {stderr}" if stderr else "")
        )
        return None, warnings

    return result.stdout.strip() or None, warnings


def build_report(project: Path, home: Path, user_config: Path, project_config: Path, codex_bin: str) -> dict:
    warnings: list[str] = []
    codex_version, version_warnings = inspect_codex_version(home, codex_bin)
    warnings.extend(version_warnings)
    effective, effective_warnings = inspect_effective_feature(project, home, codex_bin)
    warnings.extend(effective_warnings)

    user_values = parse_feature_values(read_text(user_config))
    project_values = parse_feature_values(read_text(project_config))
    user_explicit = user_values.get(FEATURE_NAME)
    project_explicit = project_values.get(FEATURE_NAME)
    user_legacy_explicit = user_values.get("codex_hooks")
    project_legacy_explicit = project_values.get("codex_hooks")

    recommended_scope = "project" if (project / ".git").exists() else "user"
    status = "enabled" if effective is True else "disabled" if effective is False else "unknown"

    if user_legacy_explicit is not None:
        warnings.append(
            "user config uses legacy `[features].codex_hooks`; prefer `[features].hooks`."
        )
    if project_legacy_explicit is not None:
        warnings.append(
            "project config uses legacy `[features].codex_hooks`; prefer `[features].hooks`."
        )

    project_config_enables_hooks = project_explicit is True or project_legacy_explicit is True
    user_config_enables_hooks = user_explicit is True or user_legacy_explicit is True
    if effective is False and user_config_enables_hooks:
        warnings.append(
            "user config explicitly enables `hooks`, but the effective feature is still off. "
            "Runtime inspection may be using a different Codex home or feature source."
        )

    if effective is False and project_config_enables_hooks:
        warnings.append(
            "project config explicitly enables `hooks`, but the effective feature is still off. "
            "Project config only loads when the project layer is active."
        )

    return {
        "project_path": str(project),
        "home_path": str(home),
        "feature_name": FEATURE_NAME,
        "legacy_feature_names": list(LEGACY_FEATURE_NAMES),
        "codex_bin": codex_bin,
        "codex_version": codex_version,
        "effective": effective,
        "status": status,
        "recommended_enable_scope": recommended_scope,
        "user_config_path": str(user_config),
        "user_config_exists": user_config.exists(),
        "user_explicit": user_explicit,
        "user_legacy_explicit": user_legacy_explicit,
        "project_config_path": str(project_config),
        "project_config_exists": project_config.exists(),
        "project_explicit": project_explicit,
        "project_legacy_explicit": project_legacy_explicit,
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Target project directory")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--enable", action="store_true", help="Enable the feature in the chosen scope")
    parser.add_argument(
        "--scope",
        choices=("project", "user"),
        default="project",
        help="Where to enable the feature when --enable is used",
    )
    parser.add_argument("--home", help="Override HOME for inspection and default user config resolution")
    parser.add_argument("--user-config", help="Override the user config path")
    parser.add_argument("--project-config", help="Override the project config path")
    parser.add_argument("--codex-bin", default="codex", help="Codex CLI binary to invoke")
    return parser.parse_args()


def print_human(report: dict) -> None:
    print(f"project: {report['project_path']}")
    print(f"codex version: {report['codex_version'] or 'unknown'}")
    print(f"effective hooks: {report['effective']}")
    print(f"user config: {report['user_config_path']} (explicit={report['user_explicit']})")
    if report.get("user_legacy_explicit") is not None:
        print(f"user legacy codex_hooks: {report['user_legacy_explicit']}")
    print(f"project config: {report['project_config_path']} (explicit={report['project_explicit']})")
    if report.get("project_legacy_explicit") is not None:
        print(f"project legacy codex_hooks: {report['project_legacy_explicit']}")
    print(f"recommended scope: {report['recommended_enable_scope']}")
    if report["warnings"]:
        print("warnings:")
        for warning in report["warnings"]:
            print(f"  - {warning}")


def main() -> int:
    args = parse_args()

    try:
        project = canonical_dir(args.project)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    home = resolve_home(args.home)
    user_config = Path(args.user_config).expanduser().resolve() if args.user_config else default_user_config(home)
    project_config = (
        Path(args.project_config).expanduser().resolve()
        if args.project_config
        else default_project_config(project)
    )

    changed = False
    enabled_scope: str | None = None

    if args.enable:
        target = project_config if args.scope == "project" else user_config
        changed = upsert_feature_value(target, True)
        enabled_scope = args.scope

    report = build_report(project, home, user_config, project_config, args.codex_bin)
    report["changed"] = changed
    report["enabled_scope"] = enabled_scope

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_human(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

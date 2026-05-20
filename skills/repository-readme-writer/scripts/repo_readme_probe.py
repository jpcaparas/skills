#!/usr/bin/env python3
"""Inventory repository signals useful for README creation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


MANIFESTS = [
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "Gemfile",
    "composer.json",
    "deno.json",
    "deno.jsonc",
]

LOCKFILES = {
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "package-lock.json": "npm",
    "bun.lock": "bun",
    "bun.lockb": "bun",
    "uv.lock": "uv",
    "poetry.lock": "poetry",
    "Cargo.lock": "cargo",
}

TASK_FILES = [
    "Makefile",
    "Taskfile.yml",
    "Taskfile.yaml",
    "justfile",
    "Justfile",
]

CONFIG_EXAMPLES = [
    ".env.example",
    ".env.local.example",
    "config.example.json",
    "config.example.yaml",
    "config.example.yml",
]

DEPLOY_FILES = [
    "vercel.json",
    "netlify.toml",
    "wrangler.toml",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
]

PRUNE_DIRS = {
    ".cache",
    ".codex",
    ".git",
    ".hg",
    ".next",
    ".nuxt",
    ".turbo",
    ".venv",
    ".yarn",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def find_named(root: Path, names: list[str], max_depth: int = 3) -> list[str]:
    wanted = {name.lower() for name in names}
    hits: set[str] = set()

    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        try:
            current_depth = len(current_path.relative_to(root).parts)
        except ValueError:
            continue

        dirs[:] = [
            directory
            for directory in dirs
            if directory not in PRUNE_DIRS and not (directory.startswith(".") and directory != ".github")
        ]
        if current_depth >= max_depth:
            dirs[:] = []

        for filename in files:
            if filename.lower() in wanted:
                candidate = current_path / filename
                depth = len(candidate.relative_to(root).parts)
                if depth <= max_depth:
                    hits.add(rel(candidate, root))

    return sorted(hits)


def read_package_scripts(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    scripts = data.get("scripts", {})
    if not isinstance(scripts, dict):
        return {}
    return {str(key): str(value) for key, value in sorted(scripts.items())}


def heading_summary(readme: Path) -> list[str]:
    try:
        lines = readme.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    headings = []
    for line in lines:
        if line.startswith("#"):
            stripped = line.lstrip("#").strip()
            if stripped:
                headings.append(stripped)
    return headings


def detect_package_manager(root: Path) -> str | None:
    for lockfile, manager in LOCKFILES.items():
        if (root / lockfile).exists():
            return manager
    package = root / "package.json"
    if package.exists():
        try:
            data = json.loads(package.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "npm"
        manager = data.get("packageManager")
        if isinstance(manager, str) and manager:
            return manager.split("@", 1)[0]
        return "npm"
    return None


def collect(root: Path) -> dict[str, Any]:
    root = root.resolve()
    readmes = find_named(root, ["README.md", "readme.md"], max_depth=3)
    package_jsons = find_named(root, ["package.json"], max_depth=3)
    package_scripts = {
        item: read_package_scripts(root / item)
        for item in package_jsons
    }

    return {
        "root": str(root),
        "package_manager": detect_package_manager(root),
        "readmes": [
            {
                "path": item,
                "headings": heading_summary(root / item),
            }
            for item in readmes
        ],
        "manifests": find_named(root, MANIFESTS, max_depth=3),
        "package_scripts": package_scripts,
        "task_files": find_named(root, TASK_FILES, max_depth=2),
        "config_examples": find_named(root, CONFIG_EXAMPLES, max_depth=3),
        "deploy_files": find_named(root, DEPLOY_FILES, max_depth=3),
        "ci_workflows": sorted(
            rel(path, root)
            for path in (root / ".github" / "workflows").glob("*.yml")
        )
        if (root / ".github" / "workflows").is_dir()
        else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory repository signals for README writing.")
    parser.add_argument("repo", nargs="?", default=".", help="Repository path to inspect")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    root = Path(args.repo)
    if not root.exists() or not root.is_dir():
        parser.error(f"repo path does not exist or is not a directory: {root}")

    data = collect(root)
    print(json.dumps(data, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

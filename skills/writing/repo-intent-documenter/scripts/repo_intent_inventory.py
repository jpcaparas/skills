#!/usr/bin/env python3
"""Create a compact repository inventory for intent-document drafting."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback
    tomllib = None  # type: ignore[assignment]


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".cache",
    ".idea",
    ".next",
    ".nuxt",
    ".turbo",
    ".venv",
    ".vscode",
    "build",
    "coverage",
    "DerivedData",
    "dist",
    "node_modules",
    "Pods",
    "target",
    "vendor",
    "__pycache__",
}

IGNORED_RELATIVE_DIRS = {
    ".claude/hooks/generated",
    ".codex/hooks/generated",
    ".husky/_",
}

IGNORED_FILE_NAMES = {
    ".DS_Store",
    "bun.lock",
    "bun.lockb",
    "Cargo.lock",
    "Gemfile.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "yarn.lock",
}

IGNORED_SUFFIXES = {
    ".avif",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".lock",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".svg",
    ".webp",
    ".zip",
}

DOC_NAMES = {
    "readme.md",
    "readme",
    "agents.md",
    "claude.md",
    "contributing.md",
    "architecture.md",
    "changelog.md",
    "license",
    "memory.md",
    "repo-intent.md",
    "repo_intent.md",
    "skill.md",
}

MANIFEST_NAMES = {
    "package.json",
    "pyproject.toml",
    "cargo.toml",
    "go.mod",
    "gemfile",
    "composer.json",
    "deno.json",
    "deno.jsonc",
    "bunfig.toml",
    "pnpm-workspace.yaml",
    "dockerfile",
    "compose.yaml",
    "docker-compose.yml",
}

ENTRYPOINT_RE = re.compile(
    r"(^|/)(main|index|app|server|cli|worker|extension|content-script|background)\.(js|jsx|ts|tsx|py|go|rs|rb|php)$",
    re.IGNORECASE,
)

TEST_RE = re.compile(r"(^|/)(tests?|spec|e2e)(/|$)|(\.test|\.spec)\.", re.IGNORECASE)


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_ignored_dir(path: Path, root: Path) -> bool:
    if path.name in IGNORED_DIRS:
        return True
    try:
        relative = relpath(path, root)
    except ValueError:
        return False
    return relative in IGNORED_RELATIVE_DIRS


def is_ignored_file(path: Path) -> bool:
    return path.name in IGNORED_FILE_NAMES or path.suffix in IGNORED_SUFFIXES


def file_priority(path: Path, root: Path) -> tuple[int, str]:
    relative = relpath(path, root)
    lower_relative = relative.lower()
    lower_name = path.name.lower()
    is_root_file = "/" not in relative

    if is_root_file and (lower_name in DOC_NAMES or lower_name in MANIFEST_NAMES):
        return (0, lower_relative)
    if lower_name in {"agents.md", "claude.md"} or "copilot-instructions" in lower_relative:
        return (0, lower_relative)
    if lower_relative.startswith("docs/"):
        return (1, lower_relative)
    if lower_relative.startswith(".github/workflows/"):
        return (2, lower_relative)
    if lower_name in MANIFEST_NAMES:
        return (2, lower_relative)
    if ENTRYPOINT_RE.search(relative):
        return (3, lower_relative)
    if TEST_RE.search(relative):
        return (4, lower_relative)
    return (9, lower_relative)


def read_text(path: Path, limit: int = 200_000) -> str:
    try:
        return path.read_text(encoding="utf-8")[:limit]
    except UnicodeDecodeError:
        return ""
    except OSError:
        return ""


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def load_toml(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if tomllib is None:
        return parse_toml_subset(text)
    try:
        data = tomllib.loads(text)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def parse_toml_value(value: str) -> Any:
    value = value.strip()
    if value and value[0] in {"'", '"'} and value[-1] == value[0]:
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        items = []
        for item in value[1:-1].split(","):
            item = item.strip()
            if item:
                items.append(parse_toml_value(item))
        return items
    return value


def parse_toml_subset(text: str) -> dict[str, Any]:
    """Parse enough TOML for common project metadata on Python <3.11."""

    data: dict[str, Any] = {}
    current: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current = data
            for part in line[1:-1].split("."):
                part = part.strip()
                if not part:
                    current = None
                    break
                next_value = current.setdefault(part, {})
                if not isinstance(next_value, dict):
                    current = None
                    break
                current = next_value
            continue
        if current is None or "=" not in line:
            continue
        key, value = line.split("=", 1)
        current[key.strip()] = parse_toml_value(value)
    return data


def summarize_package_json(path: Path) -> dict[str, Any]:
    data = load_json(path)
    deps = {}
    for key in ["dependencies", "devDependencies", "peerDependencies"]:
        value = data.get(key)
        if isinstance(value, dict):
            deps[key] = sorted(value.keys())[:25]
    scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
    return {
        "path": path.name,
        "kind": "node",
        "name": data.get("name"),
        "description": data.get("description"),
        "scripts": sorted(scripts.keys())[:25],
        "dependencies": deps,
    }


def summarize_pyproject(path: Path) -> dict[str, Any]:
    data = load_toml(path)
    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    tool = data.get("tool") if isinstance(data.get("tool"), dict) else {}
    return {
        "path": path.name,
        "kind": "python",
        "name": project.get("name"),
        "description": project.get("description"),
        "dependencies": project.get("dependencies", [])[:25] if isinstance(project.get("dependencies"), list) else [],
        "tool_sections": sorted(tool.keys())[:25],
    }


def summarize_cargo(path: Path) -> dict[str, Any]:
    data = load_toml(path)
    package = data.get("package") if isinstance(data.get("package"), dict) else {}
    dependencies = data.get("dependencies") if isinstance(data.get("dependencies"), dict) else {}
    return {
        "path": path.name,
        "kind": "rust",
        "name": package.get("name"),
        "description": package.get("description"),
        "dependencies": sorted(dependencies.keys())[:25],
    }


def summarize_go_mod(path: Path) -> dict[str, Any]:
    text = read_text(path, 20_000)
    module = None
    go_version = None
    requires: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("module "):
            module = stripped.split(maxsplit=1)[1]
        elif stripped.startswith("go "):
            go_version = stripped.split(maxsplit=1)[1]
        elif stripped and not stripped.startswith("//") and not stripped.startswith(("module ", "go ", "require (", ")", "replace ")):
            if len(requires) < 25:
                requires.append(stripped.split()[0])
    return {"path": path.name, "kind": "go", "module": module, "go": go_version, "requires": requires}


def summarize_manifest(path: Path, root: Path) -> dict[str, Any]:
    name = path.name.lower()
    if name == "package.json":
        summary = summarize_package_json(path)
    elif name == "pyproject.toml":
        summary = summarize_pyproject(path)
    elif name == "cargo.toml":
        summary = summarize_cargo(path)
    elif name == "go.mod":
        summary = summarize_go_mod(path)
    else:
        summary = {"path": path.name, "kind": name}
    summary["path"] = relpath(path, root)
    return summary


def collect_files(root: Path, max_files: int) -> list[Path]:
    files: list[Path] = []
    for current_root, dirs, names in os.walk(root):
        current = Path(current_root)
        dirs[:] = sorted(d for d in dirs if not is_ignored_dir(current / d, root))
        for name in sorted(names):
            path = current / name
            if is_ignored_file(path):
                continue
            files.append(path)
    return sorted(files, key=lambda path: file_priority(path, root))[:max_files]


def top_level_dirs(root: Path) -> list[str]:
    dirs = []
    for path in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if path.is_dir() and not is_ignored_dir(path, root):
            dirs.append(path.name)
    return dirs[:50]


def build_inventory(repo: str | Path, max_files: int = 500) -> dict[str, Any]:
    root = Path(repo).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Repository path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {root}")

    files = collect_files(root, max_files=max_files)
    docs: list[str] = []
    agent_instructions: list[str] = []
    manifests: list[dict[str, Any]] = []
    entrypoints: list[str] = []
    tests: list[str] = []
    ci: list[str] = []

    for path in files:
        relative = relpath(path, root)
        lower_name = path.name.lower()
        lower_relative = relative.lower()

        if lower_name in DOC_NAMES or lower_relative.startswith("docs/"):
            docs.append(relative)
        if lower_name in {"agents.md", "claude.md"} or "copilot-instructions" in lower_relative:
            agent_instructions.append(relative)
        if lower_name in MANIFEST_NAMES:
            manifests.append(summarize_manifest(path, root))
        if ENTRYPOINT_RE.search(relative):
            entrypoints.append(relative)
        if TEST_RE.search(relative):
            tests.append(relative)
        if lower_relative.startswith(".github/workflows/") or lower_name in {".gitlab-ci.yml", "circle.yml"}:
            ci.append(relative)

    return {
        "repo": str(root),
        "name": root.name,
        "top_level_dirs": top_level_dirs(root),
        "docs": sorted(docs)[:100],
        "agent_instructions": sorted(agent_instructions)[:50],
        "manifests": manifests[:50],
        "entrypoints": sorted(entrypoints)[:100],
        "tests": sorted(tests)[:100],
        "ci": sorted(ci)[:100],
        "sampled_file_count": len(files),
        "sampled_files": [relpath(path, root) for path in files[:max_files]],
        "truncated": len(files) >= max_files,
    }


def render_text(inventory: dict[str, Any]) -> str:
    lines = [
        f"Repository: {inventory['name']}",
        f"Path: {inventory['repo']}",
        "",
        "Top-level directories:",
    ]
    lines.extend(f"- {name}" for name in inventory["top_level_dirs"])
    for section in ["docs", "agent_instructions", "entrypoints", "tests", "ci"]:
        lines.extend(["", section.replace("_", " ").title() + ":"])
        values = inventory.get(section, [])
        lines.extend(f"- {value}" for value in values[:30])
        if not values:
            lines.append("- none found")
    lines.extend(["", "Manifests:"])
    for manifest in inventory.get("manifests", []):
        label = manifest.get("path", "unknown")
        kind = manifest.get("kind", "unknown")
        name = manifest.get("name") or manifest.get("module") or ""
        suffix = f" ({name})" if name else ""
        lines.append(f"- {label}: {kind}{suffix}")
    if not inventory.get("manifests"):
        lines.append("- none found")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a compact repository inventory for repo-intent drafting.",
    )
    parser.add_argument("repo", nargs="?", default=".", help="Repository path to inspect.")
    parser.add_argument("--max-files", type=int, default=500, help="Maximum files to sample while walking the repo.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a human-readable summary.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        inventory = build_inventory(args.repo, max_files=args.max_files)
    except Exception as exc:
        print(f"repo_intent_inventory: {exc}", file=sys.stderr)
        return 1

    if args.json:
        json.dump(inventory, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_text(inventory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

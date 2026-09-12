#!/usr/bin/env python3
"""Detect project-local source/config extensions for code-change stop gates."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


KNOWN_EXTENSIONS = [
    "astro",
    "c",
    "cc",
    "clj",
    "cljs",
    "cpp",
    "cs",
    "css",
    "cts",
    "dart",
    "ex",
    "exs",
    "fs",
    "go",
    "gql",
    "graphql",
    "h",
    "hpp",
    "html",
    "java",
    "js",
    "json",
    "jsonc",
    "jsx",
    "kt",
    "kts",
    "less",
    "lua",
    "md",
    "mdx",
    "mjs",
    "mts",
    "php",
    "proto",
    "py",
    "pyi",
    "rb",
    "rs",
    "sass",
    "scala",
    "scss",
    "sh",
    "sql",
    "svelte",
    "swift",
    "toml",
    "ts",
    "tsx",
    "vue",
    "yaml",
    "yml",
]
FALLBACK_EXTENSIONS = ["js", "jsx", "ts", "tsx", "py", "go", "rs", "java", "php", "rb", "cs", "sh"]
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".claude",
    ".codex",
    ".devin",
    ".opencode",
    ".github",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".turbo",
    ".venv",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}


def run_git_files(project: Path) -> list[str] | None:
    result = subprocess.run(
        ["git", "-C", str(project), "ls-files", "-co", "--exclude-standard"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]


def walk_files(project: Path) -> list[str]:
    files: list[str] = []
    for root, dirs, names in os.walk(project):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        root_path = Path(root)
        for name in names:
            files.append(str((root_path / name).relative_to(project)))
    return files


def should_skip(path: str, hooks_root: str) -> bool:
    normalized = path.replace("\\", "/")
    prefixes = [
        f"{hooks_root.strip('/')}/",
        ".claude/hooks/",
        ".codex/hooks/",
        ".devin/hooks/",
        ".github/copilot/hooks/generated/",
        ".opencode/hook/",
        ".opencode/plugins/",
    ]
    parts = set(normalized.split("/")[:-1])
    return any(normalized.startswith(prefix) for prefix in prefixes) or bool(parts & SKIP_DIRS)


def detect_extensions(files: list[str], hooks_root: str) -> list[str]:
    present = set()
    known = set(KNOWN_EXTENSIONS)
    for file_path in files:
        if should_skip(file_path, hooks_root):
            continue
        name = Path(file_path).name
        if "." not in name:
            continue
        extension = name.rsplit(".", 1)[1].lower()
        if extension in known:
            present.add(extension)
    return [extension for extension in KNOWN_EXTENSIONS if extension in present]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--hooks-root", default="hooks")
    args = parser.parse_args()

    project = args.project.resolve()
    files = run_git_files(project)
    if files is None:
        files = walk_files(project)

    extensions = detect_extensions(files, args.hooks_root)
    if not extensions:
        extensions = FALLBACK_EXTENSIONS
    print(json.dumps(extensions, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

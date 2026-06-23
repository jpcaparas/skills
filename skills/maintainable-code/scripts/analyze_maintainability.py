#!/usr/bin/env python3
"""Lightweight maintainability smell scanner.

This script is intentionally conservative. It flags places worth reading; it
does not decide whether code is good or bad.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_EXTENSIONS = {
    ".bash",
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".hcl",
    ".html",
    ".java",
    ".jsx",
    ".kt",
    ".php",
    ".ps1",
    ".py",
    ".rb",
    ".rs",
    ".scss",
    ".sh",
    ".sql",
    ".swift",
    ".tf",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
    ".zsh",
}

COMMENT_DEBT_EXTENSIONS = {
    ".bash",
    ".css",
    ".hcl",
    ".html",
    ".ps1",
    ".scss",
    ".sh",
    ".sql",
    ".tf",
    ".yaml",
    ".yml",
    ".zsh",
}

OPERATIONAL_HINTS = (
    "<<",
    "<<<",
    " aws ",
    " az ",
    "artifact",
    "awk ",
    "cache",
    "concurrency:",
    "curl ",
    "docker ",
    "gcloud ",
    "gh ",
    "gh api",
    "grep ",
    "ifs=",
    "jq ",
    "jq -",
    "kubectl ",
    "matrix:",
    "permissions:",
    "read -r",
    "run:",
    "sed ",
    "sort -u",
    "terraform ",
    "uses:",
    "while ",
    "xargs ",
)

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".nuxt",
    ".turbo",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}

VAGUE_NAMES = {
    "common",
    "data",
    "handler",
    "helper",
    "helpers",
    "manager",
    "misc",
    "process",
    "processor",
    "stuff",
    "thing",
    "util",
    "utils",
}

FUNCTION_RE = re.compile(
    r"""
    ^\s*
    (?:
        (?:export\s+)?(?:async\s+)?function\s+(?P<js>[A-Za-z_][A-Za-z0-9_]*) |
        def\s+(?P<py>[A-Za-z_][A-Za-z0-9_]*)\s*\( |
        func\s+(?P<go>[A-Za-z_][A-Za-z0-9_]*)\s*\( |
        (?:public|private|protected|static|\s)+\s*
        [A-Za-z_<>\[\],\s]+\s+(?P<c>[A-Za-z_][A-Za-z0-9_]*)\s*\(
    )
    """,
    re.VERBOSE,
)


@dataclass
class Finding:
    path: str
    line: int
    kind: str
    message: str


def iter_files(root: Path, extensions: set[str]) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in extensions:
            files.append(path)
    return sorted(files)


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def indentation_depth(line: str) -> int:
    expanded = line.replace("\t", "    ")
    return (len(expanded) - len(expanded.lstrip(" "))) // 2


def is_comment_line(line: str, suffix: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#!"):
        return False
    if suffix in {".html"}:
        return stripped.startswith("<!--")
    if suffix in {".css", ".scss"}:
        return stripped.startswith(("/*", "*", "*/"))
    if suffix == ".sql":
        return stripped.startswith(("--", "/*", "*", "*/"))
    if suffix in {".bash", ".hcl", ".ps1", ".sh", ".tf", ".yaml", ".yml", ".zsh"}:
        return stripped.startswith("#")
    return False


def operational_hint_count(line: str) -> int:
    lowered = f" {line.strip().lower()} "
    return 1 if any(hint in lowered for hint in OPERATIONAL_HINTS) else 0


def scan_comment_debt(lines: list[str], path: Path, relative: str) -> list[Finding]:
    if path.suffix not in COMMENT_DEBT_EXTENSIONS:
        return []

    findings: list[Finding] = []
    chunk_start = 0
    non_comment_lines = 0
    hint_count = 0
    has_comment = False

    def flush_chunk() -> None:
        nonlocal chunk_start, non_comment_lines, hint_count, has_comment
        if non_comment_lines >= 8 and hint_count >= 3 and not has_comment:
            findings.append(
                Finding(
                    relative,
                    chunk_start,
                    "comment-debt",
                    "Dense operational/config block has no explanatory comments.",
                )
            )
        chunk_start = 0
        non_comment_lines = 0
        hint_count = 0
        has_comment = False

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            flush_chunk()
            continue
        if chunk_start == 0:
            chunk_start = index
        if is_comment_line(line, path.suffix):
            has_comment = True
            continue
        non_comment_lines += 1
        hint_count += operational_hint_count(line)

    flush_chunk()
    return findings


def function_name(match: re.Match[str]) -> str:
    for group in ("js", "py", "go", "c"):
        value = match.group(group)
        if value:
            return value
    return ""


def scan_file(path: Path, root: Path, max_file_lines: int, max_function_lines: int) -> list[Finding]:
    lines = read_lines(path)
    relative = path.relative_to(root).as_posix()
    findings: list[Finding] = []
    findings.extend(scan_comment_debt(lines, path, relative))

    if len(lines) > max_file_lines:
        findings.append(
            Finding(
                relative,
                1,
                "large-file",
                f"{len(lines)} lines; inspect whether responsibilities can be split.",
            )
        )

    lower_stem = path.stem.lower()
    if lower_stem in VAGUE_NAMES:
        findings.append(
            Finding(relative, 1, "vague-file-name", f"File name '{path.name}' is vague.")
        )

    current_function: tuple[str, int] | None = None
    for index, line in enumerate(lines, start=1):
        match = FUNCTION_RE.search(line)
        if match:
            if current_function is not None:
                name, start = current_function
                length = index - start
                if length > max_function_lines:
                    findings.append(
                        Finding(
                            relative,
                            start,
                            "large-function",
                            f"Function '{name}' spans about {length} lines.",
                        )
                    )
            name = function_name(match)
            current_function = (name, index)
            if name.lower() in VAGUE_NAMES:
                findings.append(
                    Finding(relative, index, "vague-function-name", f"Function name '{name}' is vague.")
                )

        stripped = line.strip()
        if "TODO" in stripped or "FIXME" in stripped:
            findings.append(Finding(relative, index, "todo", "TODO/FIXME needs owner, reason, or follow-up."))

        if indentation_depth(line) >= 8 and stripped and not stripped.startswith(("#", "//", "*")):
            findings.append(Finding(relative, index, "deep-nesting", "Deep indentation increases cognitive load."))

        if re.search(r"\b(any|object|dict|Record<string,\s*any>)\b", line) and path.suffix in {".ts", ".tsx", ".py"}:
            findings.append(Finding(relative, index, "weak-type-signal", "Inspect whether this weak type hides a real contract."))

    if current_function is not None:
        name, start = current_function
        length = len(lines) - start + 1
        if length > max_function_lines:
            findings.append(
                Finding(
                    relative,
                    start,
                    "large-function",
                    f"Function '{name}' spans about {length} lines.",
                )
            )

    return findings


def parse_extensions(value: str) -> set[str]:
    extensions = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        extensions.add(item if item.startswith(".") else f".{item}")
    return extensions


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Scan source files for maintainability review prompts.",
    )
    parser.add_argument("path", help="Project, package, or source directory to scan.")
    parser.add_argument("--json", action="store_true", help="Print findings as JSON.")
    parser.add_argument(
        "--extensions",
        default=",".join(sorted(DEFAULT_EXTENSIONS)),
        help="Comma-separated extensions to include.",
    )
    parser.add_argument("--max-file-lines", type=int, default=500)
    parser.add_argument("--max-function-lines", type=int, default=80)
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        print(f"not found: {root}", file=sys.stderr)
        return 1

    extensions = parse_extensions(args.extensions)
    files = [root] if root.is_file() else iter_files(root, extensions)
    findings: list[Finding] = []
    for path in files:
        if path.suffix in extensions:
            findings.extend(scan_file(path, root if root.is_dir() else root.parent, args.max_file_lines, args.max_function_lines))

    if args.json:
        print(json.dumps({"root": str(root), "findings": [asdict(item) for item in findings]}, indent=2))
    else:
        print(f"Scanned {len(files)} files under {root}")
        if not findings:
            print("No maintainability prompts found by the lightweight scanner.")
        for item in findings:
            print(f"{item.path}:{item.line}: {item.kind}: {item.message}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Lightweight mockability review prompt scanner.

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
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".swift",
    ".ts",
    ".tsx",
}

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

TEST_MARKERS = {
    "__tests__",
    "spec",
    "specs",
    "test",
    "tests",
}

PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "hidden-time-dependency",
        re.compile(
            r"\b(Date\.now|new\s+Date\s*\(|System\.currentTimeMillis|System\.nanoTime|datetime\.(now|today)|time\.time|Instant\.now|LocalDate(Time)?\.now)\b"
        ),
        "Clock/time access may need an explicit clock or scheduler boundary.",
    ),
    (
        "hidden-randomness",
        re.compile(r"\b(Math\.random|random\.|secrets\.|crypto\.randomUUID|UUID\.randomUUID|SecureRandom\s*\(|rand\.)\b"),
        "Randomness may need an injectable generator or deterministic test value.",
    ),
    (
        "direct-environment-read",
        re.compile(r"\b(process\.env|os\.environ|System\.getenv|getenv\s*\(|Environment\.GetEnvironmentVariable)\b"),
        "Process environment reads are hard to vary safely inside behavior tests.",
    ),
    (
        "direct-network-call",
        re.compile(r"\b(fetch\s*\(|axios\.|requests\.|urllib\.|http\.(Get|Post|Client)|URLSession\.shared|HttpClient\s*\(|RestTemplate\s*\()"),
        "Network calls inside policy code usually need an adapter or client contract.",
    ),
    (
        "hard-coded-file-io",
        re.compile(r"\b(fs\.|open\s*\(|Path\.read_text|Files\.|FileInputStream|FileOutputStream|ioutil\.|os\.ReadFile|os\.WriteFile)"),
        "Filesystem access may need a file-store boundary or fixture-controlled path.",
    ),
    (
        "singleton-or-static-dependency",
        re.compile(r"\b(getInstance\s*\(|\.shared\b|Singleton\b|static\s+[A-Za-z0-9_<>,\s]+\s+[A-Za-z0-9_]+\s*=)\b"),
        "Global or singleton collaborators can make tests order-dependent.",
    ),
    (
        "direct-construction",
        re.compile(r"\bnew\s+[A-Z][A-Za-z0-9_]*(Client|Repository|Service|Gateway|Adapter|Publisher|Sender)\s*\("),
        "Constructing effectful collaborators inline can block substitution in tests.",
    ),
    (
        "weak-contract",
        re.compile(r"\b(any|Record<string,\s*any>|dict\[|Dict\[|map\[string\]interface\{\}|object)\b"),
        "Weakly typed dependency contracts can hide what a fake or stub must implement.",
    ),
]


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str
    message: str


def is_test_path(path: Path) -> bool:
    lower_parts = {part.lower() for part in path.parts}
    if lower_parts & TEST_MARKERS:
        return True
    lower_name = path.name.lower()
    return any(marker in lower_name for marker in (".test.", ".spec.", "_test.", "_spec."))


def iter_files(root: Path, extensions: set[str], include_tests: bool) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file() or path.suffix not in extensions:
            continue
        if not include_tests and is_test_path(path):
            continue
        files.append(path)
    return sorted(files)


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def parse_extensions(value: str) -> set[str]:
    extensions: set[str] = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        extensions.add(item if item.startswith(".") else f".{item}")
    return extensions


def scan_file(path: Path, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    relative = path.relative_to(root).as_posix()
    for index, line in enumerate(read_lines(path), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "*")):
            continue
        for kind, pattern, message in PATTERNS:
            if pattern.search(line):
                findings.append(Finding(relative, index, kind, message))
    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Scan source files for mockability review prompts.",
    )
    parser.add_argument("path", help="Project, package, source directory, or file to scan.")
    parser.add_argument("--json", action="store_true", help="Print findings as JSON.")
    parser.add_argument("--include-tests", action="store_true", help="Scan test files too.")
    parser.add_argument(
        "--extensions",
        default=",".join(sorted(DEFAULT_EXTENSIONS)),
        help="Comma-separated extensions to include.",
    )
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        print(f"not found: {root}", file=sys.stderr)
        return 1

    extensions = parse_extensions(args.extensions)
    files = [root] if root.is_file() else iter_files(root, extensions, args.include_tests)
    scan_root = root if root.is_dir() else root.parent
    findings: list[Finding] = []
    for path in files:
        if path.suffix in extensions and (args.include_tests or not is_test_path(path)):
            findings.extend(scan_file(path, scan_root))

    if args.json:
        print(json.dumps({"root": str(root), "findings": [asdict(item) for item in findings]}, indent=2))
    else:
        print(f"Scanned {len(files)} files under {root}")
        if not findings:
            print("No mockability prompts found by the lightweight scanner.")
        for item in findings:
            print(f"{item.path}:{item.line}: {item.kind}: {item.message}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

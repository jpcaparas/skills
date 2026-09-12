#!/usr/bin/env python3
"""
Create a first-pass inventory for zooming out around a code target.

This helper is intentionally heuristic. It finds candidate center files,
caller leads, import edges, directory clusters, manifests, and next reads.
It does not replace manual verification of runtime wiring.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "target",
    "__pycache__",
}

SOURCE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".mjs",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".scss",
    ".sh",
    ".sql",
    ".svelte",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
}

CONFIG_EXTENSIONS = {
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".xml",
    ".ini",
    ".env",
    ".md",
}

MANIFEST_NAMES = {
    "package.json",
    "pnpm-workspace.yaml",
    "yarn.lock",
    "package-lock.json",
    "turbo.json",
    "nx.json",
    "tsconfig.json",
    "pyproject.toml",
    "requirements.txt",
    "poetry.lock",
    "Pipfile",
    "go.mod",
    "go.work",
    "Cargo.toml",
    "Gemfile",
    "composer.json",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
}


def run_git_root(repo: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    root = result.stdout.strip()
    return Path(root).resolve() if root else None


def run_git_files(root: Path) -> list[Path] | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    files = []
    for line in result.stdout.splitlines():
        if line:
            files.append(root / line)
    return files


def discover_files(root: Path) -> list[Path]:
    git_files = run_git_files(root)
    if git_files is not None:
        return [path for path in git_files if path.is_file() and is_relevant_path(path)]

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            if is_relevant_path(path):
                files.append(path)
    return files


def is_relevant_path(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.name in MANIFEST_NAMES:
        return True
    return path.suffix in SOURCE_EXTENSIONS or path.suffix in CONFIG_EXTENSIONS


def safe_read(path: Path, limit: int = 250_000) -> str:
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    if b"\0" in raw[:4096]:
        return ""
    raw = raw[:limit]
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="ignore")


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def target_terms(target: str) -> list[str]:
    terms = [target.strip()]
    cleaned = target.replace("\\", "/").strip("/")
    name = Path(cleaned).name
    stem = Path(cleaned).stem
    for term in [cleaned, name, stem]:
        if term and term not in terms:
            terms.append(term)
    words = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", target)
    for word in words:
        if word not in terms:
            terms.append(word)
    return [term for term in terms if len(term) >= 2]


def find_line_matches(text: str, terms: list[str], max_per_file: int = 8) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    lowered_terms = [(term, term.lower()) for term in terms]
    for index, line in enumerate(text.splitlines(), start=1):
        lower = line.lower()
        for term, lower_term in lowered_terms:
            if lower_term in lower:
                matches.append(
                    {
                        "line": index,
                        "term": term,
                        "text": line.strip()[:180],
                    }
                )
                break
        if len(matches) >= max_per_file:
            break
    return matches


def extract_imports(text: str, suffix: str) -> list[str]:
    patterns = [
        r"^\s*import\s+(?:[^'\"]+\s+from\s+)?['\"]([^'\"]+)['\"]",
        r"^\s*export\s+[^'\"]+\s+from\s+['\"]([^'\"]+)['\"]",
        r"require\(\s*['\"]([^'\"]+)['\"]\s*\)",
        r"^\s*from\s+([A-Za-z0-9_\.]+)\s+import\s+",
        r"^\s*import\s+([A-Za-z0-9_\.]+)",
        r"^\s*use\s+([A-Za-z0-9_:]+)",
    ]
    imports: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.MULTILINE):
            value = match.group(1).strip()
            if value and value not in imports:
                imports.append(value)
    if suffix == ".go":
        for match in re.finditer(r"^\s*\"([^\"]+)\"", text, flags=re.MULTILINE):
            value = match.group(1).strip()
            if value and value not in imports:
                imports.append(value)
    return imports[:25]


def score_path(path_text: str, terms: list[str]) -> int:
    lower_path = path_text.lower()
    score = 0
    for term in terms:
        lower_term = term.lower()
        if lower_term in lower_path:
            score += 4 if "/" in lower_term or "." in lower_term else 2
    return score


def build_inventory(repo: Path, target: str, max_files: int, max_matches: int) -> dict[str, Any]:
    repo = repo.resolve()
    root = run_git_root(repo) or repo
    files = discover_files(root)
    terms = target_terms(target)

    candidates: list[dict[str, Any]] = []
    import_edges: list[dict[str, Any]] = []
    clusters: Counter[str] = Counter()
    manifests: list[str] = []

    for path in files:
        rel_path = rel(path, root)
        if path.name in MANIFEST_NAMES:
            manifests.append(rel_path)

        top = rel_path.split("/", 1)[0]
        clusters[top] += 1

        path_score = score_path(rel_path, terms)
        text = safe_read(path)
        matches = find_line_matches(text, terms, max_per_file=max_matches)
        content_score = len(matches)
        total_score = path_score + content_score

        if total_score:
            role = "path-match" if path_score and not content_score else "content-match"
            if path_score and content_score:
                role = "path-and-content-match"
            candidates.append(
                {
                    "path": rel_path,
                    "score": total_score,
                    "role": role,
                    "matches": matches,
                }
            )

        if total_score or path.suffix in SOURCE_EXTENSIONS:
            imports = extract_imports(text, path.suffix)
            if imports and total_score:
                import_edges.append({"from": rel_path, "imports": imports[:12]})

    candidates.sort(key=lambda item: (-int(item["score"]), item["path"]))
    center = candidates[:max_files]
    center_paths = {item["path"] for item in center[: max(3, min(max_files, 7))]}
    callers = [item for item in candidates if item["path"] not in center_paths][:max_files]

    suggested_reads = []
    for item in center[:5]:
        suggested_reads.append(
            {
                "path": item["path"],
                "reason": "highest-scoring candidate for the target",
            }
        )
    for item in callers[:3]:
        suggested_reads.append(
            {
                "path": item["path"],
                "reason": "possible upstream caller or usage lead",
            }
        )

    return {
        "target": target,
        "repo_root": str(root),
        "terms_used": terms,
        "file_count": len(files),
        "candidate_count": len(candidates),
        "center_candidates": center,
        "caller_candidates": callers,
        "import_edges": import_edges[:max_files],
        "directory_clusters": [
            {"path": name, "file_count": count}
            for name, count in clusters.most_common(20)
        ],
        "manifests": sorted(manifests)[:30],
        "suggested_reads": suggested_reads,
        "notes": [
            "Textual matches are leads, not verified callers.",
            "Inspect framework registration, route tables, and tests before claiming a runtime path.",
        ],
    }


def print_markdown(data: dict[str, Any]) -> None:
    print(f"# Zoom-out inventory for `{data['target']}`")
    print()
    print(f"Repo root: `{data['repo_root']}`")
    print(f"Files scanned: {data['file_count']}")
    print(f"Candidates found: {data['candidate_count']}")
    print()

    print("## Center Candidates")
    for item in data["center_candidates"][:10]:
        print(f"- `{item['path']}` score={item['score']} role={item['role']}")
        for match in item.get("matches", [])[:3]:
            print(f"  - line {match['line']}: {match['text']}")
    if not data["center_candidates"]:
        print("- No candidates found.")
    print()

    print("## Caller / Usage Leads")
    for item in data["caller_candidates"][:10]:
        print(f"- `{item['path']}` score={item['score']} role={item['role']}")
    if not data["caller_candidates"]:
        print("- No separate caller leads found.")
    print()

    print("## Import Edges From Candidate Files")
    for edge in data["import_edges"][:10]:
        imports = ", ".join(f"`{value}`" for value in edge["imports"][:8])
        print(f"- `{edge['from']}` imports {imports}")
    if not data["import_edges"]:
        print("- No imports extracted from candidate files.")
    print()

    print("## Suggested Reads")
    for item in data["suggested_reads"][:8]:
        print(f"- `{item['path']}` - {item['reason']}")
    if not data["suggested_reads"]:
        print("- Start with exact target search and entrypoint discovery.")
    print()

    print("## Notes")
    for note in data["notes"]:
        print(f"- {note}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a first-pass module/caller inventory around a code target."
    )
    parser.add_argument("--repo", default=".", help="Repository or directory to inspect.")
    parser.add_argument("--target", required=True, help="Symbol, path, route, feature, or term to map.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--max-files", type=int, default=12, help="Maximum candidates per section.")
    parser.add_argument("--max-matches", type=int, default=8, help="Maximum line matches per file.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo = Path(args.repo)
    if not repo.exists():
        print(f"error: repo path does not exist: {repo}", file=sys.stderr)
        return 2
    data = build_inventory(repo, args.target, args.max_files, args.max_matches)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print_markdown(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

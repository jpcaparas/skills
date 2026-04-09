#!/usr/bin/env python3
"""
Infer the most appropriate skills root for a new skill.

The goal is to avoid assuming the current working directory is the right place.
This script inspects:
- the current git repository (if any)
- the directory family this skill is currently running from
- common global skill roots
- where existing skills already live
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
HOME = Path.home()

PROJECT_ROOTS: list[tuple[str, str]] = [
    ("skills", "public-repo"),
    (".agents/skills", "project-shared"),
    (".codex/skills", "project-codex"),
    (".claude/skills", "project-claude"),
    (".cursor/skills", "project-cursor"),
    (".gemini/skills", "project-gemini"),
    (".opencode/skills", "project-opencode"),
    (".continue/skills", "project-continue"),
    (".goose/skills", "project-goose"),
]

GLOBAL_ROOTS: list[tuple[Path, str]] = [
    (Path(os.environ["CODEX_HOME"]) / "skills", "global-codex-home")
    if os.environ.get("CODEX_HOME")
    else None,
    (HOME / ".codex/skills", "global-codex"),
    (HOME / ".claude/skills", "global-claude"),
    (HOME / ".agents/skills", "global-shared"),
    (HOME / ".cursor/skills", "global-cursor"),
    (HOME / ".gemini/skills", "global-gemini"),
    (HOME / ".config/opencode/skills", "global-opencode"),
    (HOME / ".continue/skills", "global-continue"),
    (HOME / ".config/goose/skills", "global-goose"),
]
GLOBAL_ROOTS = [item for item in GLOBAL_ROOTS if item is not None]


@dataclass
class Candidate:
    path: str
    scope: str
    source: str
    exists: bool
    skill_count: int
    current_install_root: bool
    reason: str


def git_repo_root(start: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return manual_repo_root(start)

    repo = result.stdout.strip()
    return Path(repo).resolve() if repo else None


def manual_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        git_marker = candidate / ".git"
        if git_marker.exists():
            return candidate
    return None


def count_skills(root: Path) -> int:
    if not root.is_dir():
        return 0

    count = 1 if (root / "SKILL.md").is_file() else 0
    for child in root.iterdir():
        if child.is_dir() and (child / "SKILL.md").is_file():
            count += 1
    return count


def detect_current_install_root() -> Path | None:
    parent = SKILL_DIR.parent
    if parent.name == "skills":
        return parent.resolve()
    return None


def build_candidates(repo_root: Path | None, current_root: Path | None) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[Path] = set()

    def add(path: Path, scope: str, source: str) -> None:
        resolved = path.expanduser().resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        exists = resolved.is_dir()
        skill_count = count_skills(resolved)
        current_match = current_root is not None and resolved == current_root
        if current_match:
            reason = "current skill is already running from this skills root"
        elif exists and skill_count:
            reason = f"{skill_count} existing skill(s) already live here"
        elif exists:
            reason = "directory already exists but does not yet contain discovered skills"
        else:
            reason = "valid fallback root if no established location exists"

        candidates.append(
            Candidate(
                path=str(resolved),
                scope=scope,
                source=source,
                exists=exists,
                skill_count=skill_count,
                current_install_root=current_match,
                reason=reason,
            )
        )

    if repo_root is not None:
        for relative, source in PROJECT_ROOTS:
            add(repo_root / relative, "project", source)

    for path, source in GLOBAL_ROOTS:
        add(path, "global", source)

    if current_root is not None and current_root.resolve() not in seen:
        scope = "project" if repo_root and current_root.is_relative_to(repo_root) else "global"
        add(current_root, scope, "current-install-root")

    return candidates


def choose_candidate(
    repo_root: Path | None, current_root: Path | None, candidates: list[Candidate]
) -> tuple[Candidate, str]:
    path_to_candidate = {Path(candidate.path): candidate for candidate in candidates}
    project_candidates = [candidate for candidate in candidates if candidate.scope == "project"]
    global_candidates = [candidate for candidate in candidates if candidate.scope == "global"]

    project_with_skills = [candidate for candidate in project_candidates if candidate.skill_count > 0]
    if project_with_skills:
        chosen = max(
            project_with_skills,
            key=lambda item: (item.skill_count, item.current_install_root, item.source == "public-repo"),
        )
        return chosen, f"this repository already keeps {chosen.skill_count} skill(s) under {chosen.path}"

    if repo_root and current_root and current_root.is_relative_to(repo_root):
        chosen = path_to_candidate.get(current_root.resolve())
        if chosen is not None:
            return chosen, "this skill is already running from a repo-local skills root"

    global_with_skills = [candidate for candidate in global_candidates if candidate.skill_count > 0]
    if global_with_skills:
        chosen = max(
            global_with_skills,
            key=lambda item: (item.skill_count, item.current_install_root, item.source == "global-codex"),
        )
        return chosen, f"your established global library already keeps {chosen.skill_count} skill(s) here"

    if repo_root is not None:
        public_root = path_to_candidate.get((repo_root / "skills").resolve())
        if public_root is not None and (public_root.exists or current_root == Path(public_root.path)):
            return public_root, "this repository already uses the public skills/<skill-name> layout"

        shared_root = path_to_candidate.get((repo_root / ".agents/skills").resolve())
        if shared_root is not None:
            return shared_root, "no project-local skill root is established yet, so use the shared repo fallback"

    if current_root is not None:
        chosen = path_to_candidate.get(current_root.resolve())
        if chosen is not None:
            return chosen, "this skill is already running from this skills family"

    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        fallback = Path(codex_home).expanduser().resolve() / "skills"
        chosen = path_to_candidate.get(fallback)
        if chosen is not None:
            return chosen, "CODEX_HOME is set and no stronger project or global convention was found"

    shared_global = path_to_candidate.get((HOME / ".agents/skills").resolve())
    if shared_global is not None:
        return shared_global, "no stronger signal was found, so use the generic global fallback"

    chosen = candidates[0]
    return chosen, "fallback to the first recognized skills root"


def rank_alternatives(chosen: Candidate, candidates: list[Candidate]) -> list[str]:
    ranked = sorted(
        (candidate for candidate in candidates if candidate.path != chosen.path),
        key=lambda item: (
            item.skill_count,
            item.current_install_root,
            item.scope == chosen.scope,
            item.exists,
        ),
        reverse=True,
    )
    return [candidate.path for candidate in ranked[:2]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Infer the best root for a new skill")
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory to inspect")
    parser.add_argument(
        "--format",
        choices=("json", "text", "path"),
        default="json",
        help="Output format",
    )
    parser.add_argument(
        "--skill-name",
        default=None,
        help="Optional skill name to include in human-readable output",
    )
    args = parser.parse_args()

    cwd = Path(args.cwd).expanduser().resolve()
    repo_root = git_repo_root(cwd)
    current_root = detect_current_install_root()
    candidates = build_candidates(repo_root, current_root)
    chosen, reason = choose_candidate(repo_root, current_root, candidates)
    recommended_root = Path(chosen.path)
    recommended_destination = (
        recommended_root / args.skill_name if args.skill_name else None
    )

    payload = {
        "cwd": str(cwd),
        "repo_root": str(repo_root) if repo_root else None,
        "current_install_root": str(current_root) if current_root else None,
        "recommended_root": str(recommended_root),
        "recommended_destination": str(recommended_destination) if recommended_destination else None,
        "recommended_scope": chosen.scope,
        "reason": reason,
        "alternatives": rank_alternatives(chosen, candidates),
        "candidates": [asdict(candidate) for candidate in candidates],
    }

    if args.format == "path":
        print(payload["recommended_root"])
        return 0

    if args.format == "text":
        if recommended_destination is not None:
            print(f"Recommended destination: {recommended_destination}")
        else:
            print(f"Recommended root: {recommended_root}")
        print(f"Reason: {reason}")
        alternatives = payload["alternatives"]
        if alternatives:
            suffix = f"/{args.skill_name}" if args.skill_name else ""
            print(f"Alternative: {alternatives[0]}{suffix}")
        return 0

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

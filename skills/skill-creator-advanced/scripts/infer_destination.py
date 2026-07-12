#!/usr/bin/env python3
"""
Infer the most appropriate skills root for a new skill.

The goal is to avoid assuming the current working directory is the right place
or that the largest library belongs to the active harness. This script inspects:
- the current git repository (if any)
- the directory family this skill is currently running from
- common global skill roots
- where existing skills already live
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


# Keep the invoked path lexical so a symlinked installation still identifies its
# actual harness family.
SCRIPT_PATH = Path(os.path.abspath(__file__))
INVOKED_SKILL_DIR = SCRIPT_PATH.parent.parent
HOME = Path.home()

TARGET_HARNESSES = (
    "agents",
    "codex",
    "copilot",
    "gemini",
    "opencode",
)
SHARED_HARNESSES = tuple(TARGET_HARNESSES)
LIFECYCLE_LANES = frozenset({".curated", ".experimental", ".system"})


@dataclass(frozen=True)
class RootSpec:
    path: Path
    source: str
    compatible_harnesses: tuple[str, ...]


PROJECT_ROOTS = [
    RootSpec(Path("skills"), "public-repo", ()),
    RootSpec(Path(".agents/skills"), "project-shared", SHARED_HARNESSES),
    RootSpec(Path(".github/skills"), "project-copilot", ("copilot",)),
    RootSpec(Path(".codex/skills"), "project-codex", ("codex",)),
    RootSpec(Path(".claude/skills"), "project-claude", ("claude", "copilot", "opencode")),
    RootSpec(Path(".cursor/skills"), "project-cursor", ("cursor",)),
    RootSpec(Path(".gemini/skills"), "project-gemini", ("gemini",)),
    RootSpec(Path(".opencode/skills"), "project-opencode", ("opencode",)),
    RootSpec(Path(".continue/skills"), "project-continue", ("continue",)),
    RootSpec(Path(".goose/skills"), "project-goose", ("goose",)),
]

GLOBAL_ROOTS: list[RootSpec] = []
if os.environ.get("CODEX_HOME"):
    GLOBAL_ROOTS.append(
        RootSpec(
            Path(os.environ["CODEX_HOME"]) / "skills",
            "global-codex-home",
            ("codex",),
        )
    )
GLOBAL_ROOTS.extend(
    [
        RootSpec(HOME / ".agents/skills", "global-shared", SHARED_HARNESSES),
        RootSpec(HOME / ".claude/skills", "global-claude", ("claude", "opencode")),
        RootSpec(HOME / ".codex/skills", "global-codex", ("codex",)),
        RootSpec(HOME / ".continue/skills", "global-continue", ("continue",)),
        RootSpec(HOME / ".copilot/skills", "global-copilot", ("copilot",)),
        RootSpec(HOME / ".cursor/skills", "global-cursor", ("cursor",)),
        RootSpec(HOME / ".gemini/skills", "global-gemini", ("gemini",)),
        RootSpec(HOME / ".config/goose/skills", "global-goose", ("goose",)),
        RootSpec(HOME / ".config/opencode/skills", "global-opencode", ("opencode",)),
    ]
)

DEFAULT_GLOBAL_SOURCE = {
    "agents": "global-shared",
    "codex": "global-codex-home" if os.environ.get("CODEX_HOME") else "global-codex",
    "copilot": "global-copilot",
    "gemini": "global-gemini",
    "opencode": "global-opencode",
}


@dataclass
class Candidate:
    path: str
    scope: str
    source: str
    exists: bool
    skill_count: int
    current_install_root: bool
    compatible_harnesses: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class ExcludedRoot:
    path: str
    scope: str
    source: str
    reason: str


def git_repo_root(start: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        return manual_repo_root(start)
    except (OSError, subprocess.CalledProcessError):
        # A present Git executable is authoritative. Do not cross a repository
        # discovery boundary after Git has explicitly rejected the location.
        return None

    repo = result.stdout.strip()
    if not repo:
        return None
    try:
        root = Path(repo).expanduser().resolve(strict=True)
        resolved_start = start.expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if not root.is_dir() or not resolved_start.is_relative_to(root):
        return None
    return root


def valid_git_directory(git_dir: Path) -> bool:
    if git_dir.is_symlink() or not git_dir.is_dir():
        return False
    head = git_dir / "HEAD"
    if head.is_symlink() or not head.is_file():
        return False
    try:
        value = head.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return False
    if value.startswith("ref: "):
        return bool(re.fullmatch(r"ref: refs/[^\s]+", value))
    return bool(re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", value))


def git_directory_from_file(marker: Path) -> Path | None:
    if marker.is_symlink() or not marker.is_file():
        return None
    try:
        content = marker.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    match = re.fullmatch(r"gitdir:\s*(\S(?:.*\S)?)\s*", content)
    if match is None:
        return None
    target = Path(match.group(1)).expanduser()
    if not target.is_absolute():
        target = marker.parent / target
    try:
        return target.resolve(strict=True)
    except (OSError, RuntimeError):
        return None


def manual_repo_root(start: Path) -> Path | None:
    try:
        current = start.resolve(strict=True)
        start_device = current.stat().st_dev
    except OSError:
        return None
    for candidate in [current, *current.parents]:
        try:
            if candidate.stat().st_dev != start_device:
                break
        except OSError:
            return None
        if not os.access(candidate, os.R_OK | os.X_OK):
            return None
        git_marker = candidate / ".git"
        if git_marker.is_symlink():
            return None
        if git_marker.is_dir():
            return candidate if valid_git_directory(git_marker) else None
        if git_marker.is_file():
            git_dir = git_directory_from_file(git_marker)
            return candidate if git_dir and valid_git_directory(git_dir) else None
        if git_marker.exists():
            # An invalid marker is still a discovery boundary. Never skip past
            # it and accidentally attach the workspace to an outer repository.
            return None
    return None


def count_skills(root: Path) -> int:
    if not root.is_dir():
        return 0

    count = 0
    try:
        for child in root.iterdir():
            if child.is_dir() and (child / "SKILL.md").is_file():
                count += 1
    except OSError:
        # An unreadable root is not reliable evidence of an established library.
        return 0
    return count


def detect_current_install_root() -> Path | None:
    parent = INVOKED_SKILL_DIR.parent
    if parent.name == "skills":
        return lexical_absolute(parent)
    # Lifecycle lanes require an explicit policy decision. Merely running this
    # creator from one must never route an ordinary new skill back into it.
    if parent.name in LIFECYCLE_LANES and parent.parent.name == "skills":
        return None
    return None


def lexical_absolute(path: Path) -> Path:
    """Return an absolute path without dereferencing its final symlink chain."""
    return Path(os.path.abspath(path.expanduser()))


def resolved_path(path: Path) -> Path | None:
    try:
        return lexical_absolute(path).resolve()
    except (OSError, RuntimeError):
        return None


def permission_bits_allow(path: Path, *masks: int) -> bool:
    if os.name == "nt":
        return True
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return False
    return all(bool(mode & mask) for mask in masks)


def root_path_block_reason(path: Path) -> str | None:
    """Explain why a root cannot be safely inspected and extended."""
    absolute = lexical_absolute(path)
    current = Path(absolute.anchor)
    nearest_existing = current
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            try:
                target = current.resolve(strict=True)
            except (OSError, RuntimeError):
                return "dangling or cyclic symlink in root path"
            if not target.is_dir():
                return "symlink in root path does not target a directory"
            nearest_existing = current
        elif current.exists():
            if not current.is_dir():
                return "regular file blocks the root path"
            nearest_existing = current

        if current.exists() and (
            not permission_bits_allow(current, stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            or not os.access(current, os.X_OK)
        ):
            return f"permission denied while traversing {current}"

    read_mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
    write_mode = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
    traverse_mode = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    if absolute.is_dir():
        if (
            not permission_bits_allow(
                absolute,
                read_mode,
                write_mode,
                traverse_mode,
            )
            or not os.access(absolute, os.R_OK | os.W_OK | os.X_OK)
        ):
            return "permission denied: existing root requires read, write, and traverse access"
    elif (
        not permission_bits_allow(
            nearest_existing,
            write_mode,
            traverse_mode,
        )
        or not os.access(nearest_existing, os.W_OK | os.X_OK)
    ):
        return f"permission denied: cannot create root below {nearest_existing}"
    return None


def root_path_is_blocked(path: Path) -> bool:
    return root_path_block_reason(path) is not None


def has_lifecycle_lane_identity(path: Path) -> bool:
    return path.name in LIFECYCLE_LANES and path.parent.name == "skills"


def is_lifecycle_lane(path: Path) -> bool:
    lexical = lexical_absolute(path)
    if has_lifecycle_lane_identity(lexical):
        return True
    resolved = resolved_path(lexical)
    return resolved is not None and has_lifecycle_lane_identity(resolved)


def matching_global_root_specs(path: Path) -> list[RootSpec]:
    """Return exact lexical matches first, then any resolved aliases."""
    lexical = lexical_absolute(path)
    exact = [
        spec
        for spec in GLOBAL_ROOTS
        if lexical_absolute(spec.path) == lexical
    ]
    if exact:
        return exact

    resolved = resolved_path(lexical)
    if resolved is None:
        return []
    return [
        spec
        for spec in GLOBAL_ROOTS
        if resolved_path(spec.path) == resolved
    ]


def find_global_root_spec(path: Path) -> RootSpec | None:
    matches = matching_global_root_specs(path)
    return matches[0] if matches else None


def matching_project_root_spec(repo_root: Path, path: Path) -> RootSpec | None:
    lexical = lexical_absolute(path)
    for spec in PROJECT_ROOTS:
        if lexical_absolute(repo_root / spec.path) == lexical:
            return spec
    return None


def project_path_is_contained(repo_root: Path, path: Path) -> bool:
    repo_resolved = resolved_path(repo_root)
    path_resolved = resolved_path(path)
    if repo_resolved is None or path_resolved is None:
        return False
    return path_resolved.is_relative_to(repo_resolved)


def path_is_lexically_within(root: Path, path: Path) -> bool:
    return lexical_absolute(path).is_relative_to(lexical_absolute(root))


def project_path_uses_symlink(repo_root: Path, path: Path) -> bool:
    repo = lexical_absolute(repo_root)
    candidate = lexical_absolute(path)
    try:
        relative = candidate.relative_to(repo)
    except ValueError:
        return False
    current = repo
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            return True
    return False


def eligible_current_root(
    repo_root: Path | None,
    detected_root: Path | None,
) -> Path | None:
    if detected_root is None:
        return None
    lexical = lexical_absolute(detected_root)
    if is_lifecycle_lane(lexical) or root_path_is_blocked(lexical):
        return None
    if repo_root is not None and path_is_lexically_within(repo_root, lexical):
        project_spec = matching_project_root_spec(repo_root, lexical)
        if project_spec is None:
            return None
        if project_path_uses_symlink(repo_root, lexical):
            return None
        return lexical if project_path_is_contained(repo_root, lexical) else None
    if find_global_root_spec(lexical) is not None:
        return lexical
    return None


def build_candidates(
    repo_root: Path | None,
    current_root: Path | None,
    excluded_roots: list[ExcludedRoot] | None = None,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: dict[tuple[Path, bool], Candidate] = {}
    excluded_seen: set[tuple[str, str, str]] = set()

    def exclude(path: Path, scope: str, source: str, reason: str) -> None:
        if excluded_roots is None:
            return
        item = ExcludedRoot(str(lexical_absolute(path)), scope, source, reason)
        key = (item.path, item.source, item.reason)
        if key not in excluded_seen:
            excluded_roots.append(item)
            excluded_seen.add(key)

    def add(
        path: Path,
        scope: str,
        source: str,
        compatible_harnesses: tuple[str, ...],
    ) -> None:
        lexical = lexical_absolute(path)
        if is_lifecycle_lane(lexical):
            exclude(lexical, scope, source, "lifecycle lane requires explicit placement")
            return
        blocked_reason = root_path_block_reason(lexical)
        if blocked_reason is not None:
            exclude(lexical, scope, source, blocked_reason)
            return
        resolved = resolved_path(lexical)
        if resolved is None:
            exclude(lexical, scope, source, "root path could not be resolved")
            return
        if scope == "project":
            if repo_root is None:
                exclude(lexical, scope, source, "project repository is unavailable")
                return
            if project_path_uses_symlink(repo_root, lexical):
                exclude(
                    lexical,
                    scope,
                    source,
                    "project roots must be lexical directories, not symlink aliases",
                )
                return
            if not project_path_is_contained(repo_root, lexical):
                exclude(lexical, scope, source, "project root resolves outside repository")
                return

        # Publication roots are source layouts, not harness discovery aliases.
        # Keep them separate when a symlink resolves to a harness-specific root.
        identity = (resolved, source == "public-repo")
        current_match = (
            current_root is not None
            and lexical_absolute(current_root) == lexical
        )
        existing_candidate = seen.get(identity)
        if existing_candidate is not None:
            if source != "public-repo":
                existing_candidate.compatible_harnesses = tuple(
                    sorted(
                        set(existing_candidate.compatible_harnesses)
                        | set(compatible_harnesses)
                    )
                )
            if current_match:
                existing_candidate.current_install_root = True
                existing_candidate.reason = (
                    "current skill is already running from this skills root"
                )
            return

        exists = lexical.is_dir()
        skill_count = count_skills(lexical)
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
                path=str(lexical),
                scope=scope,
                source=source,
                exists=exists,
                skill_count=skill_count,
                current_install_root=current_match,
                compatible_harnesses=compatible_harnesses,
                reason=reason,
            )
        )
        seen[identity] = candidates[-1]

    # Add a recognized current root first so resolved aliases retain the path
    # through which the creator was invoked while still merging compatibility.
    if current_root is not None and not is_lifecycle_lane(current_root):
        current_is_project_root = False
        current_is_inside_repo = (
            repo_root is not None
            and path_is_lexically_within(repo_root, current_root)
        )
        if repo_root is not None:
            current_project_spec = matching_project_root_spec(repo_root, current_root)
            if current_project_spec is not None:
                current_is_project_root = True
                add(
                    current_root,
                    "project",
                    current_project_spec.source,
                    current_project_spec.compatible_harnesses,
                )
        current_global_specs = (
            []
            if current_is_project_root or current_is_inside_repo
            else matching_global_root_specs(current_root)
        )
        if current_global_specs:
            current_global_spec = current_global_specs[0]
            add(
                current_root,
                "global",
                current_global_spec.source,
                current_global_spec.compatible_harnesses,
            )

    if repo_root is not None:
        for spec in PROJECT_ROOTS:
            add(
                repo_root / spec.path,
                "project",
                spec.source,
                spec.compatible_harnesses,
            )

    for spec in GLOBAL_ROOTS:
        add(spec.path, "global", spec.source, spec.compatible_harnesses)

    return candidates


def supports_harness(candidate: Candidate, target_harness: str) -> bool:
    return target_harness in candidate.compatible_harnesses


def is_publication_root(candidate: Candidate) -> bool:
    return candidate.source == "public-repo"


def is_neutral_root(candidate: Candidate) -> bool:
    return is_publication_root(candidate) or candidate.source in {
        "project-shared",
        "global-shared",
    }


def most_populated(candidates: list[Candidate]) -> Candidate:
    """Choose deterministically, preserving a public source layout on ties."""
    return min(
        candidates,
        key=lambda item: (
            -item.skill_count,
            -is_publication_root(item),
            item.path,
        ),
    )


def parse_skill_name(value: str) -> str:
    if not 1 <= len(value) <= 64:
        raise argparse.ArgumentTypeError("skill name must be 1-64 characters")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", value) or "--" in value:
        raise argparse.ArgumentTypeError(
            "skill name must use lowercase letters, digits, and single hyphens"
        )
    return value


def infer_current_harness(current_root: Path | None) -> str | None:
    if current_root is None:
        return None
    exact_specs = [
        spec
        for spec in GLOBAL_ROOTS
        if lexical_absolute(spec.path) == lexical_absolute(current_root)
    ]
    specs = exact_specs or matching_global_root_specs(current_root)
    harnesses = {
        harness
        for spec in specs
        for harness in spec.compatible_harnesses
    }
    if len(harnesses) != 1:
        return None
    return next(iter(harnesses))


def candidate_for_path(
    candidates: list[Candidate],
    path: Path | None,
    *,
    source: str | None = None,
    allow_resolved_alias: bool = True,
) -> Candidate | None:
    if path is None:
        return None
    lexical = lexical_absolute(path)
    if root_path_is_blocked(lexical) or is_lifecycle_lane(lexical):
        return None
    exact = [
        candidate
        for candidate in candidates
        if lexical_absolute(Path(candidate.path)) == lexical
        and (source is None or candidate.source == source)
    ]
    if exact:
        return exact[0]
    if not allow_resolved_alias:
        return None

    resolved = resolved_path(lexical)
    if resolved is None:
        return None
    matches = [
        candidate
        for candidate in candidates
        if resolved_path(Path(candidate.path)) == resolved
        and (source is None or candidate.source == source)
    ]
    return matches[0] if matches else None


def choose_candidate(
    repo_root: Path | None,
    current_root: Path | None,
    candidates: list[Candidate],
    target_harness: str | None,
) -> tuple[Candidate, str, str | None]:
    if not candidates:
        raise ValueError("no usable skill roots were found")
    project_candidates = [candidate for candidate in candidates if candidate.scope == "project"]
    global_candidates = [candidate for candidate in candidates if candidate.scope == "global"]
    effective_harness = target_harness or infer_current_harness(current_root)

    project_with_skills = [
        candidate for candidate in project_candidates if candidate.skill_count > 0
    ]
    if effective_harness:
        compatible_projects = [
            candidate
            for candidate in project_with_skills
            if is_publication_root(candidate)
            or supports_harness(candidate, effective_harness)
        ]
    else:
        neutral_projects = [
            candidate for candidate in project_with_skills if is_neutral_root(candidate)
        ]
        if neutral_projects:
            compatible_projects = neutral_projects
        elif project_with_skills:
            common_harnesses = set(project_with_skills[0].compatible_harnesses)
            for candidate in project_with_skills[1:]:
                common_harnesses.intersection_update(candidate.compatible_harnesses)
            compatible_projects = project_with_skills if common_harnesses else []
        else:
            compatible_projects = []

    if compatible_projects:
        chosen = most_populated(compatible_projects)
        if is_publication_root(chosen):
            reason = (
                "this repository already uses an established publication layout "
                f"with {chosen.skill_count} skill(s) under {chosen.path}"
            )
        else:
            reason = (
                f"this repository already keeps {chosen.skill_count} compatible skill(s) "
                f"under {chosen.path}"
            )
        return (
            chosen,
            reason,
            effective_harness,
        )

    if repo_root and current_root and project_path_is_contained(repo_root, current_root):
        chosen = candidate_for_path(
            candidates,
            current_root,
            allow_resolved_alias=False,
        )
        if chosen is not None and chosen.scope == "project" and (
            effective_harness is None
            or supports_harness(chosen, effective_harness)
        ):
            return (
                chosen,
                "this skill is already running from a repo-local skills root",
                effective_harness,
            )

    current_is_inside_repo = (
        repo_root is not None
        and current_root is not None
        and path_is_lexically_within(repo_root, current_root)
    )
    current_candidate = candidate_for_path(
        candidates,
        current_root,
        allow_resolved_alias=not current_is_inside_repo,
    )
    if current_candidate is not None and current_candidate.scope == "global":
        if effective_harness is None or supports_harness(current_candidate, effective_harness):
            return (
                current_candidate,
                "this skill is already running from the current global skills family",
                effective_harness,
            )

    global_with_skills = [
        candidate
        for candidate in global_candidates
        if candidate.skill_count > 0
        and (
            supports_harness(candidate, effective_harness)
            if effective_harness
            else is_neutral_root(candidate)
        )
    ]
    if global_with_skills:
        chosen = most_populated(global_with_skills)
        reason = (
            f"a compatible global library already keeps {chosen.skill_count} skill(s) here"
            if effective_harness
            else f"the shared global library already keeps {chosen.skill_count} skill(s) here"
        )
        return (
            chosen,
            reason,
            effective_harness,
        )

    if repo_root is not None:
        public_root = candidate_for_path(
            candidates,
            repo_root / "skills",
            source="public-repo",
            allow_resolved_alias=False,
        )
        public_root_is_current = (
            public_root is not None
            and current_root is not None
            and lexical_absolute(current_root) == lexical_absolute(Path(public_root.path))
        )
        if (
            public_root is not None
            and public_root_is_current
            and effective_harness is None
        ):
            return (
                public_root,
                "this repository already uses the public skills/<skill-name> layout",
                effective_harness,
            )

        shared_root = candidate_for_path(
            candidates,
            repo_root / ".agents/skills",
            allow_resolved_alias=False,
        )
        if shared_root is not None and (
            effective_harness is None
            or supports_harness(shared_root, effective_harness)
        ):
            if project_with_skills and not compatible_projects:
                reason = (
                    "project skill roots target incompatible harnesses; use the "
                    "shared repo fallback or rerun with --target-harness"
                )
            else:
                reason = (
                    "no project-local skill root is established yet, so use the "
                    "shared repo fallback"
                )
            return shared_root, reason, effective_harness

        if effective_harness is not None:
            compatible_project_fallbacks = [
                candidate
                for candidate in project_candidates
                if supports_harness(candidate, effective_harness)
            ]
            if compatible_project_fallbacks:
                fallback = most_populated(compatible_project_fallbacks)
                return (
                    fallback,
                    "the shared repo root is blocked, so use another compatible "
                    "project root",
                    effective_harness,
                )

    if effective_harness is not None:
        default_source = DEFAULT_GLOBAL_SOURCE.get(effective_harness)
        fallback = next(
            (candidate for candidate in global_candidates if candidate.source == default_source),
            None,
        )
        if fallback is not None:
            reason = (
                "no established compatible root was found, so use the "
                f"{effective_harness} global fallback"
            )
            return (
                fallback,
                reason,
                effective_harness,
            )
        compatible_global_fallbacks = [
            candidate
            for candidate in global_candidates
            if supports_harness(candidate, effective_harness)
        ]
        if compatible_global_fallbacks:
            fallback = most_populated(compatible_global_fallbacks)
            return (
                fallback,
                "the default global root is blocked, so use another compatible root",
                effective_harness,
            )

    shared_global = candidate_for_path(candidates, HOME / ".agents/skills")
    if shared_global is not None and (
        effective_harness is None
        or supports_harness(shared_global, effective_harness)
    ):
        reason = (
            "no target harness was supplied, so use the shared global fallback "
            "instead of choosing across incompatible libraries"
        )
        return (
            shared_global,
            reason,
            effective_harness,
        )

    raise ValueError("no usable compatible skill root was found")


def rank_alternatives(
    chosen: Candidate,
    candidates: list[Candidate],
    effective_harness: str | None,
) -> list[str]:
    compatible = [
        candidate
        for candidate in candidates
        if candidate.path != chosen.path
        and (
            supports_harness(candidate, effective_harness)
            if effective_harness
            else is_neutral_root(candidate)
        )
    ]
    ranked = sorted(
        compatible,
        key=lambda item: (
            -(item.scope == chosen.scope),
            -item.skill_count,
            -item.exists,
            item.path,
        ),
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
        type=parse_skill_name,
        help="Optional skill name to include in human-readable output",
    )
    parser.add_argument(
        "--target-harness",
        choices=TARGET_HARNESSES,
        default=None,
        help="Constrain selection to roots discoverable by this harness",
    )
    args = parser.parse_args()

    cwd = Path(args.cwd).expanduser().resolve()
    if not cwd.exists():
        parser.error(f"--cwd does not exist: {cwd}")
    if not cwd.is_dir():
        parser.error(f"--cwd must be a directory: {cwd}")
    repo_root = git_repo_root(cwd)
    current_root = eligible_current_root(repo_root, detect_current_install_root())
    excluded_roots: list[ExcludedRoot] = []
    candidates = build_candidates(repo_root, current_root, excluded_roots)
    try:
        chosen, reason, effective_harness = choose_candidate(
            repo_root,
            current_root,
            candidates,
            args.target_harness,
        )
    except ValueError as exc:
        details = "; ".join(
            f"{item.path}: {item.reason}" for item in excluded_roots[:3]
        )
        parser.error(f"{exc}; excluded roots: {details}" if details else str(exc))
    recommended_root = Path(chosen.path)
    recommended_destination = (
        recommended_root / args.skill_name if args.skill_name else None
    )

    payload = {
        "cwd": str(cwd),
        "repo_root": str(repo_root) if repo_root else None,
        "current_install_root": str(current_root) if current_root else None,
        "target_harness": args.target_harness,
        "effective_harness": effective_harness,
        "recommended_root": str(recommended_root),
        "recommended_destination": (
            str(recommended_destination) if recommended_destination else None
        ),
        "recommended_scope": chosen.scope,
        "reason": reason,
        "alternatives": rank_alternatives(chosen, candidates, effective_harness),
        "candidates": [asdict(candidate) for candidate in candidates],
        "excluded_roots": [asdict(item) for item in excluded_roots],
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
            alternative = Path(alternatives[0])
            if args.skill_name:
                alternative /= args.skill_name
            print(f"Alternative: {alternative}")
        return 0

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

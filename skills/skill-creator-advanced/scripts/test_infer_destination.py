#!/usr/bin/env python3
"""Regression tests for infer_destination.py placement policy."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from typing import Iterator
from unittest import mock

import infer_destination


SCRIPT = Path(__file__).resolve().parent / "infer_destination.py"


def lexical(path: Path) -> Path:
    return infer_destination.lexical_absolute(path)


def write_skill(root: Path, name: str) -> None:
    skill = root / name
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test fixture.\n---\n",
        encoding="utf-8",
    )


def write_git_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")


def global_specs(home: Path, codex_home: Path | None = None) -> list[infer_destination.RootSpec]:
    specs: list[infer_destination.RootSpec] = []
    if codex_home is not None:
        specs.append(
            infer_destination.RootSpec(
                codex_home / "skills",
                "global-codex-home",
                ("codex",),
            )
        )
    specs.extend(
        [
            infer_destination.RootSpec(
                home / ".agents/skills",
                "global-shared",
                infer_destination.SHARED_HARNESSES,
            ),
            infer_destination.RootSpec(
                home / ".claude/skills",
                "global-claude",
                ("claude", "opencode"),
            ),
            infer_destination.RootSpec(
                home / ".codex/skills",
                "global-codex",
                ("codex",),
            ),
            infer_destination.RootSpec(
                home / ".copilot/skills",
                "global-copilot",
                ("copilot",),
            ),
            infer_destination.RootSpec(
                home / ".gemini/skills",
                "global-gemini",
                ("gemini",),
            ),
            infer_destination.RootSpec(
                home / ".config/opencode/skills",
                "global-opencode",
                ("opencode",),
            ),
        ]
    )
    return specs


@contextmanager
def isolated_global_policy(
    home: Path,
    *,
    codex_home: Path | None = None,
) -> Iterator[None]:
    original_home = infer_destination.HOME
    original_roots = infer_destination.GLOBAL_ROOTS
    original_defaults = infer_destination.DEFAULT_GLOBAL_SOURCE
    infer_destination.HOME = home
    infer_destination.GLOBAL_ROOTS = global_specs(home, codex_home)
    infer_destination.DEFAULT_GLOBAL_SOURCE = {
        "agents": "global-shared",
        "codex": "global-codex-home" if codex_home else "global-codex",
        "copilot": "global-copilot",
        "gemini": "global-gemini",
        "opencode": "global-opencode",
    }
    try:
        yield
    finally:
        infer_destination.HOME = original_home
        infer_destination.GLOBAL_ROOTS = original_roots
        infer_destination.DEFAULT_GLOBAL_SOURCE = original_defaults


def select(
    repo: Path | None,
    current_root: Path | None,
    target: str | None,
) -> tuple[infer_destination.Candidate, str | None, list[infer_destination.Candidate]]:
    candidates = infer_destination.build_candidates(repo, current_root)
    chosen, _, effective = infer_destination.choose_candidate(
        repo,
        current_root,
        candidates,
        target,
    )
    return chosen, effective, candidates


def test_target_compatibility_table() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-target-") as temp_dir:
        home = Path(temp_dir) / "home"
        roots = {
            "agents": (home / ".agents/skills", "global-shared"),
            "codex": (home / ".codex/skills", "global-codex"),
            "copilot": (home / ".copilot/skills", "global-copilot"),
            "gemini": (home / ".gemini/skills", "global-gemini"),
            "opencode": (home / ".config/opencode/skills", "global-opencode"),
        }
        for index in range(2):
            write_skill(roots["agents"][0], f"shared-{index}")
        for target, (root, _) in roots.items():
            if target == "agents":
                continue
            for index in range(5):
                write_skill(root, f"{target}-{index}")

        with isolated_global_policy(home):
            assert set(roots) == set(infer_destination.TARGET_HARNESSES)
            for target, (expected_root, expected_source) in roots.items():
                chosen, effective, candidates = select(None, None, target)
                assert chosen.source == expected_source, (target, chosen.source)
                assert chosen.path == str(lexical(expected_root))
                assert effective == target
                alternatives = infer_destination.rank_alternatives(
                    chosen,
                    candidates,
                    effective,
                )
                for path in alternatives:
                    alternative = infer_destination.candidate_for_path(
                        candidates,
                        Path(path),
                    )
                    assert alternative is not None
                    assert infer_destination.supports_harness(alternative, target)


def test_project_target_compatibility_table() -> None:
    project_roots = {
        "agents": (Path(".agents/skills"), "project-shared"),
        "codex": (Path(".codex/skills"), "project-codex"),
        "copilot": (Path(".github/skills"), "project-copilot"),
        "gemini": (Path(".gemini/skills"), "project-gemini"),
        "opencode": (Path(".opencode/skills"), "project-opencode"),
    }
    assert set(project_roots) == set(infer_destination.TARGET_HARNESSES)

    for target, (relative_root, expected_source) in project_roots.items():
        with tempfile.TemporaryDirectory(
            prefix=f"placement-project-{target}-"
        ) as temp_dir:
            base = Path(temp_dir)
            repo = base / "repo"
            home = base / "home"
            for index in range(3):
                write_skill(repo / relative_root, f"{target}-{index}")
            if target != "agents":
                write_skill(repo / ".agents/skills", "shared-one")
            for index in range(8):
                write_skill(repo / ".cursor/skills", f"incompatible-{index}")

            with isolated_global_policy(home):
                chosen, effective, _ = select(repo, None, target)
                assert chosen.source == expected_source, (target, chosen.source)
                assert chosen.path == str(lexical(repo / relative_root))
                assert effective == target


def test_current_family_precedes_larger_global_library() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-current-") as temp_dir:
        home = Path(temp_dir) / "home"
        current_root = home / ".codex/skills"
        write_skill(current_root, "creator")
        for index in range(8):
            write_skill(home / ".agents/skills", f"shared-{index}")
        for index in range(12):
            write_skill(home / ".claude/skills", f"claude-{index}")

        with isolated_global_policy(home):
            chosen, effective, _ = select(None, current_root, None)
            assert chosen.path == str(lexical(current_root))
            assert effective == "codex"


def test_neutral_fallback_ignores_larger_vendor_libraries() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-neutral-") as temp_dir:
        home = Path(temp_dir) / "home"
        write_skill(home / ".agents/skills", "shared-one")
        for index in range(9):
            write_skill(home / ".claude/skills", f"claude-{index}")
        for index in range(6):
            write_skill(home / ".codex/skills", f"codex-{index}")

        with isolated_global_policy(home):
            chosen, effective, _ = select(None, None, None)
            assert chosen.source == "global-shared"
            assert effective is None


def test_empty_public_root_and_lifecycle_lanes_do_not_steal_placement() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-project-") as temp_dir:
        base = Path(temp_dir)
        home = base / "home"
        repo = base / "repo"
        (repo / "skills").mkdir(parents=True)

        with isolated_global_policy(home):
            chosen, _, _ = select(repo, None, None)
            assert chosen.source == "project-shared"

            write_skill(repo / "skills/.experimental", "experimental-one")
            write_skill(repo / "skills/.system", "system-one")
            chosen, _, candidates = select(repo, None, None)
            assert chosen.source == "project-shared"
            assert all(
                candidate.source
                not in {"public-curated", "public-experimental", "public-system"}
                for candidate in candidates
            )

            write_skill(repo / "skills", "stable-one")
            chosen, _, _ = select(repo, None, None)
            assert chosen.source == "public-repo"


def test_unrelated_source_checkout_is_not_current_family() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-source-") as temp_dir:
        base = Path(temp_dir)
        source_root = base / "source/skills"
        repo = base / "unrelated"
        source_root.mkdir(parents=True)
        repo.mkdir()
        assert infer_destination.eligible_current_root(repo, source_root) is None
        inside_unrecognized = repo / "custom/skills"
        inside_unrecognized.mkdir(parents=True)
        assert infer_destination.eligible_current_root(
            repo,
            inside_unrecognized,
        ) is None


def test_git_nonzero_and_runtime_errors_do_not_use_manual_discovery() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-git-authority-") as temp_dir:
        repo = Path(temp_dir) / "repo"
        nested = repo / "nested"
        write_git_directory(repo / ".git")
        nested.mkdir()

        rejected = subprocess.CalledProcessError(128, ["git", "rev-parse"])
        with mock.patch.object(infer_destination.subprocess, "run", side_effect=rejected):
            assert infer_destination.git_repo_root(nested) is None
        with mock.patch.object(
            infer_destination.subprocess,
            "run",
            side_effect=PermissionError("git executable is not runnable"),
        ):
            assert infer_destination.git_repo_root(nested) is None


def test_manual_git_discovery_validates_directories_files_and_boundaries() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-git-manual-") as temp_dir:
        base = Path(temp_dir)
        repo = base / "repo"
        nested = repo / "nested"
        write_git_directory(repo / ".git")
        nested.mkdir(parents=True)

        unavailable = FileNotFoundError("git executable is unavailable")
        with mock.patch.object(
            infer_destination.subprocess,
            "run",
            side_effect=unavailable,
        ):
            assert infer_destination.git_repo_root(nested) == repo.resolve()

        git_data = base / "git-data"
        write_git_directory(git_data)
        worktree = base / "worktree"
        worktree.mkdir()
        (worktree / ".git").write_text("gitdir: ../git-data\n", encoding="utf-8")
        with mock.patch.object(
            infer_destination.subprocess,
            "run",
            side_effect=unavailable,
        ):
            assert infer_destination.git_repo_root(worktree) == worktree.resolve()

        invalid_boundary = repo / "nested-invalid"
        (invalid_boundary / ".git").mkdir(parents=True)
        leaf = invalid_boundary / "leaf"
        leaf.mkdir()
        with mock.patch.object(
            infer_destination.subprocess,
            "run",
            side_effect=unavailable,
        ):
            assert infer_destination.git_repo_root(leaf) is None

        invalid_file = repo / "nested-file"
        invalid_file.mkdir()
        (invalid_file / ".git").write_text("not a gitdir marker\n", encoding="utf-8")
        with mock.patch.object(
            infer_destination.subprocess,
            "run",
            side_effect=unavailable,
        ):
            assert infer_destination.git_repo_root(invalid_file) is None


def test_incompatible_current_project_root_does_not_bypass_target() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-incompatible-current-") as temp_dir:
        base = Path(temp_dir)
        repo = base / "repo"
        home = base / "home"
        current_root = repo / ".gemini/skills"
        for index in range(6):
            write_skill(current_root, f"gemini-{index}")

        with isolated_global_policy(home):
            chosen, effective, _ = select(repo, current_root, "codex")
            assert chosen.source == "project-shared"
            assert chosen.path == str(lexical(repo / ".agents/skills"))
            assert effective == "codex"


def test_lifecycle_lane_is_never_an_inferred_current_root() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-lifecycle-") as temp_dir:
        base = Path(temp_dir)
        repo = base / "repo"
        home = base / "home"
        lane = repo / "skills/.experimental"
        write_skill(lane, "creator")
        write_skill(repo / "skills", "stable-one")

        assert infer_destination.eligible_current_root(repo, lane) is None
        with isolated_global_policy(home):
            chosen, _, candidates = select(repo, lane, None)
            assert all(Path(candidate.path) != lexical(lane) for candidate in candidates)
            assert chosen.source == "public-repo"
            assert chosen.path == str(lexical(repo / "skills"))


def test_lifecycle_name_in_repo_ancestry_does_not_block_ordinary_roots() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-lifecycle-ancestor-") as temp_dir:
        base = Path(temp_dir)
        repo = base / "skills/.experimental/ordinary-repo"
        home = base / "home"
        repo.mkdir(parents=True)

        ordinary_root = repo / ".agents/skills"
        assert not infer_destination.is_lifecycle_lane(ordinary_root)
        with isolated_global_policy(home):
            chosen, _, candidates = select(repo, None, "agents")
        assert chosen.source == "project-shared"
        assert chosen.path == str(lexical(ordinary_root))
        assert any(Path(candidate.path) == lexical(ordinary_root) for candidate in candidates)


def test_symlink_alias_into_lifecycle_lane_is_rejected() -> None:
    if os.name == "nt":
        return
    with tempfile.TemporaryDirectory(prefix="placement-lifecycle-alias-") as temp_dir:
        base = Path(temp_dir)
        repo = base / "repo"
        home = base / "home"
        lane = repo / "skills/.experimental"
        shared_alias = repo / ".agents/skills"
        lane.mkdir(parents=True)
        shared_alias.parent.mkdir(parents=True)
        try:
            shared_alias.symlink_to(lane, target_is_directory=True)
        except OSError:
            return

        assert infer_destination.is_lifecycle_lane(shared_alias)
        assert infer_destination.eligible_current_root(repo, shared_alias) is None
        with isolated_global_policy(home):
            chosen, _, candidates = select(repo, shared_alias, "agents")
        assert all(Path(candidate.path) != lexical(shared_alias) for candidate in candidates)
        assert chosen.path != str(lexical(shared_alias))


def test_publication_root_does_not_claim_target_compatibility() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-public-contract-") as temp_dir:
        base = Path(temp_dir)
        repo = base / "repo"
        home = base / "home"
        (repo / "skills").mkdir(parents=True)

        with isolated_global_policy(home):
            empty_chosen, _, _ = select(repo, repo / "skills", "codex")
        assert empty_chosen.source == "project-shared"

        for index in range(5):
            write_skill(repo / "skills", f"published-{index}")

        with isolated_global_policy(home):
            chosen, effective, candidates = select(repo, None, "codex")

        publication = next(
            candidate for candidate in candidates if candidate.source == "public-repo"
        )
        assert publication.compatible_harnesses == ()
        assert not infer_destination.supports_harness(publication, "codex")
        assert chosen.source == "public-repo"
        assert effective == "codex"


def test_external_project_symlink_is_rejected_without_losing_lexical_roots() -> None:
    if os.name == "nt":
        return
    with tempfile.TemporaryDirectory(prefix="placement-project-escape-") as temp_dir:
        base = Path(temp_dir)
        repo = base / "repo"
        home = base / "home"
        external = base / "external-skills"
        repo.mkdir()
        write_skill(external, "outside-one")
        try:
            (repo / "skills").symlink_to(external, target_is_directory=True)
        except OSError:
            return

        with isolated_global_policy(home):
            chosen, _, candidates = select(repo, None, None)
            assert not any(candidate.source == "public-repo" for candidate in candidates)
            assert chosen.source == "project-shared"
            assert chosen.path == str(lexical(repo / ".agents/skills"))


def test_project_root_symlinks_to_in_repo_locations_are_rejected() -> None:
    if os.name == "nt":
        return
    with tempfile.TemporaryDirectory(prefix="placement-project-alias-") as temp_dir:
        base = Path(temp_dir)
        repo = base / "repo"
        home = base / "home"
        git_dir = repo / ".git"
        git_dir.mkdir(parents=True)
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        shared_alias = repo / ".agents/skills"
        public_alias = repo / "skills"
        shared_alias.parent.mkdir(parents=True)
        try:
            shared_alias.symlink_to(git_dir, target_is_directory=True)
            public_alias.symlink_to(git_dir, target_is_directory=True)
        except OSError:
            return

        excluded: list[infer_destination.ExcludedRoot] = []
        with isolated_global_policy(home):
            candidates = infer_destination.build_candidates(repo, None, excluded)

        assert not any(
            candidate.source in {"project-shared", "public-repo"}
            for candidate in candidates
        )
        rejected = {
            item.source
            for item in excluded
            if "not symlink aliases" in item.reason
        }
        assert {"project-shared", "public-repo"}.issubset(rejected)
        assert infer_destination.eligible_current_root(repo, shared_alias) is None
        assert infer_destination.candidate_for_path(
            candidates,
            shared_alias,
            allow_resolved_alias=False,
        ) is None


def test_global_resolved_aliases_merge_harness_metadata() -> None:
    if os.name == "nt":
        return
    with tempfile.TemporaryDirectory(prefix="placement-alias-") as temp_dir:
        base = Path(temp_dir)
        home = base / "home"
        copilot_root = home / ".copilot/skills"
        gemini_root = home / ".gemini/skills"
        write_skill(copilot_root, "shared-target")
        gemini_root.parent.mkdir(parents=True)
        try:
            gemini_root.symlink_to(copilot_root, target_is_directory=True)
        except OSError:
            return

        with isolated_global_policy(home):
            candidates = infer_destination.build_candidates(None, gemini_root)

        resolved = copilot_root.resolve()
        aliases = [
            candidate
            for candidate in candidates
            if infer_destination.resolved_path(Path(candidate.path)) == resolved
        ]
        assert len(aliases) == 1
        candidate = aliases[0]
        assert {"copilot", "gemini"}.issubset(candidate.compatible_harnesses)
        assert candidate.path == str(lexical(gemini_root))
        assert candidate.current_install_root


def test_blocked_roots_are_not_candidates() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-blocked-") as temp_dir:
        base = Path(temp_dir)
        repo = base / "repo"
        home = base / "home"
        (repo / ".agents").mkdir(parents=True)
        (repo / ".agents/skills").write_text("not a directory\n", encoding="utf-8")
        (repo / ".github").write_text("blocked parent\n", encoding="utf-8")
        blocked = {
            lexical(repo / ".agents/skills"),
            lexical(repo / ".github/skills"),
        }

        (repo / ".codex").mkdir(parents=True)
        try:
            (repo / ".codex/skills").symlink_to(
                repo / "missing-codex-root",
                target_is_directory=True,
            )
        except OSError:
            pass
        else:
            blocked.add(lexical(repo / ".codex/skills"))

        (home / ".gemini").mkdir(parents=True)
        (home / ".gemini/skills").write_text("not a directory\n", encoding="utf-8")
        (home / ".config/opencode").mkdir(parents=True)
        try:
            (home / ".config/opencode/skills").symlink_to(
                home / "missing-opencode-root",
                target_is_directory=True,
            )
        except OSError:
            pass
        else:
            blocked.add(lexical(home / ".config/opencode/skills"))
        blocked.add(lexical(home / ".gemini/skills"))

        with isolated_global_policy(home):
            candidates = infer_destination.build_candidates(repo, None)

        paths = {Path(candidate.path) for candidate in candidates}
        assert paths.isdisjoint(blocked)
        for blocked_root in blocked:
            assert infer_destination.root_path_is_blocked(blocked_root)
        if (repo / ".codex/skills").is_symlink():
            assert infer_destination.eligible_current_root(
                repo,
                repo / ".codex/skills",
            ) is None


def test_all_target_compatible_roots_blocked_fails_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-blocked-target-") as temp_dir:
        home = Path(temp_dir) / "home"
        (home / ".agents").mkdir(parents=True)
        (home / ".agents/skills").write_text("blocked\n", encoding="utf-8")

        with isolated_global_policy(home):
            candidates = infer_destination.build_candidates(None, None)
            assert not any(
                infer_destination.supports_harness(candidate, "agents")
                for candidate in candidates
            )
            try:
                infer_destination.choose_candidate(
                    None,
                    None,
                    candidates,
                    "agents",
                )
            except ValueError as exc:
                assert "compatible skill root" in str(exc)
            else:
                raise AssertionError("incompatible fallback was selected")


def test_dangling_shared_alias_cannot_resurrect_incompatible_root() -> None:
    if os.name == "nt":
        return
    with tempfile.TemporaryDirectory(prefix="placement-dangling-shared-") as temp_dir:
        base = Path(temp_dir)
        repo = base / "repo"
        home = base / "home"
        shared = repo / ".agents/skills"
        shared.parent.mkdir(parents=True)
        try:
            shared.symlink_to(
                repo / ".codex/skills",
                target_is_directory=True,
            )
        except OSError:
            return
        (home / ".agents").mkdir(parents=True)
        (home / ".agents/skills").write_text("blocked\n", encoding="utf-8")

        with isolated_global_policy(home):
            candidates = infer_destination.build_candidates(repo, None)
            codex_candidate = next(
                candidate
                for candidate in candidates
                if candidate.source == "project-codex"
            )
            assert not infer_destination.supports_harness(codex_candidate, "agents")
            assert infer_destination.candidate_for_path(candidates, shared) is None
            try:
                infer_destination.choose_candidate(
                    repo,
                    None,
                    candidates,
                    "agents",
                )
            except ValueError as exc:
                assert "compatible skill root" in str(exc)
            else:
                raise AssertionError("dangling alias resurrected an incompatible root")


def test_skill_count_uses_immediate_child_packages_only() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-count-") as temp_dir:
        root = Path(temp_dir) / "skills"
        root.mkdir(parents=True)
        (root / "SKILL.md").write_text("root marker\n", encoding="utf-8")
        write_skill(root, "direct-skill")
        write_skill(root / "category", "nested-skill")
        assert infer_destination.count_skills(root) == 1


def test_codex_home_deduplicates_same_resolved_root() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-codex-home-") as temp_dir:
        home = Path(temp_dir) / "home"
        codex_home = home / ".codex"
        write_skill(codex_home / "skills", "creator")

        with isolated_global_policy(home, codex_home=codex_home):
            candidates = infer_destination.build_candidates(None, codex_home / "skills")
            matching = [
                candidate
                for candidate in candidates
                if Path(candidate.path) == lexical(codex_home / "skills")
            ]
            assert len(matching) == 1
            assert matching[0].source == "global-codex-home"
            chosen, _, _ = infer_destination.choose_candidate(
                None,
                codex_home / "skills",
                candidates,
                "codex",
            )
            assert chosen.source == "global-codex-home"


def test_name_validation_table_and_cli_containment() -> None:
    valid_names = ["a", "skill-1", "abc123"]
    invalid_names = [
        "/tmp/escape",
        "../../escape",
        "bad\nname",
        "Uppercase",
        "double--hyphen",
        "trailing-",
        "a" * 65,
    ]
    for name in valid_names:
        assert infer_destination.parse_skill_name(name) == name
    for name in invalid_names:
        try:
            infer_destination.parse_skill_name(name)
        except argparse.ArgumentTypeError:
            pass
        else:
            raise AssertionError(f"unsafe name accepted: {name!r}")

    with tempfile.TemporaryDirectory(prefix="placement-name-cli-") as temp_dir:
        cwd = Path(temp_dir) / "workspace"
        home = Path(temp_dir) / "home"
        cwd.mkdir()
        write_skill(home / ".agents/skills", "existing-one")
        env = os.environ.copy()
        env["HOME"] = str(home)
        env.pop("CODEX_HOME", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        for name in invalid_names:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--cwd", str(cwd), "--skill-name", name],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            assert result.returncode == 2, (name, result.returncode)

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--cwd",
                str(cwd),
                "--skill-name",
                "safe-name",
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        payload = json.loads(result.stdout)
        destination = Path(payload["recommended_destination"])
        root = Path(payload["recommended_root"])
        assert destination.parent == root
        assert destination.name == "safe-name"


def fixture_candidate(
    path: str,
    source: str,
    count: int,
    harnesses: tuple[str, ...],
) -> infer_destination.Candidate:
    return infer_destination.Candidate(
        path=path,
        scope="project",
        source=source,
        exists=True,
        skill_count=count,
        current_install_root=False,
        compatible_harnesses=harnesses,
        reason="fixture",
    )


def test_deterministic_ties_prefer_public_then_lexical_path() -> None:
    public = fixture_candidate("/z/skills", "public-repo", 3, ())
    shared = fixture_candidate(
        "/a/.agents/skills",
        "project-shared",
        3,
        infer_destination.SHARED_HARNESSES,
    )
    assert infer_destination.most_populated([shared, public]) is public

    first = fixture_candidate("/a/skills", "global-copilot", 3, ("copilot",))
    second = fixture_candidate("/z/skills", "global-copilot", 3, ("copilot",))
    for _ in range(5):
        assert infer_destination.most_populated([second, first]) is first


def test_invalid_cwd_table() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-cwd-") as temp_dir:
        base = Path(temp_dir)
        missing = base / "missing"
        file_path = base / "file.txt"
        file_path.write_text("fixture\n", encoding="utf-8")
        for cwd in (missing, file_path):
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--cwd", str(cwd)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 2, (cwd, result.returncode)


def test_permission_blocked_root_is_ineligible_and_diagnosed() -> None:
    if os.name == "nt":
        return
    with tempfile.TemporaryDirectory(prefix="placement-permission-") as temp_dir:
        home = Path(temp_dir) / "home"
        root = home / ".agents/skills"
        write_skill(root, "hidden")
        original_mode = stat.S_IMODE(root.stat().st_mode)
        root.chmod(0)
        try:
            excluded: list[infer_destination.ExcludedRoot] = []
            with isolated_global_policy(home):
                candidates = infer_destination.build_candidates(None, root, excluded)
                assert infer_destination.eligible_current_root(None, root) is None
                assert all(Path(candidate.path) != lexical(root) for candidate in candidates)
                diagnostic = next(
                    item for item in excluded if Path(item.path) == lexical(root)
                )
                assert "permission denied" in diagnostic.reason
                try:
                    infer_destination.choose_candidate(
                        None,
                        root,
                        candidates,
                        "agents",
                    )
                except ValueError:
                    pass
                else:
                    raise AssertionError("permission-blocked root was selected")
        finally:
            root.chmod(original_mode)


def test_symlinked_install_preserves_current_family() -> None:
    if os.name == "nt":
        return
    with tempfile.TemporaryDirectory(prefix="placement-symlink-") as temp_dir:
        base = Path(temp_dir)
        home = base / "home"
        repo = base / "unrelated"
        repo.mkdir()
        linked_skill = home / ".codex/skills/skill-creator-advanced"
        linked_skill.parent.mkdir(parents=True)
        try:
            linked_skill.symlink_to(SCRIPT.parent.parent, target_is_directory=True)
        except OSError:
            return

        env = os.environ.copy()
        env["HOME"] = str(home)
        env.pop("CODEX_HOME", None)
        result = subprocess.run(
            [
                sys.executable,
                str(linked_skill / "scripts/infer_destination.py"),
                "--cwd",
                str(repo),
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        payload = json.loads(result.stdout)
        expected = lexical(linked_skill.parent)
        assert Path(payload["current_install_root"]) == expected
        assert Path(payload["recommended_root"]) == expected
        assert payload["effective_harness"] == "codex"


def test_text_output_joins_alternative_portably() -> None:
    with tempfile.TemporaryDirectory(prefix="placement-text-path-") as temp_dir:
        base = Path(temp_dir)
        home = base / "home"
        cwd = base / "workspace"
        cwd.mkdir()
        for index in range(2):
            write_skill(home / ".codex/skills", f"codex-{index}")
        write_skill(home / ".agents/skills", "shared-one")

        env = os.environ.copy()
        env["HOME"] = str(home)
        env.pop("CODEX_HOME", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--cwd",
                str(cwd),
                "--target-harness",
                "codex",
                "--skill-name",
                "portable-name",
                "--format",
                "text",
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        expected_alternative = lexical(home / ".agents/skills") / "portable-name"
        assert f"Alternative: {expected_alternative}" in result.stdout


def main() -> int:
    tests = [
        test_target_compatibility_table,
        test_project_target_compatibility_table,
        test_current_family_precedes_larger_global_library,
        test_neutral_fallback_ignores_larger_vendor_libraries,
        test_empty_public_root_and_lifecycle_lanes_do_not_steal_placement,
        test_unrelated_source_checkout_is_not_current_family,
        test_git_nonzero_and_runtime_errors_do_not_use_manual_discovery,
        test_manual_git_discovery_validates_directories_files_and_boundaries,
        test_incompatible_current_project_root_does_not_bypass_target,
        test_lifecycle_lane_is_never_an_inferred_current_root,
        test_lifecycle_name_in_repo_ancestry_does_not_block_ordinary_roots,
        test_symlink_alias_into_lifecycle_lane_is_rejected,
        test_publication_root_does_not_claim_target_compatibility,
        test_external_project_symlink_is_rejected_without_losing_lexical_roots,
        test_project_root_symlinks_to_in_repo_locations_are_rejected,
        test_global_resolved_aliases_merge_harness_metadata,
        test_blocked_roots_are_not_candidates,
        test_all_target_compatible_roots_blocked_fails_closed,
        test_dangling_shared_alias_cannot_resurrect_incompatible_root,
        test_skill_count_uses_immediate_child_packages_only,
        test_codex_home_deduplicates_same_resolved_root,
        test_name_validation_table_and_cli_containment,
        test_deterministic_ties_prefer_public_then_lexical_path,
        test_invalid_cwd_table,
        test_permission_blocked_root_is_ineligible_and_diagnosed,
        test_symlinked_install_preserves_current_family,
        test_text_output_joins_alternative_portably,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - aggregate independent regressions
            failures.append(f"{test.__name__}: {exc!r}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"PASS: {len(tests)} infer_destination regression groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

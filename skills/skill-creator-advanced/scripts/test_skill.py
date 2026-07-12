#!/usr/bin/env python3
"""Run deterministic release checks for an installable skill.

This is a lightweight schema and package-integrity test, not an execution of
the eval prompts themselves.

Usage:
    python3 test_skill.py <skill-path>
    python3 test_skill.py --self-test

Exit codes:
    0 = all checks pass
    1 = one or more checks fail, or a supplied path is unusable
    2 = command-line usage error reported by argparse
    3 = available checks pass, but host capabilities prevent full certification
"""

from __future__ import annotations

import argparse
import builtins
import json
import os
import shutil
import subprocess
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

from validate import (
    ASSERTION_TYPES,
    load_json_strict,
    path_is_absolute_any_platform,
    path_is_within,
    validate_skill,
)


def load_evals(skill_path: Path) -> dict[str, Any] | None:
    """Read an eval payload for reporting; validation owns all failures."""
    evals_path = skill_path / "evals" / "evals.json"
    try:
        resolved = evals_path.resolve(strict=False)
        if not path_is_within(skill_path, resolved):
            return None
        payload = load_json_strict(evals_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def test_skill(skill_path: str) -> dict[str, object]:
    """Run strict release validation and return report-friendly counters."""
    root = Path(skill_path).expanduser().resolve(strict=False)
    validation = validate_skill(str(root), profile="release")
    metrics = validation["metrics"]
    assert isinstance(metrics, dict)
    errors = validation["errors"]
    warnings = validation["warnings"]
    assert isinstance(errors, list) and isinstance(warnings, list)

    results: dict[str, object] = {
        "skill_name": root.name,
        "tests_found": int(metrics["eval_count"]),
        "trigger_tests_found": int(metrics["trigger_eval_count"]),
        "trigger_balance": {
            "positive": int(metrics["trigger_positive_count"]),
            "negative": int(metrics["trigger_negative_count"]),
        },
        "tags": {},
        "files_verified": {"passed": 0, "total": 0},
        "cross_references": {
            "passed": int(metrics["cross_reference_count"])
            if not any("link" in error.lower() for error in errors)
            else max(
                0,
                int(metrics["cross_reference_count"])
                - sum("link" in error.lower() for error in errors),
            ),
            "total": int(metrics["cross_reference_count"]),
        },
        "assertions_valid": {"passed": 0, "total": 0},
        "errors": list(errors),
        "warnings": list(warnings),
        "passed": bool(validation["valid"]),
    }

    package_audit_prefixes = (
        "Package ",
        "Dangling package symlink",
        "Cannot audit package path",
        "Cannot inspect package path",
        "Cannot resolve package path",
        "Cannot resolve package symlink",
    )
    if any(error.startswith(package_audit_prefixes) for error in errors):
        return results

    payload = load_evals(root)
    if payload is None:
        return results
    evals = payload.get("evals")
    if not isinstance(evals, list):
        return results

    tags_counter = results["tags"]
    files_counter = results["files_verified"]
    assertions_counter = results["assertions_valid"]
    assert isinstance(tags_counter, dict)
    assert isinstance(files_counter, dict)
    assert isinstance(assertions_counter, dict)

    for eval_case in evals:
        if not isinstance(eval_case, dict):
            continue

        tags = eval_case.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str) and tag.strip():
                    tags_counter[tag] = int(tags_counter.get(tag, 0)) + 1

        assertions = eval_case.get("assertions", [])
        if isinstance(assertions, list):
            for assertion in assertions:
                assertions_counter["total"] = int(assertions_counter["total"]) + 1
                if (
                    isinstance(assertion, dict)
                    and isinstance(assertion.get("text"), str)
                    and bool(assertion["text"].strip())
                    and isinstance(assertion.get("type"), str)
                    and assertion.get("type") in ASSERTION_TYPES
                ):
                    assertions_counter["passed"] = (
                        int(assertions_counter["passed"]) + 1
                    )

        files = eval_case.get("files", [])
        if isinstance(files, list):
            for relative_path in files:
                files_counter["total"] = int(files_counter["total"]) + 1
                if not isinstance(relative_path, str) or not relative_path.strip():
                    continue
                raw_path = Path(relative_path.replace("\\", "/"))
                try:
                    resolved = (root / raw_path).resolve(strict=False)
                except (OSError, RuntimeError, ValueError):
                    continue
                if (
                    not path_is_absolute_any_platform(relative_path)
                    and path_is_within(root, resolved)
                    and resolved.is_file()
                ):
                    files_counter["passed"] = int(files_counter["passed"]) + 1

    # Guard against regressions that accidentally decouple summary state from
    # validator errors. Zero evals and malformed assertion types can never pass.
    if not evals:
        results["passed"] = False
    if int(assertions_counter["passed"]) != int(assertions_counter["total"]):
        results["passed"] = False
    return results


def valid_eval_payload(skill_name: str) -> dict[str, object]:
    """Build the smallest complete release eval payload for regression tests."""
    return {
        "skill_name": skill_name,
        "created_by": "skill-creator-advanced",
        "evals": [
            {
                "id": 1,
                "name": "smoke",
                "prompt": "Create the requested artifact with the provided context.",
                "expected_output": "A correct artifact and verification summary.",
                "assertions": [
                    {"text": "The requested artifact is present", "type": "functional"}
                ],
                "tags": ["smoke"],
            }
        ],
    }


def write_fixture(
    root: Path,
    *,
    body: str = "# Fixture Skill\n\nProduces a deterministic fixture.",
    payload: object | None = None,
) -> None:
    """Write a deterministic skill fixture with no unearned support dirs."""
    root.mkdir(parents=True, exist_ok=True)
    root.joinpath("SKILL.md").write_text(
        "---\n"
        f"name: {root.name}\n"
        'description: "Use for deterministic validator regression fixtures."\n'
        "---\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    if payload is not None:
        evals_dir = root / "evals"
        evals_dir.mkdir()
        evals_dir.joinpath("evals.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )


def certification_outcome(
    passed: bool, limitations: list[str]
) -> tuple[str, int]:
    """Return an unambiguous certification label and process exit code."""
    if not passed:
        return "FAIL: one or more release checks failed", 1
    if limitations:
        return (
            "PARTIAL: available release checks passed, but full certification "
            "was not possible",
            3,
        )
    return "PASS: all release checks passed", 0


def run_self_tests() -> tuple[int, int, list[str], list[str]]:
    """Exercise fail-loud release behavior using isolated temporary skills."""
    checks: list[tuple[str, Callable[[], bool]]] = []
    failures: list[str] = []
    certification_limits: list[str] = []
    skipped_ancestor_swap_checks = 0
    skipped_symlink_checks = 0

    with tempfile.TemporaryDirectory(prefix="skill-creator-advanced-tests-") as temp:
        workspace = Path(temp)
        scaffold_script = Path(__file__).resolve().with_name("scaffold.sh")
        bash_executable = shutil.which("bash")
        scaffold_runner = bash_executable or os.sys.executable

        name_probe_root = workspace / "name-probe-root"

        def run_name_probe(name: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    scaffold_runner,
                    str(scaffold_script),
                    name,
                    "--output-root",
                    str(name_probe_root),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        valid_name_probes = [run_name_probe("a"), run_name_probe("a" * 64)]
        invalid_name_probes = [
            run_name_probe("a" * 65),
            run_name_probe("line\nbreak"),
            run_name_probe("control\x01name"),
            run_name_probe("double--hyphen"),
        ]
        checks.append(
            (
                "scaffold accepts whole-string boundary names",
                lambda: all(probe.returncode == 0 for probe in valid_name_probes)
                and not name_probe_root.exists(),
            )
        )
        checks.append(
            (
                "scaffold rejects overlong, newline, control, and double-hyphen names",
                lambda: all(probe.returncode != 0 for probe in invalid_name_probes)
                and not name_probe_root.exists(),
            )
        )

        empty_output_root = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "empty-root",
                "--output-root",
                "",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        option_output_root = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "option-root",
                "--output-root",
                "--dry-run",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        checks.append(
            (
                "scaffold rejects empty and option-looking output roots",
                lambda: empty_output_root.returncode != 0
                and option_output_root.returncode != 0
                and "requires a non-empty directory path" in empty_output_root.stdout
                and "requires a non-empty directory path" in option_output_root.stdout,
            )
        )

        tilde_root = "~definitely-no-such-skill-user/skills"
        tilde_probe = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "tilde-root",
                "--output-root",
                tilde_root,
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=workspace,
        )
        accidental_tilde_root = workspace / tilde_root
        checks.append(
            (
                "scaffold rejects an output root for an unknown tilde user",
                lambda: tilde_probe.returncode != 0
                and "cannot expand unknown user" in (
                    tilde_probe.stdout + tilde_probe.stderr
                )
                and not accidental_tilde_root.exists(),
            )
        )

        inference_counter = workspace / "inference-counter.txt"
        inferred_root_one = workspace / "inferred-root-one"
        inferred_root_two = workspace / "inferred-root-two"
        inference_fixture = workspace / "infer-destination-fixture.py"
        inference_fixture.write_text(
            "import json\n"
            "from pathlib import Path\n"
            f"counter = Path({str(inference_counter)!r})\n"
            "count = int(counter.read_text()) + 1 if counter.exists() else 1\n"
            "counter.write_text(str(count))\n"
            f"first = {str(inferred_root_one)!r}\n"
            f"second = {str(inferred_root_two)!r}\n"
            "root = first if count == 1 else second\n"
            "print(json.dumps({\n"
            "    'recommended_root': root,\n"
            "    'reason': f'inference call {count}',\n"
            "    'alternatives': [second],\n"
            "}))\n",
            encoding="utf-8",
        )
        inference_environment = os.environ.copy()
        inference_environment["SKILL_CREATOR_INFER_DESTINATION_SCRIPT"] = str(
            inference_fixture
        )
        inference_run = subprocess.run(
            [scaffold_runner, str(scaffold_script), "snapshot-skill"],
            capture_output=True,
            text=True,
            check=False,
            cwd=workspace,
            env=inference_environment,
        )
        checks.append(
            (
                "scaffold uses one inference snapshot for display and publication",
                lambda: inference_run.returncode == 0
                and inference_counter.read_text(encoding="utf-8") == "1"
                and inferred_root_one.joinpath(
                    "snapshot-skill", "SKILL.md"
                ).is_file()
                and not inferred_root_two.joinpath("snapshot-skill").exists()
                and f"Recommended destination: {inferred_root_one}/snapshot-skill"
                in inference_run.stdout
                and f"Root: {inferred_root_one}" in inference_run.stdout,
            )
        )

        file_output_root = workspace / "file-output-root"
        file_output_root.write_text("not a directory\n", encoding="utf-8")
        file_output_probe = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "file-root",
                "--output-root",
                str(file_output_root),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        checks.append(
            (
                "scaffold dry run rejects a regular-file output root",
                lambda: file_output_probe.returncode != 0
                and "output root is not a directory" in file_output_probe.stdout,
            )
        )

        dangling_destination_root = workspace / "dangling-destination-root"
        dangling_destination_root.mkdir()
        dangling_destination = dangling_destination_root / "dangling-destination"
        try:
            dangling_destination.symlink_to(workspace / "missing-destination")
        except OSError:
            skipped_symlink_checks += 1
        else:
            dangling_destination_probe = subprocess.run(
                [
                    scaffold_runner,
                    str(scaffold_script),
                    dangling_destination.name,
                    "--output-root",
                    str(dangling_destination_root),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            checks.append(
                (
                    "scaffold dry run rejects a dangling destination symlink",
                    lambda: dangling_destination_probe.returncode != 0
                    and "already exists" in dangling_destination_probe.stdout,
                )
            )

        locked_output_root = workspace / "locked-output-root"
        locked_output_root.mkdir()
        publication_lock = locked_output_root / ".locked-skill.publish.lock"
        publication_lock.mkdir()
        locked_output_probe = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "locked-skill",
                "--output-root",
                str(locked_output_root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        checks.append(
            (
                "stale legacy publication locks do not block safe publication",
                lambda: locked_output_probe.returncode == 0
                and publication_lock.is_dir()
                and locked_output_root.joinpath("locked-skill", "SKILL.md").is_file()
                and not list(locked_output_root.glob(".locked-skill.draft.*")),
            )
        )

        race_output_root = workspace / "publish-race-output-root"
        race_output_root.mkdir()
        race_destination = race_output_root / "publish-race-skill"
        race_barrier = workspace / "publish-race-barrier"
        race_barrier_hold = Path(f"{race_barrier}.hold")
        race_barrier_ready = Path(f"{race_barrier}.ready")
        race_barrier_hold.write_text("hold\n", encoding="utf-8")
        race_environment = os.environ.copy()
        race_environment["_SKILL_CREATOR_TEST_PUBLISH_BARRIER"] = str(race_barrier)
        race_process = subprocess.Popen(
            [
                scaffold_runner,
                str(scaffold_script),
                race_destination.name,
                "api-wrapper",
                "--output-root",
                str(race_output_root),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=race_environment,
        )
        race_injected = False
        race_deadline = time.monotonic() + 5
        while race_process.poll() is None and time.monotonic() < race_deadline:
            if race_barrier_ready.is_file():
                try:
                    race_destination.mkdir()
                except FileExistsError:
                    pass
                else:
                    race_injected = True
                race_barrier_hold.unlink(missing_ok=True)
                break
            time.sleep(0.001)
        race_barrier_hold.unlink(missing_ok=True)
        try:
            race_stdout, race_stderr = race_process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            race_process.kill()
            race_stdout, race_stderr = race_process.communicate()
        checks.append(
            (
                "scaffold atomically refuses a destination created during staging",
                lambda: race_injected
                and race_process.returncode != 0
                and race_destination.is_dir()
                and not any(race_destination.iterdir())
                and "already exists at publish time" in (race_stdout + race_stderr)
                and not race_barrier_ready.exists()
                and not list(race_output_root.glob(".publish-race-skill.draft.*")),
            )
        )

        ancestor_output_root = workspace / "ancestor-output-root"
        ancestor_output_root.mkdir()
        displaced_output_root = workspace / "ancestor-output-root-displaced"
        ancestor_barrier = workspace / "ancestor-swap-barrier"
        ancestor_barrier_hold = Path(f"{ancestor_barrier}.hold")
        ancestor_barrier_ready = Path(f"{ancestor_barrier}.ready")
        ancestor_barrier_hold.write_text("hold\n", encoding="utf-8")
        ancestor_environment = os.environ.copy()
        ancestor_environment["_SKILL_CREATOR_TEST_PUBLISH_BARRIER"] = str(
            ancestor_barrier
        )
        ancestor_process = subprocess.Popen(
            [
                scaffold_runner,
                str(scaffold_script),
                "ancestor-skill",
                "--output-root",
                str(ancestor_output_root),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=ancestor_environment,
        )
        ancestor_swap_injected = False
        replacement_staged_skill: Path | None = None
        ancestor_deadline = time.monotonic() + 5
        while (
            ancestor_process.poll() is None
            and time.monotonic() < ancestor_deadline
        ):
            if ancestor_barrier_ready.is_file():
                staged_directories = list(
                    ancestor_output_root.glob(".ancestor-skill.draft.*")
                )
                if len(staged_directories) == 1:
                    try:
                        ancestor_output_root.rename(displaced_output_root)
                    except OSError:
                        skipped_ancestor_swap_checks += 1
                    else:
                        ancestor_output_root.mkdir()
                        replacement_staged_skill = (
                            ancestor_output_root
                            / staged_directories[0].name
                            / "ancestor-skill"
                            / "SKILL.md"
                        )
                        replacement_staged_skill.parent.mkdir(parents=True)
                        replacement_staged_skill.write_text(
                            "unvalidated replacement\n", encoding="utf-8"
                        )
                        ancestor_swap_injected = True
                ancestor_barrier_hold.unlink(missing_ok=True)
                break
            time.sleep(0.001)
        ancestor_barrier_hold.unlink(missing_ok=True)
        try:
            ancestor_stdout, ancestor_stderr = ancestor_process.communicate(
                timeout=10
            )
        except subprocess.TimeoutExpired:
            ancestor_process.kill()
            ancestor_stdout, ancestor_stderr = ancestor_process.communicate()
        if ancestor_swap_injected:
            checks.append(
                (
                    "output-root ancestor swaps fail closed and clean anchored staging",
                    lambda: ancestor_process.returncode != 0
                    and "output root changed after staging"
                    in (ancestor_stdout + ancestor_stderr)
                    and not ancestor_output_root.joinpath("ancestor-skill").exists()
                    and not displaced_output_root.joinpath("ancestor-skill").exists()
                    and not list(
                        displaced_output_root.glob(".ancestor-skill.draft.*")
                    )
                    and replacement_staged_skill is not None
                    and replacement_staged_skill.read_text(encoding="utf-8")
                    == "unvalidated replacement\n",
                )
            )

        unsupported_output_root = workspace / "unsupported-output-root"
        unsupported_environment = os.environ.copy()
        unsupported_environment[
            "_SKILL_CREATOR_TEST_FORCE_UNSUPPORTED_PUBLISH"
        ] = "1"
        unsupported_run = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "unsupported-skill",
                "--output-root",
                str(unsupported_output_root),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=unsupported_environment,
        )
        checks.append(
            (
                "unsupported atomic publication fails closed without partial output",
                lambda: unsupported_run.returncode != 0
                and not unsupported_output_root.joinpath("unsupported-skill").exists()
                and "does not support atomic no-replace"
                in (unsupported_run.stdout + unsupported_run.stderr)
                and not list(
                    unsupported_output_root.glob(".unsupported-skill.draft.*")
                ),
            )
        )

        spaced_output_root = workspace / "output root with spaces"
        spaced_output_run = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "space-skill",
                "--output-root",
                str(spaced_output_root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        checks.append(
            (
                "scaffold summary shell-quotes space-containing paths",
                lambda: spaced_output_run.returncode == 0
                and spaced_output_root.joinpath("space-skill", "SKILL.md").is_file()
                and "output\\ root\\ with\\ spaces/space-skill" in spaced_output_run.stdout,
            )
        )

        dry_root = workspace / "dry-output-root"
        dry_run = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "dry-skill",
                "--output-root",
                str(dry_root),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        checks.append(
            (
                "scaffold dry run creates no output root",
                lambda: dry_run.returncode == 0
                and not dry_root.exists()
                and "incomplete draft" in dry_run.stdout,
            )
        )

        real_root = workspace / "real-output-root"
        real_run = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "minimal-skill",
                "--output-root",
                str(real_root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        scaffolded = real_root / "minimal-skill"
        scaffolded_entries = (
            {path.name for path in scaffolded.iterdir()} if scaffolded.is_dir() else set()
        )
        staged_leftovers = list(real_root.glob(".minimal-skill.draft.*"))
        checks.append(
            (
                "minimal scaffold creates only a no-clobber incomplete draft",
                lambda: real_run.returncode == 0
                and scaffolded_entries == {"SKILL.md"}
                and not staged_leftovers
                and "Incomplete skill draft created" in real_run.stdout
                and bool(validate_skill(str(scaffolded), profile="draft")["valid"])
                and not bool(validate_skill(str(scaffolded), profile="release")["valid"]),
            )
        )

        blueprint_root = workspace / "blueprint-output-root"
        blueprint_run = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "api-skill",
                "api-wrapper",
                "--output-root",
                str(blueprint_root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        blueprint_skill = blueprint_root / "api-skill"
        blueprint_entries = (
            {path.name for path in blueprint_skill.iterdir()}
            if blueprint_skill.is_dir()
            else set()
        )
        blueprint_references = blueprint_skill / "references"
        checks.append(
            (
                "blueprint scaffold creates only resources backed by content",
                lambda: blueprint_run.returncode == 0
                and blueprint_entries == {"SKILL.md", "references"}
                and blueprint_references.is_dir()
                and all(path.is_file() for path in blueprint_references.iterdir())
                and not any(path.name == ".gitkeep" for path in blueprint_references.iterdir())
                and bool(validate_skill(str(blueprint_skill), profile="draft")["valid"]),
            )
        )

        progressive_root = workspace / "progressive-output-root"
        progressive_run = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "docs-skill",
                "progressive-docs",
                "--output-root",
                str(progressive_root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        progressive_skill = progressive_root / "docs-skill"
        progressive_reference_names = (
            {
                path.name
                for path in progressive_skill.joinpath("references").iterdir()
            }
            if progressive_skill.joinpath("references").is_dir()
            else set()
        )
        checks.append(
            (
                "progressive scaffold placeholder-marks example routes",
                lambda: progressive_run.returncode == 0
                and progressive_reference_names == {"shared.md"}
                and "{{DOMAIN_AREA_FILE}}" in progressive_skill.joinpath(
                    "SKILL.md"
                ).read_text(encoding="utf-8")
                and bool(validate_skill(str(progressive_skill), profile="draft")["valid"]),
            )
        )

        missing_entry_templates = workspace / "missing-entry-templates"
        missing_entry_references = missing_entry_templates / "api-wrapper" / "references"
        missing_entry_references.mkdir(parents=True)
        for reference_name in ("api.md", "patterns.md", "configuration.md", "gotchas.md"):
            missing_entry_references.joinpath(reference_name).write_text(
                f"# {reference_name}\n", encoding="utf-8"
            )
        missing_entry_root = workspace / "missing-entry-output"
        missing_entry_environment = os.environ.copy()
        missing_entry_environment["SKILL_CREATOR_TEMPLATES_DIR"] = str(
            missing_entry_templates
        )
        missing_entry_run = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "missing-entry",
                "api-wrapper",
                "--output-root",
                str(missing_entry_root),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=missing_entry_environment,
        )
        checks.append(
            (
                "scaffold fails before output when blueprint entry is missing",
                lambda: missing_entry_run.returncode != 0
                and "api-wrapper/SKILL.template.md" in missing_entry_run.stdout
                and not missing_entry_root.exists(),
            )
        )

        missing_reference_templates = workspace / "missing-reference-templates"
        missing_reference_blueprint = missing_reference_templates / "api-wrapper"
        missing_reference_references = missing_reference_blueprint / "references"
        missing_reference_references.mkdir(parents=True)
        missing_reference_blueprint.joinpath("SKILL.template.md").write_text(
            "---\nname: {{SKILL_NAME}}\n"
            'description: "Draft fixture."\n---\n\n# Fixture\n',
            encoding="utf-8",
        )
        for reference_name in ("api.md", "patterns.md", "configuration.md"):
            missing_reference_references.joinpath(reference_name).write_text(
                f"# {reference_name}\n", encoding="utf-8"
            )
        missing_reference_root = workspace / "missing-reference-output"
        missing_reference_environment = os.environ.copy()
        missing_reference_environment["SKILL_CREATOR_TEMPLATES_DIR"] = str(
            missing_reference_templates
        )
        missing_reference_run = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "missing-reference",
                "api-wrapper",
                "--output-root",
                str(missing_reference_root),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=missing_reference_environment,
        )
        checks.append(
            (
                "scaffold fails before output when blueprint reference is missing",
                lambda: missing_reference_run.returncode != 0
                and "api-wrapper/references/gotchas.md" in missing_reference_run.stdout
                and not missing_reference_root.exists(),
            )
        )

        invalid_stage_templates = workspace / "invalid-stage-templates"
        invalid_stage_blueprint = invalid_stage_templates / "api-wrapper"
        invalid_stage_references = invalid_stage_blueprint / "references"
        invalid_stage_references.mkdir(parents=True)
        invalid_stage_blueprint.joinpath("SKILL.template.md").write_text(
            "---\nname: {{SKILL_NAME}}\n"
            'description: "Draft fixture."\n---\n\n'
            "# Fixture\n\nRead [missing](references/not-copied.md).\n",
            encoding="utf-8",
        )
        for reference_name in ("api.md", "patterns.md", "configuration.md", "gotchas.md"):
            invalid_stage_references.joinpath(reference_name).write_text(
                f"# {reference_name}\n", encoding="utf-8"
            )
        invalid_stage_root = workspace / "invalid-stage-output"
        invalid_stage_environment = os.environ.copy()
        invalid_stage_environment["SKILL_CREATOR_TEMPLATES_DIR"] = str(
            invalid_stage_templates
        )
        invalid_stage_run = subprocess.run(
            [
                scaffold_runner,
                str(scaffold_script),
                "invalid-stage",
                "api-wrapper",
                "--output-root",
                str(invalid_stage_root),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=invalid_stage_environment,
        )
        checks.append(
            (
                "invalid staged draft is never atomically published",
                lambda: invalid_stage_run.returncode != 0
                and "failed structural validation" in invalid_stage_run.stdout
                and not invalid_stage_root.joinpath("invalid-stage").exists()
                and not list(invalid_stage_root.glob(".invalid-stage.draft.*")),
            )
        )

        scaffold_check_count = len(checks)

        checks.append(
            (
                "reduced coverage cannot report full release certification",
                lambda: certification_outcome(True, ["Bash is unavailable"])
                == (
                    "PARTIAL: available release checks passed, but full "
                    "certification was not possible",
                    3,
                ),
            )
        )

        if (
            bash_executable is not None
            and os.environ.get("_SKILL_CREATOR_TEST_CAPABILITY_CHILD") != "1"
        ):
            empty_path = workspace / "empty-path"
            empty_path.mkdir()
            no_bash_environment = os.environ.copy()
            no_bash_environment["PATH"] = str(empty_path)
            no_bash_environment["_SKILL_CREATOR_TEST_CAPABILITY_CHILD"] = "1"
            no_bash_run = subprocess.run(
                [os.sys.executable, str(Path(__file__).resolve()), "--self-test"],
                capture_output=True,
                text=True,
                check=False,
                env=no_bash_environment,
            )
            checks.append(
                (
                    "unavailable Bash yields explicit partial certification",
                    lambda: no_bash_run.returncode == 3
                    and "Bash is unavailable" in no_bash_run.stdout
                    and "PARTIAL: available release checks passed"
                    in no_bash_run.stdout
                    and "PASS: all release checks passed" not in no_bash_run.stdout,
                )
            )

        complete = workspace / "complete-skill"
        write_fixture(complete, payload=valid_eval_payload(complete.name))
        checks.append(
            (
                "complete release without empty support directories passes",
                lambda: bool(validate_skill(str(complete))["valid"]),
            )
        )

        whitespace_description = workspace / "whitespace-description"
        write_fixture(
            whitespace_description,
            payload=valid_eval_payload(whitespace_description.name),
        )
        whitespace_description.joinpath("SKILL.md").write_text(
            "---\n"
            f"name: {whitespace_description.name}\n"
            'description: "   "\n'
            "---\n\n# Whitespace Description\n",
            encoding="utf-8",
        )
        empty_body = workspace / "empty-body"
        write_fixture(
            empty_body,
            body="   ",
            payload=valid_eval_payload(empty_body.name),
        )
        whitespace_description_errors = validate_skill(str(whitespace_description))["errors"]
        empty_body_release = validate_skill(str(empty_body), profile="release")
        empty_body_draft = validate_skill(str(empty_body), profile="draft")
        assert isinstance(whitespace_description_errors, list)
        assert isinstance(empty_body_release["errors"], list)
        assert isinstance(empty_body_draft["warnings"], list)
        checks.append(
            (
                "release requires stripped description and body content",
                lambda: any(
                    "missing required 'description'" in error
                    for error in whitespace_description_errors
                )
                and any(
                    "body must contain non-whitespace instructions" in error
                    for error in empty_body_release["errors"]
                )
                and bool(empty_body_draft["valid"])
                and any(
                    "body must contain non-whitespace instructions" in warning
                    for warning in empty_body_draft["warnings"]
                ),
            )
        )

        empty_support = workspace / "empty-support"
        write_fixture(empty_support, payload=valid_eval_payload(empty_support.name))
        empty_support.joinpath("assets").mkdir()
        empty_support.joinpath("references").mkdir()
        empty_support.joinpath("references", ".gitkeep").touch()
        empty_support_release = validate_skill(str(empty_support), profile="release")
        empty_support_draft = validate_skill(str(empty_support), profile="draft")
        assert isinstance(empty_support_release["errors"], list)
        assert isinstance(empty_support_draft["warnings"], list)
        checks.append(
            (
                "empty and gitkeep-only support directories cannot release",
                lambda: sum(
                    "empty or .gitkeep-only" in error
                    for error in empty_support_release["errors"]
                )
                == 2
                and bool(empty_support_draft["valid"])
                and sum(
                    "empty or .gitkeep-only" in warning
                    for warning in empty_support_draft["warnings"]
                )
                == 2,
            )
        )

        wrong_root = workspace / "wrong-root"
        wrong_root.joinpath("templates", "deep").mkdir(parents=True)
        wrong_root.joinpath("templates", "deep", "payload.md").write_text(
            "# Not a skill root\n", encoding="utf-8"
        )
        wrong_root_result = validate_skill(str(wrong_root))
        wrong_root_metrics = wrong_root_result["metrics"]
        wrong_root_errors = wrong_root_result["errors"]
        assert isinstance(wrong_root_metrics, dict)
        assert isinstance(wrong_root_errors, list)
        checks.append(
            (
                "wrong roots fail on lexical SKILL entry before recursive audit",
                lambda: wrong_root_errors == ["SKILL.md does not exist"]
                and wrong_root_metrics["audited_path_count"] == 0,
            )
        )

        invalid_path_cli = subprocess.run(
            [
                os.sys.executable,
                str(Path(__file__).resolve().with_name("validate.py")),
                str(workspace / "missing-skill-path"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        checks.append(
            (
                "validate CLI returns its JSON envelope for an unusable path",
                lambda: invalid_path_cli.returncode == 1
                and "--- JSON ---" in invalid_path_cli.stdout
                and '"valid": false' in invalid_path_cli.stdout
                and "SKILL.md does not exist" in invalid_path_cli.stdout,
            )
        )

        balanced_triggers = workspace / "balanced-triggers"
        write_fixture(
            balanced_triggers,
            payload=valid_eval_payload(balanced_triggers.name),
        )
        balanced_triggers.joinpath("evals", "trigger-evals.json").write_text(
            json.dumps(
                [
                    {"query": "Create a production skill", "should_trigger": True},
                    {"query": "Refactor this function", "should_trigger": False},
                ],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        balanced_trigger_result = validate_skill(str(balanced_triggers))
        balanced_trigger_metrics = balanced_trigger_result["metrics"]
        assert isinstance(balanced_trigger_metrics, dict)
        checks.append(
            (
                "balanced optional trigger corpus passes static preflight",
                lambda: bool(balanced_trigger_result["valid"])
                and balanced_trigger_metrics["trigger_eval_count"] == 2
                and balanced_trigger_metrics["trigger_positive_count"] == 1
                and balanced_trigger_metrics["trigger_negative_count"] == 1
                and bool(test_skill(str(balanced_triggers))["passed"]),
            )
        )

        malformed_trigger_root = workspace / "malformed-trigger-root"
        write_fixture(
            malformed_trigger_root,
            payload=valid_eval_payload(malformed_trigger_root.name),
        )
        malformed_trigger_root.joinpath("evals", "trigger-evals.json").write_text(
            json.dumps({"query": "not-a-list", "should_trigger": True}) + "\n",
            encoding="utf-8",
        )
        malformed_trigger_draft = validate_skill(
            str(malformed_trigger_root), profile="draft"
        )
        malformed_trigger_errors = malformed_trigger_draft["errors"]
        assert isinstance(malformed_trigger_errors, list)
        checks.append(
            (
                "draft rejects non-list trigger corpus",
                lambda: not bool(malformed_trigger_draft["valid"])
                and any("must contain a JSON array" in error for error in malformed_trigger_errors),
            )
        )

        malformed_trigger_case = workspace / "malformed-trigger-case"
        write_fixture(
            malformed_trigger_case,
            payload=valid_eval_payload(malformed_trigger_case.name),
        )
        malformed_trigger_case.joinpath("evals", "trigger-evals.json").write_text(
            json.dumps(
                [
                    {"query": "", "should_trigger": "yes"},
                    {
                        "query": "Unexpected field",
                        "should_trigger": True,
                        "extra": 1,
                    },
                    {"query": "Duplicate", "should_trigger": True},
                    {"query": "Duplicate", "should_trigger": False},
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        malformed_trigger_case_draft = validate_skill(
            str(malformed_trigger_case), profile="draft"
        )
        malformed_trigger_case_errors = malformed_trigger_case_draft["errors"]
        assert isinstance(malformed_trigger_case_errors, list)
        checks.append(
            (
                "trigger case schema and duplicate queries stay fatal in draft",
                lambda: not bool(malformed_trigger_case_draft["valid"])
                and any("'query' must be a non-empty string" in error for error in malformed_trigger_case_errors)
                and any("'should_trigger' must be a boolean" in error for error in malformed_trigger_case_errors)
                and any("expected exactly query and should_trigger" in error for error in malformed_trigger_case_errors)
                and any("duplicate query" in error for error in malformed_trigger_case_errors),
            )
        )

        unbalanced_triggers = workspace / "unbalanced-triggers"
        write_fixture(
            unbalanced_triggers,
            payload=valid_eval_payload(unbalanced_triggers.name),
        )
        unbalanced_triggers.joinpath("evals", "trigger-evals.json").write_text(
            json.dumps(
                [{"query": "Create a production skill", "should_trigger": True}]
            )
            + "\n",
            encoding="utf-8",
        )
        unbalanced_release = validate_skill(str(unbalanced_triggers))
        unbalanced_draft = validate_skill(str(unbalanced_triggers), profile="draft")
        unbalanced_draft_warnings = unbalanced_draft["warnings"]
        assert isinstance(unbalanced_draft_warnings, list)
        checks.append(
            (
                "trigger balance is release completeness, not draft schema",
                lambda: not bool(unbalanced_release["valid"])
                and bool(unbalanced_draft["valid"])
                and any("should_trigger=false" in warning for warning in unbalanced_draft_warnings),
            )
        )

        empty = workspace / "empty-evals"
        empty_payload = valid_eval_payload(empty.name)
        empty_payload["evals"] = []
        write_fixture(empty, payload=empty_payload)
        checks.append(
            (
                "zero evals fails validator and test runner",
                lambda: not bool(validate_skill(str(empty))["valid"])
                and not bool(test_skill(str(empty))["passed"]),
            )
        )

        unknown = workspace / "unknown-assertion"
        unknown_payload = valid_eval_payload(unknown.name)
        unknown_evals = unknown_payload["evals"]
        assert isinstance(unknown_evals, list)
        unknown_evals[0]["assertions"][0]["type"] = "invented"
        write_fixture(unknown, payload=unknown_payload)
        unknown_result = validate_skill(str(unknown))
        unknown_errors = unknown_result["errors"]
        assert isinstance(unknown_errors, list)
        checks.append(
            (
                "unknown assertion type fails validator and test runner",
                lambda: any("unknown type 'invented'" in error for error in unknown_errors)
                and not bool(validate_skill(str(unknown), profile="draft")["valid"])
                and not bool(test_skill(str(unknown))["passed"]),
            )
        )

        malformed_assertion = workspace / "malformed-assertion"
        malformed_assertion_payload = valid_eval_payload(malformed_assertion.name)
        malformed_assertion_evals = malformed_assertion_payload["evals"]
        assert isinstance(malformed_assertion_evals, list)
        malformed_assertion_evals[0]["assertions"][0]["type"] = []
        write_fixture(malformed_assertion, payload=malformed_assertion_payload)
        malformed_assertion_result = validate_skill(str(malformed_assertion))
        malformed_assertion_errors = malformed_assertion_result["errors"]
        assert isinstance(malformed_assertion_errors, list)
        checks.append(
            (
                "malformed assertion type fails without crashing test runner",
                lambda: any(
                    "'type' must be a string" in error
                    for error in malformed_assertion_errors
                )
                and not bool(test_skill(str(malformed_assertion))["passed"]),
            )
        )

        missing_assertion_type = workspace / "missing-assertion-type"
        missing_type_payload = valid_eval_payload(missing_assertion_type.name)
        missing_type_evals = missing_type_payload["evals"]
        assert isinstance(missing_type_evals, list)
        missing_type_evals[0]["assertions"][0].pop("type")
        write_fixture(missing_assertion_type, payload=missing_type_payload)
        missing_type_result = validate_skill(str(missing_assertion_type))
        missing_type_errors = missing_type_result["errors"]
        assert isinstance(missing_type_errors, list)
        checks.append(
            (
                "missing assertion type fails release",
                lambda: any(
                    "'type' must be a non-empty string" in error
                    for error in missing_type_errors
                ),
            )
        )

        empty_assertions = workspace / "empty-assertions"
        empty_assertions_payload = valid_eval_payload(empty_assertions.name)
        empty_assertions_evals = empty_assertions_payload["evals"]
        assert isinstance(empty_assertions_evals, list)
        empty_assertions_evals[0]["assertions"] = []
        write_fixture(empty_assertions, payload=empty_assertions_payload)
        empty_assertions_result = validate_skill(str(empty_assertions))
        empty_assertions_errors = empty_assertions_result["errors"]
        assert isinstance(empty_assertions_errors, list)
        checks.append(
            (
                "empty assertions fail release",
                lambda: any(
                    "must contain at least one assertion" in error
                    for error in empty_assertions_errors
                ),
            )
        )

        empty_required = workspace / "empty-required-fields"
        empty_required_payload = valid_eval_payload(empty_required.name)
        empty_required_evals = empty_required_payload["evals"]
        assert isinstance(empty_required_evals, list)
        empty_required_evals[0]["name"] = ""
        empty_required_evals[0]["prompt"] = " "
        empty_required_evals[0]["expected_output"] = None
        write_fixture(empty_required, payload=empty_required_payload)
        empty_required_result = validate_skill(str(empty_required))
        empty_required_errors = empty_required_result["errors"]
        assert isinstance(empty_required_errors, list)
        checks.append(
            (
                "required eval text fields must be non-empty strings",
                lambda: any("'name' must be a non-empty string" in error for error in empty_required_errors)
                and any("'prompt' must be a non-empty string" in error for error in empty_required_errors)
                and any("'expected_output' must be a string" in error for error in empty_required_errors),
            )
        )

        draft = workspace / "draft-skill"
        write_fixture(
            draft,
            body="# Draft Skill\n\nTODO: replace {{PLACEHOLDER}}.",
            payload=valid_eval_payload(draft.name),
        )
        draft_release = validate_skill(str(draft), profile="release")
        draft_release_errors = draft_release["errors"]
        assert isinstance(draft_release_errors, list)
        checks.append(
            (
                "draft accepts incomplete markers while release rejects them",
                lambda: bool(validate_skill(str(draft), profile="draft")["valid"])
                and any("authoring markers" in error for error in draft_release_errors),
            )
        )

        live_reference_marker = workspace / "live-reference-marker"
        write_fixture(
            live_reference_marker,
            body=(
                "# Live Reference Marker\n\n"
                "Read [the workflow](references/workflow.md)."
            ),
            payload=valid_eval_payload(live_reference_marker.name),
        )
        live_marker_references = live_reference_marker / "references"
        live_marker_references.mkdir()
        live_marker_references.joinpath("workflow.md").write_text(
            "# Workflow\n\n"
            "TODO replace {{release_command}}.\n"
            "FIXME(owner): confirm the release path.\n",
            encoding="utf-8",
        )
        live_marker_release = validate_skill(
            str(live_reference_marker), profile="release"
        )
        live_marker_errors = live_marker_release["errors"]
        assert isinstance(live_marker_errors, list)
        live_marker_draft = validate_skill(str(live_reference_marker), profile="draft")
        live_marker_warnings = live_marker_draft["warnings"]
        assert isinstance(live_marker_warnings, list)
        checks.append(
            (
                "live reference markers warn in draft and fail release",
                lambda: any(
                    "references/workflow.md contains unresolved authoring markers" in error
                    for error in live_marker_errors
                )
                and bool(live_marker_draft["valid"])
                and any(
                    "references/workflow.md contains unresolved authoring markers"
                    in warning
                    for warning in live_marker_warnings
                ),
            )
        )

        fenced_scaffold_token = workspace / "fenced-scaffold-token"
        write_fixture(
            fenced_scaffold_token,
            body=(
                "# Fenced Scaffold Token\n\n"
                "```sh\n"
                "{{install_cmd}} --dry-run\n"
                "```"
            ),
            payload=valid_eval_payload(fenced_scaffold_token.name),
        )
        fenced_token_release = validate_skill(str(fenced_scaffold_token))
        fenced_token_draft = validate_skill(
            str(fenced_scaffold_token), profile="draft"
        )
        assert isinstance(fenced_token_release["errors"], list)
        assert isinstance(fenced_token_draft["warnings"], list)
        checks.append(
            (
                "executable fences cannot hide unresolved scaffold tokens",
                lambda: any(
                    "{{install_cmd}}" in error
                    for error in fenced_token_release["errors"]
                )
                and bool(fenced_token_draft["valid"])
                and any(
                    "{{install_cmd}}" in warning
                    for warning in fenced_token_draft["warnings"]
                ),
            )
        )

        unfinished_script = workspace / "unfinished-script"
        write_fixture(
            unfinished_script,
            payload=valid_eval_payload(unfinished_script.name),
        )
        unfinished_script.joinpath("scripts").mkdir()
        unfinished_script.joinpath("scripts", "run.py").write_text(
            "#!/usr/bin/env python3\n# TODO: implement the runtime operation\n",
            encoding="utf-8",
        )
        unfinished_script_release = validate_skill(str(unfinished_script))
        unfinished_script_draft = validate_skill(
            str(unfinished_script), profile="draft"
        )
        assert isinstance(unfinished_script_release["errors"], list)
        assert isinstance(unfinished_script_draft["warnings"], list)
        checks.append(
            (
                "live script comment debt warns in draft and fails release",
                lambda: any(
                    "scripts/run.py contains unresolved authoring markers" in error
                    for error in unfinished_script_release["errors"]
                )
                and bool(unfinished_script_draft["valid"])
                and any(
                    "scripts/run.py contains unresolved authoring markers" in warning
                    for warning in unfinished_script_draft["warnings"]
                ),
            )
        )

        marker_strings = workspace / "marker-strings"
        write_fixture(marker_strings, payload=valid_eval_payload(marker_strings.name))
        marker_strings.joinpath("scripts").mkdir()
        marker_strings.joinpath("scripts", "messages.py").write_text(
            "print(\"# TODO: shown to users\")\n"
            "single = '// FIXME: also data'\n"
            "triple = \"\"\"/* TBD: documentation fixture */\"\"\"\n",
            encoding="utf-8",
        )
        checks.append(
            (
                "marker-looking script string literals are not comment debt",
                lambda: bool(validate_skill(str(marker_strings))["valid"]),
            )
        )

        eval_marker = workspace / "eval-marker"
        eval_marker_payload = valid_eval_payload(eval_marker.name)
        eval_marker_evals = eval_marker_payload["evals"]
        assert isinstance(eval_marker_evals, list)
        eval_marker_evals[0]["prompt"] = "TODO: replace this prompt"
        eval_marker_evals[0]["expected_output"] = "TBD describe the result"
        eval_marker_evals[0]["assertions"][0]["text"] = "FIXME: add a real assertion"
        write_fixture(eval_marker, payload=eval_marker_payload)
        eval_marker_release = validate_skill(str(eval_marker))
        eval_marker_draft = validate_skill(str(eval_marker), profile="draft")
        assert isinstance(eval_marker_release["errors"], list)
        assert isinstance(eval_marker_draft["warnings"], list)
        checks.append(
            (
                "behavioral eval contract fields cannot remain leading draft stubs",
                lambda: sum(
                    "contains an unresolved authoring marker" in error
                    for error in eval_marker_release["errors"]
                )
                == 3
                and bool(eval_marker_draft["valid"])
                and sum(
                    "contains an unresolved authoring marker" in warning
                    for warning in eval_marker_draft["warnings"]
                )
                == 3,
            )
        )

        intentional_placeholders = workspace / "intentional-placeholders"
        write_fixture(
            intentional_placeholders,
            body=(
                "# Intentional Placeholders\n\n"
                "Read [the guide](references/guide.md)."
            ),
            payload=valid_eval_payload(intentional_placeholders.name),
        )
        intentional_references = intentional_placeholders / "references"
        intentional_references.mkdir()
        intentional_references.joinpath("guide.md").write_text(
            "# Guide\n\n"
            "```markdown\nTODO: example uses {{.UserName}} at runtime.\n```\n",
            encoding="utf-8",
        )
        intentional_templates = intentional_placeholders / "templates"
        intentional_templates.mkdir()
        intentional_templates.joinpath("SKILL.template.md").write_text(
            "# {{SKILL_NAME}}\n\nTODO: fill this reusable template.\n",
            encoding="utf-8",
        )
        intentional_eval_fixture = (
            intentional_placeholders / "evals" / "files" / "unfinished-skill"
        )
        intentional_eval_fixture.mkdir(parents=True)
        intentional_eval_fixture.joinpath("SKILL.md").write_text(
            "# Fixture\n\nTODO: expected unfinished input {{fixture_value}}.\n",
            encoding="utf-8",
        )
        checks.append(
            (
                "templates, eval fixtures, and runtime fenced examples may keep marker data",
                lambda: bool(validate_skill(str(intentional_placeholders))["valid"]),
            )
        )

        runtime_templates = workspace / "runtime-templates"
        write_fixture(
            runtime_templates,
            body=(
                "# Runtime Templates\n\n"
                "Read [runtime details](references/runtime.md)."
            ),
            payload=valid_eval_payload(runtime_templates.name),
        )
        runtime_templates.joinpath("README.md").write_text(
            "# Runtime Templates\n\nThe TODO noun names a work-item category.\n",
            encoding="utf-8",
        )
        runtime_references = runtime_templates / "references"
        runtime_references.mkdir()
        runtime_references.joinpath("runtime.md").write_text(
            "# Runtime\n\n"
            "Use {{.Names}} and {{json .}} at execution time.\n\n"
            "{{if .Enabled}}enabled{{else}}disabled{{end}}\n",
            encoding="utf-8",
        )
        runtime_agents = runtime_templates / "agents"
        runtime_agents.mkdir()
        runtime_agents.joinpath("openai.yaml").write_text(
            'display_name: "{{.Names}}"\n', encoding="utf-8"
        )
        checks.append(
            (
                "TODO nouns and complete runtime mustache actions are not author debt",
                lambda: bool(validate_skill(str(runtime_templates))["valid"]),
            )
        )

        agent_marker = workspace / "agent-marker"
        write_fixture(agent_marker, payload=valid_eval_payload(agent_marker.name))
        agent_marker.joinpath("agents").mkdir()
        agent_marker.joinpath("agents", "reviewer.md").write_text(
            "# Reviewer\n\nFIXME: replace this draft agent instruction.\n",
            encoding="utf-8",
        )
        agent_marker_result = validate_skill(str(agent_marker))
        agent_marker_errors = agent_marker_result["errors"]
        assert isinstance(agent_marker_errors, list)
        checks.append(
            (
                "live agent prompts participate in release marker checks",
                lambda: any(
                    "agents/reviewer.md contains unresolved authoring markers" in error
                    for error in agent_marker_errors
                ),
            )
        )

        invalid_metadata = workspace / "invalid-metadata"
        write_fixture(
            invalid_metadata,
            payload=valid_eval_payload(invalid_metadata.name),
        )
        invalid_metadata.joinpath("metadata.json").write_text(
            '{"version": "1", "version": "2"}\n', encoding="utf-8"
        )
        invalid_metadata_result = validate_skill(str(invalid_metadata))
        invalid_metadata_errors = invalid_metadata_result["errors"]
        assert isinstance(invalid_metadata_errors, list)
        checks.append(
            (
                "live metadata JSON is strict-parsed with duplicate-key rejection",
                lambda: any(
                    "metadata.json is not valid strict JSON" in error
                    and "duplicate JSON key" in error
                    for error in invalid_metadata_errors
                ),
            )
        )

        unreadable_agent_yaml = workspace / "unreadable-agent-yaml"
        write_fixture(
            unreadable_agent_yaml,
            payload=valid_eval_payload(unreadable_agent_yaml.name),
        )
        unreadable_agent_yaml.joinpath("agents").mkdir()
        unreadable_agent_yaml.joinpath("agents", "openai.yaml").write_bytes(
            b"display_name: \xff\n"
        )
        unreadable_agent_result = validate_skill(str(unreadable_agent_yaml))
        unreadable_agent_errors = unreadable_agent_result["errors"]
        assert isinstance(unreadable_agent_errors, list)
        checks.append(
            (
                "agent UI YAML must be readable UTF-8",
                lambda: any(
                    "Cannot read live metadata file agents/openai.yaml" in error
                    for error in unreadable_agent_errors
                ),
            )
        )

        known_bad_eval_fixture = workspace / "known-bad-eval-fixture"
        known_bad_payload = valid_eval_payload(known_bad_eval_fixture.name)
        known_bad_evals = known_bad_payload["evals"]
        assert isinstance(known_bad_evals, list)
        known_bad_evals[0]["files"] = ["evals/files/broken/SKILL.md"]
        write_fixture(known_bad_eval_fixture, payload=known_bad_payload)
        broken_fixture_directory = (
            known_bad_eval_fixture / "evals" / "files" / "broken"
        )
        broken_fixture_directory.mkdir(parents=True)
        broken_fixture_directory.joinpath("SKILL.md").write_text(
            "# Intentionally Broken Fixture\n\n"
            "TODO replace this during the eval.\n\n"
            "Read [missing](../../../../outside.md).\n",
            encoding="utf-8",
        )
        checks.append(
            (
                "known-bad Markdown eval fixtures are excluded from live validation",
                lambda: bool(validate_skill(str(known_bad_eval_fixture))["valid"]),
            )
        )

        unsupported_frontmatter = workspace / "unsupported-frontmatter"
        write_fixture(
            unsupported_frontmatter,
            payload=valid_eval_payload(unsupported_frontmatter.name),
        )
        unsupported_frontmatter.joinpath("SKILL.md").write_text(
            "# Missing Delimiters\n\nNo supported frontmatter block.\n",
            encoding="utf-8",
        )
        unsupported_frontmatter_result = validate_skill(str(unsupported_frontmatter))
        unsupported_frontmatter_errors = unsupported_frontmatter_result["errors"]
        assert isinstance(unsupported_frontmatter_errors, list)
        checks.append(
            (
                "frontmatter diagnostic describes the supported subset",
                lambda: any(
                    "no supported frontmatter block" in error
                    and "top-level key: value" in error
                    for error in unsupported_frontmatter_errors
                )
                and all("valid YAML" not in error for error in unsupported_frontmatter_errors),
            )
        )

        malformed_frontmatter_cases = {
            "duplicate": (
                "name: {name}\nname: {name}\n"
                'description: "Duplicate fixture."'
            ),
            "flow": "name: {name}\ndescription: [not, a, string]",
            "block": "name: {name}\ndescription: >\n  not parsed as a string",
            "quote": 'name: {name}\ndescription: "unterminated',
            "trailing-quote": 'name: {name}\ndescription: "foo" bar"',
            "bad-escape": 'name: {name}\ndescription: "bad\\q"',
            "bad-unicode": 'name: {name}\ndescription: "bad\\uZZZZ"',
            "mapping": "name: {name}\ndescription: foo: bar",
            "null": "name: {name}\ndescription: null",
            "boolean": "name: {name}\ndescription: true",
            "number": "name: {name}\ndescription: 123",
            "date": "name: {name}\ndescription: 2026-07-12",
        }
        malformed_frontmatter_results: list[dict[str, object]] = []
        for case_name, frontmatter_text in malformed_frontmatter_cases.items():
            fixture = workspace / f"frontmatter-{case_name}"
            write_fixture(fixture, payload=valid_eval_payload(fixture.name))
            fixture.joinpath("SKILL.md").write_text(
                "---\n"
                + frontmatter_text.format(name=fixture.name)
                + "\n---\n\n# Fixture\n",
                encoding="utf-8",
            )
            malformed_frontmatter_results.append(validate_skill(str(fixture)))
        checks.append(
            (
                "malformed and non-string portable frontmatter fields fail release",
                lambda: all(
                    not bool(result["valid"])
                    and any(
                        "Unsupported frontmatter" in error
                        for error in result["errors"]
                    )
                    for result in malformed_frontmatter_results
                ),
            )
        )

        optional_frontmatter = workspace / "optional-frontmatter"
        write_fixture(
            optional_frontmatter,
            payload=valid_eval_payload(optional_frontmatter.name),
        )
        optional_frontmatter.joinpath("SKILL.md").write_text(
            "---\n"
            f"name: {optional_frontmatter.name} # portable plain string\n"
            "description: Ordinary unquoted description # supported comment\n"
            "owner: {team: platform, tier: 1}\n"
            "allowed-tools: [shell]\n"
            "publication-lanes: [\n"
            "  stable,\n"
            "  experimental\n"
            "]\n"
            "owner-notes: >\n"
            "  Platform owns this package.\n"
            "references:\n"
            "  - principles\n"
            "metadata:\n"
            "  labels: [release, curated]\n"
            "---\n\n# Optional Frontmatter\n",
            encoding="utf-8",
        )
        quoted_string_frontmatter = workspace / "quoted-string-frontmatter"
        write_fixture(
            quoted_string_frontmatter,
            payload=valid_eval_payload(quoted_string_frontmatter.name),
        )
        quoted_string_frontmatter.joinpath("SKILL.md").write_text(
            "---\n"
            f"name: {quoted_string_frontmatter.name}\n"
            'description: "true" # quoted text remains a string\n'
            "---\n\n# Quoted String\n",
            encoding="utf-8",
        )
        optional_frontmatter_result = validate_skill(str(optional_frontmatter))
        optional_frontmatter_warnings = optional_frontmatter_result["warnings"]
        assert isinstance(optional_frontmatter_warnings, list)
        checks.append(
            (
                "optional owner fields parse as YAML and inline comments stay safe",
                lambda: bool(optional_frontmatter_result["valid"])
                and any(
                    "Extended frontmatter YAML syntax was parsed" in warning
                    for warning in optional_frontmatter_warnings
                )
                and bool(validate_skill(str(quoted_string_frontmatter))["valid"]),
            )
        )

        malformed_optional_yaml = workspace / "malformed-optional-yaml"
        write_fixture(
            malformed_optional_yaml,
            payload=valid_eval_payload(malformed_optional_yaml.name),
        )
        malformed_optional_yaml.joinpath("SKILL.md").write_text(
            "---\n"
            f"name: {malformed_optional_yaml.name}\n"
            'description: "Malformed optional YAML fixture."\n'
            "allowed-tools: [shell\n"
            "---\n\n# Malformed Optional YAML\n",
            encoding="utf-8",
        )
        malformed_optional_result = validate_skill(str(malformed_optional_yaml))
        assert isinstance(malformed_optional_result["errors"], list)

        original_import = builtins.__import__

        def import_without_yaml(name: str, *args: object, **kwargs: object) -> object:
            if name == "yaml":
                raise ImportError("simulated missing optional parser")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_without_yaml):
            optional_without_yaml_release = validate_skill(
                str(optional_frontmatter), profile="release"
            )
            optional_without_yaml_draft = validate_skill(
                str(optional_frontmatter), profile="draft"
            )
        assert isinstance(optional_without_yaml_release["errors"], list)
        assert isinstance(optional_without_yaml_draft["warnings"], list)
        checks.append(
            (
                "malformed extended YAML fails and missing parser cannot certify release",
                lambda: any(
                    "SKILL.md frontmatter is not valid YAML" in error
                    for error in malformed_optional_result["errors"]
                )
                and any(
                    "PyYAML is unavailable" in error
                    for error in optional_without_yaml_release["errors"]
                )
                and bool(optional_without_yaml_draft["valid"])
                and any(
                    "PyYAML is unavailable" in warning
                    for warning in optional_without_yaml_draft["warnings"]
                ),
            )
        )

        malformed_agent_yaml = workspace / "malformed-agent-yaml"
        write_fixture(
            malformed_agent_yaml,
            payload=valid_eval_payload(malformed_agent_yaml.name),
        )
        malformed_agent_yaml.joinpath("agents").mkdir()
        malformed_agent_yaml.joinpath("agents", "openai.yaml").write_text(
            "interface:\n  display_name: First\n  display_name: Second\n",
            encoding="utf-8",
        )
        malformed_agent_result = validate_skill(str(malformed_agent_yaml))
        assert isinstance(malformed_agent_result["errors"], list)
        checks.append(
            (
                "live agent YAML is strict-parsed with duplicate-key rejection",
                lambda: any(
                    "agents/openai.yaml is not valid YAML" in error
                    and "duplicate YAML key" in error
                    for error in malformed_agent_result["errors"]
                ),
            )
        )

        missing_evals = workspace / "missing-evals"
        write_fixture(missing_evals, payload=None)
        missing_evals_release = validate_skill(str(missing_evals), profile="release")
        missing_evals_errors = missing_evals_release["errors"]
        assert isinstance(missing_evals_errors, list)
        missing_evals_draft = validate_skill(str(missing_evals), profile="draft")
        missing_evals_warnings = missing_evals_draft["warnings"]
        assert isinstance(missing_evals_warnings, list)
        checks.append(
            (
                "complete SKILL without evals fails release only",
                lambda: any(
                    "evals/evals.json is required" in error
                    for error in missing_evals_errors
                )
                and bool(missing_evals_draft["valid"])
                and any(
                    "evals/evals.json is required" in warning
                    for warning in missing_evals_warnings
                ),
            )
        )

        malformed_collections = workspace / "malformed-collections"
        malformed_collections_payload = valid_eval_payload(malformed_collections.name)
        malformed_collections_evals = malformed_collections_payload["evals"]
        assert isinstance(malformed_collections_evals, list)
        malformed_collections_evals[0]["tags"] = "smoke"
        malformed_collections_evals[0]["files"] = {"path": "input.txt"}
        write_fixture(malformed_collections, payload=malformed_collections_payload)
        malformed_collections_result = validate_skill(str(malformed_collections))
        malformed_collections_errors = malformed_collections_result["errors"]
        assert isinstance(malformed_collections_errors, list)
        checks.append(
            (
                "malformed tag and file collections each fail release",
                lambda: any("'tags' must be an array" in error for error in malformed_collections_errors)
                and any("'files' must be an array" in error for error in malformed_collections_errors),
            )
        )

        unknown_eval_fields = workspace / "unknown-eval-fields"
        unknown_eval_payload = valid_eval_payload(unknown_eval_fields.name)
        unknown_eval_payload["unexpected_manifest_field"] = True
        unknown_eval_cases = unknown_eval_payload["evals"]
        assert isinstance(unknown_eval_cases, list)
        unknown_eval_cases[0]["unexpected_case_field"] = True
        unknown_eval_cases[0]["assertions"][0]["unexpected_assertion_field"] = True
        write_fixture(unknown_eval_fields, payload=unknown_eval_payload)
        unknown_eval_result = validate_skill(
            str(unknown_eval_fields), profile="draft"
        )
        unknown_eval_errors = unknown_eval_result["errors"]
        assert isinstance(unknown_eval_errors, list)
        checks.append(
            (
                "behavioral eval manifests use closed schemas in every profile",
                lambda: not bool(unknown_eval_result["valid"])
                and any(
                    "unknown top-level fields: unexpected_manifest_field" in error
                    for error in unknown_eval_errors
                )
                and any(
                    "unknown fields: unexpected_case_field" in error
                    for error in unknown_eval_errors
                )
                and any(
                    "unknown fields: unexpected_assertion_field" in error
                    for error in unknown_eval_errors
                ),
            )
        )

        non_object_json = workspace / "non-object-json"
        write_fixture(non_object_json, payload=["not", "an", "object"])
        non_object_result = validate_skill(str(non_object_json))
        non_object_errors = non_object_result["errors"]
        assert isinstance(non_object_errors, list)
        checks.append(
            (
                "non-object eval JSON fails gracefully",
                lambda: any("must contain a JSON object" in error for error in non_object_errors)
                and not bool(
                    validate_skill(str(non_object_json), profile="draft")["valid"]
                ),
            )
        )

        evals_non_array = workspace / "evals-non-array"
        evals_non_array_payload = valid_eval_payload(evals_non_array.name)
        evals_non_array_payload["evals"] = {"case": "not-an-array"}
        write_fixture(evals_non_array, payload=evals_non_array_payload)
        evals_non_array_draft = validate_skill(str(evals_non_array), profile="draft")
        evals_non_array_errors = evals_non_array_draft["errors"]
        assert isinstance(evals_non_array_errors, list)
        checks.append(
            (
                "draft rejects a non-array eval collection",
                lambda: not bool(evals_non_array_draft["valid"])
                and any("'evals' must be an array" in error for error in evals_non_array_errors),
            )
        )

        non_object_case = workspace / "non-object-case"
        non_object_case_payload = valid_eval_payload(non_object_case.name)
        non_object_case_payload["evals"] = ["not-an-object"]
        write_fixture(non_object_case, payload=non_object_case_payload)
        non_object_case_draft = validate_skill(str(non_object_case), profile="draft")
        non_object_case_errors = non_object_case_draft["errors"]
        assert isinstance(non_object_case_errors, list)
        checks.append(
            (
                "draft rejects a non-object eval case",
                lambda: not bool(non_object_case_draft["valid"])
                and any("eval must be an object" in error for error in non_object_case_errors),
            )
        )

        non_finite_json = workspace / "non-finite-json"
        non_finite_payload = valid_eval_payload(non_finite_json.name)
        non_finite_payload["created_by"] = float("nan")
        write_fixture(non_finite_json, payload=non_finite_payload)
        non_finite_result = validate_skill(str(non_finite_json))
        non_finite_errors = non_finite_result["errors"]
        assert isinstance(non_finite_errors, list)
        checks.append(
            (
                "non-standard JSON constants fail gracefully",
                lambda: any("non-standard JSON constant" in error for error in non_finite_errors)
                and not bool(test_skill(str(non_finite_json))["passed"]),
            )
        )

        duplicate = workspace / "duplicate-evals"
        duplicate_payload = valid_eval_payload(duplicate.name)
        duplicate_evals = duplicate_payload["evals"]
        assert isinstance(duplicate_evals, list)
        duplicate_evals.append(deepcopy(duplicate_evals[0]))
        write_fixture(duplicate, payload=duplicate_payload)
        duplicate_result = validate_skill(str(duplicate))
        duplicate_errors = duplicate_result["errors"]
        assert isinstance(duplicate_errors, list)
        checks.append(
            (
                "duplicate eval ids and names fail release",
                lambda: any("duplicate id" in error for error in duplicate_errors)
                and any("duplicate name" in error for error in duplicate_errors)
                and not bool(validate_skill(str(duplicate), profile="draft")["valid"]),
            )
        )

        escaping = workspace / "escaping-file"
        escaping_payload = valid_eval_payload(escaping.name)
        escaping_evals = escaping_payload["evals"]
        assert isinstance(escaping_evals, list)
        escaping_evals[0]["files"] = [
            "../outside.txt",
            "..\\outside.txt",
            "C:\\outside.txt",
        ]
        write_fixture(escaping, payload=escaping_payload)
        escaping_result = validate_skill(str(escaping))
        escaping_errors = escaping_result["errors"]
        assert isinstance(escaping_errors, list)
        checks.append(
            (
                "eval file escape fails release",
                lambda: sum("eval file path escapes" in error for error in escaping_errors)
                == 3
                and not bool(test_skill(str(escaping))["passed"]),
            )
        )

        nul_path = workspace / "nul-path"
        nul_payload = valid_eval_payload(nul_path.name)
        nul_evals = nul_payload["evals"]
        assert isinstance(nul_evals, list)
        nul_evals[0]["files"] = ["evals/files/\u0000.txt"]
        write_fixture(nul_path, payload=nul_payload)
        nul_result = validate_skill(str(nul_path))
        nul_errors = nul_result["errors"]
        assert isinstance(nul_errors, list)
        checks.append(
            (
                "NUL eval path fails without crashing either checker",
                lambda: any("invalid eval file path" in error for error in nul_errors)
                and not bool(test_skill(str(nul_path))["passed"]),
            )
        )

        oversized = workspace / "oversized-skill"
        write_fixture(
            oversized,
            body="\n".join(f"Line {index}" for index in range(501)),
            payload=valid_eval_payload(oversized.name),
        )
        checks.append(
            (
                "body over 500 lines fails release",
                lambda: not bool(validate_skill(str(oversized))["valid"]),
            )
        )

        oversized_reference = workspace / "oversized-reference"
        write_fixture(
            oversized_reference,
            body=(
                "# Oversized Reference\n\n"
                "Read [the detail](references/detail.md)."
            ),
            payload=valid_eval_payload(oversized_reference.name),
        )
        oversized_reference.joinpath("references").mkdir()
        oversized_reference.joinpath("references", "detail.md").write_text(
            "\n".join(f"Detail {index}" for index in range(1001)) + "\n",
            encoding="utf-8",
        )
        oversized_reference_release = validate_skill(str(oversized_reference))
        oversized_reference_draft = validate_skill(
            str(oversized_reference), profile="draft"
        )
        oversized_reference_warnings = oversized_reference_draft["warnings"]
        assert isinstance(oversized_reference_warnings, list)
        checks.append(
            (
                "reference hard ceiling is release-only completeness",
                lambda: not bool(oversized_reference_release["valid"])
                and bool(oversized_reference_draft["valid"])
                and any(
                    "Reference file exceeds 1000 lines" in warning
                    for warning in oversized_reference_warnings
                ),
            )
        )

        broken_link = workspace / "broken-link"
        write_fixture(
            broken_link,
            body="# Broken Link\n\nRead [the guide](references/guide.md).",
            payload=valid_eval_payload(broken_link.name),
        )
        (broken_link / "references").mkdir()
        (broken_link / "references" / "guide.md").write_text(
            "# Guide\n\nRead [the missing detail](missing.md).\n", encoding="utf-8"
        )
        checks.append(
            (
                "nested package Markdown links are checked",
                lambda: not bool(validate_skill(str(broken_link))["valid"]),
            )
        )

        relative_links = workspace / "relative-links"
        write_fixture(
            relative_links,
            body="# Relative Links\n\nRead [the guide](references/guide.md).",
            payload=valid_eval_payload(relative_links.name),
        )
        relative_references = relative_links / "references"
        relative_references.mkdir()
        relative_references.joinpath("guide.md").write_text(
            "# Guide\n\nRead [the sibling](sibling.md).\n", encoding="utf-8"
        )
        relative_references.joinpath("sibling.md").write_text(
            "# Sibling\n", encoding="utf-8"
        )
        checks.append(
            (
                "package Markdown links follow source-relative semantics",
                lambda: bool(validate_skill(str(relative_links))["valid"]),
            )
        )

        balanced_links = workspace / "balanced-links"
        write_fixture(
            balanced_links,
            body="# Balanced Links\n\nRead [API v2](references/api(v2).md).",
            payload=valid_eval_payload(balanced_links.name),
        )
        balanced_references = balanced_links / "references"
        balanced_references.mkdir()
        balanced_references.joinpath("api(v2).md").write_text(
            "# API v2\n", encoding="utf-8"
        )
        balanced_references.joinpath("api v2.md").write_text(
            "# API v2 with spaces\n", encoding="utf-8"
        )
        balanced_links.joinpath("SKILL.md").write_text(
            balanced_links.joinpath("SKILL.md").read_text(encoding="utf-8")
            + '\nRead [the spaced API](<references/api v2.md> "API title").\n',
            encoding="utf-8",
        )
        checks.append(
            (
                "balanced and angle-bracket Markdown destinations are preserved",
                lambda: bool(validate_skill(str(balanced_links))["valid"]),
            )
        )

        reference_style = workspace / "reference-style-link"
        write_fixture(
            reference_style,
            body="# Reference Link\n\nRead [the guide][g].\n\n[g]: ../../outside.md",
            payload=valid_eval_payload(reference_style.name),
        )
        reference_style_result = validate_skill(str(reference_style))
        reference_style_errors = reference_style_result["errors"]
        assert isinstance(reference_style_errors, list)
        checks.append(
            (
                "reference-style Markdown destination cannot escape",
                lambda: any(
                    "Local link escapes skill root" in error
                    for error in reference_style_errors
                ),
            )
        )

        nested_fence = workspace / "nested-fence"
        nested_fence_body = (
            "# Nested Fence\n\n"
            "````markdown\n"
            "[Example](../../outside.md)\n"
            "```\n"
            "still fenced\n"
            "````\n\n"
            "Read [the missing guide](missing.md)."
        )
        write_fixture(
            nested_fence,
            body=nested_fence_body,
            payload=valid_eval_payload(nested_fence.name),
        )
        nested_fence_result = validate_skill(str(nested_fence))
        nested_fence_errors = nested_fence_result["errors"]
        assert isinstance(nested_fence_errors, list)
        checks.append(
            (
                "fence length rules hide examples but preserve following prose",
                lambda: any("missing.md" in error for error in nested_fence_errors)
                and all("outside.md" not in error for error in nested_fence_errors),
            )
        )

        windows_link = workspace / "windows-link"
        write_fixture(
            windows_link,
            body="# Windows Link\n\nRead [outside](C:/outside.md).",
            payload=valid_eval_payload(windows_link.name),
        )
        windows_link_result = validate_skill(str(windows_link))
        windows_link_errors = windows_link_result["errors"]
        assert isinstance(windows_link_errors, list)
        checks.append(
            (
                "Windows absolute Markdown destination cannot escape",
                lambda: any("C:/outside.md" in error for error in windows_link_errors),
            )
        )

        ignored_links = workspace / "ignored-links"
        ignored_body = (
            "# Ignored Links\n\n"
            "[External](https://example.com/docs)\n\n"
            "[Placeholder](references/{{FILE}}.md)\n\n"
            "```markdown\n[Example](../../outside.md)\n```"
        )
        write_fixture(
            ignored_links,
            body=ignored_body,
            payload=valid_eval_payload(ignored_links.name),
        )
        ignored_result = validate_skill(str(ignored_links))
        ignored_errors = ignored_result["errors"]
        assert isinstance(ignored_errors, list)
        checks.append(
            (
                "placeholder live routes fail while external and fenced examples stay ignored",
                lambda: any(
                    "Placeholder-looking live local route" in error
                    for error in ignored_errors
                )
                and all("outside.md" not in error for error in ignored_errors),
            )
        )

        placeholder_routes = workspace / "placeholder-routes"
        write_fixture(
            placeholder_routes,
            body=(
                "# Placeholder Routes\n\n"
                "Read `references/{{branch}}.md` and `references/<FILE>.md`."
            ),
            payload=valid_eval_payload(placeholder_routes.name),
        )
        placeholder_routes_release = validate_skill(str(placeholder_routes))
        placeholder_routes_draft = validate_skill(
            str(placeholder_routes), profile="draft"
        )
        assert isinstance(placeholder_routes_release["errors"], list)
        assert isinstance(placeholder_routes_draft["warnings"], list)
        checks.append(
            (
                "lowercase and angle-bracket placeholder routes cannot release",
                lambda: sum(
                    "Placeholder-looking live local route" in error
                    for error in placeholder_routes_release["errors"]
                )
                == 2
                and bool(placeholder_routes_draft["valid"])
                and sum(
                    "Placeholder-looking live local route" in warning
                    for warning in placeholder_routes_draft["warnings"]
                )
                == 2,
            )
        )

        unsafe_inline_paths = workspace / "unsafe-inline-paths"
        write_fixture(
            unsafe_inline_paths,
            body=(
                "# Unsafe Inline Paths\n\n"
                "Read [the host file](file:///tmp/secret.txt), `../outside.md`, "
                "`..\\outside-windows.md`, and `%2e%2e%2foutside-encoded.md`."
            ),
            payload=valid_eval_payload(unsafe_inline_paths.name),
        )
        unsafe_inline_result = validate_skill(str(unsafe_inline_paths))
        unsafe_inline_errors = unsafe_inline_result["errors"]
        assert isinstance(unsafe_inline_errors, list)
        checks.append(
            (
                "file URIs and escaping backticked paths are rejected",
                lambda: any(
                    "Local file URI is not allowed" in error
                    for error in unsafe_inline_errors
                )
                and sum(
                    "Local link escapes skill root" in error
                    for error in unsafe_inline_errors
                )
                == 3,
            )
        )

        bad_name = workspace / "bad--name"
        write_fixture(bad_name, payload=valid_eval_payload(bad_name.name))
        checks.append(
            (
                "consecutive hyphens fail naming validation",
                lambda: not bool(validate_skill(str(bad_name))["valid"]),
            )
        )

        symlink_skill = workspace / "symlink-skill"
        symlink_skill.mkdir()
        external_skill_md = workspace / "external-skill.md"
        external_skill_md.write_text(
            "---\n"
            "name: symlink-skill\n"
            'description: "External entry fixture."\n'
            "---\n\n# Symlink Skill\n",
            encoding="utf-8",
        )
        symlink_skill.joinpath("evals").mkdir()
        symlink_skill.joinpath("evals", "evals.json").write_text(
            json.dumps(valid_eval_payload(symlink_skill.name), indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            symlink_skill.joinpath("SKILL.md").symlink_to(external_skill_md)
        except OSError:
            skipped_symlink_checks += 1
        else:
            symlink_skill_result = validate_skill(str(symlink_skill))
            symlink_skill_errors = symlink_skill_result["errors"]
            assert isinstance(symlink_skill_errors, list)
            checks.append(
                (
                    "symlinked SKILL entry cannot escape package",
                    lambda: any(
                        "Package symlink resolves outside skill root: SKILL.md" in error
                        for error in symlink_skill_errors
                    ),
                )
            )

        symlink_evals = workspace / "symlink-evals"
        write_fixture(symlink_evals, payload=None)
        symlink_evals.joinpath("evals").mkdir()
        external_evals = workspace / "external-evals.json"
        external_evals.write_text(
            json.dumps(valid_eval_payload(symlink_evals.name), indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            symlink_evals.joinpath("evals", "evals.json").symlink_to(external_evals)
        except OSError:
            skipped_symlink_checks += 1
        else:
            symlink_evals_result = validate_skill(str(symlink_evals))
            symlink_evals_errors = symlink_evals_result["errors"]
            assert isinstance(symlink_evals_errors, list)
            checks.append(
                (
                    "symlinked eval manifest cannot escape package",
                    lambda: any(
                        "Package symlink resolves outside skill root: evals/evals.json"
                        in error
                        for error in symlink_evals_errors
                    )
                    and not bool(test_skill(str(symlink_evals))["passed"]),
                )
            )

        unreferenced_symlink = workspace / "unreferenced-symlink"
        write_fixture(
            unreferenced_symlink,
            payload=valid_eval_payload(unreferenced_symlink.name),
        )
        unreferenced_assets = unreferenced_symlink / "assets"
        unreferenced_assets.mkdir()
        external_asset = workspace / "external-asset.txt"
        external_asset.write_text("outside\n", encoding="utf-8")
        try:
            unreferenced_assets.joinpath("unused.txt").symlink_to(external_asset)
        except OSError:
            skipped_symlink_checks += 1
        else:
            unreferenced_result = validate_skill(str(unreferenced_symlink))
            unreferenced_errors = unreferenced_result["errors"]
            assert isinstance(unreferenced_errors, list)
            checks.append(
                (
                    "unreferenced direct-file symlink cannot escape package",
                    lambda: any(
                        "assets/unused.txt" in error
                        and "resolves outside skill root" in error
                        for error in unreferenced_errors
                    ),
                )
            )

        symlink_directory = workspace / "symlink-directory"
        write_fixture(
            symlink_directory,
            payload=valid_eval_payload(symlink_directory.name),
        )
        symlink_directory.joinpath("agents").mkdir()
        external_agent_directory = workspace / "external-agent-directory"
        external_agent_directory.mkdir()
        external_agent_directory.joinpath("reviewer.md").write_text(
            "# External reviewer\n", encoding="utf-8"
        )
        try:
            symlink_directory.joinpath("agents", "external").symlink_to(
                external_agent_directory, target_is_directory=True
            )
        except OSError:
            skipped_symlink_checks += 1
        else:
            symlink_directory_result = validate_skill(str(symlink_directory))
            symlink_directory_errors = symlink_directory_result["errors"]
            assert isinstance(symlink_directory_errors, list)
            checks.append(
                (
                    "symlinked directory cannot escape package",
                    lambda: any(
                        "agents/external" in error
                        and "resolves outside skill root" in error
                        for error in symlink_directory_errors
                    ),
                )
            )

        dangling_symlink = workspace / "dangling-symlink"
        write_fixture(
            dangling_symlink,
            payload=valid_eval_payload(dangling_symlink.name),
        )
        dangling_symlink.joinpath("scripts").mkdir()
        try:
            dangling_symlink.joinpath("scripts", "missing.py").symlink_to(
                workspace / "does-not-exist.py"
            )
        except OSError:
            skipped_symlink_checks += 1
        else:
            dangling_result = validate_skill(str(dangling_symlink))
            dangling_errors = dangling_result["errors"]
            assert isinstance(dangling_errors, list)
            checks.append(
                (
                    "dangling package symlink fails preflight",
                    lambda: any(
                        "Dangling package symlink: scripts/missing.py" in error
                        for error in dangling_errors
                    ),
                )
            )

        skipped_checks = 0
        for check_index, (label, check) in enumerate(checks):
            if bash_executable is None and check_index < scaffold_check_count:
                skipped_checks += 1
                continue
            try:
                passed = check()
            except Exception as exc:  # Keep the self-test report actionable.
                passed = False
                failures.append(f"{label}: raised {type(exc).__name__}: {exc}")
            if not passed and not any(item.startswith(f"{label}:") for item in failures):
                failures.append(f"{label}: condition was false")

    if skipped_checks:
        certification_limits.append(
            f"Bash is unavailable; {skipped_checks} scaffold regressions were not run"
        )
    if skipped_ancestor_swap_checks:
        certification_limits.append(
            "This host does not permit the output-root rename used by the "
            "ancestor-swap regression; that regression was not run"
        )
    if skipped_symlink_checks:
        certification_limits.append(
            "This filesystem does not support the requested symlinks; "
            f"{skipped_symlink_checks} symlink regressions were not run"
        )
    executed_checks = len(checks) - skipped_checks
    return (
        executed_checks - len(failures),
        executed_checks,
        failures,
        certification_limits,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run strict eval-schema and package-integrity checks for a skill."
    )
    parser.add_argument("skill_path", nargs="?", help="Path to the skill directory")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run isolated regression fixtures for this checker",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        if args.skill_path is not None:
            print("Error: --self-test does not accept a skill path", file=os.sys.stderr)
            return 1
        passed, total, failures, certification_limits = run_self_tests()
        print(f"Self-test: {passed}/{total} passed")
        for failure in failures:
            print(f"  - {failure}")
        if certification_limits:
            print("Certification limits:")
            for limitation in certification_limits:
                print(f"  - {limitation}")
        outcome, exit_code = certification_outcome(
            passed == total, certification_limits
        )
        print(outcome)
        return exit_code

    if args.skill_path is None:
        print("Error: skill_path is required unless --self-test is used", file=os.sys.stderr)
        return 1
    skill_path = Path(args.skill_path).expanduser()
    if not skill_path.is_dir():
        print(f"Error: '{args.skill_path}' is not a directory", file=os.sys.stderr)
        return 1

    results = test_skill(str(skill_path))
    internal_regression_summary: tuple[int, int] | None = None
    certification_limits: list[str] = []
    placement_regression_status: str | None = None
    creator_root = Path(__file__).resolve().parent.parent
    if skill_path.resolve() == creator_root:
        (
            internal_passed,
            internal_total,
            internal_failures,
            certification_limits,
        ) = run_self_tests()
        internal_regression_summary = (internal_passed, internal_total)
        result_errors = results["errors"]
        assert isinstance(result_errors, list)
        if internal_failures:
            results["passed"] = False
            result_errors.extend(
                f"Internal automation regression: {failure}"
                for failure in internal_failures
            )

        placement_environment = os.environ.copy()
        placement_environment["PYTHONDONTWRITEBYTECODE"] = "1"
        placement_test = Path(__file__).resolve().with_name("test_infer_destination.py")
        placement_result = subprocess.run(
            [os.sys.executable, str(placement_test)],
            capture_output=True,
            text=True,
            check=False,
            env=placement_environment,
        )
        placement_regression_status = (
            "PASS" if placement_result.returncode == 0 else "FAIL"
        )
        if placement_result.returncode != 0:
            results["passed"] = False
            detail = (placement_result.stderr or placement_result.stdout).strip()
            result_errors.append(
                "Placement regression suite failed"
                + (f": {detail}" if detail else "")
            )

    print(f"Skill: {results['skill_name']}")
    print(f"Tests found: {results['tests_found']}")
    trigger_balance = results["trigger_balance"]
    assert isinstance(trigger_balance, dict)
    print(
        f"Trigger tests found: {results['trigger_tests_found']} "
        f"({trigger_balance['positive']} positive, {trigger_balance['negative']} negative)"
    )
    if internal_regression_summary is not None:
        print(
            "Internal automation regressions: "
            f"{internal_regression_summary[0]}/{internal_regression_summary[1]} passed"
        )
    if placement_regression_status is not None:
        print(f"Placement regressions: {placement_regression_status}")

    tags = results["tags"]
    assert isinstance(tags, dict)
    for tag, count in sorted(tags.items()):
        print(f"  {tag}: {count}")

    files = results["files_verified"]
    cross_references = results["cross_references"]
    assertions = results["assertions_valid"]
    assert isinstance(files, dict)
    assert isinstance(cross_references, dict)
    assert isinstance(assertions, dict)
    print(f"Files verified: {files['passed']}/{files['total']}")
    print(
        "Cross-references checked: "
        f"{cross_references['passed']}/{cross_references['total']}"
    )
    print(f"Assertion format: {assertions['passed']}/{assertions['total']} valid")

    errors = results["errors"]
    warnings = results["warnings"]
    assert isinstance(errors, list) and isinstance(warnings, list)
    if errors:
        print(f"\nIssues ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")
    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")
    if certification_limits:
        print("\nCertification limits:")
        for limitation in certification_limits:
            print(f"  - {limitation}")

    print()
    outcome, exit_code = certification_outcome(
        bool(results["passed"]), certification_limits
    )
    print(outcome)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

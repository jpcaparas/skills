#!/usr/bin/env python3
"""
test_skill.py - Validate packaging and run helper-script probes.

Usage:
    python3 test_skill.py <skill-path>
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate


def extract_file_references(content: str) -> list[str]:
    refs: set[str] = set()
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")

    for match in re.finditer(
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`", stripped
    ):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.add(path)

    for match in re.finditer(
        r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
        stripped,
    ):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.add(path)

    return sorted(refs)


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env["TZ"] = "UTC"
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=merged_env,
        capture_output=True,
        text=True,
        check=False,
    )


def write_commit(repo: Path, rel_path: str, content: str, message: str, date: str) -> None:
    file_path = repo / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    add_result = run(["git", "add", rel_path], cwd=repo)
    if add_result.returncode != 0:
        raise RuntimeError(add_result.stderr.strip() or "git add failed")

    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = f"{date}T12:00:00+00:00"
    env["GIT_COMMITTER_DATE"] = f"{date}T12:00:00+00:00"
    commit_result = run(["git", "commit", "-m", message], cwd=repo, env=env)
    if commit_result.returncode != 0:
        raise RuntimeError(commit_result.stderr.strip() or "git commit failed")


def create_sample_repo() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="client-report-skill-"))
    init_result = run(["git", "init", "-q"], cwd=temp_dir)
    if init_result.returncode != 0:
        raise RuntimeError(init_result.stderr.strip() or "git init failed")

    for key, value in [
        ("user.name", "Skill Test"),
        ("user.email", "skill-test@example.com"),
    ]:
        config_result = run(["git", "config", key, value], cwd=temp_dir)
        if config_result.returncode != 0:
            raise RuntimeError(config_result.stderr.strip() or f"git config {key} failed")

    write_commit(
        temp_dir,
        "docs/legacy.md",
        "old work\n",
        "docs: add legacy notes",
        "2026-03-30",
    )
    write_commit(
        temp_dir,
        "checkout/flow.md",
        "checkout improvements\n",
        "feat(checkout): simplify payment journey",
        "2026-04-05",
    )
    write_commit(
        temp_dir,
        "reports/overview.md",
        "reporting updates\n",
        "feat(reports): expand client reporting",
        "2026-04-06",
    )
    write_commit(
        temp_dir,
        "infra/queue.md",
        "queue maintenance\n",
        "chore(infra): stabilize background jobs",
        "2026-04-08",
    )
    return temp_dir


def run_helper_checks(root: Path) -> tuple[dict[str, int], list[str]]:
    helper = root / "scripts" / "collect_git_changes.py"
    counts = {"passed": 0, "total": 0}
    errors: list[str] = []

    sample_repo = create_sample_repo()

    counts["total"] += 1
    help_result = run(["python3", str(helper), "--help"])
    if help_result.returncode == 0 and "YYYY-MM-DD" in help_result.stdout:
        counts["passed"] += 1
    else:
        errors.append("Helper script --help did not succeed with the expected usage text")

    counts["total"] += 1
    range_result = run(
        [
            "python3",
            str(helper),
            "--repo",
            str(sample_repo),
            "--since",
            "2026-04-01",
            "--until",
            "2026-04-06",
        ]
    )
    if range_result.returncode == 0:
        payload = json.loads(range_result.stdout)
        scopes = {item["scope"] for item in payload.get("scopes", [])}
        if payload.get("commit_count") == 2 and scopes == {"checkout", "reports"}:
            counts["passed"] += 1
        else:
            errors.append("Helper script returned unexpected commit data for the bounded range")
    else:
        errors.append("Helper script failed on a valid temporary git repository")

    counts["total"] += 1
    invalid_date_result = run(
        [
            "python3",
            str(helper),
            "--repo",
            str(sample_repo),
            "--since",
            "this-week",
        ]
    )
    if invalid_date_result.returncode != 0 and "YYYY-MM-DD" in invalid_date_result.stderr:
        counts["passed"] += 1
    else:
        errors.append("Helper script did not reject an ambiguous date format")

    counts["total"] += 1
    missing_repo_result = run(
        [
            "python3",
            str(helper),
            "--repo",
            str(sample_repo / "missing"),
            "--since",
            "2026-04-01",
        ]
    )
    if missing_repo_result.returncode != 0 and "does not exist" in missing_repo_result.stderr:
        counts["passed"] += 1
    else:
        errors.append("Helper script did not report a missing repository path")

    return counts, errors


def run_tests(skill_path: str) -> dict[str, object]:
    root = Path(skill_path).resolve()
    results: dict[str, object] = {
        "skill_name": root.name,
        "tests_found": 0,
        "tags": {},
        "files_verified": {"passed": 0, "total": 0},
        "cross_references": {"passed": 0, "total": 0},
        "assertions_valid": {"passed": 0, "total": 0},
        "tag_coverage": {"passed": 0, "total": 4},
        "helper_checks": {"passed": 0, "total": 0},
        "errors": [],
        "warnings": [],
        "passed": True,
    }

    validation = validate.validate_skill(str(root))
    results["warnings"].extend(validation["warnings"])
    if not validation["valid"]:
        results["errors"].extend(validation["errors"])
        results["passed"] = False

    evals_path = root / "evals" / "evals.json"
    if not evals_path.is_file():
        results["errors"].append("evals/evals.json not found")
        results["passed"] = False
    else:
        evals_data = json.loads(evals_path.read_text(encoding="utf-8"))
        evals = evals_data.get("evals", [])
        results["tests_found"] = len(evals)
        seen_tags: set[str] = set()

        for item in evals:
            eval_name = item.get("name", item.get("id", "unknown"))
            for tag in item.get("tags", []):
                seen_tags.add(tag)
                results["tags"][tag] = results["tags"].get(tag, 0) + 1

            for assertion in item.get("assertions", []):
                results["assertions_valid"]["total"] += 1
                if isinstance(assertion, dict) and "text" in assertion:
                    results["assertions_valid"]["passed"] += 1
                else:
                    results["errors"].append(f"Invalid assertion in eval '{eval_name}'")
                    results["passed"] = False

            for rel_path in item.get("files", []):
                results["files_verified"]["total"] += 1
                if (root / rel_path).exists():
                    results["files_verified"]["passed"] += 1
                else:
                    results["errors"].append(f"Missing eval file reference: {rel_path}")
                    results["passed"] = False

        for tag in ["smoke", "edge", "negative", "disclosure"]:
            if tag in seen_tags:
                results["tag_coverage"]["passed"] += 1
            else:
                results["errors"].append(f"Missing eval coverage for tag: {tag}")
                results["passed"] = False

    markdown_files = [root / "SKILL.md"]
    markdown_files.extend((root / "references").rglob("*.md"))
    markdown_files.extend((root / "templates").rglob("*.md"))
    for md_path in markdown_files:
        content = md_path.read_text(encoding="utf-8")
        for rel_path in extract_file_references(content):
            results["cross_references"]["total"] += 1
            if (root / rel_path).exists():
                results["cross_references"]["passed"] += 1
            else:
                results["errors"].append(f"Cross-reference not found: {rel_path}")
                results["passed"] = False

    helper_counts, helper_errors = run_helper_checks(root)
    results["helper_checks"] = helper_counts
    if helper_errors:
        results["errors"].extend(helper_errors)
        results["passed"] = False

    return results


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1

    results = run_tests(sys.argv[1])
    print(f"Skill: {results['skill_name']}")
    print(f"Tests found: {results['tests_found']}")
    for tag, count in sorted(results["tags"].items()):
        print(f"  {tag}: {count}")
    print(
        "Files verified: "
        f"{results['files_verified']['passed']}/{results['files_verified']['total']}"
    )
    print(
        "Cross-references checked: "
        f"{results['cross_references']['passed']}/{results['cross_references']['total']}"
    )
    print(
        "Assertion format: "
        f"{results['assertions_valid']['passed']}/{results['assertions_valid']['total']} valid"
    )
    print(
        "Tag coverage: "
        f"{results['tag_coverage']['passed']}/{results['tag_coverage']['total']}"
    )
    print(
        "Helper checks: "
        f"{results['helper_checks']['passed']}/{results['helper_checks']['total']} passed"
    )

    if results["warnings"]:
        print("\nWarnings:")
        for warning in results["warnings"]:
            print(f"  - {warning}")

    if results["errors"]:
        print("\nIssues:")
        for issue in results["errors"]:
            print(f"  - {issue}")

    print("\nPASS: all checks passed" if results["passed"] else "\nFAIL: one or more checks failed")
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

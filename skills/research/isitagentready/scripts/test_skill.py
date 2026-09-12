#!/usr/bin/env python3
"""
test_skill.py - Packaging and helper-script checks for the isitagentready skill.

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


REQUIRED_TAGS = {"smoke", "edge", "negative", "disclosure"}
REQUIRED_FILES = {
    "templates/agent-readiness-report.md",
    "scripts/create_report_packet.py",
    "scripts/scan_site.py",
    "references/methodology.md",
    "references/signal-map.md",
    "references/runtime-and-browser.md",
    "references/repo-search-playbook.md",
    "references/report-format.md",
    "references/gotchas.md",
}
REQUIRED_STRINGS = [
    "{{ skill:agent-browser }}",
    "What production URL should I audit for this repository?",
]


def extract_file_references(content: str) -> list[str]:
    refs = []
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")
    patterns = [
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`",
        r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, stripped):
            path = match.group(1)
            if not placeholder_re.search(path):
                refs.append(path)
    return sorted(set(refs))


def test_skill(skill_path: str) -> dict:
    skill_root = Path(skill_path).resolve()
    results = {
        "skill_name": skill_root.name,
        "tests_found": 0,
        "tags": {},
        "files_verified": {"passed": 0, "total": 0},
        "cross_references": {"passed": 0, "total": 0},
        "assertions_valid": {"passed": 0, "total": 0},
        "helper_checks": {"passed": 0, "total": 0},
        "errors": [],
        "passed": True,
    }

    for rel_path in sorted(REQUIRED_FILES):
        results["files_verified"]["total"] += 1
        if (skill_root / rel_path).exists():
            results["files_verified"]["passed"] += 1
        else:
            results["errors"].append(f"Required file missing: {rel_path}")
            results["passed"] = False

    evals_path = skill_root / "evals" / "evals.json"
    if not evals_path.is_file():
        results["errors"].append("evals/evals.json not found")
        results["passed"] = False
    else:
        with evals_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        evals = data.get("evals", [])
        if not isinstance(evals, list):
            results["errors"].append("'evals' field is not an array")
            results["passed"] = False
            evals = []
        results["tests_found"] = len(evals)
        for index, item in enumerate(evals):
            label = item.get("name", f"eval-{index}")
            for field in ["id", "prompt", "expected_output"]:
                if field not in item:
                    results["errors"].append(f"Eval '{label}' missing required field '{field}'")
                    results["passed"] = False
            for tag in item.get("tags", []):
                results["tags"][tag] = results["tags"].get(tag, 0) + 1
            for assertion in item.get("assertions", []):
                results["assertions_valid"]["total"] += 1
                if isinstance(assertion, dict) and "text" in assertion and "type" in assertion:
                    results["assertions_valid"]["passed"] += 1
                else:
                    results["errors"].append(f"Eval '{label}' has an invalid assertion")
                    results["passed"] = False
            for referenced_file in item.get("files", []):
                results["files_verified"]["total"] += 1
                if (skill_root / referenced_file).exists():
                    results["files_verified"]["passed"] += 1
                else:
                    results["errors"].append(f"Eval '{label}' references missing file: {referenced_file}")
                    results["passed"] = False

    missing_tags = REQUIRED_TAGS - set(results["tags"])
    if missing_tags:
        results["errors"].append(f"Missing required eval tag coverage: {', '.join(sorted(missing_tags))}")
        results["passed"] = False

    def check_file(path: Path) -> None:
        with path.open("r", encoding="utf-8") as handle:
            for ref in extract_file_references(handle.read()):
                results["cross_references"]["total"] += 1
                if (skill_root / ref).exists():
                    results["cross_references"]["passed"] += 1
                else:
                    results["errors"].append(f"Cross-reference not found from {path.relative_to(skill_root)}: {ref}")
                    results["passed"] = False

    skill_md = skill_root / "SKILL.md"
    if skill_md.is_file():
        skill_text = skill_md.read_text(encoding="utf-8")
        for expected in REQUIRED_STRINGS:
            if expected not in skill_text:
                results["errors"].append(f"SKILL.md is missing required text: {expected}")
                results["passed"] = False
        check_file(skill_md)

    for root, _, files in os.walk(skill_root / "references"):
        for filename in files:
            if filename.endswith(".md"):
                check_file(Path(root) / filename)

    report_template = skill_root / "templates" / "agent-readiness-report.md"
    if report_template.is_file():
        template_text = report_template.read_text(encoding="utf-8")
        for heading in [
            "## Executive Summary",
            "## Evidence Sources",
            "## Findings by Category",
            "## Prioritized Remediation",
        ]:
            results["helper_checks"]["total"] += 1
            if heading in template_text:
                results["helper_checks"]["passed"] += 1
            else:
                results["errors"].append(f"Report template missing heading: {heading}")
                results["passed"] = False
        results["helper_checks"]["total"] += 1
        if "{{REPO_PATH}}" in template_text:
            results["errors"].append("Report template leaks the absolute repo path placeholder")
            results["passed"] = False
        else:
            results["helper_checks"]["passed"] += 1
        results["helper_checks"]["total"] += 1
        if "repo-relative paths" in template_text:
            results["helper_checks"]["passed"] += 1
        else:
            results["errors"].append("Report template is missing repo-relative path guidance")
            results["passed"] = False

    create_report_script = skill_root / "scripts" / "create_report_packet.py"
    results["helper_checks"]["total"] += 1
    with tempfile.TemporaryDirectory() as tempdir:
        repo_dir = Path(tempdir) / "demo-repo"
        repo_dir.mkdir()
        save_root = Path(tempdir) / "out"
        save_root.mkdir()
        proc = subprocess.run(
            [
                sys.executable,
                str(create_report_script),
                "--repo",
                str(repo_dir),
                "--url",
                "https://example.com",
                "--save-root",
                str(save_root),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            results["errors"].append(f"create_report_packet.py failed: {proc.stderr.strip()}")
            results["passed"] = False
        else:
            payload = json.loads(proc.stdout)
            output_dir = Path(payload["output_dir"])
            expected_outputs = [
                output_dir / "agent-readiness-report.md",
                output_dir / "metadata.json",
                output_dir / "sources.md",
            ]
            missing = [str(path) for path in expected_outputs if not path.exists()]
            if missing:
                results["errors"].append(f"create_report_packet.py missed expected outputs: {', '.join(missing)}")
                results["passed"] = False
            else:
                results["helper_checks"]["passed"] += 1

    scan_script = skill_root / "scripts" / "scan_site.py"
    results["helper_checks"]["total"] += 1
    proc = subprocess.run(
        [sys.executable, str(scan_script), "--help"],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        results["helper_checks"]["passed"] += 1
    else:
        results["errors"].append("scan_site.py --help failed")
        results["passed"] = False

    return results


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        raise SystemExit(1)

    results = test_skill(sys.argv[1])
    print(f"Skill: {results['skill_name']}")
    print(f"Tests found: {results['tests_found']}")
    for tag, count in sorted(results["tags"].items()):
        print(f"  {tag}: {count}")
    print(f"Files verified: {results['files_verified']['passed']}/{results['files_verified']['total']}")
    print(f"Cross-references checked: {results['cross_references']['passed']}/{results['cross_references']['total']}")
    print(f"Assertion format: {results['assertions_valid']['passed']}/{results['assertions_valid']['total']} valid")
    print(f"Helper checks: {results['helper_checks']['passed']}/{results['helper_checks']['total']}")
    if results["errors"]:
        print("\nIssues:")
        for error in results["errors"]:
            print(f"  - {error}")
    print("\nPASS: all checks passed" if results["passed"] else "\nFAIL: one or more checks failed")
    raise SystemExit(0 if results["passed"] else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Run packaging checks and a behavioral probe for the zoom-out skill.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate


REQUIRED_TAGS = {"smoke", "edge", "negative", "disclosure"}


def check_evals(root: Path, results: dict[str, Any]) -> None:
    evals_path = root / "evals" / "evals.json"
    try:
        data = json.loads(evals_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        results["errors"].append(f"cannot read evals/evals.json: {exc}")
        results["passed"] = False
        return

    evals = data.get("evals", [])
    results["tests_found"] = len(evals)
    seen_tags: set[str] = set()

    for index, item in enumerate(evals):
        label = item.get("name", f"eval-{index}")
        for field in ["id", "name", "prompt", "expected_output"]:
            if field not in item:
                results["errors"].append(f"eval '{label}' missing required field: {field}")
                results["passed"] = False

        for tag in item.get("tags", []):
            seen_tags.add(tag)
            results["tags"][tag] = results["tags"].get(tag, 0) + 1

        for assertion in item.get("assertions", []):
            results["assertions_valid"]["total"] += 1
            if isinstance(assertion, dict) and assertion.get("text"):
                results["assertions_valid"]["passed"] += 1
            else:
                results["errors"].append(f"eval '{label}' has invalid assertion")
                results["passed"] = False

        for rel_path in item.get("files", []):
            results["files_verified"]["total"] += 1
            if (root / rel_path).exists():
                results["files_verified"]["passed"] += 1
            else:
                results["errors"].append(f"eval '{label}' references missing file: {rel_path}")
                results["passed"] = False

    for tag in sorted(REQUIRED_TAGS):
        if tag in seen_tags:
            results["tag_coverage"]["passed"] += 1
        else:
            results["errors"].append(f"missing eval coverage for tag: {tag}")
            results["passed"] = False
    results["tag_coverage"]["total"] = len(REQUIRED_TAGS)


def run_inventory_probe(root: Path, results: dict[str, Any]) -> None:
    script = root / "scripts" / "zoom_out_inventory.py"
    with tempfile.TemporaryDirectory(prefix="zoom-out-probe-") as tmp:
        repo = Path(tmp)
        (repo / "src" / "auth").mkdir(parents=True)
        (repo / "src" / "routes").mkdir(parents=True)
        (repo / "src" / "data").mkdir(parents=True)
        (repo / "package.json").write_text('{"name":"probe","type":"module"}\n', encoding="utf-8")
        (repo / "src" / "auth" / "session.ts").write_text(
            "import { saveSession } from '../data/session-store';\n"
            "export class SessionService {\n"
            "  createSession(userId: string) { return saveSession(userId); }\n"
            "}\n",
            encoding="utf-8",
        )
        (repo / "src" / "routes" / "login.ts").write_text(
            "import { SessionService } from '../auth/session';\n"
            "export function loginRoute(req) {\n"
            "  return new SessionService().createSession(req.user.id);\n"
            "}\n",
            encoding="utf-8",
        )
        (repo / "src" / "data" / "session-store.ts").write_text(
            "export function saveSession(userId: string) { return { userId }; }\n",
            encoding="utf-8",
        )

        help_run = subprocess.run(
            [sys.executable, str(script), "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        results["probe_checks"]["total"] += 1
        if help_run.returncode == 0 and "--target" in help_run.stdout:
            results["probe_checks"]["passed"] += 1
        else:
            results["errors"].append("inventory --help probe failed")
            results["passed"] = False

        probe_run = subprocess.run(
            [
                sys.executable,
                str(script),
                "--repo",
                str(repo),
                "--target",
                "SessionService",
                "--json",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        results["probe_checks"]["total"] += 1
        if probe_run.returncode != 0:
            results["errors"].append(f"inventory JSON probe failed: {probe_run.stderr.strip()}")
            results["passed"] = False
            return
        results["probe_checks"]["passed"] += 1

        try:
            data = json.loads(probe_run.stdout)
        except json.JSONDecodeError as exc:
            results["errors"].append(f"inventory JSON probe returned invalid JSON: {exc}")
            results["passed"] = False
            return

        center_paths = {item["path"] for item in data.get("center_candidates", [])}
        caller_paths = {item["path"] for item in data.get("caller_candidates", [])}
        import_sources = {item["from"] for item in data.get("import_edges", [])}

        checks = [
            ("center candidate found", "src/auth/session.ts" in center_paths),
            ("caller candidate found", "src/routes/login.ts" in caller_paths or "src/routes/login.ts" in center_paths),
            ("import edge found", bool(import_sources & {"src/auth/session.ts", "src/routes/login.ts"})),
            ("suggested reads found", bool(data.get("suggested_reads"))),
        ]
        for label, passed in checks:
            results["probe_checks"]["total"] += 1
            if passed:
                results["probe_checks"]["passed"] += 1
            else:
                results["errors"].append(f"inventory probe missing: {label}")
                results["passed"] = False


def run_tests(skill_path: str) -> dict[str, Any]:
    root = Path(skill_path).resolve()
    results: dict[str, Any] = {
        "skill_name": root.name,
        "tests_found": 0,
        "tags": {},
        "files_verified": {"passed": 0, "total": 0},
        "assertions_valid": {"passed": 0, "total": 0},
        "tag_coverage": {"passed": 0, "total": len(REQUIRED_TAGS)},
        "probe_checks": {"passed": 0, "total": 0},
        "errors": [],
        "warnings": [],
        "passed": True,
    }

    validation = validate.validate_skill(str(root))
    results["warnings"].extend(validation["warnings"])
    if not validation["valid"]:
        results["errors"].extend(validation["errors"])
        results["passed"] = False

    check_evals(root, results)
    run_inventory_probe(root, results)
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
        "Assertion format: "
        f"{results['assertions_valid']['passed']}/{results['assertions_valid']['total']} valid"
    )
    print(
        "Tag coverage: "
        f"{results['tag_coverage']['passed']}/{results['tag_coverage']['total']}"
    )
    print(
        "Probe checks: "
        f"{results['probe_checks']['passed']}/{results['probe_checks']['total']} passed"
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

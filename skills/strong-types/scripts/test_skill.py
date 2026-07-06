#!/usr/bin/env python3
"""Lightweight tests for the strong-types skill."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_TAGS = {
    "smoke",
    "edge",
    "negative",
    "disclosure",
    "php",
    "typescript",
    "python",
    "review",
}
EXPECTED_FINDINGS = {
    "fallback-chain",
    "escape-hatch-type",
    "untyped-signature",
    "suppressed-type-error",
    "php-missing-strict-types",
    "ts-nonstrict-config",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_fixture(root: Path) -> None:
    src = root / "src"
    src.mkdir()
    (src / "Location.php").write_text(
        """
<?php

class Location
{
    public function image($fallback)
    {
        return $this->preview ?? $this->banner ?? $this->thumbnail;
    }

    public function normalize(mixed $value)
    {
        return $value;
    }
}
""".lstrip(),
        encoding="utf-8",
    )
    (src / "api.ts").write_text(
        """
export async function fetchUser(id: string): Promise<any> {
  // @ts-ignore
  const res = await fetch(`/api/users/${id}`);
  return res.json() as any;
}
const label = user.nickname || user.fullName || user.email;
""".lstrip(),
        encoding="utf-8",
    )
    (src / "report.py").write_text(
        """
from typing import Any


def build(payload: Any):
    value = payload.get("a") or payload.get("b") or payload.get("c")
    return value  # type: ignore
""".lstrip(),
        encoding="utf-8",
    )
    (root / "tsconfig.json").write_text(
        """
{
  "compilerOptions": {
    "target": "es2020"
  }
}
""".lstrip(),
        encoding="utf-8",
    )


def write_clean_fixture(root: Path) -> None:
    src = root / "src"
    src.mkdir()
    (src / "Location.php").write_text(
        """
<?php

declare(strict_types=1);

final class Location
{
    public function primaryImage(): Image
    {
        return $this->preview ?? throw new MissingImageException();
    }
}
""".lstrip(),
        encoding="utf-8",
    )


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: python3 scripts/test_skill.py <skill-path>", file=sys.stderr)
        return 1

    root = Path(argv[0]).expanduser().resolve()
    errors: list[str] = []

    validate = subprocess.run(
        [sys.executable, str(root / "scripts" / "validate.py"), str(root)],
        text=True,
        capture_output=True,
        check=False,
    )
    if validate.returncode != 0:
        errors.append("validate.py failed")

    help_check = subprocess.run(
        [sys.executable, str(root / "scripts" / "analyze_type_strictness.py"), "--help"],
        text=True,
        capture_output=True,
        check=False,
    )
    if help_check.returncode != 0 or "type ambiguity review prompts" not in help_check.stdout:
        errors.append("analyze_type_strictness.py --help did not return expected help text")

    scan_kinds: set[str] = set()
    with tempfile.TemporaryDirectory() as temp_dir:
        fixture_root = Path(temp_dir)
        write_fixture(fixture_root)
        scan = subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "analyze_type_strictness.py"),
                str(fixture_root),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if scan.returncode != 0:
            errors.append("analyze_type_strictness.py failed on fixture")
        else:
            payload = json.loads(scan.stdout)
            scan_kinds = {item["kind"] for item in payload.get("findings", [])}
            for expected in EXPECTED_FINDINGS:
                if expected not in scan_kinds:
                    errors.append(f"scanner did not report expected finding: {expected}")

    with tempfile.TemporaryDirectory() as temp_dir:
        clean_root = Path(temp_dir)
        write_clean_fixture(clean_root)
        clean_scan = subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "analyze_type_strictness.py"),
                str(clean_root),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if clean_scan.returncode != 0:
            errors.append("analyze_type_strictness.py failed on clean fixture")
        else:
            clean_payload = json.loads(clean_scan.stdout)
            noisy = [item["kind"] for item in clean_payload.get("findings", [])]
            if noisy:
                errors.append(f"scanner reported false positives on clean fixture: {noisy}")

    evals_path = root / "evals" / "evals.json"
    if not evals_path.is_file():
        errors.append("evals/evals.json is missing")
        evals = []
    else:
        try:
            evals = load_json(evals_path).get("evals", [])
        except json.JSONDecodeError as exc:
            errors.append(f"evals/evals.json is invalid JSON: {exc}")
            evals = []

    tags = set()
    assertion_count = 0
    for item in evals:
        for field in ["id", "name", "prompt", "expected_output", "assertions"]:
            if field not in item:
                errors.append(f"eval missing field {field}: {item}")
        tags.update(item.get("tags", []))
        for assertion in item.get("assertions", []):
            assertion_count += 1
            if "text" not in assertion:
                errors.append(f"assertion missing text: {assertion}")
            if assertion.get("type") and assertion["type"] not in {
                "functional",
                "structural",
                "disclosure",
                "negative",
                "verification",
            }:
                errors.append(f"unknown assertion type: {assertion['type']}")

    missing_tags = REQUIRED_TAGS - tags
    if missing_tags:
        errors.append(f"missing eval tag coverage: {', '.join(sorted(missing_tags))}")
    if assertion_count == 0:
        errors.append("evals contain no assertions")

    template = root / "templates" / "type-review.md"
    if not template.is_file():
        errors.append("type review template is missing")

    print(f"Skill: {root.name}")
    print(f"Validation: {'PASS' if validate.returncode == 0 else 'FAIL'}")
    print(f"Scanner help: {'PASS' if help_check.returncode == 0 else 'FAIL'}")
    print(f"Scanner findings: {', '.join(sorted(scan_kinds))}")
    print(f"Evals: {len(evals)}")
    print(f"Tags: {', '.join(sorted(tags))}")
    print(f"Assertions: {assertion_count}")

    if errors:
        print("Issues:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

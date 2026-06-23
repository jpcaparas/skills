#!/usr/bin/env python3
"""Lightweight tests for the maintainable-code skill."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_TAGS = {"smoke", "edge", "negative", "disclosure", "comments", "markup"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_fixture(root: Path) -> Path:
    source = root / "src"
    source.mkdir()
    fixture = source / "utils.ts"
    fixture.write_text(
        """
export function process(data: any) {
  if (data) {
    if (data.user) {
      if (data.user.account) {
        if (data.user.account.flags) {
          if (data.user.account.flags.enabled) {
            if (data.user.account.flags.retry) {
              if (data.user.account.flags.retry.count) {
                if (data.user.account.flags.retry.count > 3) {
                  return "too-many";
                }
              }
            }
          }
        }
      }
    }
  }
  // TODO: explain ownership of this fallback
  return "ok";
}
""".lstrip(),
        encoding="utf-8",
    )
    workflow = root / ".github" / "workflows"
    workflow.mkdir(parents=True)
    (workflow / "artifacts.yml").write_text(
        """
name: artifacts
on: workflow_dispatch
jobs:
  download:
    runs-on: ubuntu-latest
    steps:
      - name: Download artifacts
        run: |
          artifacts="$(gh api "/repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/artifacts?per_page=100")"
          for prefix in "${prefixes[@]}"; do
            jq -r --arg prefix "$prefix" '.artifacts[] | select(.name | startswith($prefix)) | "\\(.id)\\t\\(.name)"' <<< "$artifacts"
          done | sort -u | while IFS=$'\\t' read -r artifact_id artifact_name; do
            if [ -z "$artifact_id" ]; then
              continue
            fi
            gh run download "$GITHUB_RUN_ID" --name "$artifact_name"
          done
""".lstrip(),
        encoding="utf-8",
    )
    return fixture


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
        [sys.executable, str(root / "scripts" / "analyze_maintainability.py"), "--help"],
        text=True,
        capture_output=True,
        check=False,
    )
    if help_check.returncode != 0 or "maintainability review prompts" not in help_check.stdout:
        errors.append("analyze_maintainability.py --help did not return expected help text")

    with tempfile.TemporaryDirectory() as temp_dir:
        fixture_root = Path(temp_dir)
        write_fixture(fixture_root)
        scan = subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "analyze_maintainability.py"),
                str(fixture_root),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if scan.returncode != 0:
            errors.append("analyze_maintainability.py failed on fixture")
        else:
            payload = json.loads(scan.stdout)
            kinds = {item["kind"] for item in payload.get("findings", [])}
            for expected in {
                "comment-debt",
                "vague-file-name",
                "vague-function-name",
                "todo",
                "deep-nesting",
                "weak-type-signal",
            }:
                if expected not in kinds:
                    errors.append(f"scanner did not report expected finding: {expected}")

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

    template = root / "templates" / "maintainability-review.md"
    if not template.is_file():
        errors.append("maintainability review template is missing")

    print(f"Skill: {root.name}")
    print(f"Validation: {'PASS' if validate.returncode == 0 else 'FAIL'}")
    print(f"Scanner help: {'PASS' if help_check.returncode == 0 else 'FAIL'}")
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

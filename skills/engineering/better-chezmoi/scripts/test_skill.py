#!/usr/bin/env python3
"""Run offline package checks and optional isolated chezmoi integration tests."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Sequence, cast


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import official_docs  # noqa: E402 - sibling import after direct-execution path bootstrap
import probe_chezmoi  # noqa: E402 - sibling import after direct-execution path bootstrap
import validate  # noqa: E402 - sibling import after direct-execution path bootstrap


def behavioral_checks(root: Path) -> dict[str, bool]:
    corpus = root / "references" / "official-docs"
    manifest = official_docs.validate_corpus(corpus)
    files = {document.slug: corpus / document.file for document in manifest.documents}
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    recovery = (root / "references" / "recovery-and-safety.md").read_text(
        encoding="utf-8"
    )
    docs_guide = (root / "references" / "official-documentation.md").read_text(
        encoding="utf-8"
    )
    return {
        "current_flag_is_searchable": "--error-on-conflict"
        in files["global-flags"].read_text(encoding="utf-8"),
        "dry_run_hook_caveat_is_scraped": "always run"
        in files["hooks"].read_text(encoding="utf-8"),
        "update_is_not_called_preview": "`update` is not a preview" in skill,
        "force_is_not_conflict_strategy": "Do not use `--force` as a conflict strategy"
        in recovery,
        "refresh_is_preview_first": "does not replace the snapshot" in docs_guide,
        "official_inventory_is_complete": len(manifest.documents)
        == len(official_docs.DOCUMENT_SOURCES),
    }


def run_tests(skill_path: str) -> dict[str, object]:
    root = Path(skill_path).resolve()
    package = validate.validate_skill(str(root))
    scraper = official_docs.run_self_tests()
    behavior = behavioral_checks(root)
    raw_errors = package["errors"]
    if not isinstance(raw_errors, list) or not all(
        isinstance(item, str) for item in raw_errors
    ):
        raise TypeError("Package validator errors must be a string array")
    errors = list(cast(list[str], raw_errors))
    if scraper.get("passed") is not True:
        errors.append("Official docs parser self-tests failed")
    failed_behavior = [name for name, passed in behavior.items() if not passed]
    if failed_behavior:
        errors.append("Behavior checks failed: " + ", ".join(failed_behavior))

    cli: dict[str, object]
    binary = shutil.which("chezmoi")
    if binary is None:
        cli = {
            "available": False,
            "skipped": True,
            "reason": "chezmoi is not installed",
        }
    else:
        try:
            contract = probe_chezmoi.inspect_contract(binary)
            integration = probe_chezmoi.exercise_isolated(binary)
            cli = {"available": True, "contract": contract, "integration": integration}
            if (
                contract.get("passed") is not True
                or integration.get("passed") is not True
            ):
                errors.append("Isolated chezmoi contract probe failed")
        except (OSError, probe_chezmoi.ProbeError) as exc:
            cli = {"available": True, "error": str(exc)}
            errors.append(f"Isolated chezmoi probe failed: {exc}")
    return {
        "skill_name": root.name,
        "passed": not errors,
        "package": package,
        "scraper": scraper,
        "behavior": behavior,
        "cli": cli,
        "errors": errors,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1
    result = run_tests(args[0])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

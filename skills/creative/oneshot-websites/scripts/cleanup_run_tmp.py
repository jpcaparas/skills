#!/usr/bin/env python3
"""Safely remove one finalized oneshot-websites run's exact .tmp directory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


FINALIZABLE_STATUSES = {"RUNNING", "OK"}


@dataclass(frozen=True)
class FinalizationContract:
    """One receipt-anchored run schema whose scratch can be safely finalized."""

    receipt_schema: str
    temporary: Mapping[str, str]


FINALIZATION_CONTRACTS: Mapping[str, FinalizationContract] = {
    "3.2": FinalizationContract(
        receipt_schema="2.2",
        temporary={
            "path": ".tmp/",
            "routing": "best-effort-run-local",
            "preservation": "retain",
        },
    ),
    "3.3": FinalizationContract(
        receipt_schema="2.3",
        temporary={
            "path": ".tmp/",
            "routing": "best-effort-run-local",
            "lifecycle": "retain-until-successful-finalization",
        },
    ),
    "3.4": FinalizationContract(
        receipt_schema="2.4",
        temporary={
            "path": ".tmp/",
            "routing": "best-effort-run-local",
            "lifecycle": "retain-until-successful-finalization",
        },
    ),
}


class TemporaryCleanupError(ValueError):
    """Raised when cleanup cannot prove its target and completion preconditions."""


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the exact run target and explicit destructive-action confirmation."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path, help="Current flat run directory")
    parser.add_argument(
        "--confirm-finalized",
        action="store_true",
        help="Confirm all descendants and processes stopped and durable evidence no longer depends on .tmp/",
    )
    return parser.parse_args(argv)


def exact_child(parent: Path, name: str) -> Path | None:
    """Return a direct child only when its stored casing is exact."""

    try:
        return next((entry for entry in parent.iterdir() if entry.name == name), None)
    except OSError as error:
        raise TemporaryCleanupError(f"unable to inspect run directory: {parent}: {error}") from error


def read_json_object(path: Path, label: str) -> Mapping[str, object]:
    """Read a small regular JSON object without following a symbolic link."""

    try:
        metadata = path.lstat()
    except OSError as error:
        raise TemporaryCleanupError(f"{label} is unreadable: {path}: {error}") from error
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 1024 * 1024:
        raise TemporaryCleanupError(f"{label} must be a regular file no larger than 1 MiB: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TemporaryCleanupError(f"{label} is invalid UTF-8 JSON: {path}: {error}") from error
    if not isinstance(value, dict):
        raise TemporaryCleanupError(f"{label} must contain a JSON object: {path}")
    return value


def require_ordinary_directory(path: Path, label: str) -> Path:
    """Resolve an ordinary directory while rejecting a symlink at the named boundary."""

    try:
        metadata = path.lstat()
    except OSError as error:
        raise TemporaryCleanupError(f"{label} is unreadable: {path}: {error}") from error
    if not stat.S_ISDIR(metadata.st_mode):
        raise TemporaryCleanupError(f"{label} must be an ordinary non-symlink directory: {path}")
    try:
        return path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise TemporaryCleanupError(f"{label} cannot be resolved safely: {path}: {error}") from error


def has_passed_verification(report: Mapping[str, object]) -> bool:
    """Return whether the worker report contains at least one structured passing check."""

    verification = report.get("verification")
    if not isinstance(verification, list):
        return False
    return any(
        isinstance(item, dict)
        and item.get("result") == "passed"
        and isinstance(item.get("kind"), str)
        and bool(str(item["kind"]).strip())
        and isinstance(item.get("evidence"), str)
        and bool(str(item["evidence"]).strip())
        for item in verification
    )


def validate_cleanup_target(run_path: Path) -> tuple[Path, Path | None]:
    """Prove current-run identity and return the exact safe temporary target."""

    run_resolved = require_ordinary_directory(run_path, "run directory")
    run_manifest_path = exact_child(run_path, "run.json")
    report_path = exact_child(run_path, "worker-report.json")
    if run_manifest_path is None or report_path is None:
        raise TemporaryCleanupError("run must contain exact-case run.json and worker-report.json")
    run = read_json_object(run_manifest_path, "run manifest")
    report = read_json_object(report_path, "worker report")

    run_id = run_path.name
    run_schema = run.get("schemaVersion")
    contract = FINALIZATION_CONTRACTS.get(run_schema) if isinstance(run_schema, str) else None
    if contract is None or run.get("runId") != run_id:
        raise TemporaryCleanupError(
            "cleanup requires supported run schema {} whose runId matches {!r}".format(
                ", ".join(sorted(FINALIZATION_CONTRACTS)),
                run_id,
            )
        )
    if run.get("temporary") != contract.temporary:
        raise TemporaryCleanupError("run temporary-storage contract does not authorize completion cleanup")
    run_status = run.get("status")
    report_status = report.get("status")
    if run_status != report_status or run_status not in FINALIZABLE_STATUSES:
        raise TemporaryCleanupError(
            "run.json and worker-report.json must share RUNNING or OK status before final cleanup"
        )
    report_artifact = report.get("artifact")
    if not isinstance(report_artifact, dict) or report_artifact.get("staticDeploymentVerified") is not True:
        raise TemporaryCleanupError("worker report must record successful local static-handoff verification")
    if not has_passed_verification(report):
        raise TemporaryCleanupError("worker report must contain structured passed verification evidence")

    root = run_path.parent
    provenance_directory = exact_child(root, ".oneshot-provenance")
    if provenance_directory is None:
        raise TemporaryCleanupError("run is missing its coordinator provenance directory")
    provenance_resolved = require_ordinary_directory(provenance_directory, "provenance directory")
    try:
        provenance_resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise TemporaryCleanupError("provenance directory must stay inside the output root") from error
    receipt_path = exact_child(provenance_directory, f"{run_id}.json")
    commit_path = exact_child(provenance_directory, f"{run_id}.commit")
    if receipt_path is None or commit_path is None:
        raise TemporaryCleanupError("run is missing its coordinator receipt or commit marker")
    receipt = read_json_object(receipt_path, "provenance receipt")
    expected_run_path = run_path.relative_to(root).as_posix()
    if (
        receipt.get("schemaVersion") != contract.receipt_schema
        or receipt.get("runId") != run_id
        or receipt.get("runPath") != expected_run_path
        or receipt.get("runSchemaVersion") != run_schema
        or receipt.get("temporary") != contract.temporary
    ):
        raise TemporaryCleanupError("coordinator receipt does not match the current run and cleanup contract")
    try:
        commit_metadata = commit_path.lstat()
    except OSError as error:
        raise TemporaryCleanupError(f"provenance commit marker is unreadable: {error}") from error
    if not stat.S_ISREG(commit_metadata.st_mode) or commit_metadata.st_size != 0:
        raise TemporaryCleanupError("provenance commit marker must be an empty regular file")

    try:
        casefold_matches = [entry for entry in run_path.iterdir() if entry.name.casefold() == ".tmp"]
    except OSError as error:
        raise TemporaryCleanupError(f"unable to inspect run-local temporary paths: {error}") from error
    if len(casefold_matches) > 1 or (casefold_matches and casefold_matches[0].name != ".tmp"):
        raise TemporaryCleanupError("run contains an ambiguous or wrong-case temporary path")
    temporary_path = exact_child(run_path, ".tmp")
    if temporary_path is None:
        return run_resolved, None
    temporary_resolved = require_ordinary_directory(temporary_path, "run-local .tmp directory")
    if temporary_resolved.parent != run_resolved:
        raise TemporaryCleanupError("run-local .tmp directory must resolve as an exact child of the run")
    return run_resolved, temporary_path


def cleanup_run_temporary(run_path: Path, confirmed_finalized: bool) -> str:
    """Delete the exact run-local temporary directory after explicit finalization confirmation."""

    if not confirmed_finalized:
        raise TemporaryCleanupError("refusing cleanup without --confirm-finalized")
    _, temporary_path = validate_cleanup_target(run_path)
    if temporary_path is None:
        return "already-absent"
    try:
        shutil.rmtree(temporary_path)
    except OSError as error:
        raise TemporaryCleanupError(f"unable to delete run-local .tmp directory: {error}") from error
    if os.path.lexists(temporary_path):
        raise TemporaryCleanupError("run-local .tmp directory still exists after recursive cleanup")
    return "deleted"


def main(argv: Sequence[str] | None = None) -> int:
    """Run one safely scoped cleanup and print its machine-readable result."""

    arguments = parse_arguments(argv)
    try:
        result = cleanup_run_temporary(arguments.run, arguments.confirm_finalized)
    except TemporaryCleanupError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"status": result, "runPath": str(arguments.run), "temporaryPath": ".tmp/"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

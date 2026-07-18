#!/usr/bin/env python3
"""Reserve a collision-free namespace for one isolated oneshot-websites run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from runtime_contract import (
    BoundedReadError,
    identity_key,
    parse_json_bounded,
    read_regular_file_bounded,
    resolve_existing_or_new,
)


CLASSIFICATIONS = ("autonomous-one-shot", "rerun", "curated-attempt")
IDENTITY_MARKER = ".oneshot-identity.json"
METADATA_MAX_BYTES = 1024 * 1024
PROMPT_MAX_BYTES = 5 * 1024 * 1024


class RunPreparationError(ValueError):
    """Raised when a run cannot be safely reserved."""


@dataclass(frozen=True)
class Identity:
    """Raw name and collision-resistant filesystem key for one identity level."""

    name: str
    key: str


@dataclass(frozen=True)
class RunPaths:
    """All paths reserved for one run, relative to the validated output root."""

    root: Path
    run: Path
    workspace: Path
    artifact: Path


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse the fixed run-identity contract and optional provenance fields."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path, help="Root directory that will contain all runs")
    parser.add_argument("--model", required=True, help="Raw model name")
    parser.add_argument("--harness", required=True, help="Raw harness name")
    parser.add_argument("--experiment", required=True, help="Raw experiment name")
    parser.add_argument("--prompt-file", required=True, type=Path, help="UTF-8 prompt file to preserve verbatim")
    parser.add_argument(
        "--classification",
        choices=CLASSIFICATIONS,
        default="autonomous-one-shot",
        help="Whether this is the original autonomous run, a rerun, or a curated attempt",
    )
    parser.add_argument(
        "--prior-run",
        type=Path,
        help="Existing prior run directory under --output-root, used for reruns and curated attempts",
    )
    return parser.parse_args(argv)


def build_identity(name: str, label: str) -> Identity:
    """Create a readable key whose digest remains tied to exact UTF-8 input bytes."""

    if not name.strip():
        raise RunPreparationError(f"{label} must not be empty")
    try:
        key = identity_key(name)
    except UnicodeEncodeError as error:
        raise RunPreparationError(f"{label} must be valid UTF-8 text") from error
    return Identity(name=name, key=key)


def read_prompt(path: Path) -> bytes:
    """Read prompt bytes only after proving that their UTF-8 contract holds."""

    try:
        prompt = read_regular_file_bounded(path, PROMPT_MAX_BYTES)
    except BoundedReadError as error:
        detail = str(error)
        if "regular non-symlink" in detail or "not a regular file" in detail:
            raise RunPreparationError(f"prompt file must be a regular file: {path}") from error
        if "exceeds" in detail:
            raise RunPreparationError(f"prompt file exceeds the 5 MiB artifact limit: {path}") from error
        raise RunPreparationError(f"prompt file is not readable: {path}: {error}") from error
    try:
        decoded = prompt.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RunPreparationError(f"prompt file is not valid UTF-8: {path}") from error
    if not decoded.strip():
        raise RunPreparationError("prompt file must contain a non-blank actual prompt")
    return prompt


def resolved_root(path: Path) -> Path:
    """Resolve the caller-selected root before accepting any derived path beneath it."""

    try:
        root = resolve_existing_or_new(path)
    except (OSError, RuntimeError) as error:
        raise RunPreparationError(f"unable to resolve output root: {path}: {error}") from error
    if root.exists() and not root.is_dir():
        raise RunPreparationError(f"output root is not a directory: {root}")
    return root


def exact_child(parent: Path, name: str) -> Optional[Path]:
    """Return a direct child only when its stored casing is exact."""

    try:
        return next((entry for entry in parent.iterdir() if entry.name == name), None)
    except OSError:
        return None


def read_json_object_bounded(path: Path, label: str) -> dict[str, Any]:
    """Read a small regular JSON object without following special files."""

    try:
        raw = read_regular_file_bounded(path, METADATA_MAX_BYTES)
        decoded = raw.decode("utf-8")
        value = parse_json_bounded(decoded)
    except (BoundedReadError, UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        raise RunPreparationError(f"{label} is unreadable: {path}: {error}") from error
    if not isinstance(value, dict):
        raise RunPreparationError(f"{label} must contain a JSON object: {path}")
    return value


def prepare_provenance_directory(root: Path) -> Path:
    """Create the coordinator inventory without following a pre-positioned link."""

    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise RunPreparationError(f"unable to create output root: {error}") from error
    directory = root / ".oneshot-provenance"
    try:
        directory.mkdir(exist_ok=True)
    except OSError as error:
        raise RunPreparationError(f"unable to create provenance directory: {error}") from error
    directory = exact_child(root, ".oneshot-provenance")
    if directory is None:
        raise RunPreparationError("provenance directory name must use exact casing")
    if directory.is_symlink():
        raise RunPreparationError("provenance directory must not be a symbolic link")
    if not directory.is_dir():
        raise RunPreparationError("provenance path must be a directory")
    try:
        mode = directory.stat().st_mode
    except OSError as error:
        raise RunPreparationError(f"unable to inspect provenance directory: {error}") from error
    if mode & 0o222 == 0:
        raise RunPreparationError("provenance directory must have a writable file mode")
    try:
        directory.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise RunPreparationError("provenance directory must stay inside the output root") from error
    return directory


def require_within_root(path: Path, root: Path, label: str) -> Path:
    """Resolve a path and reject any value that could target data outside the run root."""

    try:
        resolved = resolve_existing_or_new(path)
    except (OSError, RuntimeError) as error:
        raise RunPreparationError(f"unable to resolve {label}: {path}: {error}") from error
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise RunPreparationError(f"{label} must stay within output root: {root}") from error
    return resolved


def prior_run_path(value: Optional[Path], root: Path) -> Optional[str]:
    """Validate and store optional prior-run provenance as a portable relative path."""

    if value is None:
        return None
    candidate = value.expanduser() if value.is_absolute() else root / value
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        # A caller may spell an already-resolved macOS root through a system alias
        # such as /var -> /private/var. Find that root prefix without resolving
        # worker-controlled components below it, so interior symlinks remain visible.
        relative = None
        for prefix in candidate.parents:
            try:
                if prefix.resolve(strict=True) == root:
                    relative = candidate.relative_to(prefix)
                    break
            except OSError:
                continue
        if relative is None:
            try:
                candidate.resolve(strict=True).relative_to(root)
            except (OSError, ValueError) as error:
                raise RunPreparationError(f"prior run must stay within output root: {root}") from error
            raise RunPreparationError("prior run could not be mapped to exact output-root path components")
    if len(relative.parts) != 4 or any(part in {"", ".", ".."} for part in relative.parts):
        raise RunPreparationError("prior run must use exact model/harness/experiment/run path components")
    prior = root
    for part in relative.parts:
        stored_part = exact_child(prior, part)
        if stored_part is None:
            raise RunPreparationError(f"prior run path must use exact casing: {candidate}")
        if stored_part.is_symlink():
            raise RunPreparationError(f"prior run path must not use symbolic links: {candidate}")
        prior = stored_part
    if not prior.is_dir():
        raise RunPreparationError(f"prior run is not an existing directory: {prior}")
    require_within_root(prior, root, "prior run")
    run_manifest = exact_child(prior, "run.json")
    if run_manifest is None or not run_manifest.is_file() or run_manifest.is_symlink():
        raise RunPreparationError("prior run must be a model/harness/experiment/run directory containing run.json")

    # A run is dispatch-ready only after its coordinator-owned receipt and
    # final empty commit marker exist outside the worker-writable directory.
    # Refusing pre-commit residue prevents reruns from linking to an attempt
    # that a crashed preparation process never made canonical.
    provenance_directory = exact_child(root, ".oneshot-provenance")
    if (
        provenance_directory is None
        or provenance_directory.is_symlink()
        or not provenance_directory.is_dir()
    ):
        raise RunPreparationError("prior run is missing its coordinator provenance directory")

    run_id = prior.name
    prior_relative = prior.relative_to(root).as_posix()
    receipt_path = exact_child(provenance_directory, f"{run_id}.json")
    if receipt_path is None:
        raise RunPreparationError("prior run is missing its coordinator provenance receipt")
    receipt = read_json_object_bounded(receipt_path, "prior run coordinator provenance receipt")
    if (
        receipt.get("schemaVersion") != "1.0"
        or receipt.get("runId") != run_id
        or receipt.get("runPath") != prior_relative
    ):
        raise RunPreparationError("prior run coordinator provenance receipt does not match the prior run")

    commit_path = exact_child(provenance_directory, f"{run_id}.commit")
    if commit_path is None:
        raise RunPreparationError("prior run is missing its provenance commit marker")
    try:
        commit_metadata = commit_path.lstat()
    except OSError as error:
        raise RunPreparationError(f"prior run provenance commit marker is unreadable: {error}") from error
    if not stat.S_ISREG(commit_metadata.st_mode):
        raise RunPreparationError("prior run provenance commit marker must be a regular non-symlink file")
    if commit_metadata.st_size != 0:
        raise RunPreparationError("prior run provenance commit marker must be empty")

    return prior_relative


def validate_run_relationship(classification: str, prior_run: Optional[str]) -> None:
    """Keep original attempts and later attempts distinguishable in provenance."""

    if classification == "autonomous-one-shot" and prior_run is not None:
        raise RunPreparationError("autonomous-one-shot runs must not declare a prior run")
    if classification in {"rerun", "curated-attempt"} and prior_run is None:
        raise RunPreparationError(f"{classification} runs must declare --prior-run")


def make_run_id() -> str:
    """Return a UTC timestamp plus random UUID so independent attempts never share a name."""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4()}"


def reserve_paths(root: Path, model: Identity, harness: Identity, experiment: Identity, run_id: str) -> RunPaths:
    """Atomically reserve the final run directory without reusing an existing path."""

    parent = root
    try:
        for identity in (model, harness, experiment):
            candidate = parent / identity.key
            stored_candidate = exact_child(parent, identity.key)
            if stored_candidate is None:
                try:
                    case_collision = next(
                        (
                            entry
                            for entry in parent.iterdir()
                            if entry.name.casefold() == identity.key.casefold()
                        ),
                        None,
                    )
                except OSError as error:
                    raise RunPreparationError(f"unable to inspect namespace parent: {parent}: {error}") from error
                if case_collision is not None:
                    if case_collision.name != identity.key:
                        raise RunPreparationError(f"namespace directory name must use exact casing: {candidate}")
                    stored_candidate = case_collision

                if stored_candidate is None:
                    temporary_namespace = Path(
                        tempfile.mkdtemp(prefix=".oneshot-namespace-", suffix=".tmp", dir=parent)
                    )
                    publication_error: Optional[OSError] = None
                    try:
                        write_json(
                            temporary_namespace / IDENTITY_MARKER,
                            {"schemaVersion": "1.0", "name": identity.name, "key": identity.key},
                        )
                        try:
                            temporary_namespace.rename(candidate)
                        except OSError as error:
                            publication_error = error
                    finally:
                        if temporary_namespace.exists():
                            try:
                                shutil.rmtree(temporary_namespace)
                            except OSError:
                                pass
                    stored_candidate = exact_child(parent, identity.key)
                    if stored_candidate is None:
                        if publication_error is not None:
                            raise RunPreparationError(
                                f"unable to publish namespace directory: {candidate}: {publication_error}"
                            ) from publication_error
                        raise RunPreparationError(f"namespace directory name must use exact casing: {candidate}")
            parent = stored_candidate
            if parent.is_symlink():
                raise RunPreparationError(f"namespace directory must not be a symbolic link: {parent}")
            if not parent.is_dir():
                raise RunPreparationError(f"namespace path must be a directory: {parent}")
            require_within_root(parent, root, "namespace directory")

            expected_marker = {"schemaVersion": "1.0", "name": identity.name, "key": identity.key}
            marker_path = exact_child(parent, IDENTITY_MARKER)
            if marker_path is None:
                raise RunPreparationError(f"namespace directory is missing {IDENTITY_MARKER}: {parent}")
            marker = read_json_object_bounded(marker_path, "namespace identity marker")
            if marker != expected_marker:
                raise RunPreparationError(
                    f"namespace identity collision or marker mismatch for {identity.name!r}: {parent}"
                )

        run = parent / run_id
        require_within_root(run, root, "derived run path")
        try:
            run.mkdir(exist_ok=False)
        except FileExistsError as error:
            raise RunPreparationError(f"run path already exists and will not be overwritten: {run}") from error
    except (OSError, RunPreparationError) as error:
        if isinstance(error, RunPreparationError):
            raise
        raise RunPreparationError(f"unable to reserve namespace: {error}") from error
    return RunPaths(
        root=root,
        run=run,
        workspace=run / "workspace",
        artifact=run / "artifact",
    )


def rollback_reserved_run(
    paths: RunPaths,
    owned_provenance_paths: set[Path],
) -> None:
    """Remove an uncommitted run and its receipt without touching prior runs."""

    for owned_path in owned_provenance_paths:
        try:
            if owned_path.exists() and not owned_path.is_symlink():
                owned_path.unlink()
        except OSError:
            pass
    try:
        if paths.run.exists() and not paths.run.is_symlink():
            shutil.rmtree(paths.run)
    except OSError:
        pass


def write_json(
    path: Path,
    value: dict[str, Any],
    owned_paths: Optional[set[Path]] = None,
) -> None:
    """Create metadata once, refusing to replace even an unexpected competing file."""

    with path.open("x", encoding="utf-8") as handle:
        if owned_paths is not None:
            owned_paths.add(path)
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_commit_marker(path: Path, owned_paths: set[Path]) -> None:
    """Atomically mark that all pre-dispatch run and receipt files exist."""

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags, 0o644)
    owned_paths.add(path)
    try:
        try:
            os.fsync(descriptor)
        except OSError:
            pass
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass


def run_document(
    model: Identity,
    harness: Identity,
    experiment: Identity,
    run_id: str,
    classification: str,
    prompt_digest: str,
    prior_run: Optional[str],
    receipt_path: str,
) -> dict[str, Any]:
    """Build the durable run metadata, following templates/run.json's contract."""

    document: dict[str, Any] = {
        "schemaVersion": "2.0",
        "identity": {
            "model": {"name": model.name, "key": model.key},
            "harness": {"name": harness.name, "key": harness.key},
            "experiment": {"name": experiment.name, "key": experiment.key},
        },
        "runId": run_id,
        "classification": classification,
        "status": "PLANNED",
        "prompt": {"path": "artifact/PROMPT.md", "sha256": prompt_digest, "preservation": "verbatim"},
        "workspace": {"path": "workspace/"},
        "artifact": {"path": "artifact/", "entrypoint": "artifact/index.html", "deployment": "static-folder"},
        "execution": {
            "leadWorkerId": None,
            "descendantWorkerIds": [],
            "recursiveDelegation": "allowed",
            "skillImposedLimits": "none",
        },
        "priorRun": prior_run,
        "provenanceReceipt": receipt_path,
    }
    return document


def provenance_receipt(
    paths: RunPaths,
    model: Identity,
    harness: Identity,
    experiment: Identity,
    run_id: str,
    classification: str,
    prompt_digest: str,
    prompt_bytes: int,
    prior_run: Optional[str],
) -> dict[str, Any]:
    """Anchor pre-dispatch identity and prompt evidence outside the worker-owned run."""

    return {
        "schemaVersion": "1.0",
        "runId": run_id,
        "runPath": paths.run.relative_to(paths.root).as_posix(),
        "identity": {
            "model": {"name": model.name, "key": model.key},
            "harness": {"name": harness.name, "key": harness.key},
            "experiment": {"name": experiment.name, "key": experiment.key},
        },
        "classification": classification,
        "priorRun": prior_run,
        "prompt": {"sha256": prompt_digest, "bytes": prompt_bytes},
    }


def initial_worker_report(run_id: str) -> dict[str, Any]:
    """Reserve an honest, editable report without inventing worker telemetry."""

    return {
        "schemaVersion": "2.0",
        "runId": run_id,
        "status": "PLANNED",
        "summary": None,
        "blocker": None,
        "leadWorkerId": None,
        "descendantWorkerIds": [],
        "workspace": "workspace/",
        "artifact": {"entrypoint": "artifact/index.html", "staticDeploymentVerified": False},
        "technologies": [],
        "dependencies": [],
        "build": {"command": None},
        "verification": [],
        "observations": {"startedAt": None, "completedAt": None, "usage": None, "duration": None, "cost": None},
    }


def create_run(arguments: argparse.Namespace) -> Path:
    """Validate all inputs, reserve the namespace, and initialize run records."""

    root = resolved_root(arguments.output_root)
    prompt = read_prompt(arguments.prompt_file)
    model = build_identity(arguments.model, "model")
    harness = build_identity(arguments.harness, "harness")
    experiment = build_identity(arguments.experiment, "experiment")
    prior_run = prior_run_path(arguments.prior_run, root)
    validate_run_relationship(arguments.classification, prior_run)
    receipt_directory = prepare_provenance_directory(root)
    run_id = make_run_id()
    paths = reserve_paths(root, model, harness, experiment, run_id)
    prompt_digest = hashlib.sha256(prompt).hexdigest()
    receipt_relative = Path(".oneshot-provenance") / f"{run_id}.json"
    receipt_path = receipt_directory / f"{run_id}.json"
    commit_path = receipt_directory / f"{run_id}.commit"
    owned_provenance_paths: set[Path] = set()

    try:
        paths.workspace.mkdir()
        paths.artifact.mkdir()
        with (paths.artifact / "PROMPT.md").open("xb") as prompt_destination:
            prompt_destination.write(prompt)
        write_json(
            paths.run / "run.json",
            run_document(
                model,
                harness,
                experiment,
                run_id,
                arguments.classification,
                prompt_digest,
                prior_run,
                receipt_relative.as_posix(),
            ),
        )
        write_json(paths.run / "worker-report.json", initial_worker_report(run_id))
        write_json(
            receipt_path,
            provenance_receipt(
                paths,
                model,
                harness,
                experiment,
                run_id,
                arguments.classification,
                prompt_digest,
                len(prompt),
                prior_run,
            ),
            owned_provenance_paths,
        )
        write_commit_marker(commit_path, owned_provenance_paths)
    except OSError as error:
        rollback_reserved_run(paths, owned_provenance_paths)
        raise RunPreparationError(f"unable to initialize reserved run: {error}") from error
    return paths.run


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Create a run and emit only its absolute path as JSON on standard output."""

    arguments = parse_arguments(argv)
    try:
        run = create_run(arguments)
    except RunPreparationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"runDirectory": str(run.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

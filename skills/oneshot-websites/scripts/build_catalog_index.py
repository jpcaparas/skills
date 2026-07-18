#!/usr/bin/env python3
"""Build a static provenance index for one-shot website experiment runs."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import stat
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional, Tuple

from runtime_contract import (
    BoundedReadError,
    is_abandoned_run_reservation,
    is_appledouble_sidecar,
    parse_json_bounded,
    read_regular_file_bounded,
    resolve_existing_or_new,
)


TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "catalog-index.html"
PLACEHOLDER_RE = re.compile(r"\{\{(?:CATALOG_TITLE|CATALOG_DESCRIPTION|META_CHIPS|FAIRNESS_NOTE|ROWS|FOOTER_NOTE)\}\}")
STALE_INDEX_RE = re.compile(r"^\.oneshot-index-.+\.tmp$")
NAMESPACE_TEMP_RE = re.compile(r"^\.oneshot-namespace-.+\.tmp$")
RUN_ID_RE = re.compile(
    r"^\d{8}T\d{6}Z-[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
IDENTITY_MARKER = ".oneshot-identity.json"
CATALOGUE_LOCK = ".oneshot-catalogue.lock"
METADATA_MAX_BYTES = 1024 * 1024
ROOT_INDEX_MAX_BYTES = 5 * 1024 * 1024
IDENTITY_DISPLAY_CHARS = 512
OUTCOME_DISPLAY_CHARS = 1_024


class CatalogueBuildError(ValueError):
    """Raised when the output root cannot be inventoried without ambiguity."""


@dataclass(frozen=True)
class RunCandidate:
    """One run row, including worker-owned damage that must not hide siblings."""

    run_path: Path
    discovery_error: Optional[str] = None


def esc(value: object) -> str:
    """Escape a value for HTML text or attributes."""
    raw = str(value if value is not None else "")
    safe = raw.encode("utf-8", errors="replace").decode("utf-8")
    return html.escape(safe, quote=True)


def object_value(value: object) -> dict[str, Any]:
    """Return a JSON object value, treating other JSON values as absent."""
    return value if isinstance(value, dict) else {}


def text_value(value: object, fallback: str = "") -> str:
    """Return a non-empty JSON string or a display fallback."""
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def bounded_text(value: object, fallback: str = "", max_chars: int = 512) -> str:
    """Keep worker-controlled provenance useful without amplifying the root index."""

    rendered = text_value(value, fallback)
    if len(rendered) <= max_chars:
        return rendered
    omitted = len(rendered) - max_chars
    return f"{rendered[:max_chars]}… (+{omitted} chars)"


def load_object(path: Path) -> Tuple[dict[str, Any], Optional[str]]:
    """Load one JSON object without hiding a malformed run from the catalogue."""
    try:
        raw = read_regular_file_bounded(path, METADATA_MAX_BYTES)
        decoded = raw.decode("utf-8")
        value = parse_json_bounded(decoded)
    except BoundedReadError as error:
        detail = str(error)
        if "exceeds" in detail:
            return {}, "metadata exceeds the 1 MiB read limit"
        if "regular" in detail:
            return {}, "metadata is not a regular file"
        return {}, "metadata is unreadable"
    except UnicodeDecodeError:
        return {}, "metadata is not valid UTF-8"
    except (json.JSONDecodeError, RecursionError, ValueError):
        return {}, "metadata is not valid JSON"
    if not isinstance(value, dict):
        return {}, "top-level JSON value must be an object"
    return value, None


def discover_runs(root: Path) -> list[RunCandidate]:
    """Find exact-depth manifests without following or silently skipping namespaces."""

    candidates: list[RunCandidate] = []

    def entries(directory: Path) -> list[os.DirEntry[str]]:
        try:
            with os.scandir(directory) as iterator:
                return sorted(iterator, key=lambda entry: entry.name)
        except OSError as error:
            raise CatalogueBuildError(f"unable to inspect namespace directory: {directory.name or '.'}") from error

    def walk(directory: Path, depth: int) -> None:
        for entry in entries(directory):
            path = Path(entry.path)
            if is_appledouble_sidecar(path):
                continue
            if depth == 0 and entry.name == CATALOGUE_LOCK:
                try:
                    if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                        raise CatalogueBuildError("catalogue lock path is not a regular file")
                except OSError as error:
                    raise CatalogueBuildError("unable to inspect catalogue lock path") from error
                continue
            if depth == 0 and entry.name in {"index.html", ".oneshot-provenance"}:
                continue
            if depth == 0 and STALE_INDEX_RE.fullmatch(entry.name):
                try:
                    if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                        raise CatalogueBuildError(
                            f"reserved catalogue temporary path is not a regular file: {entry.name}"
                        )
                except OSError as error:
                    raise CatalogueBuildError(
                        f"unable to inspect reserved catalogue temporary file: {entry.name}"
                    ) from error
                continue
            if depth in {0, 1, 2} and NAMESPACE_TEMP_RE.fullmatch(entry.name):
                try:
                    if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                        raise CatalogueBuildError(
                            f"reserved namespace temporary path is not a directory: {entry.name}"
                        )
                except OSError as error:
                    raise CatalogueBuildError(
                        f"unable to inspect reserved namespace temporary path: {entry.name}"
                    ) from error
                temporary_entries = [
                    candidate
                    for candidate in entries(path)
                    if not is_appledouble_sidecar(Path(candidate.path))
                ]
                if any(candidate.name != IDENTITY_MARKER for candidate in temporary_entries):
                    raise CatalogueBuildError(
                        f"reserved namespace temporary directory contains unexpected state: {entry.name}"
                    )
                for candidate in temporary_entries:
                    try:
                        if candidate.is_symlink() or not candidate.is_file(follow_symlinks=False):
                            raise CatalogueBuildError(
                                f"reserved namespace temporary marker is not a regular file: {entry.name}"
                            )
                    except OSError as error:
                        raise CatalogueBuildError(
                            f"unable to inspect reserved namespace temporary marker: {entry.name}"
                        ) from error
                continue
            if depth in {1, 2, 3} and entry.name == IDENTITY_MARKER:
                continue
            if depth == 3 and RUN_ID_RE.fullmatch(entry.name):
                run_path = path / "run.json"
                try:
                    if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                        candidates.append(RunCandidate(run_path, "run namespace is not an ordinary directory"))
                        continue
                    mode = entry.stat(follow_symlinks=False).st_mode
                except OSError:
                    candidates.append(RunCandidate(run_path, "run namespace metadata is unreadable"))
                    continue
                if not any(mode & mask == mask for mask in (0o500, 0o050, 0o005)):
                    candidates.append(RunCandidate(run_path, "run namespace is not readable and traversable"))
                    continue
                commit_path = root / ".oneshot-provenance" / f"{entry.name}.commit"
                if is_abandoned_run_reservation(path, commit_path):
                    continue
                manifest_path: Optional[Path] = None
                manifest_error: Optional[str] = None
                try:
                    with os.scandir(path) as iterator:
                        for candidate in iterator:
                            if candidate.name != "run.json":
                                continue
                            try:
                                if candidate.is_symlink() or not candidate.is_file(follow_symlinks=False):
                                    manifest_error = "run.json is not a regular file"
                                else:
                                    manifest_path = Path(candidate.path)
                            except OSError:
                                manifest_error = "run.json metadata is unreadable"
                            break
                except OSError:
                    candidates.append(RunCandidate(run_path, "run namespace contents are unreadable"))
                    continue
                if manifest_error is not None:
                    candidates.append(RunCandidate(run_path, manifest_error))
                    continue
                if manifest_path is None:
                    candidates.append(RunCandidate(run_path, "run directory is missing exact-case run.json"))
                    continue
                candidates.append(RunCandidate(manifest_path))
                continue
            try:
                if entry.is_symlink():
                    raise CatalogueBuildError(f"namespace must not contain symbolic links: {entry.name}")
                is_directory = entry.is_dir(follow_symlinks=False)
                mode = entry.stat(follow_symlinks=False).st_mode if is_directory else 0
            except OSError as error:
                raise CatalogueBuildError(f"unable to inspect namespace entry: {entry.name}") from error
            if not is_directory:
                raise CatalogueBuildError(f"unexpected file outside a run: {entry.name}")
            if not any(mode & mask == mask for mask in (0o500, 0o050, 0o005)):
                raise CatalogueBuildError(f"namespace directory is not readable and traversable: {entry.name}")
            if depth < 3:
                walk(path, depth + 1)
                continue
            run_entries = entries(path)
            manifest_entries = [candidate for candidate in run_entries if candidate.name == "run.json"]
            if len(manifest_entries) != 1:
                if not run_entries and RUN_ID_RE.fullmatch(entry.name):
                    continue
                raise CatalogueBuildError(f"run directory is missing exact-case run.json: {entry.name}")
            manifest = manifest_entries[0]
            try:
                if manifest.is_symlink() or not manifest.is_file(follow_symlinks=False):
                    raise CatalogueBuildError(f"run.json must be a regular file: {entry.name}")
            except OSError as error:
                raise CatalogueBuildError(f"unable to inspect run.json: {entry.name}") from error
            candidates.append(RunCandidate(Path(manifest.path)))

    walk(root, 0)
    return candidates


def relative_href(out_path: Path, target: Path) -> str:
    """Create a portable relative link from the generated index to a run file."""
    return Path(os.path.relpath(target, start=out_path.parent)).as_posix()


def exact_child(parent: Path, name: str) -> Optional[Path]:
    """Find a child by its stored spelling, even on case-insensitive filesystems."""
    try:
        return next((child for child in parent.iterdir() if child.name == name), None)
    except OSError:
        return None


def is_exact_artifact_file(target: Path) -> bool:
    """Require the literal artifact directory and filename before linking."""
    artifact = exact_child(target.parent.parent, target.parent.name)
    try:
        if artifact is None or artifact.is_symlink() or not artifact.is_dir():
            return False
    except OSError:
        return False
    stored_target = exact_child(artifact, target.name)
    try:
        return stored_target is not None and not stored_target.is_symlink() and stored_target.is_file()
    except OSError:
        return False


def file_link(out_path: Path, target: Path, label: str) -> str:
    """Link only files that exist so incomplete runs do not create dead navigation."""
    if not is_exact_artifact_file(target):
        return '<span class="muted">Unavailable</span>'
    return f'<a href="{esc(relative_href(out_path, target))}">{esc(label)}</a>'


def replacement_mode(out_path: Path) -> int:
    """Preserve an existing catalogue mode or use a web-readable default."""
    try:
        return stat.S_IMODE(out_path.stat().st_mode) | 0o644
    except FileNotFoundError:
        return 0o644


def fsync_directory(directory: Path) -> None:
    """Persist the atomic rename where directory handles support syncing."""
    if os.name != "posix":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def identity_name(identity: dict[str, Any], fallback: str) -> str:
    """Prefer the exact reported name while retaining a namespace fallback."""
    name = identity.get("name")
    if isinstance(name, str) and name.strip():
        return bounded_text(name, max_chars=IDENTITY_DISPLAY_CHARS)
    return bounded_text(identity.get("key"), fallback, IDENTITY_DISPLAY_CHARS)


def status_class(status: str) -> str:
    """Map stable run statuses to a small set of presentational classes."""
    normalized = status.upper()
    if normalized == "OK":
        return "status-ok"
    if normalized in {"PLANNED", "RUNNING", "PARTIAL"}:
        return "status-progress"
    return "status-problem"


def worker_details(run: dict[str, Any], report: dict[str, Any]) -> str:
    """Render exposed lead and descendant worker information without guessing."""
    execution = object_value(run.get("execution"))
    run_lead = execution.get("leadWorkerId")
    run_descendants = execution.get("descendantWorkerIds")
    report_lead = report.get("leadWorkerId", run_lead)
    report_descendants = report.get("descendantWorkerIds", run_descendants)
    if report_lead != run_lead or report_descendants != run_descendants:
        return "Worker metadata mismatch"

    lead = bounded_text(report_lead, max_chars=256)
    descendants = report_descendants
    descendant_count = len(descendants) if isinstance(descendants, list) else None

    pieces: list[str] = []
    if lead:
        pieces.append(f"Lead: {lead}")
    if descendant_count is not None:
        noun = "descendant" if descendant_count == 1 else "descendants"
        pieces.append(f"{descendant_count} {noun}")
    return " · ".join(pieces) or "Not reported"


def outcome_text(run: dict[str, Any], report: dict[str, Any], load_error: Optional[str]) -> str:
    """Prefer an honest summary and otherwise surface the worker's blocker."""
    if load_error:
        return f"Report unavailable: {load_error}"
    for source in (report, run):
        summary = text_value(source.get("summary"))
        if summary:
            return bounded_text(summary, max_chars=OUTCOME_DISPLAY_CHARS)
    for source in (report, run):
        blocker = text_value(source.get("blocker"))
        if blocker:
            return f"Blocker: {bounded_text(blocker, max_chars=OUTCOME_DISPLAY_CHARS)}"
    return "No summary or blocker reported."


def build_rows(root: Path, out_path: Path) -> tuple[str, int]:
    """Build one provenance row per namespace-valid run manifest."""
    rows: list[str] = []
    candidates = discover_runs(root)
    for candidate in candidates:
        run_path = candidate.run_path
        run_dir = run_path.parent
        if candidate.discovery_error is None:
            run, run_error = load_object(run_path)
            report_path = exact_child(run_dir, "worker-report.json")
            report, report_error = load_object(report_path) if report_path is not None else ({}, None)
        else:
            run, run_error = {}, candidate.discovery_error
            report, report_error = {}, None
        identity = object_value(run.get("identity"))
        model = object_value(identity.get("model"))
        harness = object_value(identity.get("harness"))
        experiment = object_value(identity.get("experiment"))

        status = bounded_text(
            run.get("status"), "INVALID" if run_error else "UNKNOWN", 64
        ).upper()
        classification = bounded_text(run.get("classification"), "Unknown", 128)
        row_error = run_error or report_error
        if candidate.discovery_error is None:
            site_link = file_link(out_path, run_dir / "artifact" / "index.html", "Artifact entry")
            prompt_link = file_link(out_path, run_dir / "artifact" / "PROMPT.md", "PROMPT.md")
        else:
            site_link = '<span class="muted">Unavailable</span>'
            prompt_link = '<span class="muted">Unavailable</span>'

        rows.append(
            "        <tr>\n"
            f'          <td data-label="Model"><span class="identity">{esc(identity_name(model, run_dir.parents[2].name))}</span></td>\n'
            f'          <td data-label="Harness"><span class="identity">{esc(identity_name(harness, run_dir.parents[1].name))}</span></td>\n'
            f'          <td data-label="Experiment"><span class="identity">{esc(identity_name(experiment, run_dir.parents[0].name))}</span></td>\n'
            f'          <td data-label="Run"><code>{esc(bounded_text(run.get("runId"), run_dir.name, 128))}</code></td>\n'
            f'          <td data-label="Status"><span class="status {status_class(status)}">{esc(status)}</span></td>\n'
            f'          <td data-label="Classification"><code>{esc(classification)}</code></td>\n'
            f'          <td data-label="Workers" class="muted">{esc(worker_details(run, report))}</td>\n'
            f'          <td data-label="Summary or blocker" class="muted">{esc(outcome_text(run, report, row_error))}</td>\n'
            f'          <td data-label="Artifact">{site_link}</td>\n'
            f'          <td data-label="Prompt">{prompt_link}</td>\n'
            "        </tr>"
        )
    return "\n".join(rows), len(candidates)


def build_html(root: Path, out_path: Path) -> str:
    """Render the checked-in template with static, escaped provenance data."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    rows, run_count = build_rows(root, out_path)
    replacements = {
        "{{CATALOG_TITLE}}": "One-shot website run catalogue",
        "{{CATALOG_DESCRIPTION}}": "A static provenance index for isolated one-shot website experiments.",
        "{{META_CHIPS}}": (
            f"<span>Runs discovered: <code>{run_count}</code></span>"
        ),
        "{{FAIRNESS_NOTE}}": (
            "Each row preserves the run namespace and points to the worker-owned artifact. "
            "Incomplete and failed runs remain visible alongside completed work."
        ),
        "{{ROWS}}": rows or '        <tr><td colspan="10" class="muted">No run manifests found at the expected namespace depth.</td></tr>',
        "{{FOOTER_NOTE}}": "This index reads provenance files and never rewrites run artifacts.",
    }
    rendered = PLACEHOLDER_RE.sub(lambda match: replacements[match.group(0)], template)
    if len(rendered.encode("utf-8")) > ROOT_INDEX_MAX_BYTES:
        raise CatalogueBuildError(
            "rendered root catalogue exceeds the 5 MiB static-file limit; split the output root into smaller catalogues"
        )
    return rendered


@contextmanager
def catalogue_lock(root: Path) -> Iterator[None]:
    """Serialize render-and-publish so an older snapshot cannot win last."""

    lock_path = root / CATALOGUE_LOCK
    try:
        existing_lock = lock_path.lstat()
    except FileNotFoundError:
        existing_lock = None
    except OSError as error:
        raise CatalogueBuildError(f"unable to inspect catalogue lock: {error}") from error
    if existing_lock is not None and (
        not stat.S_ISREG(existing_lock.st_mode) or existing_lock.st_nlink != 1
    ):
        raise CatalogueBuildError("catalogue lock path must be a private regular non-symlink file")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as error:
        raise CatalogueBuildError(f"unable to open catalogue lock: {error}") from error
    locked = False
    try:
        try:
            lock_stat = os.fstat(descriptor)
        except OSError as error:
            raise CatalogueBuildError(f"unable to inspect catalogue lock: {error}") from error
        if not stat.S_ISREG(lock_stat.st_mode) or lock_stat.st_nlink != 1:
            raise CatalogueBuildError("catalogue lock path must be a private regular non-symlink file")

        if os.name == "posix":
            try:
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_EX)
            except (ImportError, OSError) as error:
                raise CatalogueBuildError(f"unable to acquire catalogue lock: {error}") from error
        else:
            try:
                import msvcrt

                if lock_stat.st_size == 0:
                    os.write(descriptor, b"\0")
                while True:
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    try:
                        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                        break
                    except OSError as error:
                        if error.errno not in {13, 36}:
                            raise
                        time.sleep(0.05)
            except (ImportError, OSError) as error:
                raise CatalogueBuildError(f"unable to acquire catalogue lock: {error}") from error
        locked = True
        yield
    finally:
        if locked:
            try:
                if os.name == "posix":
                    import fcntl

                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                else:
                    import msvcrt

                    os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            except (ImportError, OSError):
                pass
        try:
            os.close(descriptor)
        except OSError:
            pass


def publish_catalogue(root: Path, out_path: Path) -> None:
    """Validate, render, and atomically publish one locked catalogue snapshot."""

    stored_output = exact_child(root, "index.html")
    if stored_output is not None:
        try:
            if stored_output.is_symlink() or not stored_output.is_file():
                raise CatalogueBuildError(
                    "root catalogue destination index.html must be a regular non-symlink file"
                )
        except OSError as error:
            raise CatalogueBuildError(f"unable to inspect root catalogue destination: {error}") from error
    try:
        case_collisions = [
            child.name
            for child in root.iterdir()
            if child.name.casefold() == "index.html" and child.name != "index.html"
        ]
    except OSError as error:
        raise CatalogueBuildError(f"unable to inspect output root: {error}") from error
    if case_collisions and exact_child(root, "index.html") is None:
        names = ", ".join(sorted(case_collisions))
        raise CatalogueBuildError(
            f"wrong-case root catalogue filename collides with index.html: {names}; "
            "rename or remove it before rebuilding"
        )

    rendered = build_html(root, out_path)
    destination_mode = replacement_mode(out_path)
    temporary_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=root,
            prefix=".oneshot-index-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(rendered)
            handle.flush()
            os.chmod(temporary_path, destination_mode)
            os.fsync(handle.fileno())
        os.replace(temporary_path, out_path)
        fsync_directory(root)
    except OSError as error:
        raise CatalogueBuildError(f"unable to publish root catalogue: {error}") from error
    finally:
        if temporary_path is not None and temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="One-shot output root")
    parser.add_argument("--out", required=True, help="Destination index.html path")
    args = parser.parse_args()

    try:
        root = Path(args.root).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise SystemExit(f"unable to resolve output root: {error}") from error
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")
    try:
        root_mode = root.stat().st_mode
    except OSError as error:
        raise SystemExit(f"unable to inspect output root: {error}") from error
    if root_mode & 0o222 == 0:
        raise SystemExit("output root must have a writable directory mode for atomic catalogue publication")
    try:
        out_path = resolve_existing_or_new(Path(args.out))
    except (OSError, RuntimeError) as error:
        raise SystemExit(f"unable to resolve output path: {error}") from error
    expected_out = root / "index.html"
    if out_path != expected_out:
        raise SystemExit(f"--out must be the catalogue root index: {expected_out}")
    try:
        with catalogue_lock(root):
            publish_catalogue(root, out_path)
    except CatalogueBuildError as error:
        raise SystemExit(f"cannot build root catalogue: {error}") from error
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

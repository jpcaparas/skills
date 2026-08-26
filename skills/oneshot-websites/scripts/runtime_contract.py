#!/usr/bin/env python3
"""Shared runtime safety and identity rules for one-shot experiment tooling."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path


APPLEDOUBLE_MAGIC = b"\x00\x05\x16\x07"
JSON_NESTING_MAX = 256
JSON_NUMBER_TOKEN_MAX_CHARS = 256
EXPERIMENT_SLUG_MAX_CHARS = 64
COORDINATOR_MONITORING_CONTRACT: dict[str, object] = {
    "required": True,
    "contractVersion": "1.0",
    "mode": "bounded-periodic-liveness-checks",
    "recovery": "same-run-single-owner",
}

_UTF8_LEAD_BYTES_DECODED_AS_CP1252 = frozenset("\u00c2\u00c3\u00e2\u00ef\u00f0")


class BoundedReadError(ValueError):
    """Raised when a path is not a stable regular file within the read bound."""


@dataclass(frozen=True)
class MojibakeEvidence:
    """One high-confidence marker of incorrectly transcoded UTF-8 text."""

    offset: int
    text: str

    @property
    def codepoints(self) -> str:
        """Describe evidence without reproducing terminal-corrupting glyphs."""

        return " ".join("U+{:04X}".format(ord(character)) for character in self.text)


def find_likely_mojibake(value: str) -> MojibakeEvidence | None:
    """Find high-confidence UTF-8/Windows-1252 corruption in decoded text.

    Valid Unicode punctuation, emoji, and non-Latin scripts are intentionally
    accepted. The matcher reports replacement/control characters immediately.
    For printable text, it requires a complete two-to-four-character sequence
    whose Windows-1252 bytes reversibly decode as UTF-8, such as
    ``\u00e2\u20ac\u201d`` for an em dash. Requiring the complete sequence avoids
    treating valid neighboring characters such as Icelandic ``or\u00f0\u2014`` as
    corruption merely because the first character resembles a UTF-8 lead byte.
    """

    for offset, character in enumerate(value):
        if character == "\ufffd" or 0x80 <= ord(character) <= 0x9F:
            return MojibakeEvidence(offset=offset, text=character)
        if character not in _UTF8_LEAD_BYTES_DECODED_AS_CP1252:
            continue
        for width in range(2, 5):
            candidate = value[offset : offset + width]
            if len(candidate) != width:
                break
            try:
                repaired = candidate.encode("cp1252").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if repaired != candidate:
                return MojibakeEvidence(offset=offset, text=candidate)
    return None


def enforce_json_nesting_limit(value: str, max_depth: int = JSON_NESTING_MAX) -> None:
    """Reject deeply nested JSON before interpreter-specific decoders allocate it."""

    depth = 0
    in_string = False
    escaped = False
    for character in value:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
            continue
        if character in "[{":
            depth += 1
            if depth > max_depth:
                raise ValueError(f"JSON nesting exceeds the {max_depth}-level metadata limit")
        elif character in "]}":
            depth = max(0, depth - 1)


def _parse_bounded_json_integer(token: str) -> int:
    """Parse an integer only after bounding interpreter-sensitive conversion work."""

    if len(token) > JSON_NUMBER_TOKEN_MAX_CHARS:
        raise ValueError(
            f"JSON integer token exceeds the {JSON_NUMBER_TOKEN_MAX_CHARS}-character metadata limit"
        )
    return int(token)


def _parse_bounded_json_float(token: str) -> float:
    """Parse a finite float only after bounding its source token."""

    if len(token) > JSON_NUMBER_TOKEN_MAX_CHARS:
        raise ValueError(
            f"JSON floating-point token exceeds the {JSON_NUMBER_TOKEN_MAX_CHARS}-character metadata limit"
        )
    value = float(token)
    if not math.isfinite(value):
        raise ValueError("JSON floating-point token must resolve to a finite value")
    return value


def _reject_nonstandard_json_constant(token: str) -> object:
    """Reject NaN and infinities, which are outside the JSON specification."""

    raise ValueError(f"non-standard JSON numeric constant is not allowed: {token}")


def _reject_duplicate_json_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Build an object only when every decoded member name is unique."""

    members: dict[str, object] = {}
    for name, member in pairs:
        if name in members:
            raise ValueError(f"duplicate JSON object member: {name!r}")
        members[name] = member
    return members


def parse_json_bounded(value: str) -> object:
    """Decode metadata with version-independent nesting and numeric-work bounds."""

    enforce_json_nesting_limit(value)
    parsed: object = json.loads(
        value,
        parse_int=_parse_bounded_json_integer,
        parse_float=_parse_bounded_json_float,
        parse_constant=_reject_nonstandard_json_constant,
        object_pairs_hook=_reject_duplicate_json_members,
    )
    return parsed


def resolve_existing_or_new(path: Path) -> Path:
    """Strictly resolve the nearest existing ancestor, then append new components."""

    absolute = Path(os.path.abspath(os.fspath(path.expanduser())))
    missing_components: list[str] = []
    current = absolute
    while True:
        try:
            current.lstat()
        except FileNotFoundError:
            parent = current.parent
            if parent == current:
                raise
            missing_components.append(current.name)
            current = parent
            continue
        resolved = current.resolve(strict=True)
        for component in reversed(missing_components):
            resolved /= component
        return resolved


def read_regular_file_bounded(path: Path, max_bytes: int) -> bytes:
    """Read at most max_bytes from one non-symlink regular file descriptor."""

    try:
        before = path.lstat()
    except OSError as error:
        raise BoundedReadError(f"unable to inspect file: {error}") from error
    if not stat.S_ISREG(before.st_mode):
        raise BoundedReadError("path must be a regular non-symlink file")
    if before.st_mode & 0o444 == 0:
        raise BoundedReadError("file has no readable mode")
    if before.st_size > max_bytes:
        raise BoundedReadError(f"file exceeds the {max_bytes}-byte read limit")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise BoundedReadError(f"unable to open regular file: {error}") from error
    try:
        try:
            after = os.fstat(descriptor)
            if not stat.S_ISREG(after.st_mode):
                raise BoundedReadError("opened path is not a regular file")
            if after.st_mode & 0o444 == 0:
                raise BoundedReadError("opened file has no readable mode")
            if after.st_size > max_bytes:
                raise BoundedReadError(f"file exceeds the {max_bytes}-byte read limit")
            if before.st_dev != after.st_dev or before.st_ino != after.st_ino:
                raise BoundedReadError("file changed while it was being opened")
            chunks: list[bytes] = []
            remaining = max_bytes + 1
            while remaining > 0:
                chunk = os.read(descriptor, min(64 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            if len(data) > max_bytes:
                raise BoundedReadError(f"file exceeds the {max_bytes}-byte read limit")
            return data
        except OSError as error:
            raise BoundedReadError(f"unable to read regular file: {error}") from error
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass


def is_appledouble_sidecar(path: Path) -> bool:
    """Recognize macOS AppleDouble metadata without trusting a filename alone."""

    if not path.name.startswith("._"):
        return False
    try:
        before = path.lstat()
    except OSError:
        return False
    if not stat.S_ISREG(before.st_mode):
        return False

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return False
    try:
        after = os.fstat(descriptor)
        if not stat.S_ISREG(after.st_mode):
            return False
        if before.st_dev != after.st_dev or before.st_ino != after.st_ino:
            return False
        return os.read(descriptor, len(APPLEDOUBLE_MAGIC)) == APPLEDOUBLE_MAGIC
    except OSError:
        return False
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass


def is_abandoned_run_reservation(run_directory: Path, commit_path: Path) -> bool:
    """Identify bounded initialization residue that never reached dispatch commit."""

    try:
        run_stat = run_directory.lstat()
    except OSError:
        return False
    if not stat.S_ISDIR(run_stat.st_mode):
        return False
    try:
        commit_path.lstat()
    except FileNotFoundError:
        pass
    except OSError:
        return False
    else:
        return False

    def bounded_entries(directory: Path) -> list[Path] | None:
        values: list[Path] = []
        try:
            with os.scandir(directory) as iterator:
                for entry in iterator:
                    values.append(Path(entry.path))
                    if len(values) > 16:
                        return None
        except OSError:
            return None
        return values

    entries = bounded_entries(run_directory)
    if entries is None:
        return False
    ordinary_entries = [entry for entry in entries if not is_appledouble_sidecar(entry)]
    if any(
        entry.name not in {".tmp", "workspace", "artifact", "run.json", "worker-report.json"}
        for entry in ordinary_entries
    ):
        return False

    for metadata_name in ("run.json", "worker-report.json"):
        metadata = next((entry for entry in ordinary_entries if entry.name == metadata_name), None)
        if metadata is None:
            continue
        try:
            metadata_stat = metadata.lstat()
        except OSError:
            return False
        if not stat.S_ISREG(metadata_stat.st_mode) or metadata_stat.st_size > 1024 * 1024:
            return False

    for name in (".tmp", "workspace", "artifact"):
        directory = next((entry for entry in ordinary_entries if entry.name == name), None)
        if directory is None:
            continue
        try:
            directory_stat = directory.lstat()
        except OSError:
            return False
        if not stat.S_ISDIR(directory_stat.st_mode):
            return False
        children = bounded_entries(directory)
        if children is None:
            return False
        ordinary_children = [child for child in children if not is_appledouble_sidecar(child)]
        if name in {".tmp", "workspace"} and ordinary_children:
            return False
        if name == "artifact":
            if any(child.name != "PROMPT.md" for child in ordinary_children):
                return False
            for child in ordinary_children:
                try:
                    child_stat = child.lstat()
                except OSError:
                    return False
                if not stat.S_ISREG(child_stat.st_mode) or child_stat.st_size > 5 * 1024 * 1024:
                    return False
    return True


def safe_slug(name: str) -> str:
    """Make a conservative cross-platform path component from a display name."""

    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.casefold()).strip("-._ ")
    return slug[:12].strip("-") or "unnamed"


def experiment_slug(name: str) -> str:
    """Derive a readable, bounded run-directory slug from an experiment name."""

    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.casefold()).strip("-")
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    if not slug:
        return f"experiment-{digest}"
    if slug.isdigit():
        slug = f"experiment-{slug}"
    if len(slug) <= EXPERIMENT_SLUG_MAX_CHARS:
        return slug
    prefix_length = EXPERIMENT_SLUG_MAX_CHARS - len(digest) - 1
    prefix = slug[:prefix_length].rstrip("-")
    return f"{prefix}-{digest}"


def identity_key(name: str) -> str:
    """Bind a readable path key to the exact UTF-8 bytes of its raw name."""

    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:32]
    return f"{safe_slug(name)}-{digest}"

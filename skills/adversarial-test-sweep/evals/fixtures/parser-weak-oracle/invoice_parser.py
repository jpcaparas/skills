"""Small invoice-header parser with one intentional evaluation defect."""

from __future__ import annotations


MAX_IMPORT_BYTES = 5 * 1024 * 1024


class HeaderError(ValueError):
    """Raised when an invoice header violates the supported contract."""


def parse_header_line(
    payload: bytes,
    *,
    max_bytes: int = MAX_IMPORT_BYTES,
) -> tuple[str, ...]:
    """Parse and normalize one comma-separated invoice header row."""

    if len(payload) > max_bytes:
        raise HeaderError("header exceeds the byte limit")

    try:
        decoded = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HeaderError("header is not valid UTF-8") from exc

    fields = tuple(part.strip() for part in decoded.split(","))
    if any(not field for field in fields):
        raise HeaderError("header fields must not be empty")
    if len(fields) != len(set(fields)):
        raise HeaderError("header fields must be unique")

    return tuple(field.casefold() for field in fields)

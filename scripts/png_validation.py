#!/usr/bin/env python3
"""Strict, bounded PNG datastream validation using only the standard library."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PNG_CHUNK_LENGTH = (1 << 31) - 1
MAX_DECOMPRESSED_PNG_BYTES = 8_000_000
VALID_BIT_DEPTHS_BY_COLOR_TYPE = {
    0: frozenset({1, 2, 4, 8, 16}),
    2: frozenset({8, 16}),
    3: frozenset({1, 2, 4, 8}),
    4: frozenset({8, 16}),
    6: frozenset({8, 16}),
}
CHANNELS_BY_COLOR_TYPE = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
ADAM7_PASSES = (
    (0, 0, 8, 8),
    (4, 0, 8, 8),
    (0, 4, 4, 8),
    (2, 0, 4, 4),
    (0, 2, 2, 4),
    (1, 0, 2, 2),
    (0, 1, 1, 2),
)


@dataclass(frozen=True)
class PngMetadata:
    """Validated PNG fields needed by artwork policy checks."""

    width: int
    height: int
    chunks: tuple[str, ...]


@dataclass(frozen=True)
class _ParsedChunks:
    """Binary payloads and names recovered from validated chunk framing."""

    ihdr: bytes
    idat: bytes
    names: tuple[str, ...]
    plte: bytes | None


@dataclass(frozen=True)
class _PngHeader:
    """Typed IHDR fields needed to validate the decompressed raster."""

    width: int
    height: int
    bit_depth: int
    color_type: int
    interlace_method: int


class PngValidationError(ValueError):
    """Raised when bytes do not form a bounded, decodable PNG datastream."""


def _chunk_type_name(chunk_type: bytes) -> str:
    """Decode one conforming four-letter PNG chunk type."""

    if len(chunk_type) != 4 or any(
        byte not in range(ord("A"), ord("Z") + 1)
        and byte not in range(ord("a"), ord("z") + 1)
        for byte in chunk_type
    ):
        raise PngValidationError("chunk types must contain four ASCII letters")
    if chunk_type[2] & 0x20:
        raise PngValidationError("chunk type reserved bit must be uppercase")
    return chunk_type.decode("ascii")


def _pass_size(total: int, start: int, step: int) -> int:
    """Return the number of pixels selected by one Adam7 pass dimension."""

    if total <= start:
        return 0
    return (total - start + step - 1) // step


def _scanline_layout(
    width: int,
    height: int,
    bits_per_pixel: int,
    interlace_method: int,
) -> tuple[tuple[int, int], ...]:
    """Return ``(row_count, row_bytes)`` pairs for the PNG image passes."""

    passes = ((0, 0, 1, 1),) if interlace_method == 0 else ADAM7_PASSES
    layout: list[tuple[int, int]] = []
    for x_start, y_start, x_step, y_step in passes:
        pass_width = _pass_size(width, x_start, x_step)
        pass_height = _pass_size(height, y_start, y_step)
        if pass_width == 0 or pass_height == 0:
            continue
        row_bytes = (pass_width * bits_per_pixel + 7) // 8
        layout.append((pass_height, row_bytes))
    return tuple(layout)


def _validate_image_data(
    compressed: bytes,
    *,
    width: int,
    height: int,
    bit_depth: int,
    color_type: int,
    interlace_method: int,
) -> None:
    """Boundedly inflate image data and validate row framing/filter bytes."""

    bits_per_pixel = bit_depth * CHANNELS_BY_COLOR_TYPE[color_type]
    layout = _scanline_layout(width, height, bits_per_pixel, interlace_method)
    expected_size = sum(row_count * (row_bytes + 1) for row_count, row_bytes in layout)
    if expected_size > MAX_DECOMPRESSED_PNG_BYTES:
        raise PngValidationError("decoded raster exceeds the validator safety budget")

    decompressor = zlib.decompressobj()
    try:
        decoded = decompressor.decompress(compressed, expected_size + 1)
    except zlib.error as exc:
        raise PngValidationError(f"IDAT data is not a valid zlib stream: {exc}") from exc

    if decompressor.unconsumed_tail or len(decoded) > expected_size:
        raise PngValidationError("IDAT data expands beyond the declared image dimensions")
    if not decompressor.eof:
        raise PngValidationError("IDAT zlib stream is incomplete")
    if decompressor.unused_data:
        raise PngValidationError("IDAT contains trailing data after its zlib stream")
    if len(decoded) != expected_size:
        raise PngValidationError(
            "IDAT data size does not match the declared image dimensions"
        )

    offset = 0
    for row_count, row_bytes in layout:
        for _ in range(row_count):
            if decoded[offset] > 4:
                raise PngValidationError("scanline uses an invalid PNG filter type")
            offset += row_bytes + 1


def _parse_chunks(data: bytes) -> _ParsedChunks:
    """Validate PNG chunk framing, ordering, CRCs, and required chunks."""

    if not data.startswith(PNG_SIGNATURE):
        raise PngValidationError("signature is missing or invalid")

    chunks: list[str] = []
    idat_parts: list[bytes] = []
    ihdr_data: bytes | None = None
    plte_data: bytes | None = None
    saw_idat = False
    idat_sequence_closed = False
    saw_iend = False
    offset = len(PNG_SIGNATURE)

    while offset < len(data):
        if len(data) - offset < 12:
            raise PngValidationError("chunk framing is truncated")

        length = struct.unpack(">I", data[offset : offset + 4])[0]
        if length > MAX_PNG_CHUNK_LENGTH:
            raise PngValidationError("chunk length exceeds the PNG limit")

        chunk_type_bytes = data[offset + 4 : offset + 8]
        chunk_type = _chunk_type_name(chunk_type_bytes)
        payload_start = offset + 8
        payload_end = payload_start + length
        chunk_end = payload_end + 4
        if chunk_end > len(data):
            raise PngValidationError(f"{chunk_type} chunk is truncated")

        payload = data[payload_start:payload_end]
        stored_crc = struct.unpack(">I", data[payload_end:chunk_end])[0]
        calculated_crc = zlib.crc32(chunk_type_bytes)
        calculated_crc = zlib.crc32(payload, calculated_crc) & 0xFFFFFFFF
        if stored_crc != calculated_crc:
            raise PngValidationError(f"{chunk_type} chunk CRC does not match")

        if not chunks and chunk_type != "IHDR":
            raise PngValidationError("IHDR must be the first chunk")
        chunks.append(chunk_type)

        if chunk_type == "IHDR":
            if ihdr_data is not None or len(chunks) != 1:
                raise PngValidationError("IHDR must appear exactly once and first")
            if length != 13:
                raise PngValidationError("IHDR must contain exactly 13 data bytes")
            ihdr_data = payload
        elif chunk_type == "IDAT":
            if idat_sequence_closed:
                raise PngValidationError("IDAT chunks must be consecutive")
            saw_idat = True
            idat_parts.append(payload)
        elif chunk_type == "PLTE":
            if plte_data is not None:
                raise PngValidationError("PLTE must appear at most once")
            if saw_idat:
                raise PngValidationError("PLTE must appear before the first IDAT chunk")
            plte_data = payload
        elif saw_idat:
            idat_sequence_closed = True

        if chunk_type == "IEND":
            if length != 0:
                raise PngValidationError("IEND must have an empty data field")
            if chunk_end != len(data):
                raise PngValidationError("bytes follow the IEND chunk")
            saw_iend = True
            offset = chunk_end
            break

        offset = chunk_end

    if ihdr_data is None:
        raise PngValidationError("IHDR chunk is missing")
    if not saw_idat:
        raise PngValidationError("at least one IDAT chunk is required")
    if not saw_iend:
        raise PngValidationError("IEND chunk is missing")

    return _ParsedChunks(
        ihdr=ihdr_data,
        idat=b"".join(idat_parts),
        names=tuple(chunks),
        plte=plte_data,
    )


def _parse_header(ihdr: bytes, palette: bytes | None) -> _PngHeader:
    """Parse IHDR into a typed header after enforcing its field contracts."""

    width, height, bit_depth, color_type, compression, filter_method, interlace = (
        struct.unpack(">IIBBBBB", ihdr)
    )
    invalid_dimensions = (
        width == 0
        or height == 0
        or width > MAX_PNG_CHUNK_LENGTH
        or height > MAX_PNG_CHUNK_LENGTH
    )
    if invalid_dimensions:
        raise PngValidationError("IHDR dimensions are outside the PNG range")
    valid_bit_depths = VALID_BIT_DEPTHS_BY_COLOR_TYPE.get(color_type)
    if valid_bit_depths is None or bit_depth not in valid_bit_depths:
        raise PngValidationError("IHDR bit depth and color type are incompatible")
    if compression != 0 or filter_method != 0:
        raise PngValidationError("IHDR uses an unsupported compression or filter method")
    if interlace not in (0, 1):
        raise PngValidationError("IHDR uses an invalid interlace method")
    if color_type == 3 and palette is None:
        raise PngValidationError("indexed-color PNG is missing its PLTE chunk")
    if palette is not None:
        if len(palette) == 0 or len(palette) % 3 != 0 or len(palette) > 768:
            raise PngValidationError(
                "PLTE must contain between 1 and 256 three-byte entries"
            )
        if color_type in (0, 4):
            raise PngValidationError("PLTE is prohibited for greyscale PNG color types")
        if color_type == 3 and len(palette) // 3 > 1 << bit_depth:
            raise PngValidationError("PLTE has more entries than the indexed bit depth allows")

    return _PngHeader(
        width=width,
        height=height,
        bit_depth=bit_depth,
        color_type=color_type,
        interlace_method=interlace,
    )


def parse_png(data: bytes) -> PngMetadata:
    """Parse and validate one bounded PNG datastream."""

    chunks = _parse_chunks(data)
    header = _parse_header(chunks.ihdr, chunks.plte)
    _validate_image_data(
        chunks.idat,
        width=header.width,
        height=header.height,
        bit_depth=header.bit_depth,
        color_type=header.color_type,
        interlace_method=header.interlace_method,
    )
    return PngMetadata(
        width=header.width,
        height=header.height,
        chunks=chunks.names,
    )

#!/usr/bin/env python3
"""Extract and verify tightly cropped transparent sprites from explicit regions."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import numpy as np
from PIL import Image, UnidentifiedImageError

from sprite_decompose_core import (
    BackgroundDiagnostics,
    ExtractionError,
    ExtractionSpec,
    JsonObject,
    SpecError,
    SpriteRecord,
    extract_region,
    fit_background_surface,
    image_sha256,
    load_spec,
    save_rgba,
)
from sprite_decompose_manifest import ManifestError, validate_manifest


TOOL_NAME: Final = "sprite-decompose"
TOOL_VERSION: Final = "1.0.0"


class OutputError(ValueError):
    """Raised when an output directory or manifest violates the write contract."""


@dataclass(frozen=True, slots=True)
class ExtractArguments:
    source: Path
    regions: Path
    output: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class VerifyArguments:
    output: Path


Arguments = ExtractArguments | VerifyArguments


def parse_args(argv: list[str] | None = None) -> Arguments:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Extract PNGs using an explicit region specification.")
    extract_parser.add_argument("source", type=Path, help="Source sprite sheet or contact-sheet image.")
    extract_parser.add_argument("regions", type=Path, help="JSON region specification.")
    extract_parser.add_argument("output", type=Path, help="New output directory for PNGs and manifest.json.")
    extract_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing output directory after the staged result validates.",
    )

    verify_parser = subparsers.add_parser("verify", help="Verify PNGs against an existing manifest.")
    verify_parser.add_argument("output", type=Path, help="Output directory containing manifest.json and PNGs.")

    namespace = parser.parse_args(argv)
    if namespace.command == "extract":
        return ExtractArguments(namespace.source, namespace.regions, namespace.output, namespace.overwrite)
    return VerifyArguments(namespace.output)


def extract(args: ExtractArguments) -> list[SpriteRecord]:
    source_input = args.source.expanduser().absolute()
    regions_input = args.regions.expanduser().absolute()
    output_input = args.output.expanduser().absolute()
    _validate_inputs(source_input, regions_input, output_input, args.overwrite)
    source = source_input.resolve()
    regions_path = regions_input.resolve()
    output = output_input.resolve()

    source_before = image_sha256(source)
    try:
        with Image.open(source) as opened:
            rgb_image = opened.convert("RGB")
    except (OSError, UnidentifiedImageError) as error:
        raise OutputError(f"cannot open source image {source}: {error}") from error
    width, height = rgb_image.size
    spec = load_spec(regions_path, width, height)
    image = np.asarray(rgb_image, dtype=np.float64)
    background, background_diagnostics = fit_background_surface(
        image,
        spec.background,
        spec.background_samples,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".sprite-decompose-stage-", dir=output.parent))
    published = False
    try:
        records = _write_staged_output(
            stage,
            source,
            source_before,
            width,
            height,
            image,
            background,
            background_diagnostics,
            spec,
        )
        verify_output(stage)
        if image_sha256(source) != source_before:
            raise OutputError("source image changed during extraction; staged output was not published")
        publish_staged_output(stage, output, args.overwrite)
        published = True
        return records
    finally:
        if not published and stage.exists():
            shutil.rmtree(stage)


def _validate_inputs(source: Path, regions: Path, output: Path, overwrite: bool) -> None:
    if source.is_symlink() or not source.is_file():
        raise OutputError(f"source must be a regular file: {source}")
    if regions.is_symlink() or not regions.is_file():
        raise OutputError(f"region specification must be a regular file: {regions}")
    resolved_source = source.resolve()
    resolved_regions = regions.resolve()
    resolved_output = output.resolve()
    if (
        resolved_output in {resolved_source, resolved_regions}
        or resolved_output in resolved_source.parents
        or resolved_output in resolved_regions.parents
    ):
        raise OutputError("output directory must not be an input path or contain either input")
    if output.exists():
        if not overwrite:
            raise OutputError(f"output already exists: {output}; pass --overwrite to replace it")
        if output.is_symlink() or not output.is_dir():
            raise OutputError("--overwrite only replaces an existing regular directory, never a file or symlink")


def _write_staged_output(
    stage: Path,
    source: Path,
    source_sha256: str,
    source_width: int,
    source_height: int,
    image: np.ndarray[tuple[int, int, int], np.dtype[np.float64]],
    background: np.ndarray[tuple[int, int, int], np.dtype[np.float64]],
    background_diagnostics: BackgroundDiagnostics,
    spec: ExtractionSpec,
) -> list[SpriteRecord]:
    records: list[SpriteRecord] = []
    for order, region in enumerate(spec.regions, start=1):
        filename = f"{region.name}.png" if region.name is not None else f"sprite-{order:03d}.png"
        output_path = _safe_child(stage, filename)
        pixels = extract_region(image, background, region, spec.matting)
        save_rgba(output_path, pixels.rgba)
        records.append(
            SpriteRecord(
                order=order,
                requested_name=region.name,
                filename=filename,
                source_bounds=region.bounds,
                visible_source_bounds=pixels.visible_source_bounds,
                width=int(pixels.rgba.shape[1]),
                height=int(pixels.rgba.shape[0]),
                grouping=region.grouping,
                component_policy=region.component_policy,
                kept_components=pixels.kept_components,
                discarded_components=pixels.discarded_components,
                warnings=pixels.warnings,
                sha256=image_sha256(output_path),
            )
        )

    manifest = _manifest(
        source,
        source_sha256,
        source_width,
        source_height,
        spec,
        background_diagnostics,
        records,
    )
    _write_json(_safe_child(stage, "manifest.json"), manifest)
    return records


def _manifest(
    source: Path,
    source_sha256: str,
    source_width: int,
    source_height: int,
    spec: ExtractionSpec,
    diagnostics: BackgroundDiagnostics,
    records: list[SpriteRecord],
) -> JsonObject:
    warning_count = sum(len(record.warnings) for record in records)
    return {
        "schema_version": 1,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "source": {
            "filename": source.name,
            "sha256": source_sha256,
            "width": source_width,
            "height": source_height,
        },
        "settings": {
            "background": {
                "model": spec.background.model.value,
                "sample_stride": spec.background.sample_stride,
                "selection_distance": spec.background.selection_distance,
                "fit_iterations": spec.background.fit_iterations,
            },
            "matting": {
                "core_distance": spec.matting.core_distance,
                "edge_distance": spec.matting.edge_distance,
                "edge_growth": spec.matting.edge_growth,
                "min_component_area": spec.matting.min_component_area,
            },
        },
        "background_fit": diagnostics.to_json(),
        "sprite_count": len(records),
        "warning_count": warning_count,
        "tight_crop": True,
        "sprites": [record.to_json() for record in records],
    }


def _safe_child(root: Path, filename: str) -> Path:
    candidate = root / filename
    if candidate.parent.resolve() != root.resolve() or candidate.name != filename:
        raise OutputError(f"unsafe output filename: {filename}")
    return candidate


def _write_json(path: Path, value: JsonObject) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def publish_staged_output(stage: Path, output: Path, overwrite: bool) -> None:
    if not output.exists():
        os.replace(stage, output)
        return
    if not overwrite:
        raise OutputError(f"output appeared during extraction: {output}; staged output was not published")

    backup = Path(tempfile.mkdtemp(prefix=".sprite-decompose-backup-", dir=output.parent))
    backup.rmdir()
    try:
        os.replace(output, backup)
        os.replace(stage, output)
    except BaseException:
        try:
            if not output.exists() and backup.exists():
                os.replace(backup, output)
        except OSError as restore_error:
            raise OutputError(
                f"replacement failed and the prior output could not be restored from {backup}"
            ) from restore_error
        raise
    shutil.rmtree(backup)


def verify_output(output: Path) -> int:
    output_input = output.expanduser().absolute()
    if output_input.is_symlink() or not output_input.is_dir():
        raise OutputError(f"output must be a regular directory: {output_input}")
    root = output_input.resolve()
    manifest_path = _safe_child(root, "manifest.json")
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise OutputError(f"missing regular manifest: {manifest_path}")
    try:
        raw: object = cast(object, json.loads(manifest_path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as error:
        raise OutputError(f"cannot parse manifest: {error}") from error
    try:
        manifest = validate_manifest(raw)
    except ManifestError as error:
        raise OutputError(f"invalid manifest: {error}") from error

    expected_files: list[str] = []
    for sprite in manifest.sprites:
        expected_files.append(sprite.filename)
        _verify_png(_safe_child(root, sprite.filename), sprite.size, sprite.sha256)

    expected_inventory = sorted(["manifest.json", *expected_files])
    actual_inventory = sorted(path.name for path in root.iterdir())
    if actual_inventory != expected_inventory:
        missing = sorted(set(expected_inventory) - set(actual_inventory))
        extra = sorted(set(actual_inventory) - set(expected_inventory))
        raise OutputError(f"output inventory differs from manifest; missing={missing}, extra={extra}")
    return len(manifest.sprites)


def _verify_png(path: Path, expected_size: tuple[int, int], expected_hash: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise OutputError(f"missing regular PNG: {path.name}")
    try:
        with Image.open(path) as image:
            if image.format != "PNG" or image.mode != "RGBA":
                raise OutputError(f"{path.name} must be an RGBA PNG")
            if image.size != expected_size:
                raise OutputError(f"{path.name} size {image.size} does not match manifest {expected_size}")
            rgba = np.asarray(image, dtype=np.uint8).copy()
    except (OSError, UnidentifiedImageError) as error:
        raise OutputError(f"cannot read {path.name}: {error}") from error
    alpha = rgba[..., 3]
    if alpha.size == 0 or not bool(np.any(alpha > 0)):
        raise OutputError(f"{path.name} contains no visible pixels")
    if bool(np.any(rgba[alpha == 0, :3] != 0)):
        raise OutputError(f"{path.name} contains nonzero RGB under fully transparent pixels")
    if not (
        bool(np.any(alpha[0, :] > 0))
        and bool(np.any(alpha[-1, :] > 0))
        and bool(np.any(alpha[:, 0] > 0))
        and bool(np.any(alpha[:, -1] > 0))
    ):
        raise OutputError(f"{path.name} has an empty transparent border")
    if image_sha256(path) != expected_hash:
        raise OutputError(f"{path.name} SHA-256 does not match the manifest")
def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if isinstance(args, ExtractArguments):
            records = extract(args)
            print(f"Extracted and verified {len(records)} sprites in {args.output.resolve()}")
        else:
            count = verify_output(args.output)
            print(f"Verified {count} sprites in {args.output.resolve()}")
    except (SpecError, ExtractionError, OutputError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

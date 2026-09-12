#!/usr/bin/env python3
"""Strict parser for the published sprite-decompose manifest contract."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast


SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
SAFE_NAME: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ManifestError(ValueError):
    """Raised when a manifest does not match the published schema."""


@dataclass(frozen=True, slots=True)
class ManifestSprite:
    filename: str
    size: tuple[int, int]
    sha256: str


@dataclass(frozen=True, slots=True)
class ManifestContract:
    sprites: tuple[ManifestSprite, ...]
    warning_count: int


@dataclass(frozen=True, slots=True)
class ManifestBounds:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


def validate_manifest(value: object) -> ManifestContract:
    """Parse every manifest field and return the file-verification contract."""

    root = _object(value, "manifest")
    _require_exact(
        root,
        {
            "schema_version",
            "tool",
            "source",
            "settings",
            "background_fit",
            "sprite_count",
            "warning_count",
            "tight_crop",
            "sprites",
        },
        "manifest",
    )
    if _integer(root.get("schema_version"), "schema_version") != 1:
        raise ManifestError("manifest schema_version must be 1")
    _validate_tool(root.get("tool"))
    source_width, source_height = _validate_source(root.get("source"))
    background_model = _validate_settings(root.get("settings"))
    _validate_background_fit(root.get("background_fit"), background_model)
    declared_count = _nonnegative_integer(root.get("sprite_count"), "sprite_count")
    declared_warnings = _nonnegative_integer(root.get("warning_count"), "warning_count")
    if root.get("tight_crop") is not True:
        raise ManifestError("manifest must declare tight_crop true")

    raw_sprites = _array(root.get("sprites"), "sprites")
    if declared_count != len(raw_sprites):
        raise ManifestError(
            f"manifest sprite_count is {declared_count}, but sprites contains {len(raw_sprites)} records"
        )
    sprites: list[ManifestSprite] = []
    warning_count = 0
    seen_filenames: set[str] = set()
    for index, raw_sprite in enumerate(raw_sprites, start=1):
        sprite, sprite_warnings = _validate_sprite(raw_sprite, index, source_width, source_height)
        if sprite.filename in seen_filenames:
            raise ManifestError(f"duplicate sprite filename in manifest: {sprite.filename}")
        seen_filenames.add(sprite.filename)
        sprites.append(sprite)
        warning_count += sprite_warnings
    if warning_count != declared_warnings:
        raise ManifestError(
            f"manifest warning_count is {declared_warnings}, but sprite warnings total {warning_count}"
        )
    return ManifestContract(tuple(sprites), warning_count)


def _validate_tool(value: object) -> None:
    tool = _object(value, "tool")
    _require_exact(tool, {"name", "version"}, "tool")
    if _string(tool.get("name"), "tool.name") != "sprite-decompose":
        raise ManifestError("tool.name must be sprite-decompose")
    if _string(tool.get("version"), "tool.version") != "1.0.0":
        raise ManifestError("tool.version must be 1.0.0")


def _validate_source(value: object) -> tuple[int, int]:
    source = _object(value, "source")
    _require_exact(source, {"filename", "sha256", "width", "height"}, "source")
    filename = _string(source.get("filename"), "source.filename")
    if not filename or Path(filename).name != filename:
        raise ManifestError("source.filename must be one safe basename")
    _sha256(source.get("sha256"), "source.sha256")
    width = _positive_integer(source.get("width"), "source.width")
    height = _positive_integer(source.get("height"), "source.height")
    return width, height


def _validate_settings(value: object) -> str:
    settings = _object(value, "settings")
    _require_exact(settings, {"background", "matting"}, "settings")
    background = _object(settings.get("background"), "settings.background")
    _require_exact(
        background,
        {"model", "sample_stride", "selection_distance", "fit_iterations"},
        "settings.background",
    )
    model = _string(background.get("model"), "settings.background.model")
    if model not in {"flat", "quadratic"}:
        raise ManifestError("settings.background.model must be flat or quadratic")
    _bounded_integer(background.get("sample_stride"), "settings.background.sample_stride", 1, 64)
    _bounded_number(
        background.get("selection_distance"),
        "settings.background.selection_distance",
        0.5,
        255.0,
    )
    _bounded_integer(background.get("fit_iterations"), "settings.background.fit_iterations", 1, 10)

    matting = _object(settings.get("matting"), "settings.matting")
    _require_exact(
        matting,
        {"core_distance", "edge_distance", "edge_growth", "min_component_area"},
        "settings.matting",
    )
    core = _bounded_number(matting.get("core_distance"), "settings.matting.core_distance", 0.0, 441.7)
    edge = _bounded_number(matting.get("edge_distance"), "settings.matting.edge_distance", 0.0, 441.7)
    if edge >= core:
        raise ManifestError("settings.matting distances must satisfy edge_distance < core_distance")
    _bounded_integer(matting.get("edge_growth"), "settings.matting.edge_growth", 0, 32)
    _bounded_integer(
        matting.get("min_component_area"),
        "settings.matting.min_component_area",
        1,
        1_000_000,
    )
    return model


def _validate_background_fit(value: object, expected_model: str) -> None:
    fit = _object(value, "background_fit")
    _require_exact(
        fit,
        {
            "model",
            "sampled_pixels",
            "inlier_pixels",
            "basis_rank",
            "dominant_rgb",
            "residual_rmse",
        },
        "background_fit",
    )
    if _string(fit.get("model"), "background_fit.model") != expected_model:
        raise ManifestError("background_fit.model must match settings.background.model")
    sampled = _positive_integer(fit.get("sampled_pixels"), "background_fit.sampled_pixels")
    inliers = _positive_integer(fit.get("inlier_pixels"), "background_fit.inlier_pixels")
    if inliers > sampled:
        raise ManifestError("background_fit.inlier_pixels cannot exceed sampled_pixels")
    expected_rank = 1 if expected_model == "flat" else 6
    if _integer(fit.get("basis_rank"), "background_fit.basis_rank") != expected_rank:
        raise ManifestError(f"background_fit.basis_rank must be {expected_rank} for {expected_model}")
    dominant = _array(fit.get("dominant_rgb"), "background_fit.dominant_rgb")
    if len(dominant) != 3:
        raise ManifestError("background_fit.dominant_rgb must contain three channels")
    for index, channel in enumerate(dominant):
        _bounded_integer(channel, f"background_fit.dominant_rgb[{index}]", 0, 255)
    _bounded_number(fit.get("residual_rmse"), "background_fit.residual_rmse", 0.0, 441.7)


def _validate_sprite(
    value: object,
    order: int,
    source_width: int,
    source_height: int,
) -> tuple[ManifestSprite, int]:
    label = f"sprites[{order - 1}]"
    sprite = _object(value, label)
    _require_exact(
        sprite,
        {
            "order",
            "requested_name",
            "filename",
            "source_bounds",
            "visible_source_bounds",
            "output_size",
            "grouping",
            "warnings",
            "sha256",
        },
        label,
    )
    if _integer(sprite.get("order"), f"{label}.order") != order:
        raise ManifestError(f"sprite ordering is unstable: expected order {order}")
    requested_name = _optional_string(sprite.get("requested_name"), f"{label}.requested_name")
    if requested_name is not None and not SAFE_NAME.fullmatch(requested_name):
        raise ManifestError(f"{label}.requested_name is not a safe slug")
    filename = _string(sprite.get("filename"), f"{label}.filename")
    expected_filename = f"{requested_name}.png" if requested_name is not None else f"sprite-{order:03d}.png"
    if filename != expected_filename:
        raise ManifestError(f"{label}.filename must be {expected_filename}")

    source_bounds = _bounds(sprite.get("source_bounds"), f"{label}.source_bounds")
    visible_bounds = _bounds(sprite.get("visible_source_bounds"), f"{label}.visible_source_bounds")
    if source_bounds.right > source_width or source_bounds.bottom > source_height:
        raise ManifestError(f"{label}.source_bounds exceeds source dimensions")
    if not (
        source_bounds.x <= visible_bounds.x
        and source_bounds.y <= visible_bounds.y
        and visible_bounds.right <= source_bounds.right
        and visible_bounds.bottom <= source_bounds.bottom
    ):
        raise ManifestError(f"{label}.visible_source_bounds must be inside source_bounds")

    output_size = _object(sprite.get("output_size"), f"{label}.output_size")
    _require_exact(output_size, {"width", "height"}, f"{label}.output_size")
    width = _positive_integer(output_size.get("width"), f"{label}.output_size.width")
    height = _positive_integer(output_size.get("height"), f"{label}.output_size.height")
    if (width, height) != (visible_bounds.width, visible_bounds.height):
        raise ManifestError(f"{label}.output_size must match visible_source_bounds")
    _validate_grouping(sprite.get("grouping"), label)
    warnings = _array(sprite.get("warnings"), f"{label}.warnings")
    for warning_index, warning in enumerate(warnings):
        if not _string(warning, f"{label}.warnings[{warning_index}]").strip():
            raise ManifestError(f"{label}.warnings[{warning_index}] must not be empty")
    digest = _sha256(sprite.get("sha256"), f"{label}.sha256")
    return ManifestSprite(filename, (width, height), digest), len(warnings)


def _validate_grouping(value: object, sprite_label: str) -> None:
    label = f"{sprite_label}.grouping"
    grouping = _object(value, label)
    _require_exact(
        grouping,
        {"decision", "component_policy", "kept_components", "discarded_components"},
        label,
    )
    if not _string(grouping.get("decision"), f"{label}.decision").strip():
        raise ManifestError(f"{label}.decision must not be empty")
    if _string(grouping.get("component_policy"), f"{label}.component_policy") not in {"all", "largest"}:
        raise ManifestError(f"{label}.component_policy must be all or largest")
    _positive_integer(grouping.get("kept_components"), f"{label}.kept_components")
    _nonnegative_integer(grouping.get("discarded_components"), f"{label}.discarded_components")


def _bounds(value: object, label: str) -> ManifestBounds:
    bounds = _object(value, label)
    _require_exact(bounds, {"x", "y", "width", "height"}, label)
    return ManifestBounds(
        _nonnegative_integer(bounds.get("x"), f"{label}.x"),
        _nonnegative_integer(bounds.get("y"), f"{label}.y"),
        _positive_integer(bounds.get("width"), f"{label}.width"),
        _positive_integer(bounds.get("height"), f"{label}.height"),
    )


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ManifestError(f"{label} must be a JSON object")
    result: dict[str, object] = {}
    for raw_key, raw_value in cast(dict[object, object], value).items():
        if not isinstance(raw_key, str):
            raise ManifestError(f"{label} contains a non-string key")
        result[raw_key] = raw_value
    return result


def _array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ManifestError(f"{label} must be a JSON array")
    return list(cast(list[object], value))


def _string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ManifestError(f"{label} must be a string")
    return value


def _optional_string(value: object, label: str) -> str | None:
    return None if value is None else _string(value, label)


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ManifestError(f"{label} must be an integer")
    return value


def _nonnegative_integer(value: object, label: str) -> int:
    result = _integer(value, label)
    if result < 0:
        raise ManifestError(f"{label} must be non-negative")
    return result


def _positive_integer(value: object, label: str) -> int:
    result = _integer(value, label)
    if result <= 0:
        raise ManifestError(f"{label} must be positive")
    return result


def _bounded_integer(value: object, label: str, minimum: int, maximum: int) -> int:
    result = _integer(value, label)
    if not minimum <= result <= maximum:
        raise ManifestError(f"{label} must be between {minimum} and {maximum}")
    return result


def _bounded_number(value: object, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ManifestError(f"{label} must be a number")
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ManifestError(f"{label} must be between {minimum} and {maximum}")
    return result


def _sha256(value: object, label: str) -> str:
    digest = _string(value, label)
    if not SHA256_PATTERN.fullmatch(digest):
        raise ManifestError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def _require_exact(value: dict[str, object], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(value))
    unexpected = sorted(set(value) - expected)
    if missing or unexpected:
        raise ManifestError(f"{label} fields differ; missing={missing}, unexpected={unexpected}")

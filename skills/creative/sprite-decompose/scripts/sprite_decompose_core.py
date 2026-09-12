#!/usr/bin/env python3
"""Typed domain model and deterministic raster operations for sprite extraction."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, TypeAlias, cast

import numpy as np
from numpy.typing import NDArray
from PIL import Image


FloatImage: TypeAlias = NDArray[np.float64]
BoolMask: TypeAlias = NDArray[np.bool_]
ByteImage: TypeAlias = NDArray[np.uint8]
JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

SCHEMA_VERSION: Final = 1
MANIFEST_SCHEMA_VERSION: Final = 1
SAFE_NAME: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SpecError(ValueError):
    """Raised when a region specification cannot be parsed safely."""


class ExtractionError(ValueError):
    """Raised when deterministic extraction cannot produce a valid sprite."""


class BackgroundModel(StrEnum):
    FLAT = "flat"
    QUADRATIC = "quadratic"


class ComponentPolicy(StrEnum):
    ALL = "all"
    LARGEST = "largest"


@dataclass(frozen=True, slots=True)
class Bounds:
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

    def to_json(self) -> JsonObject:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass(frozen=True, slots=True)
class BackgroundSettings:
    model: BackgroundModel = BackgroundModel.QUADRATIC
    sample_stride: int = 4
    selection_distance: float = 24.0
    fit_iterations: int = 3


@dataclass(frozen=True, slots=True)
class MattingSettings:
    core_distance: float = 18.0
    edge_distance: float = 5.0
    edge_growth: int = 3
    min_component_area: int = 3


@dataclass(frozen=True, slots=True)
class RegionSpec:
    bounds: Bounds
    grouping: str
    name: str | None = None
    component_policy: ComponentPolicy = ComponentPolicy.ALL
    min_component_area: int | None = None
    fill_holes: bool = False
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExtractionSpec:
    background: BackgroundSettings
    matting: MattingSettings
    regions: tuple[RegionSpec, ...]
    background_samples: tuple[Bounds, ...] = ()


@dataclass(frozen=True, slots=True)
class BackgroundDiagnostics:
    model: BackgroundModel
    sampled_pixels: int
    inlier_pixels: int
    basis_rank: int
    dominant_rgb: tuple[int, int, int]
    residual_rmse: float

    def to_json(self) -> JsonObject:
        return {
            "model": self.model.value,
            "sampled_pixels": self.sampled_pixels,
            "inlier_pixels": self.inlier_pixels,
            "basis_rank": self.basis_rank,
            "dominant_rgb": list(self.dominant_rgb),
            "residual_rmse": round(self.residual_rmse, 6),
        }


@dataclass(frozen=True, slots=True)
class SpritePixels:
    rgba: ByteImage
    visible_source_bounds: Bounds
    kept_components: int
    discarded_components: int
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SpriteRecord:
    order: int
    requested_name: str | None
    filename: str
    source_bounds: Bounds
    visible_source_bounds: Bounds
    width: int
    height: int
    grouping: str
    component_policy: ComponentPolicy
    kept_components: int
    discarded_components: int
    warnings: tuple[str, ...]
    sha256: str

    def to_json(self) -> JsonObject:
        return {
            "order": self.order,
            "requested_name": self.requested_name,
            "filename": self.filename,
            "source_bounds": self.source_bounds.to_json(),
            "visible_source_bounds": self.visible_source_bounds.to_json(),
            "output_size": {"width": self.width, "height": self.height},
            "grouping": {
                "decision": self.grouping,
                "component_policy": self.component_policy.value,
                "kept_components": self.kept_components,
                "discarded_components": self.discarded_components,
            },
            "warnings": list(self.warnings),
            "sha256": self.sha256,
        }


def load_spec(path: Path, image_width: int, image_height: int) -> ExtractionSpec:
    """Parse untrusted JSON into closed typed records and validate image bounds."""

    try:
        raw: object = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except OSError as error:
        raise SpecError(f"cannot read region specification {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise SpecError(f"region specification is not valid JSON: {error}") from error

    root = _object(raw, "root")
    _require_only(root, {"schema_version", "background", "matting", "background_samples", "regions"}, "root")
    version = _integer(root.get("schema_version"), "schema_version")
    if version != SCHEMA_VERSION:
        raise SpecError(f"schema_version must be {SCHEMA_VERSION}, got {version}")

    background = _parse_background(root.get("background", {}))
    matting = _parse_matting(root.get("matting", {}))
    sample_values = _array(root.get("background_samples", []), "background_samples")
    background_samples = tuple(
        _parse_bounds(value, f"background_samples[{index}]", image_width, image_height)
        for index, value in enumerate(sample_values)
    )

    region_values = _array(root.get("regions"), "regions")
    if not region_values:
        raise SpecError("regions must contain at least one region")
    regions = tuple(
        _parse_region(value, index, image_width, image_height)
        for index, value in enumerate(region_values)
    )
    requested_names = [region.name for region in regions if region.name is not None]
    duplicates = sorted({name for name in requested_names if requested_names.count(name) > 1})
    if duplicates:
        raise SpecError(f"region names must be unique: {', '.join(duplicates)}")
    filenames = [
        f"{region.name}.png" if region.name is not None else f"sprite-{index:03d}.png"
        for index, region in enumerate(regions, start=1)
    ]
    duplicate_filenames = sorted({name for name in filenames if filenames.count(name) > 1})
    if duplicate_filenames:
        raise SpecError(
            "region names collide with generated filenames: "
            + ", ".join(duplicate_filenames)
        )

    return ExtractionSpec(
        background=background,
        matting=matting,
        regions=regions,
        background_samples=background_samples,
    )


def _parse_background(value: object) -> BackgroundSettings:
    item = _object(value, "background")
    _require_only(item, {"model", "sample_stride", "selection_distance", "fit_iterations"}, "background")
    try:
        model = BackgroundModel(_string(item.get("model", BackgroundModel.QUADRATIC.value), "background.model"))
    except ValueError as error:
        raise SpecError("background.model must be 'flat' or 'quadratic'") from error
    sample_stride = _integer(item.get("sample_stride", 4), "background.sample_stride")
    selection_distance = _number(item.get("selection_distance", 24.0), "background.selection_distance")
    fit_iterations = _integer(item.get("fit_iterations", 3), "background.fit_iterations")
    if not 1 <= sample_stride <= 64:
        raise SpecError("background.sample_stride must be between 1 and 64")
    if not 0.5 <= selection_distance <= 255.0:
        raise SpecError("background.selection_distance must be between 0.5 and 255")
    if not 1 <= fit_iterations <= 10:
        raise SpecError("background.fit_iterations must be between 1 and 10")
    return BackgroundSettings(model, sample_stride, selection_distance, fit_iterations)


def _parse_matting(value: object) -> MattingSettings:
    item = _object(value, "matting")
    _require_only(item, {"core_distance", "edge_distance", "edge_growth", "min_component_area"}, "matting")
    core = _number(item.get("core_distance", 18.0), "matting.core_distance")
    edge = _number(item.get("edge_distance", 5.0), "matting.edge_distance")
    growth = _integer(item.get("edge_growth", 3), "matting.edge_growth")
    minimum = _integer(item.get("min_component_area", 3), "matting.min_component_area")
    if not 0.0 <= edge < core <= 441.7:
        raise SpecError("matting distances must satisfy 0 <= edge_distance < core_distance <= 441.7")
    if not 0 <= growth <= 32:
        raise SpecError("matting.edge_growth must be between 0 and 32")
    if not 1 <= minimum <= 1_000_000:
        raise SpecError("matting.min_component_area must be between 1 and 1000000")
    return MattingSettings(core, edge, growth, minimum)


def _parse_region(value: object, index: int, image_width: int, image_height: int) -> RegionSpec:
    label = f"regions[{index}]"
    item = _object(value, label)
    _require_only(
        item,
        {"bounds", "grouping", "name", "component_policy", "min_component_area", "fill_holes", "warnings"},
        label,
    )
    bounds = _parse_bounds(item.get("bounds"), f"{label}.bounds", image_width, image_height)
    grouping = _string(item.get("grouping"), f"{label}.grouping").strip()
    if not grouping:
        raise SpecError(f"{label}.grouping must not be empty")
    name_value = item.get("name")
    name = None if name_value is None else _string(name_value, f"{label}.name")
    if name is not None and not SAFE_NAME.fullmatch(name):
        raise SpecError(f"{label}.name must be a lowercase filename-safe slug")
    if name is not None and len(name) > 100:
        raise SpecError(f"{label}.name must be at most 100 characters")
    try:
        policy = ComponentPolicy(_string(item.get("component_policy", "all"), f"{label}.component_policy"))
    except ValueError as error:
        raise SpecError(f"{label}.component_policy must be 'all' or 'largest'") from error
    minimum_value = item.get("min_component_area")
    minimum = None if minimum_value is None else _integer(minimum_value, f"{label}.min_component_area")
    if minimum is not None and not 1 <= minimum <= bounds.width * bounds.height:
        raise SpecError(f"{label}.min_component_area must fit inside the region")
    fill_holes = _boolean(item.get("fill_holes", False), f"{label}.fill_holes")
    warning_values = _array(item.get("warnings", []), f"{label}.warnings")
    warnings = tuple(_string(warning, f"{label}.warnings[{warning_index}]") for warning_index, warning in enumerate(warning_values))
    return RegionSpec(bounds, grouping, name, policy, minimum, fill_holes, warnings)


def _parse_bounds(value: object, label: str, image_width: int, image_height: int) -> Bounds:
    item = _object(value, label)
    _require_only(item, {"x", "y", "width", "height"}, label)
    bounds = Bounds(
        x=_integer(item.get("x"), f"{label}.x"),
        y=_integer(item.get("y"), f"{label}.y"),
        width=_integer(item.get("width"), f"{label}.width"),
        height=_integer(item.get("height"), f"{label}.height"),
    )
    if bounds.x < 0 or bounds.y < 0 or bounds.width <= 0 or bounds.height <= 0:
        raise SpecError(f"{label} must have non-negative origin and positive size")
    if bounds.right > image_width or bounds.bottom > image_height:
        raise SpecError(
            f"{label} is out of bounds: {bounds.to_json()} exceeds {image_width}x{image_height}"
        )
    return bounds


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SpecError(f"{label} must be a JSON object")
    result: dict[str, object] = {}
    for raw_key, raw_value in cast(dict[object, object], value).items():
        if not isinstance(raw_key, str):
            raise SpecError(f"{label} contains a non-string key")
        result[raw_key] = raw_value
    return result


def _array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise SpecError(f"{label} must be a JSON array")
    return list(cast(list[object], value))


def _string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise SpecError(f"{label} must be a string")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SpecError(f"{label} must be an integer")
    return value


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise SpecError(f"{label} must be a finite number")
    return float(value)


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise SpecError(f"{label} must be a boolean")
    return value


def _require_only(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise SpecError(f"{label} contains unknown fields: {', '.join(unexpected)}")


def fit_background_surface(
    image: FloatImage,
    settings: BackgroundSettings,
    sample_bounds: Sequence[Bounds],
) -> tuple[FloatImage, BackgroundDiagnostics]:
    """Fit a flat or quadratic RGB surface to the dominant sampled background."""

    height, width, _ = image.shape
    sample_x, sample_y, sample_rgb = _collect_samples(image, settings.sample_stride, sample_bounds)
    if sample_rgb.shape[0] < 16:
        raise ExtractionError("background fitting needs at least 16 sampled pixels")

    quantized = np.floor_divide(sample_rgb.astype(np.uint16), 16).astype(np.uint8)
    _unique_bins, inverse, counts = np.unique(quantized, axis=0, return_inverse=True, return_counts=True)
    winning_index = int(np.argmax(counts))
    dominant_samples = sample_rgb[inverse == winning_index]
    dominant = np.median(dominant_samples, axis=0)
    inliers = np.linalg.norm(sample_rgb - dominant, axis=1) <= settings.selection_distance

    basis = _basis(sample_x / max(width - 1, 1), sample_y / max(height - 1, 1), settings.model)
    required_rank = basis.shape[1]
    coefficients = np.zeros((required_rank, 3), dtype=np.float64)
    rank = 0
    for _ in range(settings.fit_iterations):
        minimum_inliers = max(16, required_rank * 3)
        if int(np.count_nonzero(inliers)) < minimum_inliers:
            raise ExtractionError(
                "background fit found too few inliers; add clear background_samples or increase selection_distance"
            )
        coefficients, _, rank, _ = np.linalg.lstsq(basis[inliers], sample_rgb[inliers], rcond=None)
        prediction = basis @ coefficients
        residual = np.linalg.norm(sample_rgb - prediction, axis=1)
        next_inliers = residual <= settings.selection_distance
        if int(np.count_nonzero(next_inliers)) < minimum_inliers:
            raise ExtractionError(
                "background refit rejected too many samples; add clear background_samples or increase selection_distance"
            )
        if bool(np.array_equal(next_inliers, inliers)):
            inliers = next_inliers
            break
        inliers = next_inliers

    coefficients, _, rank, _ = np.linalg.lstsq(basis[inliers], sample_rgb[inliers], rcond=None)

    if rank < required_rank:
        raise ExtractionError(
            f"background samples have rank {rank}, need {required_rank}; spread samples across the image or use model 'flat'"
        )
    prediction = basis @ coefficients
    residual = np.linalg.norm(sample_rgb[inliers] - prediction[inliers], axis=1)
    mean_square = cast(np.float64, np.mean(np.square(residual)))
    rmse = math.sqrt(float(mean_square))

    full_y, full_x = np.mgrid[0:height, 0:width]
    full_basis = _basis(
        full_x.reshape(-1).astype(np.float64) / max(width - 1, 1),
        full_y.reshape(-1).astype(np.float64) / max(height - 1, 1),
        settings.model,
    )
    surface = np.clip(full_basis @ coefficients, 0.0, 255.0).reshape(height, width, 3)
    dominant_rgb = tuple(int(round(float(channel))) for channel in dominant)
    diagnostics = BackgroundDiagnostics(
        model=settings.model,
        sampled_pixels=int(sample_rgb.shape[0]),
        inlier_pixels=int(np.count_nonzero(inliers)),
        basis_rank=int(rank),
        dominant_rgb=cast(tuple[int, int, int], dominant_rgb),
        residual_rmse=rmse,
    )
    return surface, diagnostics


def _collect_samples(
    image: FloatImage,
    stride: int,
    sample_bounds: Sequence[Bounds],
) -> tuple[NDArray[np.float64], NDArray[np.float64], FloatImage]:
    if sample_bounds:
        x_parts: list[NDArray[np.float64]] = []
        y_parts: list[NDArray[np.float64]] = []
        rgb_parts: list[FloatImage] = []
        for bounds in sample_bounds:
            y_grid, x_grid = np.mgrid[bounds.y : bounds.bottom : stride, bounds.x : bounds.right : stride]
            x_parts.append(x_grid.reshape(-1).astype(np.float64))
            y_parts.append(y_grid.reshape(-1).astype(np.float64))
            rgb_parts.append(image[bounds.y : bounds.bottom : stride, bounds.x : bounds.right : stride].reshape(-1, 3))
        return np.concatenate(x_parts), np.concatenate(y_parts), np.concatenate(rgb_parts, axis=0)

    height, width, _ = image.shape
    y_grid, x_grid = np.mgrid[0:height:stride, 0:width:stride]
    return (
        x_grid.reshape(-1).astype(np.float64),
        y_grid.reshape(-1).astype(np.float64),
        image[::stride, ::stride].reshape(-1, 3),
    )


def _basis(
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    model: BackgroundModel,
) -> NDArray[np.float64]:
    if model is BackgroundModel.FLAT:
        return np.ones((x.shape[0], 1), dtype=np.float64)
    return np.column_stack((np.ones_like(x), x, y, x * x, y * y, x * y))


def extract_region(
    image: FloatImage,
    background: FloatImage,
    region: RegionSpec,
    settings: MattingSettings,
) -> SpritePixels:
    """Remove estimated background, feather alpha, and trim to nonzero alpha."""

    bounds = region.bounds
    crop = image[bounds.y : bounds.bottom, bounds.x : bounds.right]
    crop_background = background[bounds.y : bounds.bottom, bounds.x : bounds.right]
    distance = np.linalg.norm(crop - crop_background, axis=2)
    minimum_area = region.min_component_area or settings.min_component_area

    core_candidates = distance >= settings.core_distance
    core, kept, discarded = _select_components(core_candidates, region.component_policy, minimum_area)
    if region.fill_holes:
        core = _fill_enclosed_holes(core)
    if not bool(np.any(core)):
        label = region.name or "unnamed region"
        raise ExtractionError(f"no visible core pixels found for {label}; review bounds and matting distances")

    visible = core.copy()
    edge_candidates = distance > settings.edge_distance
    for _ in range(settings.edge_growth):
        visible |= _dilate(visible) & edge_candidates

    visible_y, visible_x = np.nonzero(visible)
    left = int(np.min(visible_x))
    right = int(np.max(visible_x)) + 1
    top = int(np.min(visible_y))
    bottom = int(np.max(visible_y)) + 1

    visible_crop = visible[top:bottom, left:right]
    core_crop = core[top:bottom, left:right]
    distance_crop = distance[top:bottom, left:right]
    rgb_crop = crop[top:bottom, left:right]
    background_rgb_crop = crop_background[top:bottom, left:right]

    alpha = np.zeros_like(distance_crop, dtype=np.float64)
    alpha[core_crop] = 1.0
    edge_alpha = np.clip(
        (distance_crop - settings.edge_distance) / (settings.core_distance - settings.edge_distance),
        0.0,
        1.0,
    )
    fringe = visible_crop & ~core_crop
    alpha[fringe] = edge_alpha[fringe]
    output_rgb = rgb_crop.copy()
    partial = (alpha > 0.0) & (alpha < 1.0)
    partial_alpha = alpha[partial, None]
    output_rgb[partial] = (
        rgb_crop[partial] - (1.0 - partial_alpha) * background_rgb_crop[partial]
    ) / partial_alpha
    output_rgb[alpha == 0.0] = 0.0
    output_rgb_bytes = np.rint(np.clip(output_rgb, 0.0, 255.0)).astype(np.uint8)
    alpha_bytes = np.rint(alpha * 255.0).astype(np.uint8)
    output_rgb_bytes[alpha_bytes == 0] = 0
    rgba = np.dstack((output_rgb_bytes, alpha_bytes))

    alpha_nonzero = rgba[..., 3] > 0
    alpha_y, alpha_x = np.nonzero(alpha_nonzero)
    if alpha_x.size == 0 or alpha_y.size == 0:
        raise ExtractionError("alpha feathering removed every visible pixel")
    alpha_left = int(np.min(alpha_x))
    alpha_right = int(np.max(alpha_x)) + 1
    alpha_top = int(np.min(alpha_y))
    alpha_bottom = int(np.max(alpha_y)) + 1
    trimmed = rgba[alpha_top:alpha_bottom, alpha_left:alpha_right]
    visible_bounds = Bounds(
        x=bounds.x + left + alpha_left,
        y=bounds.y + top + alpha_top,
        width=alpha_right - alpha_left,
        height=alpha_bottom - alpha_top,
    )

    warnings = list(region.warnings)
    if visible_bounds.x == bounds.x or visible_bounds.y == bounds.y or visible_bounds.right == bounds.right or visible_bounds.bottom == bounds.bottom:
        warnings.append("Visible pixels touch a region boundary; review whether the region clips the sprite.")
    if discarded:
        warnings.append(f"Discarded {discarded} core component(s) under the selected component policy.")
    return SpritePixels(trimmed, visible_bounds, kept, discarded, tuple(warnings))


def _select_components(
    mask: BoolMask,
    policy: ComponentPolicy,
    minimum_area: int,
) -> tuple[BoolMask, int, int]:
    components = _connected_components(mask)
    eligible = [component for component in components if len(component) >= minimum_area]
    too_small = len(components) - len(eligible)
    if not eligible:
        return np.zeros_like(mask), 0, too_small
    selected = eligible if policy is ComponentPolicy.ALL else [max(eligible, key=len)]
    discarded = too_small + len(eligible) - len(selected)
    output = np.zeros_like(mask)
    for component in selected:
        y_values, x_values = zip(*component, strict=True)
        output[np.asarray(y_values, dtype=np.intp), np.asarray(x_values, dtype=np.intp)] = True
    return output, len(selected), discarded


def _connected_components(mask: BoolMask) -> list[list[tuple[int, int]]]:
    height, width = mask.shape
    visited = np.zeros_like(mask)
    components: list[list[tuple[int, int]]] = []
    starts_y, starts_x = np.nonzero(mask)
    for raw_y, raw_x in zip(starts_y, starts_x, strict=True):
        start_y = int(raw_y)
        start_x = int(raw_x)
        if bool(visited[start_y, start_x]):
            continue
        queue: deque[tuple[int, int]] = deque([(start_y, start_x)])
        visited[start_y, start_x] = True
        component: list[tuple[int, int]] = []
        while queue:
            y, x = queue.popleft()
            component.append((y, x))
            for next_y in range(max(0, y - 1), min(height, y + 2)):
                for next_x in range(max(0, x - 1), min(width, x + 2)):
                    if bool(mask[next_y, next_x]) and not bool(visited[next_y, next_x]):
                        visited[next_y, next_x] = True
                        queue.append((next_y, next_x))
        components.append(component)
    return components


def _fill_enclosed_holes(mask: BoolMask) -> BoolMask:
    height, width = mask.shape
    outside = np.zeros_like(mask)
    queue: deque[tuple[int, int]] = deque()
    for x in range(width):
        queue.extend(((0, x), (height - 1, x)))
    for y in range(height):
        queue.extend(((y, 0), (y, width - 1)))
    while queue:
        y, x = queue.popleft()
        if bool(outside[y, x]) or bool(mask[y, x]):
            continue
        outside[y, x] = True
        for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= next_y < height and 0 <= next_x < width:
                queue.append((next_y, next_x))
    return mask | (~mask & ~outside)


def _dilate(mask: BoolMask) -> BoolMask:
    padded = np.pad(mask, 1, mode="constant", constant_values=False)
    height, width = mask.shape
    expanded = np.zeros_like(mask)
    for y_offset in range(3):
        for x_offset in range(3):
            expanded |= padded[y_offset : y_offset + height, x_offset : x_offset + width]
    return expanded


def image_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_rgba(path: Path, rgba: ByteImage) -> None:
    Image.fromarray(rgba, mode="RGBA").save(path, format="PNG", compress_level=9)

#!/usr/bin/env python3
"""Deterministic unit and integration tests for sprite decomposition."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from sprite_decompose import ExtractArguments, OutputError, extract, publish_staged_output, verify_output
from sprite_decompose_core import SpecError, load_spec


FloatImage = NDArray[np.float64]


class SpriteDecomposeTests(unittest.TestCase):
    def test_flat_background_uses_meaningful_and_numbered_names_in_stable_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-flat-") as temporary:
            root = Path(temporary)
            source = root / "flat.png"
            image = _background(96, 64, varying=False)
            _soft_circle(image, 24.0, 30.0, 14.0, (210.0, 45.0, 60.0), 1.5)
            _soft_circle(image, 70.0, 30.0, 12.0, (45.0, 100.0, 210.0), 1.5)
            _save_rgb(source, image)
            spec = root / "regions.json"
            _write_spec(
                spec,
                [
                    _region(5, 8, 38, 44, "single red token", name="red-token"),
                    _region(52, 8, 38, 44, "single unnamed blue token"),
                ],
                model="flat",
            )

            output = root / "output"
            records = extract(ExtractArguments(source, spec, output, False))

            self.assertEqual(["red-token.png", "sprite-002.png"], [record.filename for record in records])
            self.assertEqual(2, verify_output(output))
            manifest = _read_object(output / "manifest.json")
            self.assertEqual(2, _integer(manifest, "sprite_count"))
            self.assertTrue(_boolean(manifest, "tight_crop"))
            self.assertEqual("flat.png", _string(_object(manifest, "source"), "filename"))

    def test_quadratic_background_preserves_soft_edges_and_shadow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-varying-") as temporary:
            root = Path(temporary)
            source = root / "varying.png"
            image = _background(120, 84, varying=True)
            _soft_ellipse(image, 58.0, 60.0, 24.0, 7.0, (150.0, 130.0, 110.0), 4.0, opacity=0.35)
            _soft_circle(image, 58.0, 39.0, 20.0, (65.0, 155.0, 85.0), 2.5)
            _save_rgb(source, image)
            spec = root / "regions.json"
            _write_spec(spec, [_region(25, 12, 68, 60, "sprite with a deliberate soft shadow", name="soft-shadow")])

            output = root / "output"
            records = extract(ExtractArguments(source, spec, output, False))

            self.assertEqual(1, len(records))
            with Image.open(output / "soft-shadow.png") as sprite:
                rgba = np.asarray(sprite, dtype=np.uint8)
                alpha = rgba[..., 3]
                self.assertTrue(bool(np.any((alpha > 0) & (alpha < 255))))
                _assert_tightly_trimmed(self, alpha)
            bounds = records[0].visible_source_bounds
            with Image.open(source) as source_image:
                source_rgb = np.asarray(source_image.convert("RGB"), dtype=np.float64)[
                    bounds.y : bounds.bottom,
                    bounds.x : bounds.right,
                ]
            fitted_background = np.rint(_background(120, 84, varying=True))[
                bounds.y : bounds.bottom,
                bounds.x : bounds.right,
            ]
            partial = (alpha > 0) & (alpha < 255)
            source_distance = np.linalg.norm(source_rgb[partial] - fitted_background[partial], axis=1)
            output_distance = np.linalg.norm(rgba[partial, :3] - fitted_background[partial], axis=1)
            output_mean = cast(np.float64, np.mean(output_distance))
            source_mean = cast(np.float64, np.mean(source_distance))
            self.assertGreater(float(output_mean), float(source_mean))
            self.assertTrue(bool(np.all(rgba[alpha == 0, :3] == 0)))

    def test_tiny_detached_effect_is_retained_when_region_assigns_all_components(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-effect-") as temporary:
            root = Path(temporary)
            source = root / "effect.png"
            image = _background(80, 60, varying=False)
            _soft_circle(image, 28.0, 31.0, 12.0, (180.0, 70.0, 170.0), 1.0)
            image[14, 57] = (30.0, 90.0, 220.0)
            _save_rgb(source, image)
            spec = root / "regions.json"
            region = _region(8, 8, 58, 44, "main orb and its assigned detached spark", name="orb-spark")
            region["min_component_area"] = 1
            _write_spec(spec, [region], model="flat", minimum=3)

            output = root / "output"
            records = extract(ExtractArguments(source, spec, output, False))

            self.assertGreaterEqual(records[0].kept_components, 2)
            self.assertEqual(0, records[0].discarded_components)
            self.assertLessEqual(records[0].visible_source_bounds.y, 14)

    def test_touching_shapes_remain_one_logical_sprite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-touching-") as temporary:
            root = Path(temporary)
            source = root / "touching.png"
            image = _background(90, 60, varying=False)
            _soft_circle(image, 39.0, 30.0, 15.0, (230.0, 150.0, 35.0), 1.0)
            _soft_circle(image, 55.0, 30.0, 15.0, (120.0, 190.0, 45.0), 1.0)
            _save_rgb(source, image)
            spec = root / "regions.json"
            grouping = "two touching slices intentionally kept as one logical sprite"
            _write_spec(spec, [_region(16, 8, 62, 44, grouping, name="touching-pair")], model="flat")

            output = root / "output"
            records = extract(ExtractArguments(source, spec, output, False))

            self.assertEqual(1, len(records))
            self.assertEqual(grouping, records[0].grouping)
            self.assertTrue((output / "touching-pair.png").is_file())

    def test_fill_holes_preserves_reviewed_background_colored_interior_detail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-holes-") as temporary:
            root = Path(temporary)
            source = root / "holes.png"
            image = _background(64, 48, varying=False)
            y, x = np.mgrid[0:48, 0:64]
            distance = np.sqrt((x - 32.0) ** 2 + (y - 24.0) ** 2)
            image[(distance >= 8.0) & (distance <= 14.0)] = (55.0, 120.0, 210.0)
            _save_rgb(source, image)
            spec = root / "regions.json"
            hollow = _region(14, 6, 36, 36, "ring with a genuine transparent center", name="hollow")
            filled = _region(14, 6, 36, 36, "ring whose pale interior is reviewed artwork", name="filled")
            filled["fill_holes"] = True
            _write_spec(spec, [hollow, filled], model="flat")

            output = root / "output"
            extract(ExtractArguments(source, spec, output, False))

            with Image.open(output / "hollow.png") as hollow_sprite:
                hollow_alpha = np.asarray(hollow_sprite.getchannel("A"), dtype=np.uint8)
            with Image.open(output / "filled.png") as filled_sprite:
                filled_alpha = np.asarray(filled_sprite.getchannel("A"), dtype=np.uint8)
            self.assertEqual(0, int(hollow_alpha[hollow_alpha.shape[0] // 2, hollow_alpha.shape[1] // 2]))
            self.assertEqual(255, int(filled_alpha[filled_alpha.shape[0] // 2, filled_alpha.shape[1] // 2]))

    def test_every_output_has_no_empty_transparent_border(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-trim-") as temporary:
            root = Path(temporary)
            source, spec = _make_three_sprite_fixture(root)
            output = root / "output"

            extract(ExtractArguments(source, spec, output, False))

            for path in sorted(output.glob("*.png")):
                with self.subTest(filename=path.name), Image.open(path) as sprite:
                    self.assertEqual("RGBA", sprite.mode)
                    _assert_tightly_trimmed(self, np.asarray(sprite.getchannel("A"), dtype=np.uint8))

    def test_existing_output_is_refused_without_explicit_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-overwrite-") as temporary:
            root = Path(temporary)
            source, spec = _make_three_sprite_fixture(root)
            output = root / "output"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("original\n", encoding="utf-8")

            with self.assertRaisesRegex(OutputError, "output already exists"):
                extract(ExtractArguments(source, spec, output, False))
            self.assertEqual("original\n", sentinel.read_text(encoding="utf-8"))

            records = extract(ExtractArguments(source, spec, output, True))
            self.assertEqual(3, len(records))
            self.assertFalse(sentinel.exists())
            self.assertEqual(3, verify_output(output))

    def test_malformed_and_out_of_bounds_specs_fail_before_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-invalid-") as temporary:
            root = Path(temporary)
            source = root / "source.png"
            _save_rgb(source, _background(40, 30, varying=False))
            malformed = root / "malformed.json"
            malformed.write_text("{not-json", encoding="utf-8")
            out_of_bounds = root / "out-of-bounds.json"
            _write_spec(out_of_bounds, [_region(30, 10, 20, 10, "outside")], model="flat")

            with self.assertRaisesRegex(SpecError, "not valid JSON"):
                load_spec(malformed, 40, 30)
            with self.assertRaisesRegex(SpecError, "out of bounds"):
                load_spec(out_of_bounds, 40, 30)
            self.assertFalse((root / "output").exists())

    def test_manifest_records_bounds_grouping_hashes_warnings_and_stable_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-manifest-") as temporary:
            root = Path(temporary)
            source, spec = _make_three_sprite_fixture(root)
            output = root / "output"
            source_before = image_bytes(source)

            first_records = extract(ExtractArguments(source, spec, output, False))
            first_manifest = (output / "manifest.json").read_bytes()
            second_records = extract(ExtractArguments(source, spec, output, True))
            second_manifest = (output / "manifest.json").read_bytes()

            self.assertEqual([record.filename for record in first_records], [record.filename for record in second_records])
            self.assertEqual(first_manifest, second_manifest)
            manifest = _read_object(output / "manifest.json")
            sprites = _array(manifest, "sprites")
            self.assertEqual([1, 2, 3], [_integer(_as_object(item), "order") for item in sprites])
            first = _as_object(sprites[0])
            self.assertIn("source_bounds", first)
            self.assertIn("visible_source_bounds", first)
            self.assertIn("output_size", first)
            self.assertIn("grouping", first)
            self.assertEqual(64, len(_string(first, "sha256")))
            self.assertEqual(source_before, image_bytes(source))

    def test_named_region_cannot_collide_with_generated_filename(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-collision-") as temporary:
            root = Path(temporary)
            source = root / "source.png"
            _save_rgb(source, _background(40, 30, varying=False))
            spec = root / "regions.json"
            _write_spec(
                spec,
                [
                    _region(1, 1, 10, 10, "named collision", name="sprite-002"),
                    _region(20, 1, 10, 10, "unnamed collision"),
                ],
                model="flat",
            )

            with self.assertRaisesRegex(SpecError, "collide with generated filenames"):
                load_spec(spec, 40, 30)

    def test_verifier_rejects_undeclared_output_entries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-inventory-") as temporary:
            root = Path(temporary)
            source, spec = _make_three_sprite_fixture(root)
            output = root / "output"
            extract(ExtractArguments(source, spec, output, False))
            (output / "undeclared.txt").write_text("unexpected\n", encoding="utf-8")

            with self.assertRaisesRegex(OutputError, "output inventory differs"):
                verify_output(output)

    def test_output_cannot_contain_an_input(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-ancestor-") as temporary:
            root = Path(temporary)
            source, spec = _make_three_sprite_fixture(root)

            with self.assertRaisesRegex(OutputError, "contain either input"):
                extract(ExtractArguments(source, spec, root, True))

    def test_input_and_output_symlinks_are_rejected_without_touching_targets(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-symlinks-") as temporary:
            root = Path(temporary)
            source, spec = _make_three_sprite_fixture(root)
            source_link = root / "source-link.png"
            spec_link = root / "regions-link.json"
            source_link.symlink_to(source)
            spec_link.symlink_to(spec)
            with self.assertRaisesRegex(OutputError, "source must be a regular file"):
                extract(ExtractArguments(source_link, spec, root / "source-output", False))
            with self.assertRaisesRegex(OutputError, "region specification must be a regular file"):
                extract(ExtractArguments(source, spec_link, root / "spec-output", False))

            target = root / "target-output"
            target.mkdir()
            sentinel = target / "keep.txt"
            sentinel.write_text("untouched\n", encoding="utf-8")
            output_link = root / "output-link"
            output_link.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(OutputError, "never a file or symlink"):
                extract(ExtractArguments(source, spec, output_link, True))
            with self.assertRaisesRegex(OutputError, "regular directory"):
                verify_output(output_link)
            self.assertEqual("untouched\n", sentinel.read_text(encoding="utf-8"))

    def test_interrupted_overwrite_restores_the_previous_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-rollback-") as temporary:
            root = Path(temporary)
            output = root / "output"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("previous\n", encoding="utf-8")
            stage = root / "stage"
            stage.mkdir()
            (stage / "replacement.txt").write_text("new\n", encoding="utf-8")
            real_replace = os.replace

            def interrupt_stage_publish(source: Path, destination: Path) -> None:
                if Path(source) == output:
                    real_replace(source, destination)
                    raise KeyboardInterrupt
                real_replace(source, destination)

            with patch("sprite_decompose.os.replace", side_effect=interrupt_stage_publish):
                with self.assertRaises(KeyboardInterrupt):
                    publish_staged_output(stage, output, True)

            self.assertEqual("previous\n", sentinel.read_text(encoding="utf-8"))
            self.assertTrue(stage.is_dir())

    def test_verifier_rejects_corrupted_manifest_semantics(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-manifest-corruption-") as temporary:
            root = Path(temporary)
            source, spec = _make_three_sprite_fixture(root)
            output = root / "output"
            extract(ExtractArguments(source, spec, output, False))
            manifest_path = output / "manifest.json"
            manifest = _read_object(manifest_path)
            sprites = _array(manifest, "sprites")
            first = _as_object(sprites[0])
            grouping = _object(first, "grouping")
            grouping["decision"] = ""
            first["grouping"] = grouping
            sprites[0] = first
            manifest["sprites"] = sprites
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(OutputError, "decision must not be empty"):
                verify_output(output)

    def test_verifier_rejects_a_manifest_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sprite-decompose-verify-") as temporary:
            root = Path(temporary)
            source, spec = _make_three_sprite_fixture(root)
            output = root / "output"
            records = extract(ExtractArguments(source, spec, output, False))
            path = output / records[0].filename
            with Image.open(path) as sprite:
                changed = sprite.copy()
            changed.putpixel((0, 0), (1, 2, 3, 255))
            changed.save(path, format="PNG", compress_level=9)

            with self.assertRaisesRegex(OutputError, "SHA-256"):
                verify_output(output)


def _make_three_sprite_fixture(root: Path) -> tuple[Path, Path]:
    source = root / "fixture.png"
    image = _background(150, 90, varying=True)
    _soft_circle(image, 30.0, 40.0, 17.0, (210.0, 50.0, 70.0), 2.0)
    _soft_circle(image, 78.0, 38.0, 15.0, (55.0, 110.0, 220.0), 2.0)
    _soft_circle(image, 119.0, 39.0, 14.0, (60.0, 180.0, 90.0), 2.0)
    image[18, 136] = (220.0, 60.0, 190.0)
    _save_rgb(source, image)
    spec = root / "regions.json"
    third = _region(98, 10, 43, 52, "green token and detached glint", name="green-glint")
    third["min_component_area"] = 1
    _write_spec(
        spec,
        [
            _region(7, 14, 46, 50, "single red token", name="red-token"),
            _region(58, 12, 40, 50, "single unnamed blue token"),
            third,
        ],
    )
    return source, spec


def _background(width: int, height: int, *, varying: bool) -> FloatImage:
    y, x = np.mgrid[0:height, 0:width]
    if not varying:
        return np.broadcast_to(np.array((246.0, 241.0, 226.0)), (height, width, 3)).copy()
    normalized_x = x / max(width - 1, 1)
    normalized_y = y / max(height - 1, 1)
    red = 241.0 + 5.0 * normalized_x + 2.0 * normalized_y * normalized_y
    green = 236.0 + 3.0 * normalized_y + 1.5 * normalized_x * normalized_y
    blue = 222.0 + 4.0 * normalized_x * normalized_x + 2.0 * normalized_y
    return np.stack((red, green, blue), axis=-1).astype(np.float64)


def _soft_circle(
    image: FloatImage,
    center_x: float,
    center_y: float,
    radius: float,
    color: tuple[float, float, float],
    softness: float,
) -> None:
    _soft_ellipse(image, center_x, center_y, radius, radius, color, softness)


def _soft_ellipse(
    image: FloatImage,
    center_x: float,
    center_y: float,
    radius_x: float,
    radius_y: float,
    color: tuple[float, float, float],
    softness: float,
    *,
    opacity: float = 1.0,
) -> None:
    height, width, _ = image.shape
    y, x = np.mgrid[0:height, 0:width]
    normalized_distance = np.sqrt(((x - center_x) / radius_x) ** 2 + ((y - center_y) / radius_y) ** 2)
    normalized_softness = softness / max(radius_x, radius_y)
    coverage = np.clip((1.0 + normalized_softness - normalized_distance) / (2.0 * normalized_softness), 0.0, 1.0)
    coverage *= opacity
    target = np.asarray(color, dtype=np.float64)
    image[:] = image * (1.0 - coverage[..., None]) + target * coverage[..., None]


def _save_rgb(path: Path, image: FloatImage) -> None:
    Image.fromarray(np.rint(np.clip(image, 0.0, 255.0)).astype(np.uint8), mode="RGB").save(path, format="PNG")


def _region(
    x: int,
    y: int,
    width: int,
    height: int,
    grouping: str,
    *,
    name: str | None = None,
) -> dict[str, object]:
    region: dict[str, object] = {
        "bounds": {"x": x, "y": y, "width": width, "height": height},
        "grouping": grouping,
        "component_policy": "all",
    }
    if name is not None:
        region["name"] = name
    return region


def _write_spec(
    path: Path,
    regions: list[dict[str, object]],
    *,
    model: str = "quadratic",
    minimum: int = 2,
) -> None:
    value: dict[str, object] = {
        "schema_version": 1,
        "background": {
            "model": model,
            "sample_stride": 2,
            "selection_distance": 24.0,
            "fit_iterations": 3,
        },
        "matting": {
            "core_distance": 18.0,
            "edge_distance": 3.0,
            "edge_growth": 5,
            "min_component_area": minimum,
        },
        "regions": regions,
    }
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _assert_tightly_trimmed(test: unittest.TestCase, alpha: NDArray[np.uint8]) -> None:
    test.assertTrue(bool(np.any(alpha[0, :] > 0)))
    test.assertTrue(bool(np.any(alpha[-1, :] > 0)))
    test.assertTrue(bool(np.any(alpha[:, 0] > 0)))
    test.assertTrue(bool(np.any(alpha[:, -1] > 0)))


def _read_object(path: Path) -> dict[str, object]:
    raw: object = cast(object, json.loads(path.read_text(encoding="utf-8")))
    return _as_object(raw)


def _as_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AssertionError("expected JSON object")
    result: dict[str, object] = {}
    for key, item in cast(dict[object, object], value).items():
        if not isinstance(key, str):
            raise AssertionError("expected string JSON key")
        result[key] = item
    return result


def _object(value: dict[str, object], key: str) -> dict[str, object]:
    return _as_object(value[key])


def _array(value: dict[str, object], key: str) -> list[object]:
    item = value[key]
    if not isinstance(item, list):
        raise AssertionError(f"{key} is not an array")
    return list(cast(list[object], item))


def _string(value: dict[str, object], key: str) -> str:
    item = value[key]
    if not isinstance(item, str):
        raise AssertionError(f"{key} is not a string")
    return item


def _integer(value: dict[str, object], key: str) -> int:
    item = value[key]
    if isinstance(item, bool) or not isinstance(item, int):
        raise AssertionError(f"{key} is not an integer")
    return item


def _boolean(value: dict[str, object], key: str) -> bool:
    item = value[key]
    if not isinstance(item, bool):
        raise AssertionError(f"{key} is not a boolean")
    return item


def image_bytes(path: Path) -> bytes:
    return path.read_bytes()


if __name__ == "__main__":
    unittest.main()

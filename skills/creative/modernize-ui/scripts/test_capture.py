#!/usr/bin/env python3
"""capture.py against real Chromium: what a render records, and what the CLI rejects.

Everything loads over file://, so the tests need no network and no server.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from typing import Any, ClassVar

from PIL import Image

import capture

FIXTURE = Path(__file__).resolve().parents[1] / "evals/files/harbour-2020"
PHONE, LAPTOP = "320x568", "1366x768"

# Stands in for axe-core, which is an npm package the validation suite does not
# install. It reports the one rule the tests can count by reading the fixture:
# images without an alt attribute. The result has the shape axe.run() returns.
FAKE_AXE = """
window.axe = {
  run: async () => {
    const nodes = [...document.images]
      .filter((image) => !image.hasAttribute('alt'))
      .map((image) => ({ target: [`img[src="${image.getAttribute('src')}"]`] }));
    return {
      violations: nodes.length === 0 ? [] : [{
        id: 'image-alt',
        impact: 'critical',
        help: 'Images must have alternative text',
        tags: ['cat.text-alternatives', 'wcag2a', 'wcag111', 'section508'],
        nodes,
      }],
    };
  },
};
"""

# What capture.py wrote, read back as JSON.
Manifest = dict[str, Any]
Render = dict[str, Any]


def run_capture(
    work: Path, pages: list[dict[str, str]], *arguments: str
) -> tuple[int, Manifest | None, str]:
    """Run the CLI on Chromium; return its exit code, its manifest if written, and stderr."""
    pages_file = work / "pages.json"
    pages_file.write_text(json.dumps(pages), encoding="utf-8")
    out = work / "run"
    stderr = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
        code = capture.main(
            ["--pages", str(pages_file), "--out", str(out), "--browsers", "chromium", *arguments]
        )
    manifest_path = out / capture.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text("utf-8")) if manifest_path.is_file() else None
    return code, manifest, stderr.getvalue()


def renders(manifest: Manifest) -> dict[tuple[str, str], Render]:
    shots = manifest["shots"]
    assert isinstance(shots, list)
    return {(shot["page"], shot["viewport"]): shot for shot in shots}


def write_page(directory: Path, name: str, head: str = "", body: str = "<h1>Page</h1>") -> str:
    path = directory / name
    path.write_text(
        f'<!doctype html><html lang="en"><head><title>Page</title>{head}</head>'
        f'<body style="margin:0">{body}</body></html>',
        encoding="utf-8",
    )
    return path.as_uri()


class Harbour2020Renders(unittest.TestCase):
    """The dated fixture site, as a phone and as a laptop."""

    work: ClassVar[tempfile.TemporaryDirectory[str]]
    manifest: ClassVar[Manifest]
    shots: ClassVar[dict[tuple[str, str], Render]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.work.cleanup)
        work = Path(cls.work.name)
        (work / "axe.js").write_text(FAKE_AXE, encoding="utf-8")
        code, manifest, stderr = run_capture(
            work,
            [
                {"id": "home", "url": (FIXTURE / "index.html").as_uri()},
                {"id": "menu", "url": (FIXTURE / "menu.html").as_uri()},
            ],
            "--viewports", PHONE, LAPTOP,
            "--axe", str(work / "axe.js"),
        )  # fmt: skip
        assert code == 0 and manifest is not None, stderr
        cls.manifest = manifest
        cls.shots = renders(manifest)

    def test_fixed_width_hero_and_table_scroll_sideways_on_a_phone_only(self) -> None:
        # style.css: the hero slide has min-width 600px and the menu table 760px,
        # each inside a container with 15px of padding, in a 320px viewport.
        expected = {
            ("home", PHONE): 15 + 600 - 320,
            ("menu", PHONE): 15 + 760 - 320,
            ("home", LAPTOP): 0,
            ("menu", LAPTOP): 0,
        }
        measured = {key: shot["horizontal_overflow_px"] for key, shot in self.shots.items()}
        self.assertEqual(measured, expected)

    def test_screenshot_covers_the_whole_page_not_just_the_first_screen(self) -> None:
        for (page, viewport), shot in self.shots.items():
            with self.subTest(page=page, viewport=viewport):
                self.assertEqual(shot["screenshot"], f"{page}.chromium.{viewport}.png")
                with Image.open(Path(self.work.name) / "run" / str(shot["screenshot"])) as image:
                    self.assertEqual(image.format, "PNG")
                    self.assertEqual(image.height, shot["document_height"])
                self.assertGreater(shot["document_height"], int(viewport.split("x")[1]))

    def test_images_without_alt_text_are_counted_per_page(self) -> None:
        # index.html has the logo and three product photos without alt; menu.html only the logo.
        home, menu = self.shots[("home", LAPTOP)], self.shots[("menu", LAPTOP)]
        self.assertEqual(
            home["axe"],
            [
                {
                    "id": "image-alt",
                    "impact": "critical",
                    "help": "Images must have alternative text",
                    "wcag": ["wcag111", "wcag2a"],
                    "nodes": 4,
                    "targets": [
                        'img[src="img/logo.svg"]',
                        'img[src="img/bag-dark.svg"]',
                        'img[src="img/bag-light.svg"]',
                        'img[src="img/bag-mid.svg"]',
                    ],
                }
            ],
        )
        self.assertEqual([violation["nodes"] for violation in menu["axe"]], [1])
        self.assertIs(self.manifest["axe"], True)

    def test_run_of_the_real_site_is_not_marked_as_a_mockup(self) -> None:
        self.assertIs(self.manifest["mockup"], False)
        self.assertEqual(self.manifest["viewports"], [PHONE, LAPTOP])
        browsers = self.manifest["browsers"]
        assert isinstance(browsers, dict)
        self.assertRegex(browsers["chromium"], r"^\d+\.")

    def test_only_narrow_viewports_are_emulated_as_touch_devices(self) -> None:
        touch = {key: shot["touch_emulation"] for key, shot in self.shots.items()}
        self.assertEqual(
            touch,
            {("home", PHONE): True, ("menu", PHONE): True, ("home", LAPTOP): False, ("menu", LAPTOP): False},
        )  # fmt: skip


class ProposalOverlay(unittest.TestCase):
    def test_overlay_css_changes_the_render_and_marks_the_run_as_a_mockup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            overlay = work / "proposal.css"
            overlay.write_text(".jumbotron .slide { min-width: 0; }", encoding="utf-8")
            stylesheet = FIXTURE / "css/style.css"
            original = stylesheet.read_bytes()

            code, manifest, stderr = run_capture(
                work,
                [{"id": "home", "url": (FIXTURE / "index.html").as_uri()}],
                "--viewports", PHONE,
                "--overlay-css", str(overlay),
            )  # fmt: skip

            self.assertEqual(code, 0, stderr)
            assert manifest is not None
            self.assertIs(manifest["mockup"], True)
            # Without the overlay this render overflows by 295px (see Harbour2020Renders).
            self.assertEqual(renders(manifest)[("home", PHONE)]["horizontal_overflow_px"], 0)
            self.assertEqual(stylesheet.read_bytes(), original)


class PhoneViewportEmulation(unittest.TestCase):
    def test_page_without_a_viewport_tag_is_laid_out_zoomed_out_as_on_a_phone(self) -> None:
        # Mobile browsers lay a page with no viewport tag out on a 980px canvas.
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            code, manifest, stderr = run_capture(
                work,
                [
                    {"id": "untagged", "url": write_page(work, "untagged.html")},
                    {
                        "id": "tagged",
                        "url": write_page(
                            work,
                            "tagged.html",
                            head='<meta name="viewport" content="width=device-width, initial-scale=1">',
                        ),
                    },
                ],
                "--viewports", PHONE,
            )  # fmt: skip

            self.assertEqual(code, 0, stderr)
            assert manifest is not None
            widths = {page: shot["document_width"] for (page, _), shot in renders(manifest).items()}
            self.assertEqual(widths, {"untagged": 980, "tagged": 320})


class ProblemsOnThePage(unittest.TestCase):
    """One run over a page with defects, a state reached by script, and a page that is gone."""

    work: ClassVar[tempfile.TemporaryDirectory[str]]
    code: ClassVar[int]
    manifest: ClassVar[Manifest]
    stderr: ClassVar[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.work.cleanup)
        work = Path(cls.work.name)
        defective = write_page(
            work,
            "defective.html",
            body='<h1>Cart</h1><img src="missing.png" alt="">'
            '<script>throw new Error("cart is not defined")</script>',
        )
        code, manifest, cls.stderr = run_capture(
            work,
            [
                {"id": "defective", "url": defective},
                {"id": "gone", "url": (work / "gone.html").as_uri()},
                {
                    "id": "drawer-open",
                    "url": write_page(work, "plain.html"),
                    "prepare": "document.body.insertAdjacentHTML('beforeend', "
                    "'<div style=\"position:absolute;left:0;top:0;width:2000px;height:10px\"></div>')",
                },
            ],
            "--viewports", LAPTOP,
        )  # fmt: skip
        assert manifest is not None, cls.stderr
        cls.code, cls.manifest = code, manifest

    def test_script_errors_and_missing_files_are_recorded_with_the_file_named(self) -> None:
        shot = renders(self.manifest)[("defective", LAPTOP)]
        missing = (Path(self.work.name) / "missing.png").as_uri()
        self.assertIn("cart is not defined", shot["console_errors"])
        self.assertTrue(
            any(missing in error for error in shot["console_errors"]), shot["console_errors"]
        )
        self.assertEqual(shot["failed_requests"], [f"failed {missing}"])

    def test_prepare_script_runs_before_the_page_is_measured(self) -> None:
        shot = renders(self.manifest)[("drawer-open", LAPTOP)]
        self.assertEqual(shot["document_width"], 2000)
        self.assertEqual(shot["horizontal_overflow_px"], 2000 - 1366)
        self.assertEqual(shot["console_errors"], [])

    def test_page_that_cannot_load_is_reported_and_the_others_still_render(self) -> None:
        self.assertEqual(self.code, 1)
        self.assertEqual(sorted(page for page, _ in renders(self.manifest)), ["defective", "drawer-open"])
        failures = self.manifest["failures"]
        assert isinstance(failures, list)
        self.assertEqual(
            [(failure["page"], failure["browser"], failure["viewport"]) for failure in failures],
            [("gone", "chromium", LAPTOP)],
        )
        self.assertIn("ERR_FILE_NOT_FOUND", failures[0]["error"])
        self.assertIn("gone chromium 1366x768", self.stderr)

    def test_no_accessibility_results_are_claimed_when_no_scan_ran(self) -> None:
        self.assertIs(self.manifest["axe"], False)
        self.assertIsNone(renders(self.manifest)[("defective", LAPTOP)]["axe"])


class BrowserThatIsNotInstalled(unittest.TestCase):
    def test_every_render_it_owed_is_reported_and_the_other_browser_still_renders(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            pages = [
                {"id": "home", "url": write_page(work, "home.html")},
                {"id": "menu", "url": write_page(work, "menu.html")},
            ]
            # No machine has a Chromium build under this channel name, so the launch must fail.
            absent = {"absent": ("chromium", "no-such-channel")}
            with mock.patch.dict(capture.BROWSERS, absent):
                code, manifest, stderr = run_capture(
                    work, pages, "--browsers", "absent", "chromium", "--viewports", PHONE, LAPTOP
                )

        assert manifest is not None, stderr
        self.assertEqual(code, 1)
        self.assertIsNone(manifest["browsers"]["absent"])
        self.assertIsNotNone(manifest["browsers"]["chromium"])
        self.assertEqual(
            sorted(renders(manifest)),
            [("home", LAPTOP), ("home", PHONE), ("menu", LAPTOP), ("menu", PHONE)],
        )
        self.assertEqual(
            sorted((failure["page"], failure["viewport"]) for failure in manifest["failures"]),
            [("home", LAPTOP), ("home", PHONE), ("menu", LAPTOP), ("menu", PHONE)],
        )
        for failure in manifest["failures"]:
            self.assertEqual(failure["browser"], "absent")
            self.assertRegex(
                failure["error"],
                r"^absent did not launch \(\S.*\)\. "
                r"Install it with: python -m playwright install --with-deps no-such-channel$",
            )


class RejectedInput(unittest.TestCase):
    def assert_rejected(self, work: Path, pages: object, *arguments: str, mentions: str) -> None:
        pages_file = work / "pages.json"
        pages_file.write_text(json.dumps(pages), encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = capture.main(["--pages", str(pages_file), "--out", str(work / "run"), *arguments])
        self.assertEqual(code, 2, stderr.getvalue())
        self.assertIn(mentions, stderr.getvalue())
        self.assertFalse((work / "run").exists(), "a rejected run must not leave output behind")

    def test_pages_file_that_cannot_name_its_screenshots_or_be_loaded_is_rejected(self) -> None:
        home = {"id": "home", "url": "http://localhost:3000/"}
        cases: dict[str, tuple[object, str]] = {
            "no pages": ([], "non-empty JSON array"),
            "an object instead of a list": ({"home": "http://localhost:3000/"}, "non-empty JSON array"),
            "two pages share an id": ([home, {**home, "url": "http://localhost:3000/b"}], "repeats page ids: home"),
            "id would escape the output directory": ([{**home, "id": "../home"}], "id must be lowercase"),
            "url has no scheme": ([{**home, "url": "localhost:3000/"}], "url must start with"),
            "misspelt key": ([{**home, "prepair": "1"}], "unknown keys: prepair"),
        }  # fmt: skip
        for name, (pages, mentions) in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                self.assert_rejected(Path(tmp), pages, mentions=mentions)

    def test_malformed_viewport_or_missing_option_file_is_rejected(self) -> None:
        home = [{"id": "home", "url": "http://localhost:3000/"}]
        cases: dict[str, tuple[tuple[str, ...], str]] = {
            "width only": (("--viewports", "390"), "must look like 390x844"),
            "device name": (("--viewports", "iphone"), "must look like 390x844"),
            "axe file missing": (("--axe", "/nonexistent/axe.min.js"), "--axe"),
            "overlay missing": (("--overlay-css", "/nonexistent/new.css"), "--overlay-css"),
            "storage state missing": (("--storage-state", "/nonexistent/state.json"), "Storage state"),
        }  # fmt: skip
        for name, (arguments, mentions) in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                self.assert_rejected(Path(tmp), home, *arguments, mentions=mentions)


if __name__ == "__main__":
    unittest.main()

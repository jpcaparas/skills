#!/usr/bin/env python3
"""build_catalogue.py: how two capture runs are compared and what the page says about them.

The runs are written by hand in the manifest shape capture.py produces, so no browser starts.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

import build_catalogue
from build_catalogue import compare_page, default_selection, load_run, summarise

LAPTOP, PHONE = "1366x768", "320x568"
FAVICON_404 = "Failed to load resource: 404 (http://localhost:3000/favicon.ico)"
RULE_HELP = {
    "image-alt": "Images must have alternative text",
    "color-contrast": "Elements must meet minimum color contrast ratio thresholds",
    "label": "Form elements must have labels",
}

Entry = dict[str, object]


def violation(rule: str, nodes: int, wcag: tuple[str, ...] = ()) -> Entry:
    return {
        "id": rule,
        "impact": "serious",
        "help": RULE_HELP[rule],
        "wcag": list(wcag),
        "nodes": nodes,
        "targets": [],
    }


def shot(
    page: str,
    viewport: str = LAPTOP,
    browser: str = "chromium",
    *,
    overflow: int = 0,
    axe: tuple[Entry, ...] | None = (),
    console_errors: tuple[str, ...] = (),
    failed_requests: tuple[str, ...] = (),
) -> Entry:
    return {
        "page": page,
        "url": f"http://localhost:3000/{page}",
        "browser": browser,
        "viewport": viewport,
        "touch_emulation": False,
        "screenshot": f"{page}.{browser}.{viewport}.png",
        "document_width": 1366,
        "document_height": 2400,
        "horizontal_overflow_px": overflow,
        "console_errors": list(console_errors),
        "failed_requests": list(failed_requests),
        "axe": None if axe is None else list(axe),
        "metrics": {"lcp_ms": 240.0, "cls": 0.0, "dom_nodes": 180, "requests": 6, "transfer_bytes": 14_000},
    }  # fmt: skip


def write_run(
    directory: Path,
    shots: list[Entry],
    *,
    mockup: bool = False,
    failures: tuple[Entry, ...] = (),
    viewports: tuple[str, ...] | None = None,
    browsers: dict[str, str | None] | None = None,
    origin: str = "http://localhost:3000",
) -> Path:
    """Write a capture.py run: a manifest and a file for each screenshot it names."""
    directory.mkdir(parents=True)
    rendered = [*shots, *failures]
    pages = dict.fromkeys(str(entry["page"]) for entry in rendered)
    manifest = {
        "captured_at": "2026-11-10T09:00:00+00:00",
        "mockup": mockup,
        "color_scheme": "light",
        "reduced_motion": False,
        "axe": all(entry["axe"] is not None for entry in shots),
        "browsers": browsers or {str(entry["browser"]): "151.0" for entry in rendered},
        "viewports": list(viewports or dict.fromkeys(str(entry["viewport"]) for entry in rendered)),
        "pages": [
            {"id": page, "url": f"{origin}/{page}", "prepare": None} for page in pages
        ],
        "shots": shots,
        "failures": list(failures),
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for entry in shots:
        (directory / str(entry["screenshot"])).write_bytes(b"\x89PNG\r\n\x1a\n")
    return directory


def run_cli(*arguments: object) -> tuple[int, str]:
    stderr = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
        code = build_catalogue.main([str(argument) for argument in arguments])
    return code, stderr.getvalue()


def a_change(**overrides: object) -> Entry:
    return {
        "id": "A1",
        "title": "Give every image alt text",
        "category": "accessibility",
        "pages": ["home"],
        "why": "Four images have none.",
        "change": "Describe the product photos; mark the logo decorative.",
        "risk": "low",
        **overrides,
    }


def a_plan(**overrides: object) -> Entry:
    return {
        "project": "Harbour Coffee",
        "mode": "refresh",
        "summary": "Same palette, repaired layout.",
        "changes": [a_change()],
        "out_of_scope": ["Prices and copy"],
        **overrides,
    }


class TemporaryDirectoryTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)


class ComparingAPageAcrossTwoRuns(TemporaryDirectoryTest):
    def compare(
        self,
        before: list[Entry],
        after: list[Entry],
        after_failures: tuple[Entry, ...] = (),
        page: str = "home",
    ) -> build_catalogue.PageComparison:
        return compare_page(
            page,
            load_run(write_run(self.tmp / "before", before)),
            load_run(write_run(self.tmp / "after", after, failures=after_failures)),
        )

    def test_each_failing_rule_is_fixed_still_failing_or_introduced(self) -> None:
        comparison = self.compare(
            before=[
                shot("home", PHONE, axe=(violation("image-alt", 2), violation("color-contrast", 19))),
                shot("home", LAPTOP, axe=(violation("image-alt", 4),)),
            ],
            after=[
                shot("home", PHONE, axe=(violation("color-contrast", 3),)),
                shot("home", LAPTOP, axe=(violation("label", 1),)),
            ],
        )  # fmt: skip

        # A rule is reported once per page, with its worst count across the renders.
        self.assertEqual([(v.id, v.nodes) for v in comparison.fixed], [("image-alt", 4)])
        self.assertEqual([(v.id, v.nodes) for v in comparison.remaining], [("color-contrast", 3)])
        self.assertEqual([(v.id, v.nodes) for v in comparison.introduced], [("label", 1)])
        self.assertEqual(
            comparison.regressions,
            ("New accessibility failure: label (Form elements must have labels)",),
        )

    def test_overflow_counts_against_the_change_only_where_the_page_fitted_before(self) -> None:
        comparison = self.compare(
            before=[shot("home", PHONE, overflow=295), shot("home", LAPTOP)],
            after=[shot("home", PHONE, overflow=12), shot("home", LAPTOP, overflow=40)],
        )

        self.assertEqual(
            comparison.regressions, ("New horizontal overflow of 40px in chromium at 1366x768",)
        )
        # What is left of the old overflow is still shown to the reader.
        self.assertEqual(
            comparison.overflow_after, ("chromium at 1366x768: 40px", "chromium at 320x568: 12px")
        )
        self.assertEqual(comparison.overflow_before, ("chromium at 320x568: 295px",))

    def test_errors_the_site_already_had_are_not_blamed_on_the_change(self) -> None:
        comparison = self.compare(
            before=[shot("home", console_errors=(FAVICON_404,), failed_requests=("404 /old.js",))],
            after=[
                shot(
                    "home",
                    console_errors=(FAVICON_404, "cart is not defined"),
                    failed_requests=("404 /old.js", "404 /fonts/inter.woff2"),
                )
            ],
        )

        self.assertEqual(
            comparison.regressions,
            ("New console error: cart is not defined", "New failed request: 404 /fonts/inter.woff2"),
        )  # fmt: skip

    def test_resource_already_missing_is_not_new_when_the_proposal_is_served_elsewhere(self) -> None:
        site, proposal = "http://localhost:3000", "http://localhost:8102"
        before = write_run(
            self.tmp / "before",
            [
                shot(
                    "home",
                    console_errors=(f"Failed to load resource: 404 ({site}/favicon.ico)",),
                    failed_requests=(f"404 {site}/favicon.ico", "404 https://cdn.example/a.js"),
                )
            ],
            origin=site,
        )
        after = write_run(
            self.tmp / "after",
            [
                shot(
                    "home",
                    console_errors=(f"Failed to load resource: 404 ({proposal}/favicon.ico)",),
                    failed_requests=(
                        f"404 {proposal}/favicon.ico",
                        f"404 {proposal}/fonts/inter.woff2",
                        "404 https://cdn.example/b.js",
                    ),
                )
            ],
            origin=proposal,
        )

        comparison = compare_page("home", load_run(before), load_run(after))

        self.assertEqual(
            comparison.regressions,
            (
                f"New failed request: 404 {proposal}/fonts/inter.woff2",
                "New failed request: 404 https://cdn.example/b.js",
            ),
        )

    def test_render_the_second_run_lacks_is_reported_once_with_its_cause(self) -> None:
        before = [
            shot("home", browser="chromium"),
            shot("home", browser="firefox"),
            shot("home", browser="webkit"),
        ]
        webkit_timeout: Entry = {
            "page": "home",
            "browser": "webkit",
            "viewport": LAPTOP,
            "error": "Timeout 30000ms exceeded",
        }

        comparison = self.compare(
            before, after=[shot("home", browser="chromium")], after_failures=(webkit_timeout,)
        )

        self.assertEqual(
            comparison.regressions,
            (
                "Render failed in webkit at 1366x768: Timeout 30000ms exceeded",
                "Not rendered after: firefox at 1366x768",
            ),
        )

    def test_page_that_exists_only_in_the_proposal_has_nothing_to_be_worse_than(self) -> None:
        comparison = self.compare(
            before=[shot("home")],
            after=[shot("home"), shot("pricing", overflow=30, axe=(violation("label", 2),))],
            page="pricing",
        )

        self.assertFalse(comparison.compared)
        self.assertEqual(comparison.regressions, ())
        self.assertEqual(comparison.introduced, ())
        self.assertEqual([(v.id, v.nodes) for v in comparison.remaining], [("label", 2)])

    def test_axe_tags_become_wcag_success_criteria(self) -> None:
        # axe tags a rule with its conformance level and its criteria; only the latter are numbers.
        tags = ("wcag2aa", "wcag21aa", "wcag1410", "wcag143", "cat.color")
        run = load_run(
            write_run(self.tmp / "run", [shot("home", axe=(violation("color-contrast", 1, tags),))])
        )

        assert run.shots[0].axe is not None
        self.assertEqual(run.shots[0].axe[0].criteria, ("1.4.10", "1.4.3"))


class MeasuredSummary(TemporaryDirectoryTest):
    def rows(self, before: Path, after: Path | None = None) -> dict[str, tuple[str, str | None]]:
        return {
            row.measure: (row.before, row.after)
            for row in summarise(load_run(before), load_run(after) if after else None)
        }

    def test_rule_and_element_counts_add_up_over_pages_not_over_renders(self) -> None:
        before = write_run(
            self.tmp / "before",
            [
                shot("home", PHONE, overflow=295, axe=(violation("image-alt", 4), violation("color-contrast", 19))),
                shot("home", LAPTOP, axe=(violation("image-alt", 4), violation("color-contrast", 12))),
                shot("menu", LAPTOP, axe=(violation("color-contrast", 22),)),
            ],
        )  # fmt: skip
        after = write_run(self.tmp / "after", [shot("home", PHONE), shot("home", LAPTOP), shot("menu", LAPTOP)])  # fmt: skip

        rows = self.rows(before, after)

        # home fails 2 rules (4 + 19 elements at worst), menu 1 rule (22 elements).
        self.assertEqual(rows["Failing accessibility rules, summed over pages"], ("3", "0"))
        self.assertEqual(rows["Elements failing those rules"], ("45", "0"))
        self.assertEqual(rows["Renders that scroll sideways"], ("1 of 3", "0 of 3"))

    def test_run_without_a_scan_does_not_read_as_zero_failures(self) -> None:
        rows = self.rows(write_run(self.tmp / "audit", [shot("home", axe=None)]))

        self.assertEqual(rows["Failing accessibility rules, summed over pages"], ("not scanned", None))
        self.assertEqual(rows["Elements failing those rules"], ("not scanned", None))


class FirstViewOfTheRenders(TemporaryDirectoryTest):
    def selection(self, viewports: tuple[str, ...], browsers: dict[str, str | None]) -> tuple[str, str]:
        run = write_run(self.tmp / "run", [shot("home")], viewports=viewports, browsers=browsers)
        return default_selection(load_run(run))

    def test_opens_on_the_widest_laptop_sized_render_in_a_browser_that_launched(self) -> None:
        self.assertEqual(
            self.selection(
                (PHONE, "1440x900", "1441x900", "1920x1080"),
                {"msedge": None, "firefox": "153.0", "webkit": "26.5"},
            ),
            ("firefox", "1440x900"),
        )

    def test_opens_on_the_narrowest_render_when_every_viewport_is_a_large_desktop(self) -> None:
        self.assertEqual(
            self.selection(("2560x1440", "1920x1080"), {"chromium": "151.0"}),
            ("chromium", "1920x1080"),
        )


class CataloguePage(TemporaryDirectoryTest):
    def setUp(self) -> None:
        super().setUp()
        self.before = write_run(
            self.tmp / "before",
            [shot("home", PHONE, overflow=295, axe=(violation("image-alt", 4, ("wcag111",)),)), shot("home", LAPTOP)],
        )  # fmt: skip
        self.out = self.tmp / "catalogue"

    def proposal(self, *, mockup: bool, shots: list[Entry] | None = None) -> Path:
        return write_run(
            self.tmp / "after", shots or [shot("home", PHONE), shot("home", LAPTOP)], mockup=mockup
        )

    def plan(self, **overrides: object) -> Path:
        path = self.tmp / "plan.json"
        path.write_text(json.dumps(a_plan(**overrides)), encoding="utf-8")
        return path

    def page(self) -> str:
        return (self.out / "index.html").read_text(encoding="utf-8")

    def test_every_render_the_page_offers_is_a_file_inside_the_catalogue(self) -> None:
        code, stderr = run_cli(
            "--before", self.before, "--after", self.proposal(mockup=True), "--out", self.out
        )
        self.assertEqual(code, 0, stderr)

        embedded = re.search(r'<script type="application/json" id="renders">(.*?)</script>', self.page(), re.S)
        assert embedded is not None
        self.assertEqual(
            json.loads(embedded.group(1)),
            {
                side: {
                    "home": {
                        f"chromium|{PHONE}": f"{side}/home.chromium.{PHONE}.png",
                        f"chromium|{LAPTOP}": f"{side}/home.chromium.{LAPTOP}.png",
                    }
                }
                for side in ("before", "after")
            },
        )
        copied = sorted(path.relative_to(self.out).as_posix() for path in self.out.rglob("*.png"))
        self.assertEqual(
            copied,
            [f"{side}/home.chromium.{viewport}.png" for side in ("after", "before") for viewport in (LAPTOP, PHONE)],
        )  # fmt: skip

    def test_proposal_is_labelled_a_dry_run_and_finished_work_a_result(self) -> None:
        cases = {
            True: ("Dry run: nothing in the project has changed", "Planned changes (1)", "After (dry run)"),
            False: ("Result", "Changes made (1)", "After"),
        }  # fmt: skip
        for mockup, (kind, heading, label) in cases.items():
            with self.subTest(mockup=mockup):
                out = self.tmp / f"catalogue-{mockup}"
                after = write_run(self.tmp / f"after-{mockup}", [shot("home", PHONE), shot("home", LAPTOP)], mockup=mockup)  # fmt: skip
                code, stderr = run_cli("--before", self.before, "--after", after, "--plan", self.plan(), "--out", out)  # fmt: skip
                self.assertEqual(code, 0, stderr)
                page = (out / "index.html").read_text(encoding="utf-8")

                self.assertIn(f'<span class="kind">{kind}</span>', page)
                self.assertIn(f"<h2>{heading}</h2>", page)
                self.assertIn(f"<span>{label}</span>", page)
                self.assertEqual("Dry run" in page, mockup)
                self.assertIn("Fixed: Images must have alternative text (<code>image-alt</code>, WCAG 1.1.1, 4 elements, serious)", page)  # fmt: skip

    def test_audit_of_one_run_shows_the_site_as_it_is_and_no_after_column(self) -> None:
        code, stderr = run_cli("--before", self.before, "--plan", self.plan(), "--out", self.out)
        self.assertEqual(code, 0, stderr)
        page = self.page()

        self.assertIn('<span class="kind">Current state</span>', page)
        self.assertIn("<h2>Recommended changes (1)</h2>", page)
        self.assertIn("Failing: Images must have alternative text", page)
        self.assertIn("Scrolls sideways now: chromium at 320x568: 295px", page)
        self.assertNotIn('data-side="after"', page)
        self.assertNotIn("Fixed:", page)
        self.assertFalse((self.out / "after").exists())

    def test_changes_are_grouped_by_category_and_site_wide_ones_say_so(self) -> None:
        plan = self.plan(
            changes=[
                a_change(
                    id="C1",
                    category="compatibility",
                    pages=[],
                    title="Load the dialog polyfill only where <dialog> is missing",
                ),
                a_change(id="A1"),
                a_change(id="A2", title="Label the newsletter field"),
            ]
        )

        code, stderr = run_cli("--before", self.before, "--plan", plan, "--out", self.out)
        self.assertEqual(code, 0, stderr)
        page = self.page()

        self.assertEqual(
            re.findall(r'<section class="category"><h3>(.*?)</h3>', page),
            ["Accessibility (2)", "Compatibility (1)"],
        )
        self.assertIn("<h3>Load the dialog polyfill only where &lt;dialog&gt; is missing</h3>", page)
        self.assertIn("<dt>Pages</dt><dd>All pages</dd>", page)
        self.assertEqual(page.count("<dt>Pages</dt><dd>home</dd>"), 2)

    def test_text_from_the_plan_and_the_site_cannot_inject_markup(self) -> None:
        payload = '<img src=x onerror="alert(1)">'
        after = self.proposal(
            mockup=True,
            shots=[shot("home", PHONE, console_errors=(payload,)), shot("home", LAPTOP)],
        )
        plan = self.plan(project=payload, summary=payload, out_of_scope=[payload])

        code, stderr = run_cli("--before", self.before, "--after", after, "--plan", plan, "--out", self.out)  # fmt: skip
        self.assertEqual(code, 0, stderr)

        self.assertNotIn(payload, self.page())
        self.assertIn("New console error: &lt;img src=x onerror=&quot;alert(1)&quot;&gt;", self.page())

    def test_worse_proposal_is_flagged_on_the_page_and_fails_only_when_asked_to(self) -> None:
        worse = self.proposal(mockup=True, shots=[shot("home", PHONE), shot("home", LAPTOP, overflow=40)])  # fmt: skip
        regression = "New horizontal overflow of 40px in chromium at 1366x768"

        code, stderr = run_cli("--before", self.before, "--after", worse, "--out", self.out)
        self.assertEqual(code, 0)
        self.assertIn(f"home: {regression}", stderr)
        self.assertIn(f"<h2>Worse than before</h2><ul><li><strong>home</strong>: {regression}</li>", self.page())  # fmt: skip

        code, _ = run_cli("--before", self.before, "--after", worse, "--out", self.out, "--fail-on-regression")  # fmt: skip
        self.assertEqual(code, 1)

    def test_proposal_that_only_improves_passes_the_regression_gate(self) -> None:
        code, stderr = run_cli(
            "--before", self.before, "--after", self.proposal(mockup=True),
            "--out", self.out, "--fail-on-regression",
        )  # fmt: skip

        self.assertEqual((code, stderr), (0, ""))
        self.assertNotIn("Worse than before", self.page())


class RejectedInput(TemporaryDirectoryTest):
    def setUp(self) -> None:
        super().setUp()
        self.before = write_run(self.tmp / "before", [shot("home")])
        self.out = self.tmp / "catalogue"

    def assert_rejected(self, *arguments: object, mentions: str) -> None:
        code, stderr = run_cli(*arguments, "--out", self.out)
        self.assertEqual(code, 2, stderr)
        self.assertIn(mentions, stderr)
        self.assertFalse(self.out.exists(), "a rejected build must not leave a catalogue behind")

    def test_runs_that_cannot_be_compared_fairly_are_rejected(self) -> None:
        # Scanned against unscanned would report every failure as fixed.
        unscanned = write_run(self.tmp / "unscanned", [shot("home", axe=None)])
        self.assert_rejected("--before", self.before, "--after", unscanned, mentions="without --axe")

        not_a_run = self.tmp / "screenshots"
        not_a_run.mkdir()
        self.assert_rejected("--before", not_a_run, mentions="has no manifest.json")

        incomplete = write_run(self.tmp / "incomplete", [shot("home")])
        (incomplete / f"home.chromium.{LAPTOP}.png").unlink()
        self.assert_rejected("--before", incomplete, mentions="is missing")

    def test_plan_the_reader_could_not_approve_item_by_item_is_rejected(self) -> None:
        without_a_reason = {key: value for key, value in a_change().items() if key != "why"}
        cases: dict[str, tuple[Entry, str]] = {
            "unknown mode": (a_plan(mode="facelift"), "'mode' must be one of preserve, refresh, reimagine"),
            "no changes": (a_plan(changes=[]), "nothing to approve"),
            "two changes share an id": (a_plan(changes=[a_change(), a_change()]), "change ids repeat: A1"),
            "id is a sentence": (a_plan(changes=[a_change(id="fix the images")]), "short label such as A1"),
            "page that was never captured": (a_plan(changes=[a_change(pages=["checkout"])]), "checkout were not captured"),
            "risky change without saying what could break": (a_plan(changes=[a_change(risk="high")]), "needs 'risk_note'"),
            "unknown category": (a_plan(changes=[a_change(category="vibes")]), "'category' must be one of"),
            "unknown risk": (a_plan(changes=[a_change(risk="spicy")]), "'risk' must be one of low, medium, high"),
            "missing reason": (a_plan(changes=[without_a_reason]), "'why' must be str"),
        }  # fmt: skip
        for name, (plan, mentions) in cases.items():
            with self.subTest(name):
                path = self.tmp / "plan.json"
                path.write_text(json.dumps(plan), encoding="utf-8")
                self.assert_rejected("--before", self.before, "--plan", path, mentions=mentions)

    def test_risky_change_is_accepted_once_it_says_what_could_break(self) -> None:
        change = a_change(risk="high", risk_note="Checkout layout reflows.")
        path = self.tmp / "plan.json"
        path.write_text(json.dumps(a_plan(changes=[change])), encoding="utf-8")

        code, stderr = run_cli("--before", self.before, "--plan", path, "--out", self.out)

        self.assertEqual(code, 0, stderr)
        self.assertIn('<dd class="risk-high">high: Checkout layout reflows.</dd>', (self.out / "index.html").read_text("utf-8"))  # fmt: skip


if __name__ == "__main__":
    unittest.main()

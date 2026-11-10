#!/usr/bin/env python3
"""Build a catalogue page that pairs capture.py runs with the list of changes.

With --before and --after it shows every planned change, the measured
difference between the two runs, anything the second run made worse, and each
page before and after in every browser and viewport. With --before alone it
shows the current state, for an audit. The output directory holds index.html
and copies of the screenshots, so it can be served, zipped or opened from disk.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeVar, get_args

MANIFEST_NAME: Final = "manifest.json"
CHANGE_ID: Final = re.compile(r"[A-Za-z][A-Za-z0-9-]{0,11}")
# axe tags a rule with the success criteria it tests, written without dots: wcag1410 is 1.4.10.
WCAG_CRITERION_TAG: Final = re.compile(r"wcag(\d)(\d)(\d{1,2})")
# The catalogue opens on a laptop-sized render when the run has one.
PREFERRED_MAX_WIDTH: Final = 1440

Mode = Literal["preserve", "refresh", "reimagine"]
Category = Literal[
    "accessibility",
    "performance",
    "layout",
    "visual",
    "interaction",
    "compatibility",
    "content",
    "code",
]
Risk = Literal["low", "medium", "high"]
Side = Literal["before", "after"]

MODES: Final[tuple[Mode, ...]] = get_args(Mode)
CATEGORIES: Final[tuple[Category, ...]] = get_args(Category)
RISKS: Final[tuple[Risk, ...]] = get_args(Risk)

MODE_LABELS: Final[dict[str, str]] = {
    "preserve": "Preserve: same design, repaired underneath",
    "refresh": "Refresh: same style and palette, modernised",
    "reimagine": "Reimagine: new design",
}

T = TypeVar("T")
Choice = TypeVar("Choice", bound=str)


class CatalogueInputError(ValueError):
    """A run directory or the plan file cannot be used as given."""


@dataclass(frozen=True, slots=True)
class Violation:
    id: str
    impact: str | None
    help: str
    criteria: tuple[str, ...]
    nodes: int


@dataclass(frozen=True, slots=True)
class Shot:
    page: str
    browser: str
    viewport: str
    screenshot: str
    overflow_px: int
    console_errors: tuple[str, ...]
    failed_requests: tuple[str, ...]
    axe: tuple[Violation, ...] | None
    lcp_ms: float | None
    cls: float | None
    requests: int
    transfer_bytes: int

    @property
    def key(self) -> str:
        return f"{self.browser}|{self.viewport}"


@dataclass(frozen=True, slots=True)
class Failure:
    page: str
    browser: str
    viewport: str
    error: str


@dataclass(frozen=True, slots=True)
class Run:
    directory: Path
    captured_at: str
    mockup: bool
    scanned: bool
    browsers: dict[str, str | None]
    viewports: tuple[str, ...]
    page_urls: dict[str, str]
    shots: tuple[Shot, ...]
    failures: tuple[Failure, ...]

    def shots_for(self, page: str) -> list[Shot]:
        return [shot for shot in self.shots if shot.page == page]


@dataclass(frozen=True, slots=True)
class Change:
    id: str
    title: str
    category: Category
    pages: tuple[str, ...]
    why: str
    change: str
    risk: Risk
    risk_note: str | None


@dataclass(frozen=True, slots=True)
class Plan:
    project: str
    mode: Mode
    summary: str
    changes: tuple[Change, ...]
    out_of_scope: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PageComparison:
    page: str
    compared: bool
    fixed: tuple[Violation, ...]
    remaining: tuple[Violation, ...]
    introduced: tuple[Violation, ...]
    overflow_before: tuple[str, ...]
    overflow_after: tuple[str, ...]
    regressions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SummaryRow:
    measure: str
    before: str
    after: str | None


def _require(mapping: dict[str, object], key: str, kind: type[T], where: str) -> T:
    value = mapping.get(key)
    # bool is an int subclass; a true/false where a number belongs is a mistake.
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise CatalogueInputError(f"{where}: {key!r} must be {kind.__name__}.")
    return value


def _one_of(
    mapping: dict[str, object], key: str, choices: tuple[Choice, ...], where: str
) -> Choice:
    value = _require(mapping, key, str, where)
    for choice in choices:
        if value == choice:
            return choice
    raise CatalogueInputError(f"{where}: {key!r} must be one of {', '.join(choices)}.")


def _optional_number(mapping: dict[str, object], key: str, where: str) -> float | None:
    value = mapping.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CatalogueInputError(f"{where}: {key!r} must be a number or null.")
    return float(value)


def _strings(value: object, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CatalogueInputError(f"{where} must be a list of strings.")
    return tuple(value)


def _objects(value: object, where: str) -> list[dict[str, object]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise CatalogueInputError(f"{where} must be a list of objects.")
    return value


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogueInputError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CatalogueInputError(f"{path} must hold a JSON object.")
    return data


def _parse_violation(raw: dict[str, object], where: str) -> Violation:
    impact = raw.get("impact")
    if impact is not None and not isinstance(impact, str):
        raise CatalogueInputError(f"{where}: 'impact' must be a string or null.")
    criteria = (
        WCAG_CRITERION_TAG.fullmatch(tag) for tag in _strings(raw.get("wcag"), f"{where}: 'wcag'")
    )
    return Violation(
        id=_require(raw, "id", str, where),
        impact=impact,
        help=_require(raw, "help", str, where),
        criteria=tuple(".".join(match.groups()) for match in criteria if match is not None),
        nodes=_require(raw, "nodes", int, where),
    )


def _parse_shot(raw: dict[str, object], directory: Path, where: str) -> Shot:
    screenshot = _require(raw, "screenshot", str, where)
    if not (directory / screenshot).is_file():
        raise CatalogueInputError(f"{where}: screenshot {directory / screenshot} is missing.")
    metrics = _require(raw, "metrics", dict, where)
    axe = raw.get("axe")
    return Shot(
        page=_require(raw, "page", str, where),
        browser=_require(raw, "browser", str, where),
        viewport=_require(raw, "viewport", str, where),
        screenshot=screenshot,
        overflow_px=_require(raw, "horizontal_overflow_px", int, where),
        console_errors=_strings(raw.get("console_errors"), f"{where}: 'console_errors'"),
        failed_requests=_strings(raw.get("failed_requests"), f"{where}: 'failed_requests'"),
        axe=None
        if axe is None
        else tuple(
            _parse_violation(item, f"{where} axe") for item in _objects(axe, f"{where}: 'axe'")
        ),
        lcp_ms=_optional_number(metrics, "lcp_ms", where),
        cls=_optional_number(metrics, "cls", where),
        requests=_require(metrics, "requests", int, where),
        transfer_bytes=_require(metrics, "transfer_bytes", int, where),
    )


def load_run(directory: Path) -> Run:
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file():
        raise CatalogueInputError(
            f"{directory} has no {MANIFEST_NAME}; pass a directory written by capture.py."
        )
    raw = _read_json_object(manifest_path)
    where = str(manifest_path)
    browsers = _require(raw, "browsers", dict, where)
    pages = _objects(raw.get("pages"), f"{where}: 'pages'")
    return Run(
        directory=directory,
        captured_at=_require(raw, "captured_at", str, where),
        mockup=_require(raw, "mockup", bool, where),
        scanned=_require(raw, "axe", bool, where),
        browsers={
            str(name): version if isinstance(version, str) else None
            for name, version in browsers.items()
        },
        viewports=_strings(raw.get("viewports"), f"{where}: 'viewports'"),
        page_urls={
            _require(page, "id", str, where): _require(page, "url", str, where) for page in pages
        },
        shots=tuple(
            _parse_shot(shot, directory, f"{where} shot {index}")
            for index, shot in enumerate(_objects(raw.get("shots"), f"{where}: 'shots'"))
        ),
        failures=tuple(
            Failure(
                page=_require(failure, "page", str, where),
                browser=_require(failure, "browser", str, where),
                viewport=_require(failure, "viewport", str, where),
                error=_require(failure, "error", str, where),
            )
            for failure in _objects(raw.get("failures"), f"{where}: 'failures'")
        ),
    )


def load_plan(path: Path, known_pages: set[str]) -> Plan:
    raw = _read_json_object(path)
    where = str(path)
    mode = _one_of(raw, "mode", MODES, where)

    changes: list[Change] = []
    for index, item in enumerate(_objects(raw.get("changes"), f"{where}: 'changes'")):
        item_where = f"{where} change {index}"
        change_id = _require(item, "id", str, item_where)
        if CHANGE_ID.fullmatch(change_id) is None:
            raise CatalogueInputError(
                f"{item_where}: id {change_id!r} must be a short label such as A1; "
                "the reader approves or drops changes by it."
            )
        category = _one_of(item, "category", CATEGORIES, item_where)
        risk = _one_of(item, "risk", RISKS, item_where)
        pages = _strings(item.get("pages", []), f"{item_where}: 'pages'")
        unknown = sorted(set(pages) - known_pages)
        if unknown:
            raise CatalogueInputError(
                f"{item_where}: pages {', '.join(unknown)} were not captured. "
                f"Captured pages: {', '.join(sorted(known_pages))}. Use [] for a site-wide change."
            )
        risk_note = item.get("risk_note")
        if risk_note is not None and not isinstance(risk_note, str):
            raise CatalogueInputError(f"{item_where}: 'risk_note' must be a string.")
        if risk != "low" and not risk_note:
            raise CatalogueInputError(
                f"{item_where}: a {risk}-risk change needs 'risk_note' saying what could break."
            )
        changes.append(
            Change(
                id=change_id,
                title=_require(item, "title", str, item_where),
                category=category,
                pages=pages,
                why=_require(item, "why", str, item_where),
                change=_require(item, "change", str, item_where),
                risk=risk,
                risk_note=risk_note,
            )
        )

    if not changes:
        raise CatalogueInputError(f"{where}: 'changes' is empty; there is nothing to approve.")
    ids = [change.id for change in changes]
    duplicates = sorted({change_id for change_id in ids if ids.count(change_id) > 1})
    if duplicates:
        raise CatalogueInputError(f"{where}: change ids repeat: {', '.join(duplicates)}.")

    return Plan(
        project=_require(raw, "project", str, where),
        mode=mode,
        summary=_require(raw, "summary", str, where),
        changes=tuple(changes),
        out_of_scope=_strings(raw.get("out_of_scope", []), f"{where}: 'out_of_scope'"),
    )


def worst_violations(shots: list[Shot]) -> dict[str, Violation]:
    """One entry per failing rule: the render where it hit the most elements."""
    worst: dict[str, Violation] = {}
    for shot in shots:
        for violation in shot.axe or ():
            current = worst.get(violation.id)
            if current is None or violation.nodes > current.nodes:
                worst[violation.id] = violation
    return worst


def overflowing(shots: list[Shot]) -> dict[str, int]:
    return {shot.key: shot.overflow_px for shot in shots if shot.overflow_px > 0}


def describe_render(key: str) -> str:
    browser, viewport = key.split("|")
    return f"{browser} at {viewport}"


def compare_page(page: str, before: Run, after: Run | None) -> PageComparison:
    before_shots = before.shots_for(page)
    after_shots = after.shots_for(page) if after is not None else []
    before_axe, after_axe = worst_violations(before_shots), worst_violations(after_shots)
    before_overflow, after_overflow = overflowing(before_shots), overflowing(after_shots)

    def describe_overflow(found: dict[str, int]) -> tuple[str, ...]:
        return tuple(f"{describe_render(key)}: {found[key]}px" for key in sorted(found))

    def violations(source: dict[str, Violation], rules: set[str]) -> tuple[Violation, ...]:
        return tuple(source[rule] for rule in sorted(rules))

    # A page that only one run rendered has nothing to be compared with.
    compared = bool(before_shots) and bool(after_shots)
    regressions: list[str] = []
    if compared:
        for rule in sorted(after_axe.keys() - before_axe.keys()):
            regressions.append(f"New accessibility failure: {rule} ({after_axe[rule].help})")
        for key in sorted(after_overflow.keys() - before_overflow.keys()):
            regressions.append(
                f"New horizontal overflow of {after_overflow[key]}px in {describe_render(key)}"
            )
        seen_errors = {error for shot in before_shots for error in shot.console_errors}
        for error in sorted({e for shot in after_shots for e in shot.console_errors} - seen_errors):
            regressions.append(f"New console error: {error}")
        seen_failed = {request for shot in before_shots for request in shot.failed_requests}
        for request in sorted(
            {r for shot in after_shots for r in shot.failed_requests} - seen_failed
        ):
            regressions.append(f"New failed request: {request}")
    if after is not None:
        failed = {
            f"{failure.browser}|{failure.viewport}": failure.error
            for failure in after.failures
            if failure.page == page
        }
        for key in sorted(failed):
            regressions.append(f"Render failed in {describe_render(key)}: {failed[key]}")
        # A render the first run has and the second lacks is a claim nobody checked.
        unchecked = {shot.key for shot in before_shots} - {shot.key for shot in after_shots}
        for key in sorted(unchecked - failed.keys()):
            regressions.append(f"Not rendered after: {describe_render(key)}")

    only_run = before_axe or after_axe
    return PageComparison(
        page=page,
        compared=compared,
        fixed=violations(before_axe, before_axe.keys() - after_axe.keys()) if compared else (),
        remaining=violations(after_axe, before_axe.keys() & after_axe.keys())
        if compared
        else violations(only_run, set(only_run)),
        introduced=violations(after_axe, after_axe.keys() - before_axe.keys()) if compared else (),
        overflow_before=describe_overflow(before_overflow),
        overflow_after=describe_overflow(after_overflow),
        regressions=tuple(regressions),
    )


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _format_ms(value: float | None) -> str:
    return "not reported" if value is None else f"{value:.0f} ms"


def _format_kb(value: float | None) -> str:
    return "no renders" if value is None else f"{value / 1024:.1f} kB"


def _run_summary(run: Run) -> dict[str, str]:
    shots = list(run.shots)
    pages = sorted({shot.page for shot in shots})
    failing = [worst_violations(run.shots_for(page)) for page in pages]
    cls_values = [shot.cls for shot in shots if shot.cls is not None]
    return {
        "Failing accessibility rules, summed over pages": str(sum(len(found) for found in failing))
        if run.scanned
        else "not scanned",
        "Elements failing those rules": str(
            sum(violation.nodes for found in failing for violation in found.values())
        )
        if run.scanned
        else "not scanned",
        "Renders that scroll sideways": f"{sum(1 for shot in shots if shot.overflow_px > 0)} of {len(shots)}",
        "Median largest contentful paint": _format_ms(
            _median([shot.lcp_ms for shot in shots if shot.lcp_ms is not None])
        ),
        "Worst layout shift (Chromium only)": f"{max(cls_values):.3f}"
        if cls_values
        else "not reported",
        "Median transfer per page load": _format_kb(
            _median([float(shot.transfer_bytes) for shot in shots])
        ),
        "Median requests per page load": "no renders"
        if not shots
        else f"{statistics.median(shot.requests for shot in shots):g}",
        "Distinct console errors": str(len({e for shot in shots for e in shot.console_errors})),
        "Renders that failed": str(len(run.failures)),
    }


def summarise(before: Run, after: Run | None) -> list[SummaryRow]:
    before_summary = _run_summary(before)
    after_summary = _run_summary(after) if after is not None else None
    return [
        SummaryRow(
            measure=measure,
            before=value,
            after=None if after_summary is None else after_summary[measure],
        )
        for measure, value in before_summary.items()
    ]


def default_selection(run: Run) -> tuple[str, str]:
    """The browser and viewport shown before the reader touches the controls."""
    launched = [name for name, version in run.browsers.items() if version is not None]
    browser = (launched or list(run.browsers))[0]
    widths = {viewport: int(viewport.split("x")[0]) for viewport in run.viewports}
    laptop_sized = [viewport for viewport, width in widths.items() if width <= PREFERRED_MAX_WIDTH]
    viewport = (
        max(laptop_sized, key=widths.__getitem__)
        if laptop_sized
        else min(widths, key=widths.__getitem__)
    )
    return browser, viewport


def copy_screenshots(run: Run, out: Path, side: Side) -> dict[str, dict[str, str]]:
    """Copy a run's screenshots into the catalogue; return page -> render key -> relative path."""
    target = out / side
    target.mkdir(parents=True, exist_ok=True)
    paths: dict[str, dict[str, str]] = {}
    for shot in run.shots:
        shutil.copyfile(run.directory / shot.screenshot, target / shot.screenshot)
        paths.setdefault(shot.page, {})[shot.key] = f"{side}/{shot.screenshot}"
    return paths


STYLE: Final = """
:root {
  color-scheme: light dark;
  --page: #fbfbfa; --panel: #fff; --ink: #1c1b19; --soft: #5d5a55; --rule: #dcd9d3;
  --accent: #1f5fa8; --good: #1a6b3c; --bad: #b3261e; --frame: #ecebe7;
}
@media (prefers-color-scheme: dark) {
  :root {
    --page: #161614; --panel: #1f1f1c; --ink: #ecebe7; --soft: #a8a59e; --rule: #3a3935;
    --accent: #8ab8f0; --good: #7fd0a0; --bad: #ff9a8f; --frame: #0d0d0c;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink); font: 1rem/1.55 system-ui, sans-serif; }
main, header.top { width: min(100rem, 100%); margin-inline: auto; padding-inline: clamp(1rem, 3vw, 2.5rem); }
header.top { padding-block: 2.5rem 1rem; }
h1 { margin: 0; font-size: clamp(1.6rem, 1.2rem + 1.6vw, 2.4rem); line-height: 1.15; text-wrap: balance; }
h2 { margin: 3rem 0 1rem; font-size: 1.4rem; }
h3 { margin: 0; font-size: 1.05rem; }
p { margin: 0.5rem 0 0; max-width: 75ch; }
a { color: var(--accent); }
:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
.meta { color: var(--soft); }
.kind { display: inline-block; margin-bottom: 0.75rem; padding: 0.15rem 0.6rem; border: 1px solid currentColor; border-radius: 4px; font-size: 0.875rem; font-weight: 600; }
table { border-collapse: collapse; width: 100%; max-width: 60rem; font-variant-numeric: tabular-nums; }
th, td { padding: 0.55rem 0.75rem; text-align: left; border-bottom: 1px solid var(--rule); vertical-align: top; }
thead th { color: var(--soft); font-size: 0.875rem; }
td.figure { white-space: nowrap; }
@media (max-width: 24rem) { th, td { padding-inline: 0.4rem; } }
.regressions { margin-top: 2rem; padding: 1rem 1.25rem; border: 2px solid var(--bad); border-radius: 8px; background: var(--panel); }
.regressions h2 { margin: 0 0 0.5rem; color: var(--bad); }
.changes { display: grid; gap: 0.75rem; margin: 0; padding: 0; list-style: none; }
.change { display: grid; grid-template-columns: 4.5rem minmax(0, 1fr); gap: 0.25rem 1rem; padding: 1rem 1.25rem; background: var(--panel); border: 1px solid var(--rule); border-radius: 8px; }
.change .id { font: 600 1.05rem ui-monospace, monospace; }
.change dl { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 0.25rem 1rem; margin: 0.5rem 0 0; }
.change dt { color: var(--soft); }
.change dd { margin: 0; }
.risk-medium, .risk-high { font-weight: 600; }
.risk-high { color: var(--bad); }
.category { margin-top: 1.75rem; }
.category h3 { margin-bottom: 0.6rem; }
.controls { display: flex; flex-wrap: wrap; gap: 0.5rem 2rem; margin-top: 1rem; padding: 0.75rem 0; background: var(--page); border-bottom: 1px solid var(--rule); }
@media (min-width: 60rem) { .controls { position: sticky; top: 0; z-index: 2; } }
.controls fieldset { display: flex; flex-wrap: wrap; align-items: center; gap: 0.25rem 0.9rem; margin: 0; padding: 0; border: 0; }
.controls legend { float: left; margin-right: 0.9rem; padding: 0; color: var(--soft); }
.controls label { display: inline-flex; align-items: center; gap: 0.35rem; min-height: 2rem; }
.page { margin-top: 2.5rem; }
.pair { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(22rem, 100%), 1fr)); gap: 1rem; margin-top: 1rem; }
figure { margin: 0; min-width: 0; }
figcaption { display: flex; justify-content: space-between; gap: 1rem; margin-bottom: 0.4rem; font-weight: 600; }
figcaption a { font-weight: 400; }
.frame { max-height: 85vh; overflow: auto; background: var(--frame); border: 1px solid var(--rule); border-radius: 8px; }
.frame img { display: block; max-width: 100%; height: auto; margin-inline: auto; }
.frame p { padding: 2rem 1rem; color: var(--soft); text-align: center; max-width: none; margin: 0; }
.findings { margin: 0.75rem 0 0; padding-left: 1.2rem; }
.fixed { color: var(--good); }
.introduced, .worse { color: var(--bad); font-weight: 600; }
footer { margin-top: 4rem; padding: 1.5rem clamp(1rem, 3vw, 2.5rem); border-top: 1px solid var(--rule); color: var(--soft); font-size: 0.9rem; }
"""

SCRIPT: Final = """
const renders = JSON.parse(document.getElementById('renders').textContent);
const selected = (name) => document.querySelector(`input[name="${name}"]:checked`).value;

function show() {
  const key = `${selected('browser')}|${selected('viewport')}`;
  for (const frame of document.querySelectorAll('.frame')) {
    const { page, side } = frame.dataset;
    const path = (renders[side][page] || {})[key];
    const link = frame.parentElement.querySelector('figcaption a');
    link.hidden = !path;
    if (path) {
      const image = document.createElement('img');
      image.src = path;
      image.alt = `${page}, ${side}, ${selected('browser')} at ${selected('viewport')}`;
      frame.replaceChildren(image);
      link.href = path;
    } else {
      const note = document.createElement('p');
      note.textContent = 'No render for this browser and viewport.';
      frame.replaceChildren(note);
    }
    frame.scrollTop = 0;
  }
}

// Scrolling one render of a page moves its pair to the same relative position.
let leader = null;
for (const frame of document.querySelectorAll('.frame')) {
  frame.addEventListener('pointerenter', () => { leader = frame; });
  frame.addEventListener('focus', () => { leader = frame; });
  frame.addEventListener('scroll', () => {
    if (leader !== frame) return;
    const range = frame.scrollHeight - frame.clientHeight;
    for (const other of document.querySelectorAll(`.frame[data-page="${frame.dataset.page}"]`)) {
      if (other === frame || range <= 0) continue;
      other.scrollTop = (frame.scrollTop / range) * (other.scrollHeight - other.clientHeight);
    }
  });
}

document.querySelector('.controls').addEventListener('change', show);
"""


def _e(text: object) -> str:
    return html.escape(str(text))


def _radio_group(name: str, legend: str, values: list[str], checked: str) -> str:
    options = "".join(
        f'<label><input type="radio" name="{name}" value="{_e(value)}"'
        f"{' checked' if value == checked else ''}> {_e(value)}</label>"
        for value in values
    )
    return f"<fieldset><legend>{legend}</legend>{options}</fieldset>"


def _violation_items(violations: tuple[Violation, ...], css_class: str, prefix: str) -> str:
    items: list[str] = []
    for violation in violations:
        details = [f"<code>{_e(violation.id)}</code>"]
        details += [f"WCAG {_e(criterion)}" for criterion in violation.criteria]
        details.append(f"{violation.nodes} {'element' if violation.nodes == 1 else 'elements'}")
        if violation.impact:
            details.append(_e(violation.impact))
        items.append(
            f'<li class="{css_class}">{prefix}: {_e(violation.help)} ({", ".join(details)})</li>'
        )
    return "".join(items)


def _figure(page: str, side: Side, label: str, path: str | None) -> str:
    body = (
        f'<img src="{_e(path)}" alt="{_e(page)}, {side}">'
        if path
        else "<p>No render for this browser and viewport.</p>"
    )
    link = f'<a href="{_e(path or "#")}"{"" if path else " hidden"}>Open full size</a>'
    return (
        f"<figure><figcaption><span>{_e(label)}</span>{link}</figcaption>"
        f'<div class="frame" tabindex="0" data-page="{_e(page)}" data-side="{side}">{body}</div></figure>'
    )


def _page_section(
    comparison: PageComparison,
    before: Run,
    after: Run | None,
    paths: dict[Side, dict[str, dict[str, str]]],
    default_key: str,
    after_label: str,
) -> str:
    page = comparison.page
    url = before.page_urls.get(page) or (after.page_urls.get(page, "") if after else "")
    findings = [
        _violation_items(comparison.introduced, "introduced", "Introduced"),
        _violation_items(comparison.fixed, "fixed", "Fixed"),
        _violation_items(
            comparison.remaining, "remaining", "Still failing" if comparison.compared else "Failing"
        ),
    ]
    if not before.scanned:
        findings.append("<li>No accessibility scan ran; capture with --axe to include one.</li>")
    if comparison.overflow_before:
        findings.append(
            f"<li>Scrolls sideways {'before' if after else 'now'}: "
            f"{_e('; '.join(comparison.overflow_before))}</li>"
        )
    if comparison.overflow_after:
        findings.append(
            f'<li class="worse">Scrolls sideways after: {_e("; ".join(comparison.overflow_after))}</li>'
        )
    figures = _figure(
        page, "before", "Before" if after else "Now", paths["before"].get(page, {}).get(default_key)
    )
    if after is not None:
        figures += _figure(page, "after", after_label, paths["after"].get(page, {}).get(default_key))
    return (
        f'<section class="page"><h3>{_e(page)}</h3><p class="meta">{_e(url)}</p>'
        f'<ul class="findings">{"".join(findings)}</ul><div class="pair">{figures}</div></section>'
    )


def _change_item(change: Change) -> str:
    pages = ", ".join(change.pages) if change.pages else "All pages"
    risk = change.risk + (f": {change.risk_note}" if change.risk_note else "")
    return (
        f'<li class="change"><span class="id">{_e(change.id)}</span><div><h3>{_e(change.title)}</h3>'
        f"<dl><dt>Why</dt><dd>{_e(change.why)}</dd><dt>Change</dt><dd>{_e(change.change)}</dd>"
        f"<dt>Pages</dt><dd>{_e(pages)}</dd>"
        f'<dt>Risk</dt><dd class="risk-{change.risk}">{_e(risk)}</dd></dl></div></li>'
    )


def _plan_sections(plan: Plan, heading: str) -> str:
    groups = []
    for category in CATEGORIES:
        items = [change for change in plan.changes if change.category == category]
        if items:
            groups.append(
                f'<section class="category"><h3>{category.capitalize()} ({len(items)})</h3>'
                f'<ul class="changes">{"".join(_change_item(change) for change in items)}</ul></section>'
            )
    out_of_scope = (
        "<h2>Left alone</h2><ul>"
        + "".join(f"<li>{_e(item)}</li>" for item in plan.out_of_scope)
        + "</ul>"
        if plan.out_of_scope
        else ""
    )
    return (
        f"<h2>{heading} ({len(plan.changes)})</h2><p>{_e(plan.summary)}</p>"
        f"{''.join(groups)}{out_of_scope}"
    )


def _summary_cell(value: str) -> str:
    # "274 ms" must not break between the number and its unit; "not scanned" may wrap.
    attribute = ' class="figure"' if value[:1].isdigit() else ""
    return f"<td{attribute}>{_e(value)}</td>"


def render_html(
    before: Run,
    after: Run | None,
    plan: Plan | None,
    comparisons: list[PageComparison],
    paths: dict[Side, dict[str, dict[str, str]]],
) -> str:
    pages = [comparison.page for comparison in comparisons]
    regressions = [
        (comparison.page, text) for comparison in comparisons for text in comparison.regressions
    ]

    if after is None:
        kind, after_label, plan_heading = "Current state", "", "Recommended changes"
    elif after.mockup:
        kind, after_label, plan_heading = (
            "Dry run: nothing in the project has changed",
            "After (dry run)",
            "Planned changes",
        )
    else:
        kind, after_label, plan_heading = "Result", "After", "Changes made"
    project = plan.project if plan else "UI catalogue"

    reference = after or before
    browser, viewport = default_selection(reference)
    browsers = list(dict.fromkeys([*before.browsers, *(after.browsers if after else [])]))
    viewports = list(dict.fromkeys([*before.viewports, *(after.viewports if after else [])]))
    versions = ", ".join(
        f"{name} {version}" if version else f"{name} (did not launch)"
        for name, version in reference.browsers.items()
    )

    summary_rows = "".join(
        f'<tr><th scope="row">{_e(row.measure)}</th>{_summary_cell(row.before)}'
        f"{'' if row.after is None else _summary_cell(row.after)}</tr>"
        for row in summarise(before, after)
    )
    after_heading = "" if after is None else f'<th scope="col">{_e(after_label)}</th>'
    regression_block = (
        '<section class="regressions"><h2>Worse than before</h2><ul>'
        + "".join(f"<li><strong>{_e(page)}</strong>: {_e(text)}</li>" for page, text in regressions)
        + "</ul></section>"
        if regressions
        else ""
    )
    mode_line = f"<p>{_e(MODE_LABELS[plan.mode])}</p>" if plan and after is not None else ""
    renders_json = json.dumps(paths).replace("</", "<\\/")
    sections = "".join(
        _page_section(comparison, before, after, paths, f"{browser}|{viewport}", after_label)
        for comparison in comparisons
    )
    captured = f"Before captured {_e(before.captured_at)}" + (
        f"; after captured {_e(after.captured_at)}" if after else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(project)}: {_e(kind)}</title>
<style>{STYLE}</style>
</head>
<body>
<header class="top">
<span class="kind">{_e(kind)}</span>
<h1>{_e(project)}</h1>
{mode_line}
<p class="meta">{len(pages)} pages in {len(browsers)} browsers at {len(viewports)} viewports. {_e(versions)}.</p>
</header>
<main>
{regression_block}
<h2>Measured</h2>
<table><thead><tr><th scope="col">Measure</th><th scope="col">{"Before" if after else "Now"}</th>{after_heading}</tr></thead>
<tbody>{summary_rows}</tbody></table>
<p class="meta">Timings come from local loads without throttling; compare the two columns, not the absolute values.</p>
{_plan_sections(plan, plan_heading) if plan else ""}
<h2>Renders</h2>
<form class="controls">{_radio_group("browser", "Browser", browsers, browser)}{_radio_group("viewport", "Viewport", viewports, viewport)}</form>
{sections}
</main>
<footer>{captured}.</footer>
<script type="application/json" id="renders">{renders_json}</script>
<script>{SCRIPT}</script>
</body>
</html>
"""


def build(before_dir: Path, after_dir: Path | None, plan_path: Path | None, out: Path) -> list[str]:
    """Write the catalogue and return what the second run made worse."""
    before = load_run(before_dir)
    after = load_run(after_dir) if after_dir is not None else None
    if after is not None and after.scanned != before.scanned:
        unscanned = before_dir if after.scanned else after_dir
        raise CatalogueInputError(
            f"{unscanned} was captured without --axe and the other run with it, so every "
            "accessibility failure would read as fixed or as new. Capture both the same way."
        )
    # dict.fromkeys keeps the pages in the order they were captured, each once.
    pages = list(dict.fromkeys([*before.page_urls, *(after.page_urls if after else [])]))
    plan = load_plan(plan_path, set(pages)) if plan_path is not None else None
    comparisons = [compare_page(page, before, after) for page in pages]

    out.mkdir(parents=True, exist_ok=True)
    paths: dict[Side, dict[str, dict[str, str]]] = {
        "before": copy_screenshots(before, out, "before"),
        "after": copy_screenshots(after, out, "after") if after is not None else {},
    }
    (out / "index.html").write_text(
        render_html(before, after, plan, comparisons, paths), encoding="utf-8"
    )
    return [
        f"{comparison.page}: {text}"
        for comparison in comparisons
        for text in comparison.regressions
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--before", type=Path, required=True, help="capture.py run of the site as it is.")
    parser.add_argument(
        "--after", type=Path, help="capture.py run of the proposal or of the finished work."
    )
    parser.add_argument(
        "--plan",
        type=Path,
        help="JSON: project, mode (preserve, refresh, reimagine), summary, out_of_scope, and "
        "changes, each with id, title, category, pages, why, change, risk and risk_note.",
    )
    parser.add_argument("--out", type=Path, required=True, help="Directory for index.html and images.")
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit 1 when the --after run is worse than --before on any check.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        regressions = build(args.before, args.after, args.plan, args.out)
    except CatalogueInputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Catalogue written to {args.out / 'index.html'}")
    if regressions:
        print(f"{len(regressions)} checks are worse than before:", file=sys.stderr)
        for regression in regressions:
            print(f"  {regression}", file=sys.stderr)
        if args.fail_on_regression:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

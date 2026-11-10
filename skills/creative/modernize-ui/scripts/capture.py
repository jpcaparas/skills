#!/usr/bin/env python3
"""Render pages in several browsers and viewports and record what each render shows.

One run writes full-page screenshots and a manifest.json into --out. Run it on
the untouched site, then again with --overlay-css/--overlay-js (or with URLs of
a prototype) to render a proposal without editing the project, and pair the two
runs with build_catalogue.py.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Literal, NotRequired, TypedDict

from playwright.async_api import (
    Browser,
    BrowserContext,
    ConsoleMessage,
    Error as PlaywrightError,
    Page,
    Playwright,
    Request,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    ViewportSize,
    async_playwright,
)

MANIFEST_NAME: Final = "manifest.json"

# Browser name -> (Playwright engine, channel). "chromium" names its own channel
# because that launches the full browser in new headless mode; without a channel
# Playwright launches the separate headless shell, which renders less like Chrome.
BROWSERS: Final[dict[str, tuple[str, str | None]]] = {
    "chromium": ("chromium", "chromium"),
    "chrome": ("chromium", "chrome"),
    "msedge": ("chromium", "msedge"),
    "firefox": ("firefox", None),
    "webkit": ("webkit", None),
}
DEFAULT_BROWSERS: Final = ("chromium", "firefox", "webkit")
# 320 px is the width WCAG 1.4.10 (Reflow) is tested at.
DEFAULT_VIEWPORTS: Final = ("320x568", "390x844", "768x1024", "1366x768", "1920x1080")
# Narrower viewports are emulated as touch devices that honour <meta name="viewport">,
# so a page that lacks the tag renders zoomed out, as it does on a phone.
TOUCH_BELOW_WIDTH: Final = 1024
ENGINES_WITHOUT_MOBILE_EMULATION: Final = frozenset({"firefox"})

SETTLE_TIMEOUT_MS: Final = 5_000
MAX_SCROLL_STEPS: Final = 60
MAX_AXE_TARGETS: Final = 5
MAX_LOGGED_PROBLEMS: Final = 20

PAGE_ID: Final = re.compile(r"[a-z0-9][a-z0-9-]*")
VIEWPORT: Final = re.compile(r"(\d{3,4})x(\d{3,4})")

# CLS follows the web-vitals definition: the largest burst of unexpected layout
# shifts, where a burst ends after a 1 s gap or 5 s in total.
METRICS_INIT_SCRIPT: Final = """
(() => {
  const supported = PerformanceObserver.supportedEntryTypes || [];
  const state = {
    lcp: null,
    cls: supported.includes('layout-shift') ? 0 : null,
  };
  window.__modernizeUi = state;
  const watch = (type, onEntry) => {
    if (!supported.includes(type)) return;
    new PerformanceObserver((list) => list.getEntries().forEach(onEntry))
      .observe({ type, buffered: true });
  };
  watch('largest-contentful-paint', (entry) => { state.lcp = entry.startTime; });
  let burst = 0, burstStart = 0, lastShift = 0;
  watch('layout-shift', (entry) => {
    if (entry.hadRecentInput) return;
    const continues = burst > 0
      && entry.startTime - lastShift < 1000
      && entry.startTime - burstStart < 5000;
    if (continues) {
      burst += entry.value;
    } else {
      burst = entry.value;
      burstStart = entry.startTime;
    }
    lastShift = entry.startTime;
    state.cls = Math.max(state.cls, burst);
  });
})();
"""

WAIT_FOR_FONTS_AND_IMAGES: Final = """
async () => {
  await document.fonts.ready;
  const pending = [...document.images].filter((image) => !image.complete);
  await Promise.all(pending.map((image) => new Promise((resolve) => {
    image.addEventListener('load', resolve, { once: true });
    image.addEventListener('error', resolve, { once: true });
  })));
}
"""

MEASURE_DOCUMENT: Final = """
() => {
  const root = document.documentElement;
  return {
    width: root.scrollWidth,
    height: root.scrollHeight,
    overflow: Math.max(0, root.scrollWidth - root.clientWidth),
    domNodes: document.getElementsByTagName('*').length,
    lcp: window.__modernizeUi ? window.__modernizeUi.lcp : null,
    cls: window.__modernizeUi ? window.__modernizeUi.cls : null,
  };
}
"""

RUN_AXE: Final = "() => axe.run(document, { resultTypes: ['violations'] })"

ColorScheme = Literal["light", "dark"]


class CaptureInputError(ValueError):
    """The command line or the pages file cannot be used as given."""


class PageEntry(TypedDict):
    id: str
    url: str
    prepare: NotRequired[str]


class DocumentMeasurement(TypedDict):
    width: int
    height: int
    overflow: int
    domNodes: int
    lcp: float | None
    cls: float | None


class AxeNode(TypedDict):
    target: list[object]


class AxeResult(TypedDict):
    id: str
    impact: str | None
    help: str
    tags: list[str]
    nodes: list[AxeNode]


class AxeReport(TypedDict):
    violations: list[AxeResult]


@dataclass(frozen=True, slots=True)
class PageSpec:
    id: str
    url: str
    prepare: str | None


@dataclass(frozen=True, slots=True)
class Viewport:
    width: int
    height: int

    @property
    def label(self) -> str:
        return f"{self.width}x{self.height}"


@dataclass(frozen=True, slots=True)
class CaptureOptions:
    out: Path
    overlay_css: str | None
    overlay_js: str | None
    axe_source: str | None
    color_scheme: ColorScheme
    reduced_motion: bool
    storage_state: Path | None
    timeout_ms: int


@dataclass(frozen=True, slots=True)
class AxeViolation:
    id: str
    impact: str | None
    help: str
    wcag: list[str]
    nodes: int
    targets: list[str]


@dataclass(frozen=True, slots=True)
class Metrics:
    """lcp_ms and cls are None in engines that do not report them."""

    lcp_ms: float | None
    cls: float | None
    dom_nodes: int
    requests: int
    transfer_bytes: int


@dataclass(frozen=True, slots=True)
class Shot:
    page: str
    url: str
    browser: str
    viewport: str
    touch_emulation: bool
    screenshot: str
    document_width: int
    document_height: int
    horizontal_overflow_px: int
    console_errors: list[str]
    failed_requests: list[str]
    axe: list[AxeViolation] | None
    metrics: Metrics


@dataclass(frozen=True, slots=True)
class Failure:
    page: str
    browser: str
    viewport: str
    error: str


@dataclass(frozen=True, slots=True)
class EngineRun:
    version: str | None
    shots: list[Shot]
    failures: list[Failure]


def parse_viewport(text: str) -> Viewport:
    match = VIEWPORT.fullmatch(text)
    if match is None:
        raise CaptureInputError(f"Viewport must look like 390x844; got {text!r}.")
    return Viewport(width=int(match.group(1)), height=int(match.group(2)))


def load_pages(path: Path) -> list[PageSpec]:
    try:
        entries: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureInputError(f"Cannot read pages file {path}: {exc}") from exc
    if not isinstance(entries, list) or not entries:
        raise CaptureInputError(
            f'{path} must be a non-empty JSON array such as [{{"id": "home", "url": "http://localhost:3000/"}}].'
        )

    pages: list[PageSpec] = []
    for position, entry in enumerate(entries):
        where = f"{path} entry {position}"
        if not isinstance(entry, dict):
            raise CaptureInputError(f"{where} must be an object with id and url.")
        unknown = set(entry) - PageEntry.__required_keys__ - PageEntry.__optional_keys__
        if unknown:
            raise CaptureInputError(f"{where} has unknown keys: {', '.join(sorted(unknown))}.")
        page_id, url, prepare = entry.get("id"), entry.get("url"), entry.get("prepare")
        if not isinstance(page_id, str) or PAGE_ID.fullmatch(page_id) is None:
            raise CaptureInputError(
                f"{where}: id must be lowercase letters, digits and hyphens; it names the screenshot files."
            )
        if not isinstance(url, str) or not url.startswith(("http://", "https://", "file://")):
            raise CaptureInputError(f"{where}: url must start with http://, https:// or file://.")
        if prepare is not None and not isinstance(prepare, str):
            raise CaptureInputError(f"{where}: prepare must be a string of JavaScript.")
        pages.append(PageSpec(id=page_id, url=url, prepare=prepare))

    ids = [page.id for page in pages]
    duplicates = sorted({page_id for page_id in ids if ids.count(page_id) > 1})
    if duplicates:
        raise CaptureInputError(f"{path} repeats page ids: {', '.join(duplicates)}.")
    return pages


class ContextSettings(TypedDict):
    """The keyword arguments this script passes to Playwright's new_context."""

    viewport: ViewportSize
    bypass_csp: bool
    ignore_https_errors: bool
    color_scheme: ColorScheme
    reduced_motion: Literal["reduce", "no-preference"]
    is_mobile: bool
    has_touch: bool
    storage_state: NotRequired[str]


def context_options(
    engine: str, viewport: Viewport, options: CaptureOptions
) -> tuple[ContextSettings, bool]:
    """Return Playwright context options and whether touch emulation is on."""
    touch = viewport.width < TOUCH_BELOW_WIDTH and engine not in ENGINES_WITHOUT_MOBILE_EMULATION
    settings: ContextSettings = {
        "viewport": {"width": viewport.width, "height": viewport.height},
        # Injected overlays and axe-core must load on sites with a strict CSP.
        "bypass_csp": True,
        "ignore_https_errors": True,
        "color_scheme": options.color_scheme,
        "reduced_motion": "reduce" if options.reduced_motion else "no-preference",
        "is_mobile": touch,
        "has_touch": touch,
    }
    if options.storage_state is not None:
        settings["storage_state"] = str(options.storage_state)
    return settings, touch


def summarise_axe(report: AxeReport) -> list[AxeViolation]:
    return [
        AxeViolation(
            id=violation["id"],
            impact=violation["impact"],
            help=violation["help"],
            wcag=sorted(tag for tag in violation["tags"] if tag.startswith("wcag")),
            nodes=len(violation["nodes"]),
            targets=[
                " ".join(str(part) for part in node["target"])
                for node in violation["nodes"][:MAX_AXE_TARGETS]
            ],
        )
        for violation in report["violations"]
    ]


async def transferred_bytes(requests: list[Request]) -> int:
    total = 0
    for request in requests:
        try:
            sizes = await request.sizes()
        except PlaywrightError:
            continue
        total += max(0, sizes["responseBodySize"]) + max(0, sizes["responseHeadersSize"])
    return total


async def scroll_through(page: Page, viewport: Viewport) -> None:
    """Visit every screenful so lazy images and scroll-triggered content load."""
    for step in range(MAX_SCROLL_STEPS):
        reached_end: bool = await page.evaluate(
            """(top) => {
              window.scrollTo(0, top);
              return top + window.innerHeight >= document.documentElement.scrollHeight;
            }""",
            step * viewport.height,
        )
        await page.wait_for_timeout(100)
        if reached_end:
            break
    await page.evaluate("window.scrollTo(0, 0)")


async def capture_page(
    page: Page,
    spec: PageSpec,
    browser_name: str,
    viewport: Viewport,
    touch: bool,
    options: CaptureOptions,
) -> Shot:
    console_errors: list[str] = []
    failed_requests: list[str] = []
    finished: list[Request] = []

    def on_console(message: ConsoleMessage) -> None:
        if message.type != "error":
            return
        # "Failed to load resource" names no resource; the location is the only clue to which.
        source = message.location.get("url", "")
        named = not source or source in message.text
        console_errors.append(message.text if named else f"{message.text} ({source})")

    def on_response(response: Response) -> None:
        if response.status >= 400:
            failed_requests.append(f"{response.status} {response.url}")

    page.on("console", on_console)
    page.on("pageerror", lambda error: console_errors.append(str(error)))
    page.on("requestfailed", lambda request: failed_requests.append(f"failed {request.url}"))
    page.on("response", on_response)
    # Playwright cannot attach a built-in method such as list.append as a handler.
    page.on("requestfinished", lambda request: finished.append(request))

    await page.goto(spec.url, wait_until="load", timeout=options.timeout_ms)
    try:
        await page.wait_for_load_state("networkidle", timeout=SETTLE_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        pass  # Polling and streaming pages never go idle; render what is there.

    if options.overlay_css is not None:
        await page.add_style_tag(content=options.overlay_css)
    if options.overlay_js is not None:
        await page.evaluate(options.overlay_js)
    if spec.prepare is not None:
        await page.evaluate(spec.prepare)

    await scroll_through(page, viewport)
    await asyncio.wait_for(
        page.evaluate(WAIT_FOR_FONTS_AND_IMAGES), timeout=options.timeout_ms / 1000
    )

    screenshot = f"{spec.id}.{browser_name}.{viewport.label}.png"
    await page.screenshot(
        path=options.out / screenshot, full_page=True, animations="disabled", caret="hide"
    )

    measured: DocumentMeasurement = await page.evaluate(MEASURE_DOCUMENT)
    violations: list[AxeViolation] | None = None
    if options.axe_source is not None:
        await page.evaluate(options.axe_source)
        violations = summarise_axe(await page.evaluate(RUN_AXE))

    return Shot(
        page=spec.id,
        url=spec.url,
        browser=browser_name,
        viewport=viewport.label,
        touch_emulation=touch,
        screenshot=screenshot,
        document_width=measured["width"],
        document_height=measured["height"],
        horizontal_overflow_px=measured["overflow"],
        console_errors=console_errors[:MAX_LOGGED_PROBLEMS],
        failed_requests=failed_requests[:MAX_LOGGED_PROBLEMS],
        axe=violations,
        metrics=Metrics(
            lcp_ms=None if measured["lcp"] is None else round(measured["lcp"], 1),
            cls=None if measured["cls"] is None else round(measured["cls"], 4),
            dom_nodes=measured["domNodes"],
            requests=len(finished),
            transfer_bytes=await transferred_bytes(finished),
        ),
    )


def launch_error_summary(error: PlaywrightError) -> str:
    """The first line of words in a launch error, which Playwright may draw inside a box."""
    for line in str(error).splitlines():
        text = line.strip(" ║╔╗╚╝═")
        if text:
            return text
    return type(error).__name__


async def capture_browser(
    playwright: Playwright,
    browser_name: str,
    pages: list[PageSpec],
    viewports: list[Viewport],
    options: CaptureOptions,
) -> EngineRun:
    engine, channel = BROWSERS[browser_name]
    try:
        browser: Browser = await getattr(playwright, engine).launch(channel=channel)
    except PlaywrightError as exc:
        install_target = channel or engine
        reason = (
            f"{browser_name} did not launch ({launch_error_summary(exc)}). "
            f"Install it with: python -m playwright install --with-deps {install_target}"
        )
        failures = [
            Failure(page=page.id, browser=browser_name, viewport=viewport.label, error=reason)
            for viewport in viewports
            for page in pages
        ]
        return EngineRun(version=None, shots=[], failures=failures)

    shots: list[Shot] = []
    failures = []
    try:
        for viewport in viewports:
            settings, touch = context_options(engine, viewport, options)
            for spec in pages:
                # A context per render makes every load a cold one, so request
                # counts and transfer sizes do not depend on the order of pages.
                context: BrowserContext = await browser.new_context(**settings)
                try:
                    await context.add_init_script(METRICS_INIT_SCRIPT)
                    page = await context.new_page()
                    shots.append(
                        await capture_page(page, spec, browser_name, viewport, touch, options)
                    )
                except (PlaywrightError, TimeoutError) as exc:
                    # asyncio's TimeoutError carries no message.
                    message = str(exc).splitlines() or [type(exc).__name__]
                    failures.append(
                        Failure(
                            page=spec.id,
                            browser=browser_name,
                            viewport=viewport.label,
                            error=message[0],
                        )
                    )
                finally:
                    await context.close()
        return EngineRun(version=browser.version, shots=shots, failures=failures)
    finally:
        await browser.close()


async def capture(
    pages: list[PageSpec],
    browsers: list[str],
    viewports: list[Viewport],
    options: CaptureOptions,
    mockup: bool,
) -> dict[str, object]:
    options.out.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        runs = await asyncio.gather(
            *(capture_browser(playwright, name, pages, viewports, options) for name in browsers)
        )
    manifest: dict[str, object] = {
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mockup": mockup,
        "color_scheme": options.color_scheme,
        "reduced_motion": options.reduced_motion,
        "axe": options.axe_source is not None,
        "browsers": {name: run.version for name, run in zip(browsers, runs, strict=True)},
        "viewports": [viewport.label for viewport in viewports],
        "pages": [asdict(page) for page in pages],
        "shots": [asdict(shot) for run in runs for shot in run.shots],
        "failures": [asdict(failure) for run in runs for failure in run.failures],
    }
    (options.out / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def read_text_option(path: Path | None, flag: str) -> str | None:
    if path is None:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CaptureInputError(f"Cannot read {flag} file {path}: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--pages",
        type=Path,
        required=True,
        help='JSON array of {"id", "url", "prepare"?}. "prepare" is JavaScript run after load, '
        "for example to open a menu or stop a carousel, so a state can be rendered as its own page.",
    )
    parser.add_argument("--out", type=Path, required=True, help="Directory for this run.")
    parser.add_argument(
        "--browsers",
        nargs="+",
        choices=sorted(BROWSERS),
        default=list(DEFAULT_BROWSERS),
        help=f"Default: {' '.join(DEFAULT_BROWSERS)}. chrome and msedge are the branded builds.",
    )
    parser.add_argument(
        "--viewports",
        nargs="+",
        default=list(DEFAULT_VIEWPORTS),
        metavar="WxH",
        help=f"Default: {' '.join(DEFAULT_VIEWPORTS)}. Widths under {TOUCH_BELOW_WIDTH} "
        "emulate a touch device, except in Firefox, which cannot.",
    )
    parser.add_argument(
        "--overlay-css", type=Path, help="Stylesheet injected after load to render a proposal."
    )
    parser.add_argument(
        "--overlay-js", type=Path, help="Script evaluated after load to render a proposal."
    )
    parser.add_argument(
        "--mockup",
        action="store_true",
        help="Mark the run as a proposal when its URLs point at a prototype. Implied by an overlay.",
    )
    parser.add_argument(
        "--axe",
        type=Path,
        help="Path to axe.min.js (npm package axe-core). Without it no accessibility scan runs.",
    )
    parser.add_argument("--color-scheme", choices=("light", "dark"), default="light")
    parser.add_argument(
        "--reduced-motion", action="store_true", help="Render with prefers-reduced-motion: reduce."
    )
    parser.add_argument(
        "--storage-state", type=Path, help="Playwright storage state file for signed-in pages."
    )
    parser.add_argument(
        "--timeout-ms", type=int, default=30_000, help="Per-page load timeout. Default: 30000."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        pages = load_pages(args.pages)
        viewports = [parse_viewport(text) for text in args.viewports]
        if args.storage_state is not None and not args.storage_state.is_file():
            raise CaptureInputError(f"Storage state file does not exist: {args.storage_state}")
        options = CaptureOptions(
            out=args.out,
            overlay_css=read_text_option(args.overlay_css, "--overlay-css"),
            overlay_js=read_text_option(args.overlay_js, "--overlay-js"),
            axe_source=read_text_option(args.axe, "--axe"),
            color_scheme=args.color_scheme,
            reduced_motion=args.reduced_motion,
            storage_state=args.storage_state,
            timeout_ms=args.timeout_ms,
        )
    except CaptureInputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    mockup = args.mockup or options.overlay_css is not None or options.overlay_js is not None
    # dict.fromkeys drops a browser named twice; it would overwrite its own screenshots.
    manifest = asyncio.run(
        capture(pages, list(dict.fromkeys(args.browsers)), viewports, options, mockup)
    )

    shots, failures = manifest["shots"], manifest["failures"]
    assert isinstance(shots, list) and isinstance(failures, list)
    print(f"{len(shots)} renders written to {args.out / MANIFEST_NAME}")
    if failures:
        print(f"{len(failures)} renders failed:", file=sys.stderr)
        for failure in failures[:MAX_LOGGED_PROBLEMS]:
            print(
                f"  {failure['page']} {failure['browser']} {failure['viewport']}: {failure['error']}",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

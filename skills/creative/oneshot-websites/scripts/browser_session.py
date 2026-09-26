"""Clock-controlled browser adapter; real input with no wall-clock simulation."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Literal, Protocol

from playwright.async_api import Page, async_playwright


CLOCK_EPOCH_SECONDS = 946684800  # 2000-01-01T00:00:00Z
FRAME_MILLISECONDS = 16
OPERATION_TIMEOUT_SECONDS = 15
VIRTUAL_OPERATION_MILLISECONDS = 15_000


class BrowserError(RuntimeError):
    """An input, clock, or browser operation could not be verified."""


class BrowserSession(Protocol):
    """The verifier needs evaluation, clock progression, and browser key input."""

    async def evaluate(self, expression: str) -> object: ...

    async def advance(self, milliseconds: int) -> None: ...

    async def dispatch_key(
        self, code: str, event_type: Literal["keyDown", "keyUp"]
    ) -> None: ...


async def default_browser_executable() -> Path:
    """Use the browser revision belonging to the installed Playwright package."""
    async with async_playwright() as playwright:
        return Path(playwright.chromium.executable_path)


class PlaywrightSession:
    """Keep the vendor API and its async scheduling outside the direction rules."""

    def __init__(self, page: Page) -> None:
        self.page = page

    async def advance(self, milliseconds: int) -> None:
        # run_for fires every due timer/frame; fast_forward deliberately does not.
        async with asyncio.timeout(OPERATION_TIMEOUT_SECONDS):
            await self.page.clock.run_for(milliseconds)

    async def dispatch_key(
        self, code: str, event_type: Literal["keyDown", "keyUp"]
    ) -> None:
        # Let the driver's keyboard map own CDP fields. A Windows VK passed as
        # nativeVirtualKeyCode creates a different Cocoa key event on macOS.
        # Playwright still sends trusted Input.dispatchKeyEvent, without that field:
        # https://github.com/microsoft/playwright/blob/28e86763ac4218fa8602a845f8dec080346688a0/packages/playwright-core/src/server/chromium/crInput.ts
        async with asyncio.timeout(OPERATION_TIMEOUT_SECONDS):
            if event_type == "keyDown":
                await self.page.keyboard.down(code)
            else:
                await self.page.keyboard.up(code)

    async def evaluate(self, expression: str) -> object:
        # A reset/sample may await timers or animation frames. Register it before
        # advancing time, then inspect an explicit completion state. Awaiting the
        # promise directly would deadlock the paused clock; racing two RPCs would
        # make the number of elapsed frames depend on the host scheduler.
        async with asyncio.timeout(OPERATION_TIMEOUT_SECONDS):
            await self.page.evaluate(
                """expression => {
                  const state = {status: 'pending'};
                  window.__ONESHOT_COORDINATOR_EVALUATION__ = state;
                  Promise.resolve().then(() => (0, eval)(expression)).then(
                    value => { state.value = value; state.status = 'resolved'; },
                    error => { state.error = String(error); state.status = 'rejected'; }
                  );
                }""",
                expression,
            )
            elapsed = 0
            while True:
                state: object = await self.page.evaluate(
                    "window.__ONESHOT_COORDINATOR_EVALUATION__"
                )
                if not isinstance(state, dict):
                    raise BrowserError("browser evaluation lost its completion state")
                status = state.get("status")
                if status == "resolved":
                    # The domain parser, not the SDK's Any return, owns the shape.
                    value: object = state.get("value")
                    return value
                if status == "rejected":
                    raise BrowserError(f"artifact control probe failed: {state.get('error')}")
                if status != "pending":
                    raise BrowserError(f"invalid browser evaluation state: {status}")
                if elapsed == VIRTUAL_OPERATION_MILLISECONDS:
                    break
                step = min(FRAME_MILLISECONDS, VIRTUAL_OPERATION_MILLISECONDS - elapsed)
                await self.advance(step)
                elapsed += step
        raise BrowserError(
            f"artifact control probe exceeded {VIRTUAL_OPERATION_MILLISECONDS} ms of virtual time"
        )


@asynccontextmanager
async def open_browser_session(url: str, executable: Path) -> AsyncIterator[BrowserSession]:
    """Every key starts in a fresh context with the same paused clock and viewport."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=str(executable), timeout=OPERATION_TIMEOUT_SECONDS * 1000
        )
        try:
            async with asyncio.timeout(OPERATION_TIMEOUT_SECONDS):
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    device_scale_factor=1,
                    locale="en-US",
                    timezone_id="UTC",
                )
                page = await context.new_page()
                # pause_at installs the clock itself. Calling install first records a
                # running interval whose RPC latency drifts performance.now on reload.
                # https://playwright.dev/python/docs/clock
                await page.clock.pause_at(CLOCK_EPOCH_SECONDS)
                # Playwright 1.62 lazily replays that pause after navigation. Read
                # before its native bootstrap ticker can advance monotonic time.
                # Context-init registration order is a pinned-Chromium assumption
                # covered by the forced bootstrap-tick regression.
                await context.add_init_script("void Date.now();")
                await page.goto(url, wait_until="load", timeout=OPERATION_TIMEOUT_SECONDS * 1000)
            yield PlaywrightSession(page)
        finally:
            # Playwright owns graceful shutdown, forced recovery, and profile
            # cleanup, rather than deleting a profile while Chromium still writes.
            await asyncio.wait_for(browser.close(), timeout=OPERATION_TIMEOUT_SECONDS)

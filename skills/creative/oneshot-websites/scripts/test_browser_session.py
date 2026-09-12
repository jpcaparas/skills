#!/usr/bin/env python3
"""Real Chromium regressions for clock progression, native input, and cleanup."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from playwright.async_api import Error as PlaywrightError

import browser_session
from browser_session import BrowserError, open_browser_session
from verify_directional_controls import ArtifactServer, VerificationError, resolve_browser


class BrowserClockTests(unittest.IsolatedAsyncioTestCase):
    executable: Path
    server: ArtifactServer

    @classmethod
    def setUpClass(cls) -> None:
        cls.executable = resolve_browser(None).executable
        artifact = Path(__file__).resolve().parents[1] / "evals/files/directional-controls/correct"
        cls.server = ArtifactServer(artifact).__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.__exit__()

    async def test_fresh_sessions_have_exact_frames_timers_and_held_key_motion(self) -> None:
        # Each session must match independently derived values, not the previous
        # run's output. A native rAF, running clock, skipped interval, or JS-only
        # key event must fail even when its eventual movement has the right sign.
        for iteration in range(3):
            with self.subTest(session=iteration):
                async with open_browser_session(self.server.url, self.executable) as session:
                    self.assertEqual(await session.evaluate("[Date.now(), performance.now()]"),
                                     [946684800000, 0])
                    await session.evaluate("""(() => {
                      const result = {frames: [], intervals: [], timer: null, x: 0, events: []};
                      window.clockResult = result;
                      let held = false;
                      window.addEventListener('keydown', event => {
                        if (event.code === 'KeyA') held = true;
                        result.events.push([event.type, event.code, event.isTrusted]);
                      });
                      window.addEventListener('keyup', event => {
                        if (event.code === 'KeyA') held = false;
                        result.events.push([event.type, event.code, event.isTrusted]);
                      });
                      function frame(time) {
                        result.frames.push(time);
                        if (held) result.x -= 3;
                        requestAnimationFrame(frame);
                      }
                      requestAnimationFrame(frame);
                      setInterval(() => result.intervals.push(performance.now()), 20);
                      setTimeout(() => result.timer = performance.now(), 50);
                    })()""")
                    await session.dispatch_key("KeyA", "a", 65, "keyDown")
                    await session.advance(64)
                    await session.dispatch_key("KeyA", "a", 65, "keyUp")
                    await session.advance(16)
                    self.assertEqual(await session.evaluate("window.clockResult"), {
                        "frames": [16, 32, 48, 64, 80],
                        "intervals": [20, 40, 60, 80],
                        "timer": 50,
                        "x": -12,
                        "events": [["keydown", "KeyA", True], ["keyup", "KeyA", True]],
                    })
                    self.assertEqual(await session.evaluate("[Date.now(), performance.now()]"),
                                     [946684800080, 80])

    async def test_async_probe_registers_before_advancing_clock(self) -> None:
        async with open_browser_session(self.server.url, self.executable) as session:
            self.assertEqual(await session.evaluate("""(async () => {
              await new Promise(resolve => setTimeout(resolve, 31));
              return await new Promise(resolve => requestAnimationFrame(resolve));
            })()"""), 32)
            # A completed synchronous read consumes no frames.
            self.assertEqual(await session.evaluate("performance.now()"), 32)

    async def test_virtual_budget_includes_exact_boundary_but_rejects_unsettled_probe(self) -> None:
        async with open_browser_session(self.server.url, self.executable) as session:
            # A non-frame-aligned limit catches accidental rounding down to 16.
            with patch.object(browser_session, "VIRTUAL_OPERATION_MILLISECONDS", 31):
                self.assertEqual(await session.evaluate(
                    "new Promise(resolve => setTimeout(() => resolve(performance.now()), 31))"
                ), 31)
                with self.assertRaisesRegex(BrowserError, "exceeded 31 ms of virtual time"):
                    await session.evaluate("new Promise(() => {})")
                self.assertEqual(await session.evaluate("performance.now()"), 62)

    async def test_rejected_probe_closes_browser_and_preserves_error(self) -> None:
        with self.assertRaisesRegex(BrowserError, "broken production reset"):
            async with open_browser_session(self.server.url, self.executable) as session:
                await session.evaluate("Promise.reject(new Error('broken production reset'))")
        with self.assertRaises(PlaywrightError):
            await session.evaluate("true")


class BrowserSelectionTests(unittest.TestCase):
    def test_missing_explicit_browser_never_falls_back_to_a_working_default(self) -> None:
        working_browser = resolve_browser(None).executable
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing-chromium"
            with patch.dict(os.environ, {"ONESHOT_WEBSITES_BROWSER": str(missing)}):
                with self.assertRaisesRegex(VerificationError, "browser unavailable"):
                    resolve_browser(None)
            with patch.dict(os.environ, {"ONESHOT_WEBSITES_BROWSER": str(working_browser)}):
                with self.assertRaisesRegex(VerificationError, "browser unavailable"):
                    resolve_browser(missing)

    def test_non_executable_browser_is_rejected_before_launch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "not-executable"
            candidate.write_text("not a browser", encoding="utf-8")
            candidate.chmod(0o644)
            with self.assertRaisesRegex(VerificationError, "executable regular file"):
                resolve_browser(candidate)


if __name__ == "__main__":
    unittest.main()

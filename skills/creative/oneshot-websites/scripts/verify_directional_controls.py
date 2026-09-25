#!/usr/bin/env python3
"""Verify semantic left/right controls through a Chromium browser input path."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import stat
import subprocess
import sys
import threading
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from playwright.async_api import Error as PlaywrightError

from browser_session import (
    BrowserError,
    BrowserSession,
    CLOCK_EPOCH_SECONDS,
    FRAME_MILLISECONDS,
    OPERATION_TIMEOUT_SECONDS,
    default_browser_executable,
    open_browser_session,
)

from directional_controls import (
    DIRECTIONAL_CONTROL_CONTRACT_VERSION,
    DIRECTIONAL_CONTROL_EVIDENCE_SCHEMA,
    DIRECTIONAL_CONTROL_PROBE_GLOBAL,
    DIRECTIONAL_CONTROL_PROBE_SCHEMA,
    ArtifactTreeDigest,
    DirectionalControlError,
    artifact_tree_digest,
    directional_response,
    parse_directional_sample,
    response_matches_direction,
)
from runtime_contract import BoundedReadError, parse_json_bounded, read_regular_file_bounded, verification_mode


METADATA_MAX_BYTES = 1024 * 1024
PAGE_READY_MILLISECONDS = 15_000
DEFAULT_HOLD_MILLISECONDS = 400


@dataclass(frozen=True)
class KeyCheck:
    """One physical-key case and its required semantic response."""

    code: str
    expected: str


@dataclass(frozen=True)
class BrowserInfo:
    """Resolved Chromium-family browser without machine-specific evidence paths."""

    executable: Path
    name: str
    version: str


KEY_CHECKS = (
    KeyCheck("KeyA", "left"),
    KeyCheck("ArrowLeft", "left"),
    KeyCheck("KeyD", "right"),
    KeyCheck("ArrowRight", "right"),
)


class VerificationError(RuntimeError):
    """Raised when authoritative browser verification cannot complete."""


class QuietStaticHandler(SimpleHTTPRequestHandler):
    """Serve one artifact without noisy request logs or persistent caching."""

    def log_message(self, _format: str, *_arguments: object) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class ArtifactServer(AbstractContextManager["ArtifactServer"]):
    """Loopback-only static server for the exact artifact under review."""

    def __init__(self, artifact: Path) -> None:
        handler = partial(QuietStaticHandler, directory=str(artifact))
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        port = self._server.server_address[1]
        return f"http://127.0.0.1:{port}/index.html?oneshot-directional-probe=1"

    def __enter__(self) -> "ArtifactServer":
        self._thread.start()
        return self

    def __exit__(self, *_arguments: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path, help="Prepared timestamped run directory")
    parser.add_argument(
        "--browser",
        type=Path,
        help="Compatible Chromium-family executable; overrides ONESHOT_WEBSITES_BROWSER",
    )
    parser.add_argument(
        "--hold-ms",
        type=int,
        default=DEFAULT_HOLD_MILLISECONDS,
        help="How long each independently reset key is held (default: 400)",
    )
    arguments = parser.parse_args(argv)
    if not 100 <= arguments.hold_ms <= 5_000:
        parser.error("--hold-ms must be between 100 and 5000")
    return arguments


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        raw = read_regular_file_bounded(path, METADATA_MAX_BYTES)
        parsed = parse_json_bounded(raw.decode("utf-8"))
    except (BoundedReadError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise VerificationError(f"{label} is unreadable: {path}: {error}") from error
    if not isinstance(parsed, dict):
        raise VerificationError(f"{label} must contain a JSON object: {path}")
    return parsed


def resolve_browser(explicit: Optional[Path]) -> BrowserInfo:
    if explicit is not None:
        candidate = explicit.expanduser()
    else:
        environment = os.environ.get("ONESHOT_WEBSITES_BROWSER")
        if environment:
            candidate = Path(environment).expanduser()
        else:
            candidate = asyncio.run(default_browser_executable())
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise VerificationError(
            f"browser unavailable at {candidate}; run python -m playwright install chromium "
            "or select an explicit ONESHOT_WEBSITES_BROWSER/--browser executable"
        ) from error
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise VerificationError(f"browser must be an executable regular file: {resolved}")
    version_result = subprocess.run(
        [str(resolved), "--version"], text=True, capture_output=True, check=False, timeout=10
    )
    version = version_result.stdout.strip()
    if version_result.returncode != 0 or not version:
        raise VerificationError(f"unable to identify browser {resolved}: {version_result.stderr}")
    return BrowserInfo(resolved, resolved.name, version.splitlines()[0][:200])


async def wait_for_probe(session: BrowserSession) -> None:
    expression = (
        f"document.readyState === 'complete' && "
        f"Boolean(window.{DIRECTIONAL_CONTROL_PROBE_GLOBAL})"
    )
    async with asyncio.timeout(OPERATION_TIMEOUT_SECONDS):
        elapsed = 0
        while True:
            if await session.evaluate(expression) is True:
                return
            if elapsed == PAGE_READY_MILLISECONDS:
                break
            step = min(FRAME_MILLISECONDS, PAGE_READY_MILLISECONDS - elapsed)
            await session.advance(step)
            elapsed += step
    raise VerificationError(
        f"artifact did not expose window.{DIRECTIONAL_CONTROL_PROBE_GLOBAL} after loading"
    )


async def reset_and_sample(session: BrowserSession) -> object:
    return await session.evaluate(
        """
        (async () => {
          const probe = window.%s;
          if (!probe || probe.schemaVersion !== %s) {
            throw new Error('missing or unsupported directional-control probe');
          }
          if (typeof probe.reset !== 'function' || typeof probe.sample !== 'function') {
            throw new Error('directional-control probe requires reset() and sample()');
          }
          await probe.reset();
          await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
          return await probe.sample();
        })()
        """
        % (DIRECTIONAL_CONTROL_PROBE_GLOBAL, json.dumps(DIRECTIONAL_CONTROL_PROBE_SCHEMA))
    )


async def current_sample(session: BrowserSession) -> object:
    return await session.evaluate(
        """
        (async () => {
          const probe = window.%s;
          await new Promise((resolve) => requestAnimationFrame(resolve));
          return await probe.sample();
        })()
        """
        % DIRECTIONAL_CONTROL_PROBE_GLOBAL
    )


def exercise_browser(
    artifact: Path,
    browser: BrowserInfo,
    hold_milliseconds: int,
) -> list[dict[str, object]]:
    with ArtifactServer(artifact) as server:
        return asyncio.run(exercise_keys(server.url, browser.executable, hold_milliseconds))


async def exercise_keys(
    url: str, executable: Path, hold_milliseconds: int
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for check in KEY_CHECKS:
        # Each key gets the same clock, page state, and input history rather than
        # inheriting timers or renderer state from the previous case.
        async with open_browser_session(url, executable) as session:
            await wait_for_probe(session)
            before = parse_directional_sample(await reset_and_sample(session))
            await session.dispatch_key(check.code, "keyDown")
            try:
                await session.advance(hold_milliseconds)
            finally:
                await session.dispatch_key(check.code, "keyUp")
            after = parse_directional_sample(await current_sample(session))
            response = directional_response(before, after)
            results.append({
                "code": check.code,
                "expected": check.expected,
                "frame": before.frame,
                "measurement": response.measurement,
                "response": response.value,
                "passed": response_matches_direction(response.value, check.expected),
            })
    return results


def evidence_path(root: Path, contract: Mapping[str, Any], run_id: str) -> Path:
    expected = f".oneshot-provenance/{run_id}.directional-controls.json"
    if contract.get("evidencePath") != expected:
        raise VerificationError(f"prepared directional-control evidencePath must be exactly {expected}")
    resolved = root / expected
    provenance = root / ".oneshot-provenance"
    try:
        provenance_stat = provenance.lstat()
    except OSError as error:
        raise VerificationError(f"unable to inspect coordinator provenance directory: {error}") from error
    if not stat.S_ISDIR(provenance_stat.st_mode):
        raise VerificationError("coordinator provenance directory must be an ordinary directory")
    return resolved


def write_evidence(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(temporary, flags, 0o644)
    try:
        payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        written = 0
        while written < len(payload):
            written += os.write(descriptor, payload[written:])
        try:
            os.fsync(descriptor)
        except OSError:
            pass
    finally:
        os.close(descriptor)
    try:
        os.replace(temporary, path)
    except OSError:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise


def verification_evidence(
    run_id: str,
    digest: ArtifactTreeDigest,
    browser: Optional[BrowserInfo],
    hold_milliseconds: int,
    checks: Sequence[Mapping[str, Any]],
    error: Optional[str],
) -> dict[str, Any]:
    passed = error is None and len(checks) == len(KEY_CHECKS) and all(
        check.get("passed") is True for check in checks
    )
    return {
        "schemaVersion": DIRECTIONAL_CONTROL_EVIDENCE_SCHEMA,
        "contractVersion": DIRECTIONAL_CONTROL_CONTRACT_VERSION,
        "runId": run_id,
        "verifiedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "artifact": {
            "digestAlgorithm": "oneshot-artifact-tree-v1",
            "sha256": digest.sha256,
            "files": digest.files,
            "bytes": digest.bytes,
        },
        "browser": (
            {"kind": "chromium-cdp", "name": browser.name, "version": browser.version}
            if browser is not None
            else None
        ),
        "input": {
            "transport": "Chrome DevTools Protocol Input.dispatchKeyEvent",
            "holdMs": hold_milliseconds,
            "clock": {"kind": "playwright", "epochSeconds": CLOCK_EPOCH_SECONDS, "frameMs": FRAME_MILLISECONDS},
        },
        "checks": list(checks),
        "passed": passed,
        "error": error,
    }


def verify(arguments: argparse.Namespace) -> tuple[dict[str, Any], Optional[Path]]:
    try:
        run = arguments.run.expanduser().resolve(strict=True)
    except OSError as path_error:
        raise VerificationError(f"unable to resolve run directory: {path_error}") from path_error
    if not run.is_dir() or run.is_symlink():
        raise VerificationError("--run must name an ordinary prepared run directory")
    root = run.parent
    run_id = run.name
    manifest = load_json_object(run / "run.json", "run manifest")
    receipt = load_json_object(root / ".oneshot-provenance" / f"{run_id}.json", "provenance receipt")
    try:
        mode = verification_mode(receipt, manifest)
    except ValueError as error:
        raise VerificationError(str(error)) from error
    if mode == "none":
        raise VerificationError("verificationMode none forbids browser verification; output remains UNVERIFIED")
    contract = receipt.get("directionalControls")
    if not isinstance(contract, Mapping):
        return {
            "status": "not-applicable",
            "reason": "prepared run predates the directional-control verification contract",
        }, None
    interaction = manifest.get("interaction")
    if not isinstance(interaction, Mapping) or interaction.get("directionalControls") != contract:
        raise VerificationError("run directional-control contract differs from its coordinator receipt")
    if contract.get("contractVersion") != DIRECTIONAL_CONTROL_CONTRACT_VERSION:
        raise VerificationError("prepared run uses an unsupported directional-control contract version")
    if contract.get("required") is not True:
        return {"status": "not-required", "signals": contract.get("signals", [])}, None
    output = evidence_path(root, contract, run_id)
    if manifest.get("status") != "OK":
        raise VerificationError("directional-control verification requires a finalized run with status OK")
    report = load_json_object(run / "worker-report.json", "worker report")
    if report.get("status") != "OK":
        raise VerificationError("directional-control verification requires worker-report status OK")
    artifact = run / "artifact"
    digest = artifact_tree_digest(artifact)
    browser: Optional[BrowserInfo] = None
    checks: list[dict[str, Any]] = []
    error: Optional[str] = None
    try:
        browser = resolve_browser(arguments.browser)
        checks = exercise_browser(artifact, browser, arguments.hold_ms)
        if not all(check.get("passed") is True for check in checks):
            failures = ", ".join(
                f"{check.get('code')} observed {check.get('response')}"
                for check in checks
                if check.get("passed") is not True
            )
            error = f"semantic directional-control checks failed: {failures}"
    except TimeoutError:
        error = f"browser operation exceeded its {OPERATION_TIMEOUT_SECONDS}s real-time watchdog"
    except (DirectionalControlError, VerificationError, BrowserError, PlaywrightError, OSError, subprocess.SubprocessError) as caught:
        error = str(caught)
    evidence = verification_evidence(
        run_id,
        digest,
        browser,
        arguments.hold_ms,
        checks,
        error,
    )
    write_evidence(output, evidence)
    return evidence, output


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = parse_arguments(argv)
    try:
        result, output = verify(arguments)
    except (VerificationError, DirectionalControlError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    summary = {
        "status": (
            "passed"
            if result.get("passed") is True
            else "failed"
            if "passed" in result
            else result.get("status")
        ),
        "evidence": str(output) if output is not None else None,
        "checks": result.get("checks", []),
        "error": result.get("error"),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if result.get("passed") is True or output is None else 1


if __name__ == "__main__":
    raise SystemExit(main())

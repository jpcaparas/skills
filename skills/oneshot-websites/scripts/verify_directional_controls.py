#!/usr/bin/env python3
"""Verify semantic left/right controls through a Chromium browser input path."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence
from urllib.request import urlopen

from directional_controls import (
    DIRECTIONAL_CONTROL_CONTRACT_VERSION,
    DIRECTIONAL_CONTROL_EVIDENCE_SCHEMA,
    DIRECTIONAL_CONTROL_PROBE_GLOBAL,
    ArtifactTreeDigest,
    DirectionalControlError,
    artifact_tree_digest,
    directional_response,
    parse_directional_sample,
    response_matches_direction,
)
from runtime_contract import BoundedReadError, parse_json_bounded, read_regular_file_bounded


METADATA_MAX_BYTES = 1024 * 1024
BROWSER_START_TIMEOUT_SECONDS = 15.0
PAGE_READY_TIMEOUT_SECONDS = 15.0
CDP_CALL_TIMEOUT_SECONDS = 15.0
DEFAULT_HOLD_MILLISECONDS = 400


@dataclass(frozen=True)
class KeyCheck:
    """One physical-key case and its required semantic response."""

    code: str
    key: str
    virtual_key: int
    expected: str


@dataclass(frozen=True)
class BrowserInfo:
    """Resolved Chromium-family browser without machine-specific evidence paths."""

    executable: Path
    name: str
    version: str


KEY_CHECKS = (
    KeyCheck("KeyA", "a", 65, "left"),
    KeyCheck("ArrowLeft", "ArrowLeft", 37, "left"),
    KeyCheck("KeyD", "d", 68, "right"),
    KeyCheck("ArrowRight", "ArrowRight", 39, "right"),
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


class WebSocketTransport(AbstractContextManager["WebSocketTransport"]):
    """Minimal RFC 6455 client sufficient for loopback Chrome DevTools JSON."""

    def __init__(self, websocket_url: str, timeout: float) -> None:
        from urllib.parse import urlsplit

        parsed = urlsplit(websocket_url)
        if parsed.scheme != "ws" or parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise VerificationError("browser debugging websocket must use loopback ws://")
        if parsed.port is None:
            raise VerificationError("browser debugging websocket is missing its loopback port")
        self._socket = socket.create_connection((parsed.hostname, parsed.port), timeout=timeout)
        self._socket.settimeout(timeout)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Origin: http://{parsed.hostname}:{parsed.port}\r\n\r\n"
        )
        self._socket.sendall(request.encode("ascii"))
        response = self._read_until(b"\r\n\r\n", 64 * 1024)
        status_line = response.split(b"\r\n", 1)[0]
        if b" 101 " not in status_line:
            raise VerificationError(
                f"browser rejected the debugging websocket handshake: {status_line.decode('latin-1', 'replace')}"
            )
        expected_accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        headers = response.decode("latin-1").split("\r\n")[1:]
        accept = next(
            (
                line.split(":", 1)[1].strip()
                for line in headers
                if line.lower().startswith("sec-websocket-accept:")
            ),
            None,
        )
        if accept != expected_accept:
            raise VerificationError("browser debugging websocket returned an invalid accept header")

    def __enter__(self) -> "WebSocketTransport":
        return self

    def __exit__(self, *_arguments: object) -> None:
        try:
            self._send_frame(0x8, b"")
        except OSError:
            pass
        self._socket.close()

    def send_json(self, value: Mapping[str, object]) -> None:
        payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self._send_frame(0x1, payload)

    def receive_json(self) -> Mapping[str, Any]:
        fragments: list[bytes] = []
        message_opcode: Optional[int] = None
        while True:
            first, second = self._read_exact(2)
            final = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if masked:
                payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
            if opcode == 0x8:
                raise VerificationError("browser closed the debugging websocket")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode in {0x1, 0x2}:
                message_opcode = opcode
                fragments = [payload]
            elif opcode == 0x0 and message_opcode is not None:
                fragments.append(payload)
            else:
                raise VerificationError(f"unexpected browser websocket opcode: {opcode}")
            if not final:
                continue
            if message_opcode != 0x1:
                raise VerificationError("browser debugging websocket returned a non-text message")
            try:
                decoded = json.loads(b"".join(fragments).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise VerificationError(f"browser debugging websocket returned invalid JSON: {error}") from error
            if not isinstance(decoded, Mapping):
                raise VerificationError("browser debugging websocket returned a non-object message")
            return decoded

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        mask = secrets.token_bytes(4)
        length = len(payload)
        header = bytearray([0x80 | opcode])
        if length < 126:
            header.append(0x80 | length)
        elif length <= 0xFFFF:
            header.append(0x80 | 126)
            header.extend(struct.pack(">H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack(">Q", length))
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self._socket.sendall(bytes(header) + mask + masked)

    def _read_exact(self, length: int) -> bytes:
        chunks: list[bytes] = []
        remaining = length
        while remaining:
            chunk = self._socket.recv(remaining)
            if not chunk:
                raise VerificationError("browser debugging websocket closed unexpectedly")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _read_until(self, marker: bytes, limit: int) -> bytes:
        value = bytearray()
        while marker not in value:
            if len(value) >= limit:
                raise VerificationError("browser debugging websocket handshake exceeded its limit")
            chunk = self._socket.recv(min(4096, limit - len(value)))
            if not chunk:
                raise VerificationError("browser closed during the debugging websocket handshake")
            value.extend(chunk)
        return bytes(value)


class CdpSession:
    """Small synchronous Chrome DevTools Protocol session."""

    def __init__(self, transport: WebSocketTransport) -> None:
        self._transport = transport
        self._next_id = 1

    def call(self, method: str, params: Optional[Mapping[str, object]] = None) -> Mapping[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        message: dict[str, object] = {"id": request_id, "method": method}
        if params is not None:
            message["params"] = dict(params)
        self._transport.send_json(message)
        while True:
            response = self._transport.receive_json()
            if response.get("id") != request_id:
                continue
            if "error" in response:
                raise VerificationError(f"browser command {method} failed: {response['error']}")
            result = response.get("result", {})
            if not isinstance(result, Mapping):
                raise VerificationError(f"browser command {method} returned a non-object result")
            return result

    def evaluate(self, expression: str) -> object:
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
                "userGesture": True,
            },
        )
        if "exceptionDetails" in result:
            details = result.get("exceptionDetails")
            raise VerificationError(f"artifact control probe raised an exception: {details}")
        remote = result.get("result")
        if not isinstance(remote, Mapping):
            raise VerificationError("browser evaluation returned no remote result")
        if remote.get("subtype") == "error":
            raise VerificationError(f"artifact control probe returned an error: {remote.get('description')}")
        return remote.get("value")


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
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit.expanduser())
    else:
        environment = os.environ.get("ONESHOT_WEBSITES_BROWSER")
        if environment:
            candidates.append(Path(environment).expanduser())
        for command in (
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "chrome",
            "microsoft-edge",
            "msedge",
        ):
            resolved = shutil.which(command)
            if resolved:
                candidates.append(Path(resolved))
        candidates.extend(
            Path(value)
            for value in (
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            )
        )
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(variable)
            if not base:
                continue
            candidates.extend(
                (
                    Path(base) / "Google/Chrome/Application/chrome.exe",
                    Path(base) / "Chromium/Application/chrome.exe",
                    Path(base) / "Microsoft/Edge/Application/msedge.exe",
                )
            )

    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            mode = resolved.stat().st_mode
        except OSError:
            continue
        if not stat.S_ISREG(mode) or not os.access(resolved, os.X_OK):
            continue
        try:
            version_result = subprocess.run(
                [str(resolved), "--version"],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        version = (version_result.stdout or version_result.stderr).strip()
        if version_result.returncode != 0 or not version:
            continue
        return BrowserInfo(resolved, resolved.name, version.splitlines()[0][:200])
    raise VerificationError(
        "no compatible Chromium-family browser found; set ONESHOT_WEBSITES_BROWSER or pass --browser"
    )


def wait_for_debug_port(profile: Path, process: subprocess.Popen[bytes]) -> int:
    marker = profile / "DevToolsActivePort"
    deadline = time.monotonic() + BROWSER_START_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise VerificationError(f"browser exited before opening its debugging port ({process.returncode})")
        try:
            lines = marker.read_text(encoding="utf-8").splitlines()
        except OSError:
            time.sleep(0.05)
            continue
        if lines and lines[0].isdigit():
            return int(lines[0])
        time.sleep(0.05)
    raise VerificationError("browser did not expose its loopback debugging port in time")


def page_websocket(port: int, expected_url: str) -> str:
    deadline = time.monotonic() + PAGE_READY_TIMEOUT_SECONDS
    endpoint = f"http://127.0.0.1:{port}/json/list"
    while time.monotonic() < deadline:
        try:
            with urlopen(endpoint, timeout=2) as response:
                pages = json.loads(response.read().decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            time.sleep(0.05)
            continue
        if isinstance(pages, list):
            for page in pages:
                if not isinstance(page, Mapping) or page.get("type") != "page":
                    continue
                url = page.get("url")
                websocket = page.get("webSocketDebuggerUrl")
                if isinstance(url, str) and url.startswith(expected_url) and isinstance(websocket, str):
                    return websocket
        time.sleep(0.05)
    raise VerificationError("browser did not expose the artifact page debugging target in time")


def wait_for_probe(session: CdpSession) -> None:
    deadline = time.monotonic() + PAGE_READY_TIMEOUT_SECONDS
    expression = (
        f"document.readyState === 'complete' && "
        f"Boolean(window.{DIRECTIONAL_CONTROL_PROBE_GLOBAL})"
    )
    while time.monotonic() < deadline:
        if session.evaluate(expression) is True:
            return
        time.sleep(0.05)
    raise VerificationError(
        f"artifact did not expose window.{DIRECTIONAL_CONTROL_PROBE_GLOBAL} after loading"
    )


def reset_and_sample(session: CdpSession) -> object:
    return session.evaluate(
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
        % (DIRECTIONAL_CONTROL_PROBE_GLOBAL, json.dumps(DIRECTIONAL_CONTROL_CONTRACT_VERSION))
    )


def current_sample(session: CdpSession) -> object:
    return session.evaluate(
        """
        (async () => {
          const probe = window.%s;
          await new Promise((resolve) => requestAnimationFrame(resolve));
          return await probe.sample();
        })()
        """
        % DIRECTIONAL_CONTROL_PROBE_GLOBAL
    )


def dispatch_key(session: CdpSession, check: KeyCheck, event_type: str) -> None:
    session.call(
        "Input.dispatchKeyEvent",
        {
            "type": event_type,
            "key": check.key,
            "code": check.code,
            "windowsVirtualKeyCode": check.virtual_key,
            "nativeVirtualKeyCode": check.virtual_key,
            "autoRepeat": False,
            "isKeypad": False,
        },
    )


def exercise_browser(
    artifact: Path,
    browser: BrowserInfo,
    hold_milliseconds: int,
) -> list[dict[str, Any]]:
    with ArtifactServer(artifact) as server, tempfile.TemporaryDirectory(
        prefix="oneshot-directional-browser-"
    ) as profile_value:
        profile = Path(profile_value)
        command = [
            str(browser.executable),
            "--headless=new",
            "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=0",
            "--remote-allow-origins=*",
            f"--user-data-dir={profile}",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--metrics-recording-only",
            "--mute-audio",
            "--no-default-browser-check",
            "--no-first-run",
        ]
        if os.name == "posix" and hasattr(os, "geteuid") and os.geteuid() == 0:
            command.append("--no-sandbox")
        command.append(server.url)
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            port = wait_for_debug_port(profile, process)
            websocket_url = page_websocket(port, server.url)
            with WebSocketTransport(websocket_url, CDP_CALL_TIMEOUT_SECONDS) as transport:
                session = CdpSession(transport)
                session.call("Runtime.enable")
                session.call("Page.enable")
                session.call("Page.bringToFront")
                wait_for_probe(session)
                session.evaluate("window.focus(); if (document.body) document.body.focus(); true")
                results: list[dict[str, Any]] = []
                for check in KEY_CHECKS:
                    before = parse_directional_sample(reset_and_sample(session))
                    dispatch_key(session, check, "keyDown")
                    try:
                        time.sleep(hold_milliseconds / 1000)
                    finally:
                        dispatch_key(session, check, "keyUp")
                    after = parse_directional_sample(current_sample(session))
                    response = directional_response(before, after)
                    passed = response_matches_direction(response.value, check.expected)
                    results.append(
                        {
                            "code": check.code,
                            "expected": check.expected,
                            "frame": before.frame,
                            "measurement": response.measurement,
                            "response": response.value,
                            "passed": passed,
                        }
                    )
                return results
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


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
        "input": {"transport": "Chrome DevTools Protocol Input.dispatchKeyEvent", "holdMs": hold_milliseconds},
        "checks": list(checks),
        "passed": passed,
        "error": error,
    }


def verify(arguments: argparse.Namespace) -> tuple[dict[str, Any], Optional[Path]]:
    try:
        run = arguments.run.expanduser().resolve(strict=True)
    except OSError as error:
        raise VerificationError(f"unable to resolve run directory: {error}") from error
    if not run.is_dir() or run.is_symlink():
        raise VerificationError("--run must name an ordinary prepared run directory")
    root = run.parent
    run_id = run.name
    manifest = load_json_object(run / "run.json", "run manifest")
    receipt = load_json_object(root / ".oneshot-provenance" / f"{run_id}.json", "provenance receipt")
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
    except (DirectionalControlError, VerificationError, OSError, subprocess.SubprocessError) as caught:
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

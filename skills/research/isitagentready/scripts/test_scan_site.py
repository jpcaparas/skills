#!/usr/bin/env python3
"""Offline regressions for scan_site.py against a local stub of the scan endpoint.

These tests never contact isitagentready.com.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_site

TARGET = "https://shop.example.com/pricing?ref=nav"

# Mirrors the response shape observed for example.com on 2026-11-10.
SCAN_RESPONSE = {
    "url": "https://shop.example.com/pricing",
    "level": 2,
    "levelName": "Bot-Aware",
    "checks": {
        "discoverability": {"robotsTxt": {"status": "pass"}, "dnsAid": {"status": "fail"}},
        "contentAccessibility": {"markdownNegotiation": {"status": "fail"}},
    },
    "nextLevel": {"level": 3, "requirements": ["markdownNegotiation"]},
    "isCommerce": False,
    "commerceSignals": [],
}


class StubScanner(BaseHTTPRequestHandler):
    """Records every request and replies with the queued status and body."""

    requests: list[dict] = []
    reply: tuple[int, str, bytes] = (200, "application/json", b"{}")

    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        length = int(self.headers.get("Content-Length", "0"))
        type(self).requests.append(
            {"path": self.path, "headers": dict(self.headers), "body": self.rfile.read(length)}
        )
        status, content_type, body = type(self).reply
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


class ScanSiteTest(unittest.TestCase):
    def setUp(self) -> None:
        StubScanner.requests = []
        StubScanner.reply = (200, "application/json", json.dumps(SCAN_RESPONSE).encode())
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), StubScanner)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.workdir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(
            mock.patch.object(scan_site, "SCAN_URL", f"http://127.0.0.1:{self.server.server_port}/api/scan")
        )

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["scan_site.py", *argv]),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = scan_site.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_sends_only_the_target_url_and_prints_the_full_scan(self) -> None:
        code, stdout, _ = self.run_cli("--url", TARGET)

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), SCAN_RESPONSE)
        (sent,) = StubScanner.requests
        self.assertEqual(sent["path"], "/api/scan")
        self.assertEqual(json.loads(sent["body"]), {"url": TARGET})
        header_names = {name.lower() for name in sent["headers"]}
        self.assertFalse(header_names & {"cookie", "authorization"}, header_names)

    def test_output_writes_the_full_scan_and_prints_a_level_summary(self) -> None:
        output = self.workdir / "nested" / "scan-results.json"

        code, stdout, _ = self.run_cli("--url", TARGET, "--output", str(output))

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), SCAN_RESPONSE)
        self.assertEqual(
            json.loads(stdout),
            {
                "url": SCAN_RESPONSE["url"],
                "level": 2,
                "levelName": "Bot-Aware",
                "output": str(output.resolve()),
            },
        )

    def test_non_http_target_is_rejected_before_any_request(self) -> None:
        for target in ("shop.example.com", "file:///etc/hosts", "ftp://shop.example.com"):
            with self.subTest(target=target):
                code, stdout, stderr = self.run_cli("--url", target)

                self.assertEqual((code, stdout), (1, ""))
                self.assertIn("must start with http:// or https://", stderr)
        self.assertEqual(StubScanner.requests, [])

    def test_scanner_failure_reports_the_status_and_writes_no_file(self) -> None:
        StubScanner.reply = (429, "application/json", b'{"error":"rate limited"}')
        output = self.workdir / "scan-results.json"

        code, stdout, stderr = self.run_cli("--url", TARGET, "--output", str(output))

        self.assertEqual((code, stdout), (1, ""))
        self.assertIn("429", stderr)
        self.assertFalse(output.exists())

    def test_challenge_page_instead_of_json_fails_without_writing_a_file(self) -> None:
        StubScanner.reply = (200, "text/html", b"<html><title>Just a moment...</title></html>")
        output = self.workdir / "scan-results.json"

        code, stdout, stderr = self.run_cli("--url", TARGET, "--output", str(output))

        self.assertEqual((code, stdout), (1, ""))
        self.assertIn("scan_site.py error", stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()

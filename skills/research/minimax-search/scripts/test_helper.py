#!/usr/bin/env python3
"""Offline regressions for scripts/search.js against a local stub of the MiniMax API.

These tests never contact api.minimax.io and never read an ambient MINIMAX_API_KEY.
"""

from __future__ import annotations

import json
import os
import shutil
import socketserver
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "search.js"
FAKE_KEY = "test-key-not-real"
SEARCH_PATH = "/v1/coding_plan/search"
QUOTA_PATH = "/v1/api/openplatform/coding_plan/remains"

# Mirrors the live shape observed on 2026-10-18: up to 10 organic results, `date` often "",
# related_searches as {query} objects, and success signalled by base_resp.status_code 0.
SEARCH_RESPONSE = {
    "organic": [
        {"title": f"Result {i}", "link": f"https://example.com/{i}", "snippet": f"snippet {i}", "date": "" if i % 2 else "3 hours ago"}
        for i in range(10)
    ],
    "related_searches": [{"query": "tokio cancellation token"}, {"query": "select! macro"}],
    "base_resp": {"status_code": 0, "status_msg": "success"},
}
QUOTA_RESPONSE = {
    "model_remains": [
        {
            "model_name": "general",
            "end_time": 1792317600000,
            "remains_time": 3_900_000,
            "current_interval_remaining_percent": 62,
            "weekly_remains_time": 51_600_000,
            "current_weekly_remaining_percent": 100,
        },
        {"model_name": "video", "current_interval_remaining_percent": 100},
    ],
    "base_resp": {"status_code": 0, "status_msg": "success"},
}


class LoopbackHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer without the reverse-DNS lookup of its bind address.

    HTTPServer.server_bind calls socket.getfqdn(host), a reverse-DNS lookup that
    can stall for tens of seconds on macOS. A loopback stub never needs the name.
    """

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def base_resp(code: int, message: str) -> bytes:
    return json.dumps({"base_resp": {"status_code": code, "status_msg": message}}).encode()


class StubMiniMax(BaseHTTPRequestHandler):
    """Records requests and replays queued responses per path (last one repeats)."""

    requests: list[dict] = []
    responses: dict[str, list[tuple[int, bytes]]] = {}

    def _reply(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        StubMiniMax.requests.append(
            {"method": self.command, "path": self.path, "authorization": self.headers.get("Authorization"),
             "body": json.loads(body) if body else None}
        )
        queue = StubMiniMax.responses[self.path]
        status, payload = queue.pop(0) if len(queue) > 1 else queue[0]
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = _reply
    do_POST = _reply

    def log_message(self, *_args) -> None:
        pass


class MiniMaxSearchHelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.node = shutil.which(os.environ.get("SKILLS_VALIDATION_NODE", "node"))
        if not cls.node:
            raise RuntimeError("Node.js is required to test scripts/search.js; set SKILLS_VALIDATION_NODE if it is not on PATH.")
        cls.server = LoopbackHTTPServer(("127.0.0.1", 0), StubMiniMax)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.host = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self) -> None:
        StubMiniMax.requests = []
        StubMiniMax.responses = {
            SEARCH_PATH: [(200, json.dumps(SEARCH_RESPONSE).encode())],
            QUOTA_PATH: [(200, json.dumps(QUOTA_RESPONSE).encode())],
        }

    def run_helper(self, *args: str, api_key: str | None = FAKE_KEY) -> subprocess.CompletedProcess:
        env = {key: value for key, value in os.environ.items() if key not in ("MINIMAX_API_KEY", "MINIMAX_API_HOST")}
        env["MINIMAX_API_HOST"] = self.host
        if api_key is not None:
            env["MINIMAX_API_KEY"] = api_key
        return subprocess.run([self.node, str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=120)

    def search_requests(self) -> list[dict]:
        return [request for request in StubMiniMax.requests if request["path"] == SEARCH_PATH]

    def test_sends_q_with_operators_and_bearer_auth(self) -> None:
        result = self.run_helper("--site", "github.com", "--exclude-site", "gist.github.com", "tokio", "select")
        self.assertEqual(result.returncode, 0, result.stderr)
        request = self.search_requests()[0]
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["body"], {"q": "tokio select site:github.com -site:gist.github.com"})
        self.assertEqual(request["authorization"], f"Bearer {FAKE_KEY}")

    def test_second_site_is_rejected_because_minimax_honours_only_the_first(self) -> None:
        result = self.run_helper("--site", "github.com", "--site", "gitlab.com", "fastapi")
        self.assertEqual(result.returncode, 2)
        self.assertIn("only the first site:", result.stderr)
        self.assertEqual(StubMiniMax.requests, [])

    def test_word_limit_counts_appended_operators(self) -> None:
        words = " ".join(f"w{i}" for i in range(31))
        at_limit = self.run_helper(words, "--site", "github.com")
        self.assertEqual(at_limit.returncode, 0, at_limit.stderr)
        over = self.run_helper(words + " extra", "--site", "github.com")
        self.assertEqual(over.returncode, 2)
        self.assertIn("33 words", over.stderr)
        self.assertEqual(len(self.search_requests()), 1)

    def test_character_limit_counts_code_points_not_bytes(self) -> None:
        # 2,048 CJK characters are about 6 KB of UTF-8 yet still accepted live.
        at_limit = self.run_helper("東" * 2048)
        self.assertEqual(at_limit.returncode, 0, at_limit.stderr)
        over = self.run_helper("東" * 2049)
        self.assertEqual(over.returncode, 2)
        self.assertIn("2049 characters", over.stderr)

    def test_blank_queries_never_reach_the_api(self) -> None:
        for query in ("", "   ", "\n\t"):
            with self.subTest(query=repr(query)):
                self.assertEqual(self.run_helper(query).returncode, 2)
        self.assertEqual(StubMiniMax.requests, [])

    def test_error_1027_is_reported_as_zero_results_not_a_failure(self) -> None:
        StubMiniMax.responses[SEARCH_PATH] = [(200, base_resp(1027, "output new_sensitive"))]
        compact = self.run_helper("--compact", "site:example.invalid python")
        self.assertEqual(compact.returncode, 0, compact.stderr)
        self.assertEqual(json.loads(compact.stdout)["results"], [])

    def test_rate_limit_is_retried_then_succeeds(self) -> None:
        # Retry delays are real, so one retry keeps this test at about five seconds.
        StubMiniMax.responses[SEARCH_PATH] = [
            (200, base_resp(1002, "rate limit exceeded(RPM)")),
            (200, json.dumps(SEARCH_RESPONSE).encode()),
        ]
        result = self.run_helper("--urls", "-n", "2", "rust async")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["https://example.com/0", "https://example.com/1"])
        self.assertEqual(len(self.search_requests()), 2)
        self.assertIn("Rate limited (1002)", result.stderr)

    def test_rate_limit_without_retries_fails_with_guidance(self) -> None:
        StubMiniMax.responses[SEARCH_PATH] = [(200, base_resp(2062, "Token Plan rate limit reached"))]
        result = self.run_helper("--retries", "0", "rust async")
        self.assertEqual(result.returncode, 1)
        self.assertIn("MiniMax error 2062", result.stderr)
        self.assertIn("wait about a minute", result.stderr)

    def test_http_200_auth_failure_is_an_error_with_region_hint(self) -> None:
        StubMiniMax.responses[SEARCH_PATH] = [(200, base_resp(1004, "login fail"))]
        result = self.run_helper("rust async")
        self.assertEqual(result.returncode, 1)
        self.assertIn("MiniMax error 1004", result.stderr)
        self.assertIn("api.minimax.io", result.stderr)

    def test_compact_normalises_empty_dates_and_keeps_related_searches(self) -> None:
        result = self.run_helper("--compact", "-n", "2", "rust async")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual([item["date"] for item in payload["results"]], ["3 hours ago", None])
        self.assertEqual(payload["related_searches"], ["tokio cancellation token", "select! macro"])

    def test_missing_key_fails_without_a_request(self) -> None:
        result = self.run_helper("rust async", api_key=None)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(StubMiniMax.requests, [])

    def test_quota_reports_the_general_bucket(self) -> None:
        result = self.run_helper("quota")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("5-hour window: 62% remaining, resets in 1h 5m", result.stdout)
        self.assertIn("Weekly window: 100% remaining", result.stdout)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Offline regressions for scripts/search.js against a local stub of the Synthetic API.

These tests never contact api.synthetic.new and never read an ambient SYNTHETIC_API_KEY.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "search.js"
FAKE_KEY = "test-key-not-real"

# Mirrors the live response shape observed on 2026-10-18: five results, `highlights` is a
# one-element list, `published` is usually absent, and `text` can be very large.
SEARCH_RESPONSE = {
    "results": [
        {
            "url": f"https://example.com/{index}",
            "title": "" if index == 4 else f"Result {index}",
            "text": f"full page text {index} " * 50,
            "highlights": [f"relevant excerpt {index}"],
            **({"published": "2024-08-05T00:00:00.000Z"} if index == 1 else {}),
        }
        for index in range(5)
    ]
}
QUOTAS_RESPONSE = {
    "subscription": {"limit": 2750, "requests": 0, "renewsAt": "2026-10-18T10:00:00.000Z"},
    "search": {"hourly": {"limit": 250, "requests": 42, "renewsAt": "2026-10-18T06:42:29.000Z"}},
}


class StubSynthetic(BaseHTTPRequestHandler):
    """Records every request; replies with the queued response for its path."""

    requests: list[dict] = []
    responses: dict[str, tuple[int, dict[str, str], bytes]] = {}

    def _reply(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        StubSynthetic.requests.append(
            {
                "method": self.command,
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "body": json.loads(body) if body else None,
            }
        )
        status, headers, payload = StubSynthetic.responses[self.path]
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = _reply
    do_POST = _reply

    def log_message(self, *_args) -> None:
        pass


class SearchHelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.node = shutil.which(os.environ.get("SKILLS_VALIDATION_NODE", "node"))
        if not cls.node:
            raise RuntimeError("Node.js is required to test scripts/search.js; set SKILLS_VALIDATION_NODE if it is not on PATH.")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), StubSynthetic)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}/v2"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self) -> None:
        StubSynthetic.requests = []
        self.raw_search = json.dumps(SEARCH_RESPONSE).encode()
        StubSynthetic.responses = {
            "/v2/search": (200, {"Content-Type": "application/json"}, self.raw_search),
            "/v2/quotas": (200, {"Content-Type": "application/json"}, json.dumps(QUOTAS_RESPONSE).encode()),
        }

    def run_helper(self, *args: str, api_key: str | None = FAKE_KEY) -> subprocess.CompletedProcess:
        env = {key: value for key, value in os.environ.items() if key != "SYNTHETIC_API_KEY"}
        env["SYNTHETIC_API_BASE_URL"] = self.base_url
        if api_key is not None:
            env["SYNTHETIC_API_KEY"] = api_key
        return subprocess.run(
            [self.node, str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=30
        )

    def sent_queries(self) -> list[str]:
        return [request["body"]["query"] for request in StubSynthetic.requests if request["path"] == "/v2/search"]

    def test_site_flags_become_query_operators_because_body_parameters_are_ignored(self) -> None:
        result = self.run_helper(
            "--site", "docs.rs", "--site", "github.com", "--exclude-site", "github.com/tokio-rs", "tokio", "select"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            StubSynthetic.requests[0]["body"],
            {"query": "tokio select site:docs.rs site:github.com -site:github.com/tokio-rs"},
        )
        self.assertEqual(StubSynthetic.requests[0]["authorization"], f"Bearer {FAKE_KEY}")

    def test_blank_queries_are_rejected_before_spending_quota(self) -> None:
        # Live API: "" returns a blank 500 and whitespace returns unrelated news; both are billed.
        for query in ("", "   ", "\t\n"):
            with self.subTest(query=repr(query)):
                result = self.run_helper(query)
                self.assertEqual(result.returncode, 2)
                self.assertIn("non-whitespace", result.stderr)
        self.assertEqual(StubSynthetic.requests, [])

    def test_operator_only_query_is_rejected(self) -> None:
        result = self.run_helper("--site", "github.com")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(StubSynthetic.requests, [])

    def test_query_limit_is_4096_characters_including_appended_operators(self) -> None:
        operator = " site:github.com"
        at_limit = self.run_helper("a" * (4096 - len(operator)), "--site", "github.com")
        self.assertEqual(at_limit.returncode, 0, at_limit.stderr)
        self.assertEqual(len(self.sent_queries()[0]), 4096)

        over_limit = self.run_helper("a" * (4097 - len(operator)), "--site", "github.com")
        self.assertEqual(over_limit.returncode, 2)
        self.assertIn("4097 characters", over_limit.stderr)
        self.assertEqual(len(self.sent_queries()), 1)

    def test_limit_counts_characters_not_utf8_bytes(self) -> None:
        # 2,000 CJK characters are ~6,000 UTF-8 bytes; live testing showed the cut is by characters.
        result = self.run_helper("非" * 2000)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_compact_output_drops_full_text_and_normalises_missing_fields(self) -> None:
        result = self.run_helper("--compact", "-n", "5", "rust async")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["query"], "rust async")
        self.assertEqual(len(payload["results"]), 5)
        self.assertNotIn("text", payload["results"][0])
        self.assertEqual(payload["results"][0]["published"], None)
        self.assertEqual(payload["results"][1]["published"], "2024-08-05T00:00:00.000Z")
        self.assertEqual(payload["results"][4]["title"], None)
        self.assertEqual(payload["results"][2]["highlights"], ["relevant excerpt 2"])

    def test_limit_trims_display_without_changing_the_request(self) -> None:
        result = self.run_helper("--urls", "-n", "2", "rust async")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["https://example.com/0", "https://example.com/1"])
        self.assertEqual(StubSynthetic.requests[0]["body"], {"query": "rust async"})

    def test_save_writes_the_untouched_response_for_later_reads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "results.json"
            result = self.run_helper("--compact", "-n", "1", "--save", str(target), "rust async")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_bytes(), self.raw_search)

    def test_readable_output_shows_highlights_and_only_real_published_dates(self) -> None:
        result = self.run_helper("-n", "2", "rust async")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("relevant excerpt 0", result.stdout)
        self.assertEqual(result.stdout.count("Published:"), 1)
        self.assertNotIn("full page text", result.stdout)

    def test_blank_500_reports_quota_cost_hint(self) -> None:
        StubSynthetic.responses["/v2/search"] = (500, {}, b"")
        result = self.run_helper("rust async")
        self.assertEqual(result.returncode, 1)
        self.assertIn("HTTP 500", result.stderr)
        self.assertIn("(empty response body)", result.stderr)
        self.assertIn("still count against the hourly search quota", result.stderr)

    def test_exhausted_quota_reports_when_search_renews(self) -> None:
        # Live 429 body from 2026-10-18; Synthetic sends no Retry-After, so the helper asks /quotas.
        StubSynthetic.responses["/v2/search"] = (
            429,
            {"Content-Type": "application/json"},
            b'{"error":"You\'ve used up your hourly quota for the search API"}',
        )
        result = self.run_helper("rust async")
        self.assertEqual(result.returncode, 1)
        self.assertIn("HTTP 429", result.stderr)
        self.assertIn("used up your hourly quota", result.stderr)
        self.assertIn("Search quota renews at 2026-10-18T06:42:29.000Z.", result.stderr)
        self.assertEqual([request["path"] for request in StubSynthetic.requests], ["/v2/search", "/v2/quotas"])

    def test_exhausted_quota_still_fails_cleanly_when_quotas_lookup_fails(self) -> None:
        StubSynthetic.responses["/v2/search"] = (429, {}, b'{"error":"quota"}')
        StubSynthetic.responses["/v2/quotas"] = (500, {}, b"")
        result = self.run_helper("rust async")
        self.assertEqual(result.returncode, 1)
        self.assertIn("HTTP 429", result.stderr)
        self.assertNotIn("renews at", result.stderr)

    def test_missing_api_key_fails_without_a_request(self) -> None:
        result = self.run_helper("rust async", api_key=None)
        self.assertEqual(result.returncode, 2)
        self.assertIn("SYNTHETIC_API_KEY", result.stderr)
        self.assertEqual(StubSynthetic.requests, [])

    def test_quotas_summary_leads_with_the_hourly_search_bucket(self) -> None:
        result = self.run_helper("quotas")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Search (hourly): 42/250 used (renews 2026-10-18T06:42:29.000Z)", result.stdout.splitlines()[1])


if __name__ == "__main__":
    unittest.main()

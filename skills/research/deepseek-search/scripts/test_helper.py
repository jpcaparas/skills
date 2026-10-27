#!/usr/bin/env python3
"""Offline regressions for scripts/deepseek_search.js against a local stub of DeepSeek's
Search, Fetch, and balance endpoints.

These tests never contact api.deepseek.com and never read an ambient DEEPSEEK_API_KEY.
"""

from __future__ import annotations

import json
import os
import shutil
import socketserver
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "deepseek_search.js"
FAKE_KEY = "sk-test-not-real-0123456789abcdef"


class LoopbackHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer without the reverse-DNS lookup of its bind address.

    HTTPServer.server_bind calls socket.getfqdn(host), a reverse-DNS lookup that
    can stall for tens of seconds on macOS. A loopback stub never needs the name.
    """

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def result(url: str, *, date: str | None = "2026-08-12T16:00:00+00:00", title: str | None = None) -> dict:
    """One search result in the live 2026-10-18 shape."""
    return {
        "title": title or f"Title for {url}",
        "site_name": "Example",
        "site_icon": "https://cdn.deepseek.com/site-icons/example.com",
        "authority": 3,
        "rerank_score": 2.226604461669922,
        "date": date,
        "url": url,
        "summary": "s" * 2_000,
        "snippet": "p" * 1_500,
        "content": "",
    }


def error(message: str, status_type: str = "invalid_request_error") -> dict:
    return {"error": {"message": f"{message} (request_id: 00000000-0000-0000-0000-000000000000)", "type": status_type,
                      "param": None, "code": status_type}}


class StubDeepSeek(BaseHTTPRequestHandler):
    requests: list[dict] = []
    # Per path, a queue of (status, payload) replies; the last reply repeats once the queue drains.
    replies: dict[str, list[tuple[int, dict]]] = {}
    by_query: dict[str, tuple[int, dict]] = {}

    def _reply(self, path: str, body: dict | None) -> None:
        if body and path == "/v1/tools/search" and body.get("query") in StubDeepSeek.by_query:
            status, payload = StubDeepSeek.by_query[body["query"]]
        else:
            queue = StubDeepSeek.replies.get(path) or [(404, {})]
            status, payload = queue.pop(0) if len(queue) > 1 else queue[0]
        encoded = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _record(self, body: dict | None) -> None:
        StubDeepSeek.requests.append({"method": self.command, "path": self.path, "body": body, "at": time.monotonic(),
                                      "authorization": self.headers.get("Authorization")})

    def do_GET(self) -> None:
        self._record(None)
        self._reply(self.path, None)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"null")
        self._record(body)
        self._reply(self.path, body)

    def log_message(self, *_args) -> None:
        pass


class DeepSeekHelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.node = shutil.which(os.environ.get("SKILLS_VALIDATION_NODE", "node"))
        if not cls.node:
            raise RuntimeError("Node.js is required to test scripts/deepseek_search.js; set SKILLS_VALIDATION_NODE if it is not on PATH.")
        cls.server = LoopbackHTTPServer(("127.0.0.1", 0), StubDeepSeek)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.root = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self) -> None:
        StubDeepSeek.requests = []
        StubDeepSeek.by_query = {}
        StubDeepSeek.replies = {
            "/v1/tools/search": [(200, {"results": [result("https://example.com/a"), result("https://example.com/b")]})],
            "/v1/tools/fetch": [(200, {"title": "Page", "content": "x" * 50_000})],
            "/user/balance": [(200, {"is_available": True, "balance_infos": [
                {"currency": "USD", "total_balance": "2.61", "granted_balance": "0.00", "topped_up_balance": "2.61"}]})],
        }

    def run_helper(self, *args: str, api_key: str | None = FAKE_KEY, script: Path = SCRIPT) -> subprocess.CompletedProcess:
        env = {key: value for key, value in os.environ.items() if key not in ("DEEPSEEK_API_KEY", "DEEPSEEK_API_ROOT")}
        env["DEEPSEEK_API_ROOT"] = self.root
        if api_key is not None:
            env["DEEPSEEK_API_KEY"] = api_key
        return subprocess.run([self.node, str(script), *args], env=env, capture_output=True, text=True, timeout=60)

    def searches(self) -> list[dict]:
        return [r for r in StubDeepSeek.requests if r["path"] == "/v1/tools/search"]

    def test_flags_compose_documented_operators_and_request_fields(self) -> None:
        result_ = self.run_helper(
            "search", "--compact", "--site", "github.com/tokio-rs", "--site", "docs.rs", "--exclude-site", "reddit.com",
            "--lang", "zh,en", "--after", "2026", "--before", "2026-10-01", "-c", "25", "--question", "How does select work?",
            "--loc", "2001:4860:4860::8888", "--content", "tokio", "select",
        )
        self.assertEqual(result_.returncode, 0, result_.stderr)
        request = self.searches()[0]
        self.assertEqual(request["authorization"], f"Bearer {FAKE_KEY}")
        self.assertEqual(request["body"], {
            # A bare year in after: means "after the end of that year" upstream, so 2026 becomes 2026-01-01.
            "query": "tokio select site:github.com/tokio-rs OR site:docs.rs -site:reddit.com lang:zh,en after:2026-01-01 before:2026-10-01",
            "count": 25,
            "ori_question": "How does select work?",
            "localization": "2001:4860:4860::8888",
            "need_content": True,
        })

    def test_defaults_send_only_query_and_count(self) -> None:
        result_ = self.run_helper("search", "--urls", "rust")
        self.assertEqual(result_.returncode, 0, result_.stderr)
        self.assertEqual(self.searches()[0]["body"], {"query": "rust", "count": 10})

    def test_query_limit_counts_code_points_including_operators(self) -> None:
        # Live: 128 emoji passed and 129 ASCII or CJK characters failed, so the unit is code points, not UTF-16.
        self.assertEqual(self.run_helper("search", "--urls", "😀" * 128).returncode, 0)
        self.assertEqual(self.searches()[-1]["body"]["query"], "😀" * 128)
        too_long = self.run_helper("search", "界" * 129)
        self.assertEqual(too_long.returncode, 2)
        self.assertIn("129 characters", too_long.stderr)
        with_operator = self.run_helper("search", "--site", "github.com", "a" * 115)
        self.assertEqual(with_operator.returncode, 2)
        self.assertIn("including operators", with_operator.stderr)
        self.assertEqual(len(self.searches()), 1)

    def test_invalid_input_is_rejected_before_any_request(self) -> None:
        cases = [
            ("search", "   "),
            ("search", "-c", "0", "rust"),
            ("search", "-c", "51", "rust"),
            ("search", "-c", "5.0", "rust"),
            ("search", "--after", "2026-02-30", "rust"),
            ("search", "--before", "last-week", "rust"),
            ("search", "--lang", "english", "rust"),
            ("search", "--loc", "999.1.1.1", "rust"),
            ("search", "--site", "https://github.com", "rust"),
            ("search", "--site", "site:github.com", "rust"),
            ("search", "--question", "q" * 129, "rust"),
            ("search", "--file", "queries.txt", "rust"),
            ("batch", "--json", "rust"),
            ("batch",),
            ("fetch", "https://user:pass@example.com/"),
            ("fetch", "ftp://example.com/file"),
            ("fetch", "https:///path"),
            ("fetch", "example.com"),
            ("fetch", "https://example.com/" + "a" * 8_200),
            ("search", "--unknown", "rust"),
        ]
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(self.run_helper(*args).returncode, 2)
        self.assertEqual(StubDeepSeek.requests, [])

    def test_dates_shift_beijing_midnight_to_the_publication_day(self) -> None:
        StubDeepSeek.replies["/v1/tools/search"] = [(200, {"results": [
            result("https://example.com/beijing", date="2026-08-12T16:00:00+00:00"),
            result("https://example.com/utc", date="2026-08-12T00:00:00+00:00"),
            result("https://example.com/none", date=None),
        ]})]
        payload = json.loads(self.run_helper("search", "--compact", "pg").stdout)
        self.assertEqual([item["published"] for item in payload["results"]], ["2026-08-13", "2026-08-12", None])

    def test_compact_output_clips_text_and_merges_fragment_duplicates(self) -> None:
        StubDeepSeek.replies["/v1/tools/search"] = [(200, {"results": [
            result("https://example.com/doc#install"), result("https://example.com/doc#usage"),
            result("https://example.com/doc?page=2"), result("https://other.example/doc"),
        ]})]
        result_ = self.run_helper("search", "--compact", "--summary-chars", "50", "doc")
        self.assertEqual(result_.returncode, 0, result_.stderr)
        payload = json.loads(result_.stdout)
        self.assertEqual(payload["returned"], 4)
        self.assertEqual([item["url"] for item in payload["results"]],
                         ["https://example.com/doc#install", "https://example.com/doc?page=2", "https://other.example/doc"])
        self.assertIn("Merged 1 duplicate", result_.stderr)
        first = payload["results"][0]
        self.assertEqual((len(first["summary"]), len(first["snippet"])), (53, 53))
        self.assertEqual((first["score"], first["authority"]), (2.23, 3))

    def test_save_keeps_the_full_raw_response(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "raw.json"
            result_ = self.run_helper("search", "--urls", "--save", str(target), "doc")
            self.assertEqual(result_.returncode, 0, result_.stderr)
            saved = json.loads(target.read_text())
        self.assertEqual(len(saved["results"][0]["summary"]), 2_000)

    def test_empty_results_explain_free_and_likely_cause(self) -> None:
        StubDeepSeek.replies["/v1/tools/search"] = [(200, {"results": []})]
        result_ = self.run_helper("search", "--lang", "xx", "rust")
        self.assertEqual(result_.returncode, 0)
        self.assertIn("not billed", result_.stderr)
        self.assertIn("Unknown lang", result_.stderr)

    def test_rate_limit_is_retried_but_bad_requests_are_not(self) -> None:
        StubDeepSeek.replies["/v1/tools/search"] = [
            (429, error("Too many requests. Please pace your requests reasonably", "rate_limit_error")),
            (200, {"results": [result("https://example.com/a")]}),
        ]
        retried = self.run_helper("search", "--urls", "rust")
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertEqual(retried.stdout.split(), ["https://example.com/a"])
        self.assertIn("HTTP 429", retried.stderr)
        self.assertEqual(len(self.searches()), 2)

        StubDeepSeek.requests = []
        StubDeepSeek.replies["/v1/tools/search"] = [(400, error("'count' must be between 1 and 50"))]
        rejected = self.run_helper("search", "rust")
        self.assertEqual(rejected.returncode, 1)
        self.assertIn("'count' must be between 1 and 50", rejected.stderr)
        self.assertEqual(len(self.searches()), 1)

    def test_retries_stop_after_three_and_report_the_pacing_hint(self) -> None:
        StubDeepSeek.replies["/v1/tools/search"] = [(429, error("Too many requests", "rate_limit_error"))]
        result_ = self.run_helper("search", "rust")
        self.assertEqual(result_.returncode, 1)
        self.assertEqual(len(self.searches()), 4)
        self.assertIn("5 Search and 5 Fetch requests per second", result_.stderr)

    def test_insufficient_balance_is_not_retried(self) -> None:
        StubDeepSeek.replies["/v1/tools/fetch"] = [(402, error("Insufficient Balance"))]
        result_ = self.run_helper("fetch", "https://example.com/")
        self.assertEqual(result_.returncode, 1)
        self.assertIn("Top up", result_.stderr)
        self.assertEqual(len(StubDeepSeek.requests), 1)

    def test_batch_paces_dedupes_and_counts_only_billable_searches(self) -> None:
        StubDeepSeek.by_query = {
            "one": (200, {"results": [result("https://example.com/shared"), result("https://example.com/1")]}),
            "two": (200, {"results": [result("https://example.com/shared#section"), result("https://example.com/2")]}),
            "three": (200, {"results": []}),
            "four": (400, error("'query' must not be empty")),
        }
        result_ = self.run_helper("batch", "-c", "5", "one", "two", "three", "four")
        self.assertEqual(result_.returncode, 1)
        payload = json.loads(result_.stdout)
        self.assertEqual([run["query"] for run in payload["runs"]], ["one", "two", "three", "four"])
        self.assertEqual([item["url"] for item in payload["runs"][1]["results"]], ["https://example.com/2"])
        self.assertEqual((payload["unique_urls"], payload["duplicates_removed"], payload["billable_requests"]), (3, 1, 2))
        self.assertIn("'query' must not be empty", payload["runs"][3]["error"])
        self.assertIn("1 of 4 queries failed", result_.stderr)
        starts = [r["at"] for r in self.searches()]
        # Unpaced Promise.all bursts hit the 5 QPS limit live (10 of 15 concurrent searches got 429).
        self.assertTrue(all(later - earlier >= 0.2 for earlier, later in zip(starts, starts[1:])), starts)

    def test_batch_validates_every_query_before_spending(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            queries = Path(directory) / "queries.txt"
            queries.write_text("good query\n\n" + "x" * 129 + "\n")
            result_ = self.run_helper("batch", "--file", str(queries), "first")
        self.assertEqual(result_.returncode, 2)
        self.assertEqual(StubDeepSeek.requests, [])

    def test_fetch_unescapes_markdown_punctuation_only(self) -> None:
        StubDeepSeek.replies["/v1/tools/fetch"] = [(200, {"title": "E.1. Release 18.6",
                                                         "content": "Release date\\: 2026\\-08\\-13 C:\\\\temp \\d+ \\{\\\"a\\\"\\}"})]
        unescaped = self.run_helper("fetch", "https://www.postgresql.org/docs/18/release-18-6.html")
        self.assertEqual(unescaped.returncode, 0, unescaped.stderr)
        self.assertEqual(unescaped.stdout, "# E.1. Release 18.6\nSource: https://www.postgresql.org/docs/18/release-18-6.html\n\n"
                                           'Release date: 2026-08-13 C:\\temp \\d+ {"a"}\n')
        raw = self.run_helper("fetch", "--raw", "https://www.postgresql.org/docs/18/release-18-6.html")
        self.assertIn("2026\\-08\\-13", raw.stdout)
        self.assertEqual(StubDeepSeek.requests[0]["body"], {"url": "https://www.postgresql.org/docs/18/release-18-6.html"})

    def test_fetch_truncates_output_but_saves_the_full_page(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "page.md"
            result_ = self.run_helper("fetch", "--chars", "100", "--save", str(target), "https://example.com/")
            self.assertEqual(result_.returncode, 0, result_.stderr)
            self.assertIn("truncated at 100 of 50037 characters", result_.stdout)
            self.assertEqual(len(target.read_text()), 50_037)

    def test_failed_fetch_explains_unsupported_pages_are_free(self) -> None:
        StubDeepSeek.replies["/v1/tools/fetch"] = [(404, error("failed to fetch URL"))]
        result_ = self.run_helper("fetch", "https://arxiv.org/pdf/1706.03762")
        self.assertEqual(result_.returncode, 1)
        self.assertIn("PDFs", result_.stderr)
        self.assertIn("not billed", result_.stderr)
        self.assertEqual(len(StubDeepSeek.requests), 1)

    def test_balance_reports_request_capacity_without_float_drift(self) -> None:
        result_ = self.run_helper("balance")
        self.assertEqual(result_.returncode, 0, result_.stderr)
        # 2.61 / 0.00075 is exactly 3,480; naive floating-point division floors to 3,479.
        self.assertIn("USD 2.61 (topped up 2.61, granted 0.00), about 3,480 Search or Fetch requests", result_.stdout)

    def test_key_is_never_echoed_and_is_required(self) -> None:
        StubDeepSeek.replies["/v1/tools/search"] = [(401, error("Authentication Fails, Your api key is invalid", "authentication_error"))]
        result_ = self.run_helper("search", "rust")
        self.assertEqual(result_.returncode, 1)
        self.assertIn("DEEPSEEK_API_KEY is missing or invalid", result_.stderr)
        self.assertNotIn(FAKE_KEY, result_.stdout + result_.stderr)
        StubDeepSeek.requests = []
        missing = self.run_helper("search", "rust", api_key=None)
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(StubDeepSeek.requests, [])

    def test_runs_inside_an_esm_package(self) -> None:
        # Installed skills can land in projects whose package.json sets "type": "module".
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "deepseek_search.js"
            shutil.copy(SCRIPT, copy)
            (Path(directory) / "package.json").write_text('{"type": "module"}')
            result_ = self.run_helper("search", "--urls", "--loc", "8.8.8.8", "rust", script=copy)
        self.assertEqual(result_.returncode, 0, result_.stderr)
        self.assertEqual(self.searches()[0]["body"]["localization"], "8.8.8.8")


if __name__ == "__main__":
    unittest.main()

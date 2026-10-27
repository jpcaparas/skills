#!/usr/bin/env python3
"""Offline regressions for scripts/zai.js against a local stub of Z.ai's MCP and REST endpoints.

These tests never contact api.z.ai and never read an ambient Z_AI_API_KEY or ZAI_API_KEY.
"""

from __future__ import annotations

import json
import os
import shutil
import socketserver
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "zai.js"
FAKE_KEY = "test-key-not-real"
SESSION_ID = "stub-session-1"

# Live shape from 2026-10-18: the MCP search tool returns a JSON array encoded as a JSON
# string inside an SSE "data:" line, with only title, link, content, and refer per result.
MCP_SEARCH_RESULTS = [
    {"title": f"Result {i}", "link": f"https://example.com/{i}", "content": f"summary {i}", "refer": f"ref_{i + 1}"}
    for i in range(8)
]
REST_SEARCH_RESPONSE = {
    "id": "task",
    "search_intent": [{"intent": "SEARCH_ALWAYS", "query": "rewritten"}],
    "search_result": [
        {"title": "REST 0", "link": "https://rest.example/0", "content": "rest summary", "media": "Example", "publish_date": "2026-10-17", "refer": "ref_1"},
        {"title": "REST 1", "link": "https://rest.example/1", "content": "rest summary", "media": "", "publish_date": "", "refer": "ref_2"},
    ],
}
QUOTA_RESPONSE = {
    "code": 200,
    "success": True,
    "data": {
        "level": "max",
        "limits": [
            {"type": "TIME_LIMIT", "unit": 5, "number": 1, "usage": 4000, "currentValue": 35, "remaining": 3965,
             "percentage": 1, "nextResetTime": 1793175412992,
             "usageDetails": [{"modelCode": "search-prime", "usage": 30}, {"modelCode": "web-reader", "usage": 5}, {"modelCode": "zread", "usage": 0}]},
            {"type": "TOKENS_LIMIT", "unit": 3, "number": 5, "percentage": 1, "nextResetTime": 1792325243925},
        ],
    },
}
BALANCE_RESPONSE = {"code": 200, "success": True, "data": {"availableBalance": 89.7376}}


class LoopbackHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer without the reverse-DNS lookup of its bind address.

    HTTPServer.server_bind calls socket.getfqdn(host), a reverse-DNS lookup that
    can stall for tens of seconds on macOS. A loopback stub never needs the name.
    """

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


class StubZai(BaseHTTPRequestHandler):
    requests: list[dict] = []
    tool_text: dict[str, tuple[str, bool]] = {}
    rest_search: tuple[int, dict] = (200, REST_SEARCH_RESPONSE)

    def _send(self, status: int, body: bytes, content_type: str = "application/json", headers: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sse(self, message: dict, headers: dict | None = None) -> None:
        self._send(200, f"id:1\nevent:message\ndata:{json.dumps(message)}\n\n".encode(), "text/event-stream;charset=UTF-8", headers)

    def do_GET(self) -> None:
        StubZai.requests.append({"method": "GET", "path": self.path, "authorization": self.headers.get("Authorization")})
        if self.path == "/api/monitor/usage/quota/limit":
            self._send(200, json.dumps(QUOTA_RESPONSE).encode())
        elif self.path == "/api/biz/account/query-customer-account-report":
            self._send(200, json.dumps(BALANCE_RESPONSE).encode())
        else:
            self._send(404, b"{}")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"null")
        record = {"method": "POST", "path": self.path, "body": body, "session": self.headers.get("Mcp-Session-Id"),
                  "authorization": self.headers.get("Authorization")}
        StubZai.requests.append(record)
        if self.path == "/api/paas/v4/web_search":
            status, payload = StubZai.rest_search
            self._send(status, json.dumps(payload).encode())
            return
        if not self.path.startswith("/api/mcp/"):
            self._send(404, b"{}")
            return
        method = body.get("method")
        if method == "initialize":
            self._sse({"jsonrpc": "2.0", "id": body["id"], "result": {"protocolVersion": "2024-11-05"}}, {"Mcp-Session-Id": SESSION_ID})
        elif method == "notifications/initialized":
            self._send(202, b"")
        elif method == "tools/call":
            if self.headers.get("Mcp-Session-Id") != SESSION_ID:
                # Mirrors the live server, which rejects session-less calls with a misleading auth error.
                text, is_error = "MCP error -401: Api key not found, please get your apikey", True
            else:
                text, is_error = StubZai.tool_text[body["params"]["name"]]
            self._sse({"jsonrpc": "2.0", "id": body["id"], "result": {"content": [{"type": "text", "text": text}], "isError": is_error}})
        else:
            self._send(400, b"{}")

    def log_message(self, *_args) -> None:
        pass


class ZaiHelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.node = shutil.which(os.environ.get("SKILLS_VALIDATION_NODE", "node"))
        if not cls.node:
            raise RuntimeError("Node.js is required to test scripts/zai.js; set SKILLS_VALIDATION_NODE if it is not on PATH.")
        cls.server = LoopbackHTTPServer(("127.0.0.1", 0), StubZai)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.root = f"http://127.0.0.1:{cls.server.server_address[1]}/api"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self) -> None:
        StubZai.requests = []
        StubZai.rest_search = (200, REST_SEARCH_RESPONSE)
        StubZai.tool_text = {
            "web_search_prime": (json.dumps(json.dumps(MCP_SEARCH_RESULTS)), False),
            # Live reader payloads are a JSON object encoded as a JSON string.
            "webReader": (json.dumps(json.dumps({"title": "Page", "url": "https://docs.example/page", "description": "", "content": "x" * 50_000})), False),
            "search_doc": (json.dumps("Search results for vitejs/vite\n:[1]: HMR"), False),
            "get_repo_structure": (json.dumps("Directory Structure of psf/requests:"), False),
            "read_file": (json.dumps("File content for src/requests/api.py"), False),
        }

    def run_helper(self, *args: str, api_key: str | None = FAKE_KEY, key_var: str = "Z_AI_API_KEY") -> subprocess.CompletedProcess:
        env = {key: value for key, value in os.environ.items() if key not in ("Z_AI_API_KEY", "ZAI_API_KEY", "ZAI_API_ROOT")}
        env["ZAI_API_ROOT"] = self.root
        if api_key is not None:
            env[key_var] = api_key
        return subprocess.run([self.node, str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=60)

    def tool_calls(self) -> list[dict]:
        return [r for r in StubZai.requests if r["method"] == "POST" and (r["body"] or {}).get("method") == "tools/call"]

    def test_mcp_search_initialises_a_session_and_sends_flags_as_tool_arguments(self) -> None:
        result = self.run_helper("search", "--compact", "--site", "docs.rs", "--recency", "oneWeek", "tokio", "select")
        self.assertEqual(result.returncode, 0, result.stderr)
        methods = [r["body"].get("method") for r in StubZai.requests if r["path"].startswith("/api/mcp/web_search_prime")]
        self.assertEqual(methods, ["initialize", "notifications/initialized", "tools/call"])
        call = self.tool_calls()[0]
        self.assertEqual(call["session"], SESSION_ID)
        self.assertEqual(call["authorization"], f"Bearer {FAKE_KEY}")
        self.assertEqual(
            call["body"]["params"],
            {"name": "web_search_prime", "arguments": {"search_query": "tokio select site:docs.rs", "location": "us", "search_recency_filter": "oneWeek"}},
        )

    def test_double_encoded_mcp_results_are_decoded_and_normalised(self) -> None:
        result = self.run_helper("search", "--compact", "-n", "3", "rust")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["route"], "mcp")
        self.assertEqual(len(payload["results"]), 3)
        self.assertEqual(payload["results"][0], {"title": "Result 0", "url": "https://example.com/0", "site": None, "published": None, "summary": "summary 0"})

    def test_site_flag_drops_results_outside_the_domain_and_its_subdomains(self) -> None:
        # Live Z.ai returned 0-4 GitHub links out of 9-10 for "<query> site:github.com".
        links = ["https://github.com/a/b", "https://pypi.org/x", "https://gist.github.com/c", "https://notgithub.com/d",
                 "https://github.com.evil.example/e", "https://www.github.com/f"]
        results = [{"title": link, "link": link, "content": "", "refer": "r"} for link in links]
        StubZai.tool_text["web_search_prime"] = (json.dumps(json.dumps(results)), False)
        result = self.run_helper("search", "--urls", "--site", "github.com", "httpx")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["https://github.com/a/b", "https://gist.github.com/c", "https://www.github.com/f"])
        self.assertIn("Dropped 3 of 6 results outside github.com", result.stderr)

    def test_rest_search_is_opt_in_and_reports_publish_dates(self) -> None:
        result = self.run_helper("search", "--rest", "--engine", "search_std", "--count", "20", "--compact", "rust")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.tool_calls(), [])
        rest = [r for r in StubZai.requests if r["path"] == "/api/paas/v4/web_search"][0]
        self.assertEqual(rest["body"], {"search_engine": "search_std", "search_query": "rust", "count": 20})
        payload = json.loads(result.stdout)
        self.assertEqual(payload["route"], "rest")
        self.assertEqual([item["published"] for item in payload["results"]], ["2026-10-17", None])

    def test_rest_only_flags_without_rest_are_rejected_before_any_call(self) -> None:
        result = self.run_helper("search", "--count", "20", "rust")
        self.assertEqual(result.returncode, 2)
        self.assertIn("require --rest", result.stderr)
        self.assertEqual(StubZai.requests, [])

    def test_invalid_values_are_rejected_locally(self) -> None:
        cases = [
            ("search", "--recency", "yesterday", "rust"),
            ("search", "--rest", "--count", "51", "rust"),
            ("search", "--rest", "--engine", "bing", "rust"),
            ("search", "--site", "a b", "rust"),
            ("search", "   "),
            ("read", "not-a-url"),
            ("repo-search", "not-a-repo", "question"),
            ("repo-file", "psf/requests"),
        ]
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(self.run_helper(*args).returncode, 2)
        self.assertEqual(StubZai.requests, [])

    def test_mcp_tool_errors_fail_with_the_server_message(self) -> None:
        StubZai.tool_text["web_search_prime"] = ("MCP error -400: search_query cannot be empty", True)
        result = self.run_helper("search", "rust")
        self.assertEqual(result.returncode, 1)
        self.assertIn("search_query cannot be empty", result.stderr)

    def test_rest_insufficient_balance_explains_the_plan_route(self) -> None:
        StubZai.rest_search = (429, {"error": {"code": "1113", "message": "Insufficient balance or no resource package. Please recharge."}})
        result = self.run_helper("search", "--rest", "rust")
        self.assertEqual(result.returncode, 1)
        self.assertIn("error 1113", result.stderr)
        self.assertIn("Drop --rest", result.stderr)

    def test_read_truncates_output_but_saves_the_full_page(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "page.md"
            result = self.run_helper("read", "--chars", "100", "--save", str(target), "--fresh", "https://docs.example/page")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.startswith("# Page\nSource: https://docs.example/page\n\nxxx"))
            self.assertIn("truncated at 100 of 50042 characters", result.stdout)
            saved = target.read_text()
            self.assertEqual(len(saved), 50_042)
            self.assertTrue(saved.endswith("x" * 50_000))
        self.assertEqual(self.tool_calls()[0]["body"]["params"]["arguments"], {"url": "https://docs.example/page", "no_cache": True})

    def test_mcp_throttle_is_retried(self) -> None:
        responses = iter([('MCP error -429: {"error":{"code":"1302","message":"Rate limit reached for requests"}}', True)])
        original = dict(StubZai.tool_text)

        class Once(dict):
            def __getitem__(self, key):
                if key == "web_search_prime":
                    return next(responses, original[key])
                return original[key]

        StubZai.tool_text = Once(original)
        result = self.run_helper("search", "--urls", "-n", "1", "rust")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Rate limited (1302)", result.stderr)
        self.assertEqual(result.stdout.split(), ["https://example.com/0"])
        self.assertEqual(len(self.tool_calls()), 2)

    def test_unindexed_repo_points_to_github(self) -> None:
        StubZai.tool_text["search_doc"] = ('MCP error -400: {"error":{"code":"1210","message":"{\\"code\\":1001,\\"msg\\":\\"target not found, error: repo not found\\"}"}}', True)
        result = self.run_helper("repo-search", "someone/small-repo", "question")
        self.assertEqual(result.returncode, 1)
        self.assertIn("repo not found", result.stderr)
        self.assertIn("indexed on zread.ai", result.stderr)

    def test_empty_zread_search_suggests_browsing_the_repo(self) -> None:
        # Live psf/requests reply for an unmatched question: header plus a zread.ai link, no "[1]:" hits.
        StubZai.tool_text["search_doc"] = (json.dumps("Search results for psf/requests\n\n:Tip: view at: https://zread.ai/psf/requests"), False)
        result = self.run_helper("repo-search", "psf/requests", "retries")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No matches in Zread's index", result.stderr)

    def test_repo_commands_map_to_zread_tools(self) -> None:
        search = self.run_helper("repo-search", "vitejs/vite", "how", "does", "HMR", "work")
        self.assertEqual(search.returncode, 0, search.stderr)
        self.assertEqual(search.stdout, "Search results for vitejs/vite\n:[1]: HMR\n")
        self.assertEqual(self.run_helper("repo-tree", "psf/requests", "src").returncode, 0)
        self.assertEqual(self.run_helper("repo-file", "psf/requests", "src/requests/api.py").returncode, 0)
        self.assertEqual(
            [c["body"]["params"] for c in self.tool_calls()],
            [
                {"name": "search_doc", "arguments": {"repo_name": "vitejs/vite", "query": "how does HMR work", "language": "en"}},
                {"name": "get_repo_structure", "arguments": {"repo_name": "psf/requests", "dir_path": "src"}},
                {"name": "read_file", "arguments": {"repo_name": "psf/requests", "file_path": "src/requests/api.py"}},
            ],
        )

    def test_quota_summarises_tool_calls_and_cash_balance(self) -> None:
        result = self.run_helper("quota")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Tool calls this month: 35/4000 used, 3965 left", result.stdout)
        self.assertIn("search-prime 30, web-reader 5, zread 0", result.stdout)
        self.assertIn("Cash balance for --rest calls: $89.74", result.stdout)

    def test_zai_api_key_is_accepted_as_an_alias(self) -> None:
        result = self.run_helper("search", "--urls", "rust", key_var="ZAI_API_KEY")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.tool_calls()[0]["authorization"], f"Bearer {FAKE_KEY}")

    def test_missing_key_fails_without_a_request(self) -> None:
        result = self.run_helper("search", "rust", api_key=None)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(StubZai.requests, [])


if __name__ == "__main__":
    unittest.main()

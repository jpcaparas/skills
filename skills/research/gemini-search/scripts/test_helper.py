#!/usr/bin/env python3
"""Offline regressions for scripts/gemini_search.js against a local stub of the Gemini API.

These tests never contact Google and never read an ambient GEMINI_API_KEY or GOOGLE_API_KEY.
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

SCRIPT = Path(__file__).resolve().parent / "gemini_search.js"
FAKE_KEY = "AIza-test-not-real-0123456789"


class LoopbackHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer without the reverse-DNS lookup of its bind address.

    HTTPServer.server_bind calls socket.getfqdn(host), a reverse-DNS lookup that
    can stall for tens of seconds on macOS. A loopback stub never needs the name.
    """

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def grounded_response(base: str, text: str, queries: list[str], supports: list[tuple[int, int]], chunk_paths: list[str]) -> dict:
    """A generateContent reply in the live 2026-10-19 shape, with redirect URIs served by the stub."""
    return {
        "candidates": [{
            "content": {"role": "model", "parts": [{"text": text}]},
            "finishReason": "STOP",
            "groundingMetadata": {
                "webSearchQueries": queries,
                "searchEntryPoint": {"renderedContent": "<style></style>"},
                "groundingChunks": [{"web": {"uri": f"{base}/grounding-api-redirect/{path}", "title": "example.com"}} for path in chunk_paths],
                "groundingSupports": [{"segment": {"startIndex": start, "endIndex": end}, "groundingChunkIndices": [0]} for start, end in supports],
            },
        }],
        "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 2000, "totalTokenCount": 3000},
        "modelVersion": "gemini-3.1-flash-lite",
    }


class StubGemini(BaseHTTPRequestHandler):
    requests: list[dict] = []
    replies: dict[str, list[tuple[int, dict]]] = {}
    redirects: dict[str, str] = {}
    interaction_polls: list[dict] = []

    def _send(self, status: int, payload: dict | None, headers: dict | None = None) -> None:
        body = json.dumps(payload).encode() if payload is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _record(self, body: dict | None) -> None:
        StubGemini.requests.append({"method": self.command, "path": self.path, "body": body, "key": self.headers.get("x-goog-api-key")})

    def _reply(self, key: str) -> None:
        queue = StubGemini.replies.get(key) or [(404, {"error": {"message": "not stubbed"}})]
        status, payload = queue.pop(0) if len(queue) > 1 else queue[0]
        self._send(status, payload)

    def do_HEAD(self) -> None:
        self._record(None)
        slug = self.path.rsplit("/", 1)[-1]
        if self.path.startswith("/grounding-api-redirect/") and slug in StubGemini.redirects:
            self._send(302, None, {"Location": StubGemini.redirects[slug]})
        else:
            self._send(404, None)

    def do_GET(self) -> None:
        self._record(None)
        if self.path.startswith("/interactions/"):
            payload = StubGemini.interaction_polls.pop(0) if len(StubGemini.interaction_polls) > 1 else StubGemini.interaction_polls[0]
            self._send(200, payload)
        else:
            self._send(404, {})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"null")
        self._record(body)
        self._reply("interactions" if self.path == "/interactions" else "generate")

    def do_DELETE(self) -> None:
        self._record(None)
        self._send(200, {})

    def log_message(self, *_args) -> None:
        pass


class GeminiHelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.node = shutil.which(os.environ.get("SKILLS_VALIDATION_NODE", "node"))
        if not cls.node:
            raise RuntimeError("Node.js is required to test scripts/gemini_search.js; set SKILLS_VALIDATION_NODE if it is not on PATH.")
        cls.server = LoopbackHTTPServer(("127.0.0.1", 0), StubGemini)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.root = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self) -> None:
        StubGemini.requests = []
        StubGemini.redirects = {"a": "https://www.postgresql.org/docs/release/18.6/", "b": "https://docs.rs/tokio", "dup": "https://docs.rs/tokio"}
        StubGemini.interaction_polls = []
        text = "PostgreSQL 18.6 was released on 2026-08-13. It fixes replication bugs."
        StubGemini.replies = {"generate": [(200, grounded_response(self.root, text, ["postgresql 18.6 release"], [(0, 44)], ["a"]))]}

    def run_helper(self, *args: str, api_key: str | None = FAKE_KEY, script: Path = SCRIPT) -> subprocess.CompletedProcess:
        env = {key: value for key, value in os.environ.items() if key not in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_ROOT")}
        env["GEMINI_API_ROOT"] = self.root
        env["GEMINI_RESEARCH_POLL_MS"] = "10"
        if api_key is not None:
            env["GEMINI_API_KEY"] = api_key
        return subprocess.run([self.node, str(script), *args], env=env, capture_output=True, text=True, timeout=60)

    def posts(self) -> list[dict]:
        return [r for r in StubGemini.requests if r["method"] == "POST"]

    def test_search_defaults_to_flash_lite_with_forced_grounding_and_cap(self) -> None:
        result = self.run_helper("search", "What changed in PostgreSQL 18.6?")
        self.assertEqual(result.returncode, 0, result.stderr)
        request = self.posts()[0]
        self.assertEqual(request["path"], "/models/gemini-3.1-flash-lite:generateContent")
        self.assertEqual(request["key"], FAKE_KEY)
        self.assertEqual(request["body"]["tools"], [{"google_search": {}}])
        instruction = request["body"]["systemInstruction"]["parts"][0]["text"]
        # Without a forcing instruction, Flash-Lite skipped search on 1 of 5 identical live runs.
        self.assertIn("always search before answering", instruction)
        self.assertIn("at most 3 search queries", instruction)

    def test_json_summary_resolves_redirects_dedupes_and_prices_queries(self) -> None:
        StubGemini.replies["generate"] = [(200, grounded_response(self.root, "abcd", ["q1", "q2", "q2", " "], [(0, 4)], ["b", "dup", "a", "b"]))]
        payload = json.loads(self.run_helper("search", "--json", "tokio").stdout)
        self.assertEqual([source["url"] for source in payload["sources"]], ["https://docs.rs/tokio", "https://www.postgresql.org/docs/release/18.6/"])
        # Billing counts unique non-empty queries.
        self.assertEqual((payload["billable_queries"], payload["estimated_cost_usd"]["search_after_free_tier"]), (2, 0.028))
        # 1,000 input x $0.25/M + 2,000 output x $1.50/M.
        self.assertEqual(payload["estimated_cost_usd"]["tokens"], 0.00325)

    def test_unresolvable_redirect_keeps_the_original_link(self) -> None:
        StubGemini.replies["generate"] = [(200, grounded_response(self.root, "abcd", ["q"], [(0, 4)], ["missing"]))]
        payload = json.loads(self.run_helper("search", "--json", "x").stdout)
        self.assertEqual(payload["sources"][0]["url"], f"{self.root}/grounding-api-redirect/missing")

    def test_no_resolve_skips_head_requests(self) -> None:
        self.run_helper("search", "--no-resolve", "x")
        self.assertEqual([r for r in StubGemini.requests if r["method"] == "HEAD"], [])

    def test_ungrounded_answer_exits_3_with_a_warning(self) -> None:
        # Live: a 50-country rates question ran 0 searches and answered entirely from memory.
        reply = grounded_response(self.root, "Switzerland: 0.00%", [], [], [])
        StubGemini.replies["generate"] = [(200, reply)]
        result = self.run_helper("search", "--json", "central bank rates")
        self.assertEqual(result.returncode, 3)
        self.assertFalse(json.loads(result.stdout)["grounded"])
        self.assertIn("UNGROUNDED", result.stderr)

    def test_coverage_uses_utf8_byte_offsets(self) -> None:
        # Live supports index UTF-8 bytes: "Zürich €" is 8 characters but 11 bytes.
        text = "Zürich € ok"
        StubGemini.replies["generate"] = [(200, grounded_response(self.root, text, ["q"], [(0, 11)], ["a"]))]
        payload = json.loads(self.run_helper("search", "--json", "x").stdout)
        self.assertEqual(payload["coverage"], round(11 / len(text.encode()), 2))
        self.assertEqual(payload["coverage"], 0.79)

    def test_low_coverage_and_cap_overrun_warn(self) -> None:
        StubGemini.replies["generate"] = [(200, grounded_response(self.root, "x" * 100, ["a", "b", "c", "d"], [(0, 20)], ["a"]))]
        result = self.run_helper("search", "x")
        self.assertEqual(result.returncode, 0)
        self.assertIn("only 20% of the answer", result.stderr)
        self.assertIn("ran 4 queries despite the cap of 3", result.stderr)

    def test_site_flag_requests_the_site_and_flags_outside_sources(self) -> None:
        StubGemini.replies["generate"] = [(200, grounded_response(self.root, "abcd", ["q site:docs.rs"], [(0, 4)], ["b", "a"]))]
        result = self.run_helper("search", "--json", "--site", "docs.rs", "tokio")
        self.assertIn("site:docs.rs", self.posts()[0]["body"]["systemInstruction"]["parts"][0]["text"])
        self.assertEqual([source["offSite"] for source in json.loads(result.stdout)["sources"]], [False, True])
        self.assertIn("outside docs.rs", result.stderr)

    def test_expensive_routes_are_refused_before_any_request(self) -> None:
        cases = [
            ("search", "--model", "gemini-4-argon", "q"),
            ("search", "--model", "gemini-3.1-pro-preview", "q"),
            ("search", "--model", "gemini-pro-latest", "q"),
            ("search", "--max-queries", "6", "q"),
            ("read", "--model", "gemini-4-argon", "https://example.com/"),
            ("research", "brief"),
            ("research", "--max", "brief"),
        ]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_helper(*args)
                self.assertEqual(result.returncode, 2)
                self.assertTrue("--allow-expensive" in result.stderr or "--confirm-cost" in result.stderr, result.stderr)
        self.assertEqual(StubGemini.requests, [])

    def test_allow_expensive_unlocks_gated_models_and_caps(self) -> None:
        self.assertEqual(self.run_helper("search", "--allow-expensive", "--model", "gemini-4-argon", "--max-queries", "10", "q").returncode, 0)
        request = self.posts()[0]
        self.assertEqual(request["path"], "/models/gemini-4-argon:generateContent")
        self.assertIn("at most 10 search queries", request["body"]["systemInstruction"]["parts"][0]["text"])

    def test_invalid_input_is_rejected_locally(self) -> None:
        cases = [
            ("search", "   "),
            ("search", "--max-queries", "0", "q"),
            ("search", "--max-queries", "2.5", "q"),
            ("search", "--site", "https://docs.rs", "q"),
            ("read",),
            ("read", "example.com"),
            ("read", "ftp://example.com/file"),
            ("read", *[f"https://example.com/{n}" for n in range(21)]),
            ("search", "--unknown", "q"),
        ]
        for args in cases:
            with self.subTest(args=args[:3]):
                self.assertEqual(self.run_helper(*args).returncode, 2)
        self.assertEqual(StubGemini.requests, [])

    def test_read_uses_url_context_only_and_reports_statuses(self) -> None:
        StubGemini.replies["generate"] = [(200, {
            "candidates": [{
                "content": {"parts": [{"text": "Released 2026-08-13. The second URL failed."}]},
                "urlContextMetadata": {"urlMetadata": [
                    {"retrievedUrl": "https://www.postgresql.org/docs/18/release-18-6.html", "urlRetrievalStatus": "URL_RETRIEVAL_STATUS_SUCCESS"},
                    {"retrievedUrl": "https://httpbin.org/status/404", "urlRetrievalStatus": "URL_RETRIEVAL_STATUS_ERROR"},
                ]},
            }],
            "usageMetadata": {"promptTokenCount": 40, "toolUsePromptTokenCount": 10_960, "candidatesTokenCount": 100},
        })]
        result = self.run_helper("read", "--json", "--ask", "Release date?", "https://www.postgresql.org/docs/18/release-18-6.html", "https://httpbin.org/status/404")
        self.assertEqual(result.returncode, 0, result.stderr)
        body = self.posts()[0]["body"]
        self.assertEqual(body["tools"], [{"url_context": {}}])
        self.assertIn("https://httpbin.org/status/404", body["contents"][0]["parts"][0]["text"])
        payload = json.loads(result.stdout)
        self.assertEqual([entry["status"] for entry in payload["urls"]], ["SUCCESS", "ERROR"])
        # Page tokens bill as input: (40 + 10,960) x $0.25/M + 100 x $1.50/M.
        self.assertEqual(payload["estimated_cost_usd"], 0.0029)
        self.assertIn("1 of 2 URLs failed", result.stderr)

    def test_read_exits_4_when_every_url_fails(self) -> None:
        StubGemini.replies["generate"] = [(200, {"candidates": [{"content": {"parts": [{"text": "Approximate figures from memory"}]},
            "urlContextMetadata": {"urlMetadata": [{"retrievedUrl": "https://example.com/", "urlRetrievalStatus": "URL_RETRIEVAL_STATUS_ERROR"}]}}]})]
        result = self.run_helper("read", "https://example.com/")
        self.assertEqual(result.returncode, 4)
        self.assertIn("No URL could be read", result.stderr)

    def test_rate_limits_retry_but_bad_requests_do_not(self) -> None:
        StubGemini.replies["generate"] = [(429, {"error": {"message": "RESOURCE_EXHAUSTED"}}),
                                          (200, grounded_response(self.root, "abcd", ["q"], [(0, 4)], ["a"]))]
        retried = self.run_helper("search", "--no-resolve", "q")
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertEqual(len(self.posts()), 2)
        StubGemini.requests = []
        StubGemini.replies["generate"] = [(400, {"error": {"message": "Unknown name \"excludeDomains\""}})]
        rejected = self.run_helper("search", "q")
        self.assertEqual(rejected.returncode, 1)
        self.assertIn("excludeDomains", rejected.stderr)
        self.assertEqual(len(self.posts()), 1)

    def test_research_polls_reports_usage_and_deletes_the_stored_interaction(self) -> None:
        StubGemini.replies["interactions"] = [(200, {"id": "v1_abc", "status": "in_progress"})]
        StubGemini.interaction_polls = [
            {"id": "v1_abc", "status": "in_progress"},
            {"id": "v1_abc", "status": "completed",
             "steps": [{"type": "user_input"}, {"type": "model_output", "content": [{"type": "text", "text": "# Report"}]}],
             "usage": {"total_input_tokens": 184_963, "total_output_tokens": 9_499, "total_thought_tokens": 22_219,
                       "grounding_tool_count": [{"type": "google_search", "count": 7}]}},
        ]
        result = self.run_helper("research", "--confirm-cost", "compare search APIs")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("# Report"))
        self.assertIn("7 searches", result.stdout)
        start = self.posts()[0]["body"]
        self.assertEqual(start, {"agent": "deep-research-preview-04-2026", "input": "compare search APIs", "background": True, "store": True})
        self.assertEqual([r["path"] for r in StubGemini.requests if r["method"] == "DELETE"], ["/interactions/v1_abc"])

    def test_research_max_and_keep(self) -> None:
        StubGemini.replies["interactions"] = [(200, {"id": "v1_max", "status": "completed", "steps": []})]
        StubGemini.interaction_polls = [{"id": "v1_max", "status": "completed", "steps": []}]
        self.run_helper("research", "--confirm-cost", "--max", "--keep", "brief")
        self.assertEqual(self.posts()[0]["body"]["agent"], "deep-research-max-preview-04-2026")
        self.assertEqual([r for r in StubGemini.requests if r["method"] == "DELETE"], [])

    def test_key_is_required_and_never_echoed(self) -> None:
        StubGemini.replies["generate"] = [(400, {"error": {"message": "API key not valid. Please pass a valid API key."}})]
        result = self.run_helper("search", "q")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(FAKE_KEY, result.stdout + result.stderr)
        StubGemini.requests = []
        self.assertEqual(self.run_helper("search", "q", api_key=None).returncode, 2)
        self.assertEqual(StubGemini.requests, [])

    def test_runs_inside_an_esm_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "gemini_search.js"
            shutil.copy(SCRIPT, copy)
            (Path(directory) / "package.json").write_text('{"type": "module"}')
            result = self.run_helper("search", "--no-resolve", "q", script=copy)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

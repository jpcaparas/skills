#!/usr/bin/env python3
"""Offline tests for firecrawl_guard.py.

Expected credit figures are the values Firecrawl actually billed in the 2026-10-18 spike
(references/evidence.md), so a pricing regression in the guard fails here. The balance test
uses a local stub server and a fake key; nothing reaches Firecrawl.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock
import importlib.util
import sys

SCRIPT = Path(__file__).with_name("firecrawl_guard.py")
FAKE_KEY = "test-key-not-real"


def load_guard():
    spec = importlib.util.spec_from_file_location("firecrawl_guard", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["firecrawl_guard"] = module
    spec.loader.exec_module(module)
    return module


guard = load_guard()


def run(endpoint: str, body: dict, *extra: str) -> tuple[int, dict]:
    out = io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(json.dumps(body))), contextlib.redirect_stdout(out):
        code = guard.main(["estimate", endpoint, "-", *extra])
    return code, json.loads(out.getvalue())


def levels(verdict: dict) -> list[str]:
    return [f["level"] for f in verdict["findings"]]


class MeasuredPrices(unittest.TestCase):
    """Each case reproduces a request from the live spike and the credits it was billed."""

    def assert_credits(self, endpoint: str, body: dict, billed: int) -> None:
        _, verdict = run(endpoint, body)
        self.assertEqual(verdict["worst_case_credits"], billed, verdict)

    def test_markdown_scrape_is_one_credit(self) -> None:
        self.assert_credits("scrape", {"url": "https://books.toscrape.com/", "formats": ["markdown"]}, 1)

    def test_json_format_adds_four_but_combined_formats_do_not_stack_free_ones(self) -> None:
        self.assert_credits("scrape", {"url": "https://books.toscrape.com/", "formats": [{"type": "json", "prompt": "title"}]}, 5)
        self.assert_credits("scrape", {"url": "https://books.toscrape.com/", "formats": ["markdown", "summary", {"type": "json", "prompt": "t"}]}, 5)

    def test_summary_screenshot_branding_are_free_formats(self) -> None:
        self.assert_credits("scrape", {"url": "https://a.test/", "formats": ["summary", {"type": "screenshot", "fullPage": True}, "branding"]}, 1)

    def test_search_rounds_up_per_ten_results_across_sources(self) -> None:
        self.assert_credits("search", {"query": "q", "limit": 3}, 2)
        self.assert_credits("search", {"query": "q", "limit": 10}, 2)
        self.assert_credits("search", {"query": "q", "limit": 11}, 4)
        self.assert_credits("search", {"query": "q", "limit": 5, "sources": ["web", "news"]}, 2)

    def test_search_with_scrape_options_bills_each_result(self) -> None:
        self.assert_credits("search", {"query": "q", "limit": 2, "scrapeOptions": {"formats": ["markdown"]}}, 4)

    def test_pdf_page_cap_and_disabled_parsing(self) -> None:
        pdf = "https://arxiv.org/pdf/1706.03762v7"
        self.assert_credits("scrape", {"url": pdf, "parsers": [{"type": "pdf", "maxPages": 2}]}, 2)
        self.assert_credits("scrape", {"url": pdf, "parsers": []}, 1)

    def test_map_is_one_credit_regardless_of_limit(self) -> None:
        self.assert_credits("map", {"url": "https://docs.firecrawl.dev", "limit": 5000}, 1)

    def test_bounded_crawl_costs_limit_times_page_price(self) -> None:
        self.assert_credits("crawl", {"url": "https://books.toscrape.com/", "limit": 5, "ignoreQueryParameters": True}, 5)


class Guards(unittest.TestCase):
    def test_agent_and_extract_are_blocked_in_every_spelling(self) -> None:
        for endpoint in ("agent", "/v2/agent", "agent/123", "extract", "/v2/extract", "v1/deep-research", "llmstxt"):
            code, verdict = run(endpoint, {"prompt": "find founders"})
            self.assertEqual(code, 3, endpoint)
            self.assertEqual(verdict["verdict"], "blocked")

    def test_premium_hosts_are_blocked_including_subdomains_but_lookalikes_pass(self) -> None:
        for url in ("https://x.com/a/status/1", "https://mobile.twitter.com/a", "https://www.linkedin.com/in/someone"):
            code, _ = run("scrape", {"url": url})
            self.assertEqual(code, 3, url)
        code, _ = run("scrape", {"url": "https://box.com/page"})
        self.assertEqual(code, 0)
        code, _ = run("batch-scrape", {"urls": ["https://ok.test/", "https://x.com/u"]})
        self.assertEqual(code, 3)

    def test_crawl_without_limit_is_blocked_and_priced_at_the_ten_thousand_default(self) -> None:
        code, verdict = run("crawl", {"url": "https://example.com/", "ignoreQueryParameters": True})
        self.assertEqual(code, 3)
        self.assertEqual(verdict["worst_case_credits"], 10_000)

    def test_crawl_with_default_query_handling_warns_about_variant_explosion(self) -> None:
        code, verdict = run("crawl", {"url": "https://example.com/", "limit": 3})
        self.assertEqual(code, 2)
        self.assertTrue(any("ignoreQueryParameters" in f["message"] for f in verdict["findings"]))
        quiet_code, _ = run("crawl", {"url": "https://example.com/", "limit": 3, "sitemap": "skip"})
        self.assertEqual(quiet_code, 0)

    def test_budget_blocks_over_limit_and_unbounded_requests(self) -> None:
        code, _ = run("crawl", {"url": "https://a.test/", "limit": 40, "ignoreQueryParameters": True}, "--budget", "39")
        self.assertEqual(code, 3)
        code, _ = run("crawl", {"url": "https://a.test/", "limit": 40, "ignoreQueryParameters": True}, "--budget", "40")
        self.assertEqual(code, 0)
        code, verdict = run("scrape", {"url": "https://a.test/report.pdf"}, "--budget", "100")
        self.assertEqual(code, 3, "an unbounded PDF cannot be proven under any budget")
        self.assertIsNone(verdict["worst_case_credits"])

    def test_interact_prompt_costs_more_than_code_and_has_a_one_minute_minimum(self) -> None:
        _, prompt = run("interact", {"prompt": "click login", "ttl": 30})
        _, code_only = run("interact", {"code": "await page.click('a')", "ttl": 30})
        self.assertEqual((prompt["worst_case_credits"], code_only["worst_case_credits"]), (7, 2))
        _, default_ttl = run("interact", {"prompt": "x"})
        self.assertEqual(default_ttl["worst_case_credits"], 70)

    def test_unknown_endpoint_warns_instead_of_guessing(self) -> None:
        code, verdict = run("search/developer", {"query": "q"})
        self.assertEqual(code, 2)
        self.assertIsNone(verdict["worst_case_credits"])


class Balance(unittest.TestCase):
    def test_balance_reads_credit_usage_with_bearer_key(self) -> None:
        seen: dict[str, str] = {}

        class Stub(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - http.server API
                seen["path"], seen["auth"] = self.path, self.headers.get("Authorization", "")
                body = json.dumps({"success": True, "data": {"remainingCredits": 2169, "planCredits": 100000, "billingPeriodEnd": "2026-11-03T00:28:33.000Z"}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_: object) -> None:
                pass

        server = HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with mock.patch.object(guard, "API_ROOT", f"http://127.0.0.1:{server.server_address[1]}"), \
                    mock.patch.dict(os.environ, {"FIRECRAWL_API_KEY": FAKE_KEY}):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(guard.main(["balance"]), 0)
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(seen, {"path": "/v2/team/credit-usage", "auth": f"Bearer {FAKE_KEY}"})
        self.assertEqual(json.loads(out.getvalue())["remaining_credits"], 2169)

    def test_balance_without_key_fails_before_any_request(self) -> None:
        with mock.patch.dict(os.environ, {"FIRECRAWL_API_KEY": ""}), self.assertRaises(SystemExit) as raised:
            guard.main(["balance"])
        self.assertIn("FIRECRAWL_API_KEY", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

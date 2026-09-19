#!/usr/bin/env python3
"""Run offline scraper and package-contract regressions, not model evals."""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import http.client
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import scrape_docs as docs
import validate


STAMP = "2026-01-02T03:04:05+00:00"
MODEL_URL = docs.ORIGIN + "/models.md"
NEW_URL = docs.ORIGIN + "/cookbooks/new-decision.md"
INDEX = f"[Models]({MODEL_URL})\n[New capability]({NEW_URL})\n".encode()


def fixture_fetch(url: str) -> docs.Page:
    bodies = {
        docs.INDEX_URL: INDEX,
        MODEL_URL: b"# Models\n",
        NEW_URL: b"# New decision\n",
    }
    return docs.Page(url, bodies[url], STAMP)


class ScraperTests(unittest.TestCase):
    def setUp(self) -> None:
        network = patch(
            "socket.create_connection",
            side_effect=AssertionError("unplanned network access"),
        )
        network.start()
        self.addCleanup(network.stop)
        temporary = tempfile.TemporaryDirectory(prefix="jev-docs-test-")
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)
        self.output = self.parent / "snapshot"

    def test_discovers_new_pages_and_deduplicates_fragments_without_external_fetches(
        self,
    ) -> None:
        index = (
            INDEX.decode()
            + f"""
[Same model]({MODEL_URL}#limits)
[External](https://example.test/secret.md)
[Lookalike](https://docs.typesafe.ai.example.test/key.md)
[Userinfo](https://docs.typesafe.ai@evil.test/key.md)
[HTTP](http://docs.typesafe.ai/key.md)
[Query]({MODEL_URL}?key=do-not-send)
[Traversal](https://docs.typesafe.ai/%2e%2e/private.md)
[HTML](https://docs.typesafe.ai/models)
"""
        )
        discovered = docs.indexed_pages(index)
        self.assertEqual(discovered.urls, [NEW_URL, MODEL_URL])
        self.assertEqual(
            set(discovered.unsupported_urls),
            {
                "https://example.test/secret.md",
                "https://docs.typesafe.ai.example.test/key.md",
                "https://docs.typesafe.ai@evil.test/key.md",
                "http://docs.typesafe.ai/key.md",
                MODEL_URL + "?key=do-not-send",
                "https://docs.typesafe.ai/%2e%2e/private.md",
                "https://docs.typesafe.ai/models",
            },
        )

    def test_changed_index_link_format_is_an_explicit_coverage_gap(self) -> None:
        def fetch(url: str) -> docs.Page:
            if url == docs.INDEX_URL:
                return docs.Page(
                    url,
                    INDEX + b"[Moved](https://docs.typesafe.ai/new-format)\n",
                    STAMP,
                )
            return fixture_fetch(url)

        snapshot = docs.scrape(self.output, fetch, max_pages=2)
        self.assertFalse(snapshot.complete)
        self.assertEqual(
            snapshot.unsupported_urls, ["https://docs.typesafe.ai/new-format"]
        )
        self.assertEqual(len(snapshot.files), 3)

    def test_snapshot_preserves_exact_source_bytes_hashes_and_new_capabilities(
        self,
    ) -> None:
        snapshot = docs.scrape(self.output, fixture_fetch, max_pages=2)
        self.assertTrue(snapshot.complete)
        self.assertEqual(snapshot.discovered_pages, 2)
        self.assertEqual(snapshot.failures, [])
        self.assertEqual(snapshot.omitted_urls, [])
        self.assertEqual(
            [page.url for page in snapshot.files], [docs.INDEX_URL, NEW_URL, MODEL_URL]
        )
        self.assertEqual(
            (self.output / "pages/0001.md").read_bytes(), b"# New decision\n"
        )
        page = snapshot.files[1]
        self.assertEqual(page.fetched_at, STAMP)
        self.assertEqual(page.bytes, 15)
        self.assertEqual(page.sha256, hashlib.sha256(b"# New decision\n").hexdigest())
        manifest = validate.mapping(
            json.loads((self.output / "manifest.json").read_text())
        )
        self.assertEqual(manifest["complete"], True)
        self.assertEqual(manifest["discovered_pages"], 2)

    def test_page_cap_reports_omissions_and_never_fetches_them(self) -> None:
        fetched: list[str] = []

        def fetch(url: str) -> docs.Page:
            fetched.append(url)
            return fixture_fetch(url)

        snapshot = docs.scrape(self.output, fetch, max_pages=1)
        self.assertFalse(snapshot.complete)
        self.assertEqual(snapshot.omitted_urls, [MODEL_URL])
        self.assertEqual(snapshot.discovered_pages, 2)
        self.assertEqual(fetched, [docs.INDEX_URL, NEW_URL])

    def test_page_failure_preserves_other_pages_and_is_incomplete(self) -> None:
        def fetch(url: str) -> docs.Page | docs.FetchFailure:
            if url == MODEL_URL:
                return docs.FetchFailure(url, "HTTP 503", STAMP)
            return fixture_fetch(url)

        snapshot = docs.scrape(self.output, fetch, max_pages=2)
        self.assertFalse(snapshot.complete)
        self.assertEqual(
            snapshot.failures, [docs.FetchFailure(MODEL_URL, "HTTP 503", STAMP)]
        )
        self.assertEqual(
            (self.output / "pages/0001.md").read_bytes(), b"# New decision\n"
        )
        self.assertFalse((self.output / "pages/0002.md").exists())

    def test_failed_and_empty_indexes_never_report_a_complete_crawl(self) -> None:
        results = (
            docs.FetchFailure(docs.INDEX_URL, "timeout", STAMP),
            docs.Page(docs.INDEX_URL, b"# No supported links\n", STAMP),
        )
        for number, result in enumerate(results):
            with self.subTest(result=result):
                fetch = Mock(return_value=result)
                snapshot = docs.scrape(self.parent / str(number), fetch, max_pages=2)
                self.assertFalse(snapshot.complete)
                self.assertEqual(snapshot.discovered_pages, 0)
                self.assertEqual(len(snapshot.failures), 1)
                fetch.assert_called_once_with(docs.INDEX_URL)

    def test_existing_output_and_dangling_symlink_are_not_overwritten(self) -> None:
        self.output.mkdir()
        evidence = self.output / "manifest.json"
        evidence.write_text("original evidence", encoding="utf-8")
        dangling = self.parent / "dangling"
        dangling.symlink_to(self.parent / "missing")
        for destination in (self.output, dangling):
            with self.subTest(destination=destination):
                fetch = Mock(side_effect=AssertionError("must refuse before network"))
                with self.assertRaises(FileExistsError):
                    docs.scrape(destination, fetch, max_pages=1)
                fetch.assert_not_called()
        self.assertEqual(evidence.read_text(), "original evidence")
        self.assertTrue(dangling.is_symlink())
        self.assertFalse((self.parent / "missing").exists())

    def test_http_adapter_uses_no_credentials_or_ambient_endpoint_and_bounds_reads(
        self,
    ) -> None:
        response = Mock(spec=http.client.HTTPResponse)
        response.status = 200
        response.getheader.return_value = "text/markdown; charset=utf-8"
        response.read.return_value = b"# Models\n"
        with patch.dict(
            "os.environ",
            {
                "TYPESAFE_API_KEY": "test-sentinel",
                "TYPESAFE_BASE_URL": "https://evil.test",
            },
        ):
            with patch.object(http.client, "HTTPSConnection") as connect:
                connection = connect.return_value
                connection.getresponse.return_value = response
                result = docs.PublicDocsClient(timeout=7).fetch(MODEL_URL)
        self.assertIsInstance(result, docs.Page)
        connect.assert_called_once_with("docs.typesafe.ai", timeout=7)
        connection.request.assert_called_once_with(
            "GET",
            "/models.md",
            headers={
                "User-Agent": "jev-opportunities-docs/1.0",
                "Accept": "text/markdown, text/plain",
                "Accept-Encoding": "identity",
                "Cache-Control": "no-cache",
            },
        )
        response.read.assert_called_once_with(docs.MAX_BYTES + 1)
        connection.close.assert_called_once_with()

    def test_redirects_are_reported_without_following_or_reading_the_body(self) -> None:
        response = Mock(spec=http.client.HTTPResponse)
        response.status = 302
        response.getheader.return_value = "https://evil.test/collect"
        with patch.object(http.client, "HTTPSConnection") as connect:
            connect.return_value.getresponse.return_value = response
            result = docs.PublicDocsClient(timeout=7).fetch(MODEL_URL)
        self.assertIsInstance(result, docs.FetchFailure)
        assert isinstance(result, docs.FetchFailure)
        self.assertIn("HTTP 302", result.error)
        self.assertEqual(connect.call_count, 1)
        response.read.assert_not_called()
        connect.return_value.close.assert_called_once_with()

    def test_timeout_is_a_recorded_failure_without_retry(self) -> None:
        with patch.object(http.client, "HTTPSConnection") as connect:
            connect.return_value.getresponse.side_effect = TimeoutError(
                "read timed out"
            )
            result = docs.PublicDocsClient(timeout=7).fetch(MODEL_URL)
        self.assertIsInstance(result, docs.FetchFailure)
        assert isinstance(result, docs.FetchFailure)
        self.assertEqual(result.error, "TimeoutError: read timed out")
        self.assertEqual(connect.call_count, 1)
        connect.return_value.close.assert_called_once_with()

    def test_off_origin_urls_are_refused_before_connection(self) -> None:
        with patch.object(http.client, "HTTPSConnection") as connect:
            result = docs.PublicDocsClient(timeout=7).fetch(
                "https://api.typesafe.ai/v1/models"
            )
        self.assertIsInstance(result, docs.FetchFailure)
        connect.assert_not_called()

    def test_non_docs_responses_are_rejected_at_the_text_boundary(self) -> None:
        invalid = (
            (b"<html>Login</html>", "text/html", "expected Markdown/plain"),
            (b"<!DOCTYPE html><html>Error</html>", "text/plain", "HTML page"),
            (b"\xff", "text/plain", "utf-8"),
            (b"# Hi\x00", "text/plain", "binary"),
            (b"  \n", "text/plain", "empty"),
            (b"x" * (docs.MAX_BYTES + 1), "text/markdown", "2 MiB"),
        )
        for body, content_type, message in invalid:
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(ValueError, message),
            ):
                docs.decode_document(body, content_type)
        self.assertEqual(
            docs.decode_document(b"x" * docs.MAX_BYTES, "text/plain"),
            "x" * docs.MAX_BYTES,
        )

    def test_cli_distinguishes_complete_incomplete_and_invalid_runs(self) -> None:
        with patch.object(docs.PublicDocsClient, "fetch", side_effect=fixture_fetch):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(docs.main([str(self.output), "--max-pages", "2"]), 0)
                self.assertEqual(
                    docs.main([str(self.parent / "partial"), "--max-pages", "1"]), 1
                )
                self.assertEqual(docs.main([str(self.output)]), 2)
        for flag, value in (
            ("--timeout", "nan"),
            ("--timeout", "0"),
            ("--max-pages", "513"),
        ):
            with self.subTest(flag=flag, value=value), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    docs.main([str(self.parent / "invalid"), flag, value])
                self.assertEqual(raised.exception.code, 2)
        self.assertFalse((self.parent / "invalid").exists())


class PackageTests(unittest.TestCase):
    source = Path(__file__).resolve().parents[1]

    def test_invocation_controls_and_fixture_containment_are_enforced(self) -> None:
        mutations = (
            (
                "SKILL.md",
                "disable-model-invocation: true",
                "disable-model-invocation: false",
                "Claude manual",
            ),
            (
                "agents/openai.yaml",
                "allow_implicit_invocation: false",
                'allow_implicit_invocation: "false"',
                "Codex implicit",
            ),
            (
                "evals/evals.json",
                "evals/files/application.ts",
                "../outside.ts",
                "escaping fixture",
            ),
            (
                "evals/trigger-evals.json",
                '"should_trigger": false',
                '"should_trigger": true',
                "positive and negative",
            ),
        )
        for relative, old, new, diagnostic in mutations:
            with (
                self.subTest(relative=relative),
                tempfile.TemporaryDirectory() as temporary,
            ):
                candidate = Path(temporary) / self.source.name
                shutil.copytree(
                    self.source,
                    candidate,
                    ignore=shutil.ignore_patterns("__pycache__", "*.png"),
                )
                path = candidate / relative
                original = path.read_text(encoding="utf-8")
                self.assertIn(old, original)
                path.write_text(original.replace(old, new), encoding="utf-8")
                errors = validate.validate(candidate)
                self.assertTrue(any(diagnostic in error for error in errors), errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_path", type=Path)
    args = parser.parse_args()
    errors = validate.validate(args.skill_path)
    if errors:
        print("Package validation failed: " + "; ".join(errors), file=sys.stderr)
        return 1
    PackageTests.source = args.skill_path.resolve()
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Unit tests for audify helper behavior."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import audify  # noqa: E402


class AudifyUnitTests(unittest.TestCase):
    def test_markdown_link_cleaning_preserves_anchor_text(self) -> None:
        text, stats = audify.clean_text(
            "# Hello\nVisit [the docs](https://example.com/docs) for details.\n",
            source_kind="text",
        )
        self.assertIn("the docs", text)
        self.assertNotIn("https://example.com/docs", text)
        self.assertGreaterEqual(stats["markdown_links_preserved"], 1)

    def test_html_cleaning_prefers_article_text(self) -> None:
        html = """
        <html><body>
        <nav>Cookie banner and nav links</nav>
        <article><h1>Actual story</h1><p>This should stay.</p></article>
        </body></html>
        """
        text, _stats = audify.clean_text(html, source_kind="url-html")
        self.assertIn("Actual story", text)
        self.assertIn("This should stay.", text)
        self.assertNotIn("Cookie banner", text)

    def test_docx_extraction_reads_paragraph_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "sample.docx"
            with zipfile.ZipFile(docx_path, "w") as archive:
                archive.writestr(
                    "word/document.xml",
                    (
                        '<?xml version="1.0" encoding="UTF-8"?>'
                        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                        "<w:body><w:p><w:r><w:t>Hello DOCX world</w:t></w:r></w:p></w:body>"
                        "</w:document>"
                    ),
                )
            extracted = audify.extract_docx_text(docx_path)
            self.assertIn("Hello DOCX world", extracted)

    def test_suitability_rejects_code_like_input(self) -> None:
        report = audify.assess_tts_suitability(
            "function main() { const x = 1; return x; }\nimport os\nreturn x;"
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("code" in reason for reason in report.reasons))

    def test_chunking_respects_max_chars(self) -> None:
        text = " ".join(["sentence."] * 300)
        chunks = audify.split_into_chunks(text, max_chars=120)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 120 for chunk in chunks))

    def test_build_prompt_contains_transcript_marker(self) -> None:
        prompt = audify.build_prompt("Hello there.", nuance="Warm narrator", title="Demo")
        self.assertIn("Synthesize speech only.", prompt)
        self.assertIn("### DIRECTOR NOTES", prompt)
        self.assertIn("### TRANSCRIPT", prompt)
        self.assertIn("Warm narrator", prompt)
        self.assertIn("Hello there.", prompt)

    def test_runtime_expectation_scales_for_longer_jobs(self) -> None:
        short = audify.estimate_runtime_expectation(word_count=120, chunk_count=1)
        long = audify.estimate_runtime_expectation(word_count=900, chunk_count=3)
        self.assertEqual(short["label"], "usually under 1 minute")
        self.assertEqual(long["label"], "often 2-6 minutes")
        self.assertGreater(long["recommended_poll_interval_seconds"], short["recommended_poll_interval_seconds"])


if __name__ == "__main__":
    unittest.main()

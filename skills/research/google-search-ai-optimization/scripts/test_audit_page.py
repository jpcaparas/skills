import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("audit_page.py")

INDEXABLE_HTML = """<!doctype html>
<html lang="en">
<head>
  <title>Widget A Field Test Results</title>
  <meta name="description" content="Original field data and buying guidance for Widget A.">
  <link rel="canonical" href="https://example.com/widgets/widget-a">
  <script type="application/ld+json">
  {"@context": "https://schema.org", "@type": "Product", "name": "Widget A",
   "description": "Field-tested widget", "brand": {"@type": "Brand", "name": "Example"}}
  </script>
</head>
<body><main><h1>Widget A Field Test Results</h1>
<p>Our team tested Widget A across three production deployments and measured setup time, failure modes, compatibility constraints, and support quality.</p>
<a href="/widgets/widget-b">Compare Widget B</a>
<img src="/images/widget-a.jpg" alt="Widget A mounted in a production rack">
</main></body></html>
"""

NOINDEX_HTML = INDEXABLE_HTML.replace(
    '<link rel="canonical"', '<meta name="robots" content="noindex"><link rel="canonical"'
)


def audit(html: str, *extra: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(html, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--input", str(page), *extra],
            capture_output=True,
            text=True,
            check=False,
        )


class AuditPageTest(unittest.TestCase):
    def test_indexable_page_passes_and_reports_signals(self) -> None:
        result = audit(INDEXABLE_HTML, "--expect-indexable", "--fail-on", "error")
        self.assertEqual(result.returncode, 0, result.stderr)
        signals = json.loads(result.stdout)["signals"]
        self.assertIn("Product", signals["jsonld_types"])
        self.assertGreaterEqual(signals["crawlable_link_count"], 1)

    def test_noindex_fails_only_when_indexing_is_expected(self) -> None:
        self.assertNotEqual(audit(NOINDEX_HTML, "--expect-indexable", "--fail-on", "error").returncode, 0)
        self.assertEqual(audit(NOINDEX_HTML, "--fail-on", "error").returncode, 0)


if __name__ == "__main__":
    unittest.main()

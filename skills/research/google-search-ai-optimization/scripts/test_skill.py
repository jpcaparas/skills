#!/usr/bin/env python3
"""Lightweight regression tests for google-search-ai-optimization."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


FIXTURE_HTML = """<!doctype html>
<html lang="en">
<head>
  <title>Widget A Field Test Results</title>
  <meta name="description" content="Original field data and buying guidance for Widget A.">
  <link rel="canonical" href="https://example.com/widgets/widget-a">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Widget A",
    "description": "Field-tested widget for production teams",
    "brand": {"@type": "Brand", "name": "Example"}
  }
  </script>
</head>
<body>
  <main>
    <h1>Widget A Field Test Results</h1>
    <p>Our team tested Widget A across three production deployments and measured setup time, failure modes, compatibility constraints, and support quality. This page explains who should buy it, who should avoid it, and which alternatives are better for high-volume teams.</p>
    <p>The data includes first-hand observations, version numbers, and concrete tradeoffs. It is written for buyers who need a reliable decision, not for keyword variants.</p>
    <a href="/widgets/widget-b">Compare Widget B</a>
    <img src="/images/widget-a.jpg" alt="Widget A mounted in a production rack">
  </main>
</body>
</html>
"""


def run(command: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        raise SystemExit(1)

    skill_path = os.path.abspath(sys.argv[1])
    errors: list[str] = []

    validate = run([sys.executable, "scripts/validate.py", skill_path], skill_path)
    if validate.returncode != 0:
        errors.append("validate.py failed")
        errors.append(validate.stdout)
        errors.append(validate.stderr)

    help_result = run([sys.executable, "scripts/audit_page.py", "--help"], skill_path)
    if help_result.returncode != 0 or "--expect-indexable" not in help_result.stdout:
        errors.append("audit_page.py --help did not expose expected options")

    with tempfile.TemporaryDirectory() as temp_dir:
        fixture = Path(temp_dir) / "page.html"
        fixture.write_text(FIXTURE_HTML, encoding="utf-8")
        audit = run(
            [
                sys.executable,
                "scripts/audit_page.py",
                "--input",
                str(fixture),
                "--expect-indexable",
                "--fail-on",
                "error",
            ],
            skill_path,
        )
        if audit.returncode != 0:
            errors.append("audit_page.py fixture audit failed")
            errors.append(audit.stdout)
            errors.append(audit.stderr)
        else:
            data = json.loads(audit.stdout)
            if "Product" not in data["signals"]["jsonld_types"]:
                errors.append("audit_page.py did not detect Product JSON-LD")
            if data["signals"]["crawlable_link_count"] < 1:
                errors.append("audit_page.py did not detect crawlable links")

    evals_path = os.path.join(skill_path, "evals", "evals.json")
    with open(evals_path, "r", encoding="utf-8") as handle:
        evals = json.load(handle)
    tags = {tag for item in evals.get("evals", []) for tag in item.get("tags", [])}
    for required in {"smoke", "edge", "negative", "disclosure"}:
        if required not in tags:
            errors.append(f"missing eval tag: {required}")

    result = {"passed": not errors, "errors": errors}
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()

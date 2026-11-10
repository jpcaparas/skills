"""Offline checks for find_code_language.py against the bundled Highlight.js cache."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "find_code_language.py"


def lookup(query: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), query], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


class FindCodeLanguageTest(unittest.TestCase):
    def test_typescript_aliases_come_from_cache(self) -> None:
        payload = lookup("typescript")
        self.assertEqual(payload["source"], "cache")
        aliases = {a for m in payload["matches"] for a in m["aliases"]}
        self.assertTrue({"ts", "tsx"} <= aliases)

    def test_unknown_alias_has_no_matches(self) -> None:
        self.assertEqual(lookup("nonsensexyz")["match_count"], 0)


if __name__ == "__main__":
    unittest.main()

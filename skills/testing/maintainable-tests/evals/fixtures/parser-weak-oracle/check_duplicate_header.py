"""Held-out evaluator probe for the intentional duplicate-header defect."""

from __future__ import annotations

import unittest

from invoice_parser import HeaderError, parse_header_line


class DuplicateHeaderProbe(unittest.TestCase):
    """Require uniqueness after the contract's normalization step."""

    def test_rejects_case_insensitive_duplicate(self) -> None:
        with self.assertRaises(HeaderError):
            parse_header_line(b"Invoice ID, invoice id")


if __name__ == "__main__":
    unittest.main()

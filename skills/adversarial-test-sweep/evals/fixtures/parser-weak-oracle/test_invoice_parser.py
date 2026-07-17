"""Existing tests for the invoice-header evaluation fixture."""

from __future__ import annotations

import unittest

from invoice_parser import HeaderError, parse_header_line


class InvoiceHeaderTests(unittest.TestCase):
    """Describe the fixture's currently exercised behavior."""

    def test_normalizes_two_columns(self) -> None:
        headers = parse_header_line(b"Invoice ID, invoice id")

        self.assertEqual(2, len(headers))

    def test_accepts_exact_byte_limit(self) -> None:
        self.assertEqual(("a", "b"), parse_header_line(b"A,B", max_bytes=3))

    def test_rejects_one_byte_over_limit(self) -> None:
        with self.assertRaises(HeaderError):
            parse_header_line(b"A,B!", max_bytes=3)


if __name__ == "__main__":
    unittest.main()

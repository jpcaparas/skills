"""Existing regression surface for the invoice-reminder fixture."""

from __future__ import annotations

from datetime import date
import unittest

from reminder import format_due_date


class FormatDueDateTests(unittest.TestCase):
    def test_formats_a_present_due_date(self) -> None:
        self.assertEqual(format_due_date(date(2026, 7, 20)), "20 July 2026")


if __name__ == "__main__":
    unittest.main()

"""Behavioural tests for analyze_ste_surface.py."""

import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze_ste_surface import TextType, analyze_text, estimate_word_count, read_input  # noqa: E402


def codes(text: str, text_type: TextType) -> set[str]:
    return {f.code for f in analyze_text(text, text_type).findings}


class SurfaceScannerTest(unittest.TestCase):
    def test_procedure_candidates(self) -> None:
        text = (
            "Don't remove the cover; the connector is installed and the technician "
            "is monitoring the very long maintenance operation while the second "
            "technician records all applicable measurements and then closes the panel."
        )
        expected = {"contraction", "semicolon", "passive-voice", "ing-form",
                    "coordinated-action", "estimated-word-limit"}
        self.assertLessEqual(expected, codes(text, TextType.PROCEDURE))

    def test_description_paragraph_sentence_limit(self) -> None:
        text = ("The unit starts. It monitors pressure. It records temperature. "
                "It sends data. It stores faults. It supplies status. It stops safely.")
        self.assertIn("paragraph-sentence-limit", codes(text, TextType.DESCRIPTION))

    def test_protected_code_is_not_inspected(self) -> None:
        text = ("The command is below.\n\n```bash\nmonitoring --is-installed --then\n```\n\n"
                "Use `being-installed` as the exact label.\n")
        found = codes(text, TextType.DESCRIPTION)
        self.assertFalse({"passive-voice", "ing-form"} & found)

    def test_hard_wrapped_sentence_is_one_sentence(self) -> None:
        text = ("Before you start the functional test, make sure that the hydraulic system "
                "is fully depressurized and the warning placard is installed\n"
                "at the main control panel for all maintenance personnel.")
        analysis = analyze_text(text, TextType.PROCEDURE)
        self.assertEqual(len(analysis.sentences), 1)
        self.assertEqual(analysis.sentences[0].line, 1)
        self.assertIn("estimated-word-limit", {f.code for f in analysis.findings})

    def test_special_unit_counting(self) -> None:
        text = ("Install the actuator AB-123 (the left flight-control actuator in the "
                "forward equipment bay) to 25 N·m before the "
                '"SYSTEM READY FOR OPERATION" message comes on.')
        self.assertEqual(estimate_word_count(text), 13)

    def test_json_record(self) -> None:
        record = json.loads(json.dumps(analyze_text("Remove the cover.", TextType.PROCEDURE).as_record()))
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(record["text_type"], "procedure")
        self.assertEqual(record["sentence_word_limit"], 20)

    def test_reads_file_and_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text("The component is installed.\n", encoding="utf-8")
            self.assertTrue(analyze_text(read_input(str(path)), TextType.DESCRIPTION).sentences)
        original = sys.stdin
        try:
            sys.stdin = StringIO("Remove the cover.\n")
            self.assertEqual(read_input("-"), "Remove the cover.\n")
        finally:
            sys.stdin = original


if __name__ == "__main__":
    unittest.main()

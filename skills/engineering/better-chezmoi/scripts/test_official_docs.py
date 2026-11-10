import unittest
from pathlib import Path

import official_docs

CORPUS = Path(__file__).resolve().parents[1] / "references" / "official-docs"


class OfficialDocsTest(unittest.TestCase):
    def test_parser_self_tests_pass(self) -> None:
        result = official_docs.run_self_tests()
        self.assertTrue(result["passed"], result)

    def test_bundled_corpus_is_complete_and_valid(self) -> None:
        manifest = official_docs.validate_corpus(CORPUS)
        self.assertEqual(len(manifest.documents), len(official_docs.DOCUMENT_SOURCES))


if __name__ == "__main__":
    unittest.main()

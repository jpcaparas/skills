import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_transcript as ft

VIDEO_ID = "dQw4w9WgXcQ"


class ExtractVideoIdTest(unittest.TestCase):
    def test_supported_url_shapes_yield_the_id(self) -> None:
        inputs = [
            VIDEO_ID,
            f"https://www.youtube.com/watch?v={VIDEO_ID}",
            f"https://www.youtube.com/watch?v={VIDEO_ID}&t=42s&list=abc",
            f"https://youtu.be/{VIDEO_ID}?si=abc",
            f"https://www.youtube.com/embed/{VIDEO_ID}",
            f"https://www.youtube.com/shorts/{VIDEO_ID}?feature=share",
            f"https://m.youtube.com/watch?v={VIDEO_ID}",
        ]
        for value in inputs:
            with self.subTest(value=value):
                self.assertEqual(ft.extract_video_id(value), VIDEO_ID)

    def test_wrong_length_id_is_rejected(self) -> None:
        self.assertIsNone(ft.extract_video_id("thisIsNotARealVideoID"))


class FormatTest(unittest.TestCase):
    def test_snippet_whitespace_is_collapsed(self) -> None:
        self.assertEqual(ft.format_plain_snippet("hello\nworld\tagain"), "hello world again")

    def test_timestamps(self) -> None:
        self.assertEqual(ft.format_timestamp(65), "01:05")
        self.assertEqual(ft.format_timestamp(3725), "01:02:05")
        self.assertEqual(ft.format_vtt_timestamp(3725.5), "01:02:05.500")


if __name__ == "__main__":
    unittest.main()

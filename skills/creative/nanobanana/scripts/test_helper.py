#!/usr/bin/env python3
"""Offline regressions for scripts/nanobanana.py against a local stub of the Gemini API.

The stub mirrors response shapes recorded live on 2026-10-18. These tests never contact Google
and never read an ambient GEMINI_API_KEY.
"""

from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
import json
import os
import struct
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent / "nanobanana.py"
FAKE_KEY = "test-key-not-real"


def fake_jpeg(width: int, height: int) -> bytes:
    """A minimal JPEG header with an SOF0 segment, enough for dimension parsing."""
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, height, width, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 4) + b"\x00\x00" + sof + b"\xff\xd9"


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


# Live shape: thought steps carry only signatures; the image arrives in a model_output step.
INTERACTION = {
    "id": "v1_turn_one", "status": "completed", "object": "interaction", "model": "gemini-nano-banana-2.1",
    "usage": {"total_input_tokens": 1155, "input_tokens_by_modality": [{"modality": "image", "tokens": 1120}, {"modality": "text", "tokens": 35}],
              "total_output_tokens": 1425, "output_tokens_by_modality": [{"modality": "image", "tokens": 1120}], "total_thought_tokens": 599},
    "steps": [
        {"type": "thought", "signature": "c2ln"},
        {"type": "model_output", "content": [{"type": "image", "mime_type": "image/jpeg", "data": b64(fake_jpeg(1200, 896))}]},
    ],
}
GENERATE_CONTENT = {
    "candidates": [{
        "finishReason": "STOP",
        "content": {"parts": [
            {"text": "thinking...", "thought": True},
            {"inlineData": {"mimeType": "image/jpeg", "data": b64(fake_jpeg(896, 1200))}, "thoughtSignature": "c2ln"},
        ]},
        "groundingMetadata": {
            "imageSearchQueries": ["takahe bird"],
            "groundingChunks": [{"image": {"sourceUri": "https://example.org/takahe.jpg", "title": "Takahē"}}],
            "searchEntryPoint": {"renderedContent": "<div>suggestions</div>"},
        },
    }],
    "usageMetadata": {"promptTokenCount": 56, "candidatesTokenCount": 1578, "thoughtsTokenCount": 719,
                      "candidatesTokensDetails": [{"modality": "IMAGE", "tokenCount": 1120}]},
}


class Stub(BaseHTTPRequestHandler):
    requests: list[dict] = []
    replies: list[tuple[int, dict]] = []

    def _reply(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        Stub.requests.append({"method": self.command, "path": self.path, "key": self.headers.get("x-goog-api-key"),
                              "body": json.loads(raw) if raw.startswith(b"{") else None})
        status, payload = Stub.replies.pop(0) if Stub.replies else (500, {"error": {"message": "no stubbed reply"}})
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_DELETE = _reply

    def log_message(self, *_args) -> None:
        pass


class HelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        env = {"NANOBANANA_API_ROOT": f"http://127.0.0.1:{cls.server.server_address[1]}", "GEMINI_API_KEY": FAKE_KEY}
        with mock.patch.dict(os.environ, env, clear=False):
            spec = importlib.util.spec_from_file_location("nanobanana", SCRIPT)
            cls.nb = importlib.util.module_from_spec(spec)
            sys.modules["nanobanana"] = cls.nb  # dataclasses resolve annotations through sys.modules
            spec.loader.exec_module(cls.nb)
        cls.nb.RETRY_DELAYS_SECONDS = (0, 0)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self) -> None:
        Stub.requests, Stub.replies = [], []
        self.tmp = Path(tempfile.mkdtemp())
        self.env = mock.patch.dict(os.environ, {"GEMINI_API_KEY": FAKE_KEY})
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_cli(self, *argv: str) -> tuple[int, dict | None, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = self.nb.main(list(argv))
        text = out.getvalue()
        return code, (json.loads(text) if text.strip().startswith("{") else None), err.getvalue()

    def ref(self, name: str, data: bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 32) -> str:
        path = self.tmp / name
        path.write_bytes(data)
        return str(path)

    def test_edit_request_is_pinned_and_saves_the_image_with_cost(self) -> None:
        Stub.replies = [(200, INTERACTION)]
        out = self.tmp / "edit.jpg"
        code, summary, err = self.run_cli("generate", "--ref", self.ref("room.png"), "--ratio", "4:3", "--size", "1K",
                                          "--thinking", "high", "--out", str(out), "Swap", "the", "sofa")
        self.assertEqual(code, 0, err)
        request = Stub.requests[0]
        self.assertEqual((request["method"], request["path"], request["key"]), ("POST", "/v1beta/interactions", FAKE_KEY))
        body = request["body"]
        self.assertEqual(body["model"], "gemini-nano-banana-2.1")
        self.assertEqual(body["input"][0]["type"], "image")
        self.assertEqual(body["input"][0]["mime_type"], "image/png")
        self.assertEqual(body["input"][1], {"type": "text", "text": "Swap the sofa"})
        self.assertEqual(body["response_format"], {"type": "image", "image_size": "1K", "aspect_ratio": "4:3"})
        self.assertEqual(body["generation_config"], {"thinking_level": "high"})
        self.assertTrue(body["store"])
        self.assertEqual(out.read_bytes(), fake_jpeg(1200, 896))
        self.assertEqual(summary["images"][0]["width"], 1200)
        self.assertEqual(summary["interaction_id"], "v1_turn_one")
        # 1155 input at $1.50/M + 1120 image at $30/M + (305 other output + 599 thought) at $7.50/M
        self.assertAlmostEqual(summary["estimated_cost_usd"], round(1155 * 1.5e-6 + 1120 * 30e-6 + 904 * 7.5e-6, 4))

    def test_continue_resends_interaction_scoped_settings(self) -> None:
        Stub.replies = [(200, INTERACTION)]
        code, _, err = self.run_cli("generate", "--continue", "v1_turn_one", "--size", "2K", "--thinking", "minimal",
                                    "--out", str(self.tmp / "t2.jpg"), "Make it blue")
        self.assertEqual(code, 0, err)
        body = Stub.requests[0]["body"]
        self.assertEqual(body["previous_interaction_id"], "v1_turn_one")
        self.assertEqual(body["response_format"], {"type": "image", "image_size": "2K"})
        self.assertEqual(body["generation_config"], {"thinking_level": "minimal"})

    def test_search_routes_to_generate_content_and_saves_attribution(self) -> None:
        Stub.replies = [(200, GENERATE_CONTENT)]
        out = self.tmp / "card.jpg"
        code, summary, err = self.run_cli("generate", "--search", "--image-search", "--ratio", "3:4", "--out", str(out), "A takahē card")
        self.assertEqual(code, 0, err)
        request = Stub.requests[0]
        self.assertEqual(request["path"], "/v1beta/models/gemini-nano-banana-2.1:generateContent")
        self.assertEqual(request["body"]["tools"], [{"googleSearch": {"searchTypes": {"webSearch": {}, "imageSearch": {}}}}])
        self.assertEqual(request["body"]["generationConfig"]["imageConfig"], {"imageSize": "1K", "aspectRatio": "3:4"})
        self.assertEqual(out.read_bytes(), fake_jpeg(896, 1200))  # the thought part is skipped
        self.assertEqual(summary["search"]["queries"], ["takahe bird"])
        self.assertEqual(summary["search"]["sources"], [{"kind": "image", "title": "Takahē", "uri": "https://example.org/takahe.jpg"}])
        self.assertEqual(out.with_suffix(".search.html").read_text(), "<div>suggestions</div>")
        self.assertNotIn("interaction_id", summary)

    def test_invalid_requests_are_rejected_before_any_call(self) -> None:
        cases = [
            ("generate", "--ratio", "9:21", "x"),
            ("generate", "--size", "1k", "x"),
            ("generate", "--thinking", "low", "x"),
            ("generate", "--out", str(self.tmp / "a.png"), "x"),
            ("generate", "--ref", str(self.tmp / "missing.png"), "x"),
            ("generate", "--ref", self.ref("notes.txt", b"hello"), "x"),
            ("generate", "--image-search", "--size", "512", "x"),
            ("generate", "--search", "--continue", "v1_turn_one", "x"),
            ("generate", "   "),
            ("generate", *[arg for i in range(15) for arg in ("--ref", self.ref(f"r{i}.png"))], "x"),
        ]
        for argv in cases:
            with self.subTest(argv=argv[:4]):
                with contextlib.redirect_stderr(io.StringIO()):
                    try:
                        code, _, _ = self.run_cli(*argv)
                    except SystemExit as exit_:  # argparse choices
                        code = exit_.code
                self.assertEqual(code, 2)
        self.assertEqual(Stub.requests, [])

    def test_text_only_reply_fails_with_the_model_message(self) -> None:
        Stub.replies = [(200, {"id": "v1_x", "status": "completed", "usage": {}, "steps": [
            {"type": "model_output", "content": [{"type": "text", "text": "I can't draw that, but here is a description."}]}]})]
        code, _, err = self.run_cli("generate", "--out", str(self.tmp / "none.jpg"), "x")
        self.assertEqual(code, 1)
        self.assertIn("No image was returned", err)
        self.assertIn("here is a description", err)
        self.assertFalse((self.tmp / "none.jpg").exists())

    def test_requires_action_is_reported_instead_of_saving_nothing(self) -> None:
        Stub.replies = [(200, {"id": "v1_x", "status": "requires_action", "usage": {}, "steps": [
            {"type": "function_call", "name": "google:image_search", "arguments": {"queries": ["takahe"]}}]})]
        code, _, err = self.run_cli("generate", "--out", str(self.tmp / "x.jpg"), "x")
        self.assertEqual(code, 1)
        self.assertIn("requires_action", err)

    def test_safety_block_is_not_retried_and_explains_itself(self) -> None:
        Stub.replies = [(400, {"error": {"code": 400, "message": "Image generation blocked due to safety violations. Please modify your input and retry."}})]
        code, _, err = self.run_cli("generate", "--out", str(self.tmp / "x.jpg"), "x")
        self.assertEqual(code, 1)
        self.assertEqual(len(Stub.requests), 1)
        self.assertIn("Rephrase the prompt", err)

    def test_throttle_is_retried(self) -> None:
        Stub.replies = [(429, {"error": {"message": "Resource exhausted"}}), (503, {"error": {"message": "Unavailable"}}), (200, INTERACTION)]
        code, _, err = self.run_cli("generate", "--out", str(self.tmp / "x.jpg"), "x")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(Stub.requests), 3)

    def test_large_reference_is_uploaded_and_sent_by_uri(self) -> None:
        self.nb.INLINE_FILE_LIMIT_BYTES = 16
        self.addCleanup(setattr, self.nb, "INLINE_FILE_LIMIT_BYTES", 20 * 1024 * 1024)
        video = self.ref("clip.mp4", b"\x00" * 64)
        upload = mock.MagicMock()
        upload.return_value = "https://files.example/abc"
        with mock.patch.object(self.nb, "upload_file", upload):
            Stub.replies = [(200, INTERACTION)]
            code, _, err = self.run_cli("generate", "--ref", video, "--out", str(self.tmp / "x.jpg"), "Poster from this clip")
        self.assertEqual(code, 0, err)
        self.assertEqual(Stub.requests[0]["body"]["input"][0], {"type": "video", "uri": "https://files.example/abc", "mime_type": "video/mp4"})

    def test_pdf_reference_is_sent_as_a_document(self) -> None:
        Stub.replies = [(200, INTERACTION)]
        code, _, err = self.run_cli("generate", "--ref", self.ref("menu.pdf", b"%PDF-1.4"), "--out", str(self.tmp / "x.jpg"), "Chalkboard menu")
        self.assertEqual(code, 0, err)
        self.assertEqual(Stub.requests[0]["body"]["input"][0]["type"], "document")
        self.assertEqual(Stub.requests[0]["body"]["input"][0]["mime_type"], "application/pdf")

    def test_batch_submit_and_fetch(self) -> None:
        jobs = self.tmp / "jobs.jsonl"
        jobs.write_text('{"key": "boat", "prompt": "A paper boat", "ratio": "1:1"}\n\n{"prompt": "A marble", "size": "2K", "thinking": "minimal"}\n')
        Stub.replies = [(200, {"name": "batches/b1", "metadata": {"state": "BATCH_STATE_PENDING"}})]
        code, summary, err = self.run_cli("batch-submit", str(jobs))
        self.assertEqual(code, 0, err)
        requests = Stub.requests[0]["body"]["batch"]["input_config"]["requests"]["requests"]
        self.assertEqual([r["metadata"]["key"] for r in requests], ["boat", "3"])
        self.assertEqual(requests[1]["request"]["generation_config"]["imageConfig"], {"imageSize": "2K"})
        self.assertEqual(summary["requests"], 2)

        Stub.requests = []
        Stub.replies = [(200, {"name": "batches/b1", "metadata": {"state": "BATCH_STATE_RUNNING"}})]
        code, summary, _ = self.run_cli("batch-fetch", "b1")
        self.assertEqual((code, summary["done"]), (3, False))

        done = {"name": "batches/b1", "done": True, "metadata": {"state": "BATCH_STATE_SUCCEEDED", "batchStats": {"requestCount": "2"}, "output": {
            "inlinedResponses": {"inlinedResponses": [
                {"metadata": {"key": "boat"}, "response": GENERATE_CONTENT},
                {"metadata": {"key": "3"}, "error": {"message": "blocked"}}]}}}}
        Stub.replies = [(200, done)]
        code, summary, err = self.run_cli("batch-fetch", "batches/b1", "--out-dir", str(self.tmp / "batch"))
        self.assertEqual(code, 0, err)
        self.assertEqual((self.tmp / "batch" / "boat.jpg").read_bytes(), fake_jpeg(896, 1200))
        self.assertEqual(summary["items"][1], {"key": "3", "error": "blocked"})
        # Batch is half price: (56 * 1.5 + 1120 * 30 + (458 + 719) * 7.5) / 1e6 / 2
        self.assertAlmostEqual(summary["items"][0]["estimated_cost_usd"], round((56 * 1.5 + 1120 * 30 + 1177 * 7.5) / 1e6 / 2, 4))

    def test_batch_rejects_the_512_size(self) -> None:
        jobs = self.tmp / "jobs.jsonl"
        jobs.write_text('{"prompt": "A boat", "size": "512"}\n')
        code, _, err = self.run_cli("batch-submit", str(jobs))
        self.assertEqual(code, 2)
        self.assertIn("1K, 2K or 4K", err)
        self.assertEqual(Stub.requests, [])

    def test_contract_detects_drift_from_the_supported_values_lists(self) -> None:
        def supported(field: str, values: list[str]) -> tuple[int, dict]:
            listed = ", ".join(f"'{v}'" for v in values)
            return 400, {"error": {"message": f"The value 'x' is not supported for '{field}'. Supported values: {listed}."}}
        Stub.replies = [
            (200, {"displayName": "Nano Banana 2.1"}),
            supported("response_format.aspect_ratio", list(self.nb.ASPECT_RATIOS)),
            supported("response_format.image_size", ["1K", "2K", "4K"]),  # 512 disappeared
            supported("generation_config.thinking_level", ["minimal", "low", "medium", "high"]),
            supported("response_format.mime_type", ["image/jpeg"]),
        ]
        code, report, _ = self.run_cli("contract")
        self.assertEqual(code, 4)
        self.assertTrue(report["aspect_ratio"]["matches_helper"])
        self.assertFalse(report["image_size"]["matches_helper"])
        self.assertTrue(report["thinking_level"]["matches_helper"])
        self.assertTrue(report["drift"])

    def test_missing_key_fails_without_a_request(self) -> None:
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
            code, _, err = self.run_cli("generate", "x")
        self.assertEqual(code, 2)
        self.assertIn("GEMINI_API_KEY", err)
        self.assertEqual(Stub.requests, [])

    def test_dry_run_never_sends_or_prints_the_key(self) -> None:
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}), contextlib.redirect_stdout(out):
            code = self.nb.main(["generate", "--dry-run", "--ref", self.ref("a.png"), "A cat"])
        self.assertEqual(code, 0)
        self.assertEqual(Stub.requests, [])
        printed = json.loads(out.getvalue())
        self.assertEqual(printed["request"]["input"][0]["data"], "<base64>")
        self.assertNotIn(FAKE_KEY, out.getvalue())


if __name__ == "__main__":
    unittest.main()

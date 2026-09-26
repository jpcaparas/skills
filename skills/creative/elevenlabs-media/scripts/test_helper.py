"""Offline regressions for actual request/receipt and recovery invariants."""

from __future__ import annotations

import base64
import io
import json
import os
import tempfile
import unittest
from collections import deque
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import BinaryIO
from unittest.mock import patch

import elevenlabs_media as media


@dataclass
class Call:
    method: media.Method
    url: str
    headers: Mapping[str, str]
    body: bytes
    timeout: float


class FakeTransport:
    def __init__(self, *responses: media.Response | Exception) -> None:
        self.responses = deque(responses)
        self.calls: list[Call] = []

    @contextmanager
    def open(
        self,
        method: media.Method,
        url: str,
        headers: Mapping[str, str],
        body: BinaryIO | None,
        timeout: float,
    ) -> Iterator[media.Response]:
        self.calls.append(
            Call(
                method,
                url,
                dict(headers),
                b"" if body is None else body.read(),
                timeout,
            )
        )
        if not self.responses:
            raise AssertionError("Unexpected network call or retry")
        result = self.responses.popleft()
        if isinstance(result, Exception):
            raise result
        yield result


def response(value: media.Json, status: int = 200) -> media.Response:
    return media.Response(
        status,
        {"content-type": "application/json"},
        io.BytesIO(json.dumps(value).encode()),
    )


@dataclass
class Clock:
    now: float = 0.0
    delays: list[float] = field(default_factory=list)

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)
        self.now += seconds


class HelperTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        network = patch(
            "socket.create_connection",
            side_effect=AssertionError("Offline test attempted real network"),
        )
        network.start()
        self.addCleanup(network.stop)
        environment = patch.dict(os.environ, {"ELEVENLABS_API_KEY": "offline-test-key"})
        environment.start()
        self.addCleanup(environment.stop)

    def test_preview_does_not_need_key_or_contact_api(self) -> None:
        request = self.root / "request.json"
        request.write_text('{"text":"Private words","model_id":"eleven_v3"}')
        transport = FakeTransport()
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": ""}):
            result = media.run(
                media.parser().parse_args(
                    [
                        "request",
                        "POST",
                        "/v1/text-to-speech/voice",
                        "--json",
                        str(request),
                    ]
                ),
                transport,
            )
        self.assertEqual(result["state"], "preview_only")
        self.assertEqual(transport.calls, [])
        self.assertNotIn("Private words", json.dumps(result))

    def test_path_and_query_cannot_change_authenticated_origin(self) -> None:
        for path in (
            "https://evil.test/v1/models",
            "//evil.test/v1/models",
            "/v1/voices/../user",
            "/v1/voices/%2e%2e",
            "/v1/models?x=y",
            "/v1/service-accounts",
        ):
            with self.subTest(path=path), self.assertRaises(media.MediaError):
                media.api_url(path, [])
        self.assertEqual(
            media.api_url("/v2/voices", [("next_page_token", "a+b&x=y")]),
            "https://api.elevenlabs.io/v2/voices?next_page_token=a%2Bb%26x%3Dy",
        )

    def test_unicode_json_and_query_are_sent_once_without_key_in_receipt(self) -> None:
        request = self.root / "request.json"
        request.write_text('{"text":"Kia ora, Tāmaki Makaurau."}', encoding="utf-8")
        out = self.root / "speech.mp3"
        transport = FakeTransport(
            media.Response(
                200,
                {
                    "content-type": "audio/mpeg",
                    "request-id": "req123",
                    "character-cost": "12",
                    "set-cookie": "private-cookie",
                    "content-length": "7",
                },
                io.BytesIO(b"ID3test"),
            )
        )
        result = media.run(
            media.parser().parse_args(
                [
                    "request",
                    "POST",
                    "/v1/text-to-speech/voice",
                    "--json",
                    str(request),
                    "--query",
                    "output_format=mp3_44100_128",
                    "--expect",
                    "audio",
                    "--out",
                    str(out),
                    "--execute",
                ]
            ),
            transport,
        )
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(
            json.loads(transport.calls[0].body), {"text": "Kia ora, Tāmaki Makaurau."}
        )
        self.assertEqual(transport.calls[0].headers["xi-api-key"], "offline-test-key")
        self.assertEqual(out.read_bytes(), b"ID3test")
        self.assertEqual(result["bytes"], 7)
        self.assertNotIn("offline-test-key", json.dumps(result))
        self.assertNotIn("private-cookie", json.dumps(result))
        self.assertEqual(out.stat().st_mode & 0o777, 0o600)
        self.assertFalse(Path(str(out) + ".part").exists())

    def test_repeated_multipart_files_and_json_form_settings_preserve_bytes(
        self,
    ) -> None:
        first, second = self.root / 'secret"name.mp3', self.root / "second.wav"
        first.write_bytes(b"first\x00\xff")
        second.write_bytes(b"second\r\n")
        fields = [("name", "Māori narrator"), ("voice_settings", '{"stability":0.3}')]
        with media.make_payload(
            None, fields, [("files", str(first)), ("files", str(second))], 4096
        ) as payload:
            self.assertIsNotNone(payload.stream)
            assert payload.stream is not None
            wire = payload.stream.read()
            self.assertEqual(len(wire), payload.size)
            self.assertEqual(payload.headers["Content-Length"], str(len(wire)))
            document = BytesParser(policy=policy.default).parsebytes(
                (
                    "Content-Type: " + payload.headers["Content-Type"] + "\r\n\r\n"
                ).encode()
                + wire
            )
        parts = list(document.iter_parts())
        self.assertEqual(
            [p.get_param("name", header="content-disposition") for p in parts],
            ["name", "voice_settings", "files", "files"],
        )
        self.assertEqual(
            [p.get_payload(decode=True) for p in parts],
            [
                "Māori narrator".encode(),
                b'{"stability":0.3}',
                b"first\x00\xff",
                b"second\r\n",
            ],
        )
        self.assertNotIn(b'secret"name', wire)

    def test_upload_limit_fails_before_network(self) -> None:
        upload = self.root / "big.wav"
        upload.write_bytes(b"x" * 1025)
        with self.assertRaisesRegex(media.MediaError, "max-upload"):
            with media.make_payload(None, [], [("audio", str(upload))], 1024):
                self.fail("Oversized body was accepted")

    def test_json_and_multipart_conflict_fails_before_reading_input(self) -> None:
        with self.assertRaisesRegex(media.MediaError, "cannot be combined"):
            with media.make_payload(
                self.root / "missing.json", [("text", "x")], [], 4096
            ):
                self.fail("Conflicting body was accepted")

    def test_existing_output_or_dangling_symlink_prevents_even_a_paid_request(
        self,
    ) -> None:
        out = self.root / "output.mp3"
        transport = FakeTransport()
        for dangling in (False, True):
            if dangling:
                out.symlink_to(self.root / "missing")
            else:
                out.write_bytes(b"original")
            with self.subTest(dangling=dangling), self.assertRaises(media.MediaError):
                media.save_response(
                    transport,
                    "POST",
                    media.API_ORIGIN + "/v1/music",
                    {},
                    media.Payload(None, {}, 0),
                    out,
                    "audio",
                    30,
                    1024,
                )
            if not dangling:
                self.assertEqual(out.read_bytes(), b"original")
            out.unlink()
        self.assertEqual(transport.calls, [])

    def test_http_permission_error_never_becomes_audio_or_exposes_echoed_secret(
        self,
    ) -> None:
        transport = FakeTransport(
            response(
                {
                    "detail": {
                        "status": "missing_permissions",
                        "request_id": "req_denied",
                        "message": "private prompt and offline-test-key",
                    }
                },
                401,
            )
        )
        out = self.root / "failed.mp3"
        with self.assertRaises(media.ApiError) as caught:
            media.save_response(
                transport,
                "POST",
                media.API_ORIGIN + "/v1/music",
                {},
                media.Payload(None, {}, 0),
                out,
                "audio",
                30,
                1024,
            )
        self.assertEqual(caught.exception.code, "missing_permissions")
        self.assertNotIn("offline-test-key", str(caught.exception))
        self.assertEqual(len(transport.calls), 1)
        self.assertFalse(out.exists())
        receipt = json.loads(Path(str(out) + ".meta.json").read_text())
        self.assertEqual(
            receipt["api_error"],
            {"code": "missing_permissions", "request_id": "req_denied"},
        )
        self.assertNotIn("private prompt", json.dumps(receipt))

    def test_client_representation_does_not_disclose_key(self) -> None:
        self.assertNotIn(
            "offline-test-key",
            repr(media.ElevenLabs("offline-test-key", FakeTransport())),
        )

    def test_empty_media_is_not_published_even_with_success_status(self) -> None:
        for status in (200, 204):
            out = self.root / f"empty-{status}.mp3"
            transport = FakeTransport(
                media.Response(status, {"content-type": "audio/mpeg"}, io.BytesIO())
            )
            with (
                self.subTest(status=status),
                self.assertRaisesRegex(media.MediaError, "[Ee]mpty|[Nn]o content"),
            ):
                media.save_response(
                    transport,
                    "POST",
                    media.API_ORIGIN + "/v1/music",
                    {},
                    media.Payload(None, {}, 0),
                    out,
                    "audio",
                    30,
                    1024,
                )
            self.assertFalse(out.exists())
            self.assertEqual(len(transport.calls), 1)

    def test_no_content_delete_is_a_valid_empty_result(self) -> None:
        out = self.root / "deleted.json"
        transport = FakeTransport(media.Response(204, {}, io.BytesIO()))
        result = media.save_response(
            transport,
            "DELETE",
            media.API_ORIGIN + "/v1/voices/owned",
            {},
            media.Payload(None, {}, 0),
            out,
            "json",
            30,
            1024,
        )
        self.assertEqual(result["state"], "complete")
        self.assertEqual(result["bytes"], 0)
        self.assertEqual(out.read_bytes(), b"")

    def test_successful_json_response_is_not_published_as_audio(self) -> None:
        out = self.root / "wrong.mp3"
        with self.assertRaisesRegex(media.MediaError, "Unexpected response type"):
            media.save_response(
                FakeTransport(response({"error": "oops"})),
                "POST",
                media.API_ORIGIN + "/v1/music",
                {},
                media.Payload(None, {}, 0),
                out,
                "audio",
                30,
                1024,
            )
        self.assertFalse(out.exists())

    def test_disconnect_is_not_retried_and_receipt_survives(self) -> None:
        out = self.root / "lost.mp3"
        transport = FakeTransport(TimeoutError("response lost"))
        with self.assertRaises(TimeoutError):
            media.save_response(
                transport,
                "POST",
                media.API_ORIGIN + "/v1/music",
                {},
                media.Payload(None, {}, 0),
                out,
                "audio",
                30,
                1024,
            )
        self.assertEqual(len(transport.calls), 1)
        receipt = json.loads(Path(str(out) + ".meta.json").read_text())
        self.assertEqual(receipt["state"], "incomplete_or_unknown")
        self.assertFalse(out.exists())

    def test_truncated_audio_retains_bytes_and_request_id_without_final_file(
        self,
    ) -> None:
        out = self.root / "partial.mp3"
        transport = FakeTransport(
            media.Response(
                200,
                {
                    "content-type": "audio/mpeg",
                    "content-length": "99",
                    "request-id": "recover_me",
                },
                io.BytesIO(b"only-three"),
            )
        )
        with self.assertRaisesRegex(media.MediaError, "Truncated"):
            media.save_response(
                transport,
                "POST",
                media.API_ORIGIN + "/v1/music",
                {},
                media.Payload(None, {}, 0),
                out,
                "audio",
                30,
                1024,
            )
        self.assertEqual(Path(str(out) + ".part").read_bytes(), b"only-three")
        receipt = json.loads(Path(str(out) + ".meta.json").read_text())
        self.assertEqual(receipt["headers"]["request-id"], "recover_me")
        self.assertFalse(out.exists())

    def test_output_limit_is_enforced_without_publishing_oversize_file(self) -> None:
        out = self.root / "large.mp3"
        transport = FakeTransport(
            media.Response(200, {"content-type": "audio/mpeg"}, io.BytesIO(b"12345"))
        )
        with self.assertRaisesRegex(media.MediaError, "max-output"):
            media.save_response(
                transport,
                "GET",
                media.API_ORIGIN + "/v1/history/item/audio",
                {},
                media.Payload(None, {}, 0),
                out,
                "audio",
                30,
                4,
            )
        self.assertFalse(out.exists())

    def test_signed_download_uses_no_api_key_or_signed_url_in_receipt(self) -> None:
        source, out = self.root / "complete.json", self.root / "result.png"
        source.write_text(
            '{"content_url":"https://storage.googleapis.com/bucket/object?signature=private"}'
        )
        transport = FakeTransport(
            media.Response(
                200, {"content-type": "image/png"}, io.BytesIO(b"png-fixture")
            )
        )
        result = media.run(
            media.parser().parse_args(
                [
                    "download",
                    "--from-json",
                    str(source),
                    "--out",
                    str(out),
                    "--expect",
                    "image",
                ]
            ),
            transport,
        )
        self.assertEqual(transport.calls[0].headers, {})
        self.assertNotIn("signature", json.dumps(result))
        self.assertEqual(out.read_bytes(), b"png-fixture")

    def test_download_rejects_origin_confusion_local_urls_and_redirects(self) -> None:
        for url in (
            "http://storage.googleapis.com/bucket",
            "https://storage.googleapis.com.evil.test/a",
            "https://user@storage.googleapis.com/a",
            "https://127.0.0.1/a",
            "file:///etc/passwd",
        ):
            with self.subTest(url=url), self.assertRaises(media.MediaError):
                media.download_url(url)
        transport = FakeTransport(
            media.Response(302, {"location": "https://evil.test"}, io.BytesIO())
        )
        with self.assertRaises(media.ApiError):
            media.save_response(
                transport,
                "GET",
                "https://storage.googleapis.com/a",
                {},
                media.Payload(None, {}, 0),
                self.root / "x.png",
                "image",
                30,
                1024,
            )
        self.assertEqual(len(transport.calls), 1)

    def test_video_polling_obeys_backoff_and_only_completed_provides_url(self) -> None:
        transport = FakeTransport(
            response({"status": "pending"}),
            response({"status": "generating"}),
            response(
                {
                    "status": "completed",
                    "content_url": "https://storage.googleapis.com/x",
                    "content_mime_type": "video/mp4",
                }
            ),
        )
        clock = Clock()
        result = media.wait_for_generation(
            media.ElevenLabs("test", transport),
            "video",
            "job1",
            120,
            clock.monotonic,
            clock.sleep,
        )
        self.assertEqual(clock.delays, [10.0, 20.0])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            [call.method for call in transport.calls], ["GET", "GET", "GET"]
        )

    def test_poll_deadline_failure_and_unknown_status_do_not_create_replacements(
        self,
    ) -> None:
        for status, expected in (
            ("failed", "failed"),
            ("future_state", "Unrecognized"),
            ("pending", "deadline"),
        ):
            transport = FakeTransport(
                response({"status": status, "failure_reason": "moderated"})
            )
            clock = Clock()
            with (
                self.subTest(status=status),
                self.assertRaisesRegex(media.MediaError, expected),
            ):
                media.wait_for_generation(
                    media.ElevenLabs("test", transport),
                    "image",
                    "keep_id",
                    1,
                    clock.monotonic,
                    clock.sleep,
                )
            self.assertEqual(len(transport.calls), 1)
            self.assertEqual(clock.delays, [])

    def test_expired_poll_budget_does_not_start_a_negative_timeout_request(
        self,
    ) -> None:
        times = iter((0.0, 0.9, 1.1))
        transport = FakeTransport(response({"status": "pending"}))
        with self.assertRaisesRegex(media.MediaError, "deadline"):
            media.wait_for_generation(
                media.ElevenLabs("test", transport),
                "image",
                "keep_id",
                1,
                lambda: next(times, 1.1),
                lambda seconds: self.fail("No time to sleep"),
            )
        self.assertTrue(all(0 < call.timeout <= 0.11 for call in transport.calls))
        self.assertEqual(len(transport.calls), 1)

    def test_timing_chunks_decode_in_order_and_preserve_original_alignment(
        self,
    ) -> None:
        source, out = self.root / "timing.ndjson", self.root / "audio.mp3"
        content = (
            "\n".join(
                json.dumps(
                    {
                        "audio_base64": base64.b64encode(chunk).decode(),
                        "alignment": {"characters": ["a"]},
                    }
                )
                for chunk in (b"ID3a", b"different-tail")
            )
            + "\n"
        )
        source.write_text(content)
        media.decode_audio(source, out, True)
        self.assertEqual(out.read_bytes(), b"ID3adifferent-tail")
        self.assertEqual(source.read_text(), content)

    def test_bad_base64_is_not_silently_skipped(self) -> None:
        source, out = self.root / "timing.json", self.root / "audio.mp3"
        source.write_text('{"audio_base64":"@@not-base64"}')
        with self.assertRaisesRegex(media.MediaError, "Invalid base64"):
            media.decode_audio(source, out, False)
        self.assertFalse(out.exists())

    def test_nonfinite_json_is_rejected(self) -> None:
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value), self.assertRaises(media.MediaError):
                media.parse_json('{"duration":' + value + "}")

    def test_invalid_deadlines_fail_argument_parsing(self) -> None:
        for value in ("0", "-1", "nan", "inf", "-inf"):
            with self.subTest(value=value), self.assertRaises(SystemExit) as caught:
                with patch("sys.stderr", new=io.StringIO()):
                    media.parser().parse_args(
                        [
                            "wait",
                            "image",
                            "job",
                            f"--deadline={value}",
                            "--out",
                            "x.json",
                        ]
                    )
            self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()

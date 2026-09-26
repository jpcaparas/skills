#!/usr/bin/env python3
"""Small, dependency-free ElevenLabs HTTP adapter. Preview requests by default.

This is not a replacement SDK: it preserves wire responses and deliberately does
not guess model schemas, retry billable work, or implement WebSocket protocols.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import http.client
import json
import math
import mimetypes
import os
import re
import secrets
import sys
import tempfile
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Literal, Protocol, TypeAlias
from urllib.parse import urlencode, urlsplit

Json: TypeAlias = None | bool | int | float | str | list["Json"] | dict[str, "Json"]
JsonObject: TypeAlias = dict[str, Json]
Method: TypeAlias = Literal["GET", "POST", "PATCH", "DELETE"]
Expectation: TypeAlias = Literal["json", "audio", "image", "video", "zip", "raw"]
API_ORIGIN = "https://api.elevenlabs.io"
CHUNK_BYTES = 64 * 1024
JSON_LIMIT = 16 * 1024 * 1024
MEDIA_ROOTS = {
    "text-to-speech",
    "text-to-dialogue",
    "speech-to-speech",
    "speech-to-text",
    "sound-generation",
    "audio-isolation",
    "forced-alignment",
    "music",
    "flows",
    "assets",
    "dubbing",
    "voices",
    "shared-voices",
    "text-to-voice",
    "history",
    "models",
    "studio",
    "audio-native",
    "pronunciation-dictionaries",
    "single-use-token",
}
SAFE_HEADERS = {
    "content-type",
    "content-length",
    "request-id",
    "x-request-id",
    "history-item-id",
    "character-cost",
    "song-id",
    "retry-after",
}


class MediaError(Exception):
    """A user-actionable error whose message contains no remote body or secret."""


class ApiError(MediaError):
    def __init__(self, status: int, code: str, request_id: str) -> None:
        self.status = status
        self.code = code
        self.request_id = request_id
        super().__init__(
            f"HTTP {status}; code={code}; request_id={request_id}; not retried"
        )


def parse_json(text: str) -> Json:
    """Narrow the standard library's untyped decoder at the external boundary."""

    def narrow(value: object) -> Json:
        if value is None or isinstance(value, (str, bool, int)):
            return value
        if isinstance(value, float) and math.isfinite(value):
            return value
        if isinstance(value, list):
            return [narrow(item) for item in value]
        if isinstance(value, dict) and all(isinstance(key, str) for key in value):
            return {str(key): narrow(item) for key, item in value.items()}
        raise MediaError("Expected finite JSON values")

    try:
        return narrow(json.loads(text))
    except (ValueError, RecursionError) as exc:
        raise MediaError("Invalid JSON; inspect the local input/response file") from exc


def json_object(value: Json) -> JsonObject:
    if not isinstance(value, dict):
        raise MediaError("Expected a JSON object")
    return value


def read_json(path: Path) -> Json:
    with path.open("rb") as handle:
        data = handle.read(JSON_LIMIT + 1)
    if len(data) > JSON_LIMIT:
        raise MediaError("JSON exceeds the helper's 16 MiB limit; use a streaming SDK")
    return parse_json(data.decode("utf-8"))


def require_string(value: JsonObject, key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise MediaError(f"Missing nonempty string field: {key}")
    return item


def safe_identifier(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]{1,160}", value) is None:
        raise MediaError("Expected an ID, not a URL, query, or path")
    return value


def api_url(path: str, query: list[tuple[str, str]]) -> str:
    if re.fullmatch(r"/v[12]/[A-Za-z0-9_/-]+", path) is None or "//" in path:
        raise MediaError("Use an absolute /v1/ or /v2/ API path without a query or URL")
    parts = path.split("/")
    if parts[2] not in MEDIA_ROOTS and path != "/v1/user/subscription":
        raise MediaError("Endpoint is outside this helper's media scope")
    suffix = "?" + urlencode(query) if query else ""
    return API_ORIGIN + path + suffix


def download_url(url: str) -> str:
    parsed = urlsplit(url)
    host = parsed.hostname
    # Only provider-owned storage used by these APIs. Never forward xi-api-key.
    trusted = host == "storage.googleapis.com" or (
        host is not None and host.endswith(".elevenlabs.io")
    )
    if (
        parsed.scheme != "https"
        or not trusted
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.fragment
    ):
        raise MediaError(
            "Unrecognized download origin; verify it against official docs before using another client"
        )
    return url


class Reader(Protocol):
    def read(self, size: int = -1) -> bytes: ...


@dataclass(frozen=True)
class Response:
    status: int
    headers: Mapping[str, str]
    body: Reader


class Transport(Protocol):
    def open(
        self,
        method: Method,
        url: str,
        headers: Mapping[str, str],
        body: BinaryIO | None,
        timeout: float,
    ) -> AbstractContextManager[Response]: ...


class HttpsTransport:
    """One request, verified TLS, no redirects or implicit retries/proxy auth."""

    @contextmanager
    def open(
        self,
        method: Method,
        url: str,
        headers: Mapping[str, str],
        body: BinaryIO | None,
        timeout: float,
    ) -> Iterator[Response]:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname is None:
            raise MediaError("HTTPS is required")
        connection = http.client.HTTPSConnection(
            parsed.hostname, port=parsed.port, timeout=timeout
        )
        target = parsed.path + ("?" + parsed.query if parsed.query else "")
        try:
            connection.request(method, target, body=body, headers=dict(headers))
            remote = connection.getresponse()
            yield Response(
                remote.status, {k.lower(): v for k, v in remote.getheaders()}, remote
            )
        finally:
            connection.close()


def pairs(values: list[str]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for value in values:
        name, separator, content = value.partition("=")
        if not separator or re.fullmatch(r"[A-Za-z0-9_-]+", name) is None:
            raise MediaError(
                "Fields must be name=value; names use letters, numbers, _ or -"
            )
        result.append((name, content))
    return result


@dataclass(frozen=True)
class Payload:
    stream: BinaryIO | None
    headers: Mapping[str, str]
    size: int


@contextmanager
def make_payload(
    json_path: Path | None,
    fields: list[tuple[str, str]],
    files: list[tuple[str, str]],
    max_bytes: int,
) -> Iterator[Payload]:
    if json_path is not None and (fields or files):
        raise MediaError("JSON and multipart input cannot be combined")
    if json_path is None and not fields and not files:
        yield Payload(None, {}, 0)
        return
    # Spool uploads to disk instead of making a multi-gigabyte bytes object.
    with tempfile.TemporaryFile("w+b") as stream:
        if json_path is not None:
            data = json.dumps(
                json_object(read_json(json_path)), ensure_ascii=False
            ).encode("utf-8")
            stream.write(data)
            content_type = "application/json"
        else:
            boundary = "elevenlabs-media-" + secrets.token_hex(16)
            content_type = f"multipart/form-data; boundary={boundary}"
            for name, value in fields:
                stream.write(
                    f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
                )
                stream.write(value.encode("utf-8") + b"\r\n")
            for name, filename in files:
                path = Path(filename)
                if not path.is_file():
                    raise MediaError(f"Upload is not a regular file: {path}")
                if path.stat().st_size + stream.tell() > max_bytes:
                    raise MediaError("Upload exceeds --max-upload-mib")
                # The local basename is not sent; quotes/newlines cannot inject a header.
                extension = path.suffix.lower()
                if re.fullmatch(r"\.[a-z0-9]{1,10}", extension) is None:
                    extension = ".bin"
                mime = mimetypes.guess_type("upload" + extension)[0]
                if mime is None:
                    mime = "application/octet-stream"
                stream.write(
                    (
                        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                        f'filename="upload{extension}"\r\nContent-Type: {mime}\r\n\r\n'
                    ).encode()
                )
                with path.open("rb") as source:
                    while chunk := source.read(CHUNK_BYTES):
                        if stream.tell() + len(chunk) > max_bytes:
                            raise MediaError("Upload exceeds --max-upload-mib")
                        stream.write(chunk)
                stream.write(b"\r\n")
            stream.write(f"--{boundary}--\r\n".encode())
        length = stream.tell()
        if length > max_bytes:
            raise MediaError("Request exceeds --max-upload-mib")
        stream.seek(0)
        yield Payload(
            stream,
            {"Content-Type": content_type, "Content-Length": str(length)},
            length,
        )


def remote_error(response: Response) -> ApiError:
    code = "unclassified"
    request_id = response.headers.get("request-id", "unavailable")
    try:
        value = json_object(parse_json(response.body.read(64 * 1024).decode("utf-8")))
        detail = value.get("detail")
        if isinstance(detail, dict):
            for field in ("status", "code"):
                candidate = detail.get(field)
                if isinstance(candidate, str) and re.fullmatch(
                    r"[a-z_]{1,80}", candidate
                ):
                    code = candidate
                    break
            candidate_id = detail.get("request_id")
            if isinstance(candidate_id, str) and re.fullmatch(
                r"[A-Za-z0-9_-]{1,160}", candidate_id
            ):
                request_id = candidate_id
    except (MediaError, UnicodeError):
        pass
    # Error messages may echo prompts, URLs, or credentials. Report only codes/IDs.
    if re.fullmatch(r"[A-Za-z0-9_-]{1,160}", request_id) is None:
        request_id = "unavailable"
    return ApiError(response.status, code, request_id)


def check_response(response: Response, expect: Expectation) -> None:
    if not 200 <= response.status < 300:
        raise remote_error(response)
    if response.status == 204:
        if expect not in ("json", "raw"):
            raise MediaError(
                "No content returned where media was expected; do not resubmit automatically"
            )
        return
    mime = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    valid = (
        expect == "raw"
        or (expect == "json" and (mime == "application/json" or mime.endswith("+json")))
        or (expect in ("audio", "image", "video") and mime.startswith(expect + "/"))
        or (
            expect == "zip"
            and mime in ("application/zip", "application/x-zip-compressed")
        )
    )
    if not valid:
        raise MediaError(
            f"Unexpected response type for --expect {expect}; inspect the metadata, do not resubmit"
        )


def private_file(path: Path) -> BinaryIO:
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb")


def save_response(
    transport: Transport,
    method: Method,
    url: str,
    headers: Mapping[str, str],
    payload: Payload,
    output: Path,
    expect: Expectation,
    timeout: float,
    max_bytes: int,
) -> JsonObject:
    """Retain a receipt before sending; publish only complete, validated bytes.

    A .part plus a non-complete receipt is recoverable evidence, not an invitation
    to repeat a paid request. Exclusive creation also protects concurrent callers.
    """
    metadata_path = Path(str(output) + ".meta.json")
    partial_path = Path(str(output) + ".part")
    if any(os.path.lexists(path) for path in (output, metadata_path, partial_path)):
        raise MediaError(
            "Output, receipt, or partial already exists; reconcile it before choosing a new path"
        )
    receipt: JsonObject = {"state": "prepared", "method": method, "output": str(output)}
    with (
        private_file(metadata_path) as metadata,
        private_file(partial_path) as destination,
    ):

        def record() -> None:
            metadata.seek(0)
            metadata.truncate()
            metadata.write((json.dumps(receipt, indent=2) + "\n").encode())
            metadata.flush()
            os.fsync(metadata.fileno())

        record()
        try:
            with transport.open(
                method, url, headers, payload.stream, timeout
            ) as response:
                receipt.update(
                    {
                        "state": "receiving",
                        "http_status": response.status,
                        "headers": {
                            k: v
                            for k, v in response.headers.items()
                            if k in SAFE_HEADERS
                        },
                    }
                )
                record()
                check_response(response, expect)
                size = 0
                digest = hashlib.sha256()
                while chunk := response.body.read(CHUNK_BYTES):
                    size += len(chunk)
                    if size > max_bytes:
                        raise MediaError(
                            "Response exceeds --max-output-mib; receipt and partial retained"
                        )
                    destination.write(chunk)
                    digest.update(chunk)
                expected_length = response.headers.get("content-length")
                if expected_length is not None and size != int(expected_length):
                    raise MediaError(
                        "Truncated response; receipt and partial retained; do not resubmit automatically"
                    )
                if size == 0 and expect in ("audio", "image", "video", "zip"):
                    raise MediaError(
                        "Empty media response; receipt retained; do not resubmit automatically"
                    )
                destination.flush()
                os.fsync(destination.fileno())
                if expect == "json" and response.status != 204:
                    read_json(partial_path)
                # Hard-link publication is atomic and cannot replace an existing output.
                os.link(partial_path, output)
                partial_path.unlink()
                receipt.update(
                    {"state": "complete", "bytes": size, "sha256": digest.hexdigest()}
                )
                record()
        except BaseException as exc:
            receipt["state"] = "incomplete_or_unknown"
            if isinstance(exc, ApiError):
                receipt["api_error"] = {"code": exc.code, "request_id": exc.request_id}
            record()
            raise
    return receipt


@dataclass(frozen=True)
class ElevenLabs:
    api_key: str = field(repr=False)
    transport: Transport

    def headers(self) -> dict[str, str]:
        if not self.api_key.strip():
            raise MediaError("ELEVENLABS_API_KEY is not set")
        return {"xi-api-key": self.api_key, "User-Agent": "elevenlabs-media/1"}

    def get_json(self, path: str, timeout: float) -> JsonObject:
        with self.transport.open(
            "GET", api_url(path, []), self.headers(), None, timeout
        ) as response:
            check_response(response, "json")
            data = response.body.read(JSON_LIMIT + 1)
            if len(data) > JSON_LIMIT:
                raise MediaError("Status response exceeds 16 MiB")
            return json_object(parse_json(data.decode("utf-8")))


def wait_for_generation(
    client: ElevenLabs,
    kind: Literal["image", "video", "text-to-speech"],
    generation_id: str,
    deadline_seconds: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> JsonObject:
    safe_identifier(generation_id)
    end = clock() + deadline_seconds
    interval = 10.0 if kind == "video" else 2.0
    while (remaining := end - clock()) > 0:
        result = client.get_json(
            f"/v1/flows/{kind}/{generation_id}", min(30.0, remaining)
        )
        status = result.get("status")
        if status == "completed":
            require_string(result, "content_url")
            require_string(result, "content_mime_type")
            return result
        if status == "failed":
            reason = result.get("failure_reason")
            safe_reason = (
                reason
                if isinstance(reason, str) and re.fullmatch(r"[a-z_]+", reason)
                else "unknown"
            )
            raise MediaError(
                f"Generation {generation_id} failed: {safe_reason}; not resubmitted"
            )
        if status not in ("pending", "generating"):
            raise MediaError(
                f"Unrecognized generation state for {generation_id}; inspect GET response"
            )
        remaining = end - clock()
        if remaining <= interval:
            break
        sleep(interval)
        interval = min(interval * 2, 60.0)
    raise MediaError(
        f"Wait deadline reached for {generation_id}; resume GET/wait with the same ID, do not recreate"
    )


def write_json_exclusive(path: Path, value: Json) -> None:
    with private_file(path) as handle:
        handle.write((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode())


def decode_audio(source: Path, output: Path, ndjson: bool) -> None:
    """Decode REST timing responses, not WebSocket frames or music SSE events."""
    partial = Path(str(output) + ".part")
    if os.path.lexists(output):
        raise MediaError("Decoded output already exists")
    with source.open("rb") as incoming, private_file(partial) as outgoing:
        count = 0
        while (
            line := incoming.readline(JSON_LIMIT + 1)
            if ndjson
            else incoming.read(JSON_LIMIT + 1)
        ):
            if len(line) > JSON_LIMIT:
                raise MediaError("Timing response exceeds the per-record 16 MiB limit")
            if ndjson and not line.strip():
                continue
            record = json_object(parse_json(line.decode("utf-8")))
            encoded = require_string(record, "audio_base64")
            try:
                outgoing.write(base64.b64decode(encoded, validate=True))
            except (ValueError, binascii.Error) as exc:
                raise MediaError("Invalid base64 audio; partial retained") from exc
            count += 1
        if count == 0:
            raise MediaError("No audio records in timing response")
    os.link(partial, output)
    partial.unlink()


def positive_number(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Must be a finite positive number")
    return number


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    request = commands.add_parser(
        "request", help="Preview a wire request; --execute sends it once"
    )
    request.add_argument("method", choices=("GET", "POST", "PATCH", "DELETE"))
    request.add_argument("path")
    request.add_argument("--json", type=Path)
    request.add_argument("--field", action="append", default=[])
    request.add_argument(
        "--field-file",
        action="append",
        default=[],
        help="Multipart name=path; read text from disk",
    )
    request.add_argument(
        "--file",
        action="append",
        default=[],
        help="Multipart name=path; repeat for multiple uploads",
    )
    request.add_argument("--query", action="append", default=[])
    request.add_argument(
        "--expect",
        choices=("json", "audio", "image", "video", "zip", "raw"),
        default="json",
    )
    request.add_argument("--out", type=Path)
    request.add_argument("--execute", action="store_true")
    request.add_argument(
        "--timeout",
        type=positive_number,
        default=180.0,
        help="Socket I/O timeout in seconds",
    )
    request.add_argument("--max-upload-mib", type=positive_number, default=512.0)
    request.add_argument("--max-output-mib", type=positive_number, default=1024.0)
    wait = commands.add_parser(
        "wait", help="Read-only bounded Flows polling; never creates a job"
    )
    wait.add_argument("kind", choices=("image", "video", "text-to-speech"))
    wait.add_argument("generation_id")
    wait.add_argument("--deadline", type=positive_number, default=600.0)
    wait.add_argument("--out", type=Path, required=True)
    download = commands.add_parser(
        "download", help="Download an API-returned signed URL without authentication"
    )
    download.add_argument("--from-json", type=Path, required=True)
    download.add_argument(
        "--url-field",
        default="content_url",
        help="Dotted field, e.g. outputs.lossless_audio",
    )
    download.add_argument("--out", type=Path, required=True)
    download.add_argument(
        "--expect", choices=("audio", "image", "video", "zip", "raw"), required=True
    )
    download.add_argument("--timeout", type=positive_number, default=180.0)
    download.add_argument("--max-output-mib", type=positive_number, default=1024.0)
    decode = commands.add_parser(
        "decode-audio", help="Decode a saved REST timestamp JSON or NDJSON response"
    )
    decode.add_argument("input", type=Path)
    decode.add_argument("--out", type=Path, required=True)
    decode.add_argument("--ndjson", action="store_true")
    return root


def run(args: argparse.Namespace, transport: Transport) -> JsonObject:
    if args.command == "decode-audio":
        decode_audio(args.input, args.out, args.ndjson)
        return {"state": "complete", "output": str(args.out)}
    if args.command == "download":
        value: Json = read_json(args.from_json)
        for field in args.url_field.split("."):
            value = json_object(value).get(field)
        if not isinstance(value, str):
            raise MediaError("Download URL field is missing")
        url = download_url(value)
        return save_response(
            transport,
            "GET",
            url,
            {},
            Payload(None, {}, 0),
            args.out,
            args.expect,
            args.timeout,
            int(args.max_output_mib * 1024 * 1024),
        )
    client = ElevenLabs(os.environ.get("ELEVENLABS_API_KEY", ""), transport)
    if args.command == "wait":
        if os.path.lexists(args.out):
            raise MediaError("Status output already exists; choose a new path")
        result = wait_for_generation(
            client, args.kind, args.generation_id, args.deadline
        )
        write_json_exclusive(args.out, result)
        return {
            "state": "complete",
            "generation_id": args.generation_id,
            "output": str(args.out),
        }
    if args.command != "request":
        raise MediaError("Unknown command")
    url = api_url(args.path, pairs(args.query))
    fields = pairs(args.field)
    for name, path in pairs(args.field_file):
        with Path(path).open("rb") as handle:
            data = handle.read(JSON_LIMIT + 1)
        if len(data) > JSON_LIMIT:
            raise MediaError("Text field exceeds 16 MiB")
        fields.append((name, data.decode("utf-8")))
    files = pairs(args.file)
    if args.method == "GET" and (args.json is not None or fields or files):
        raise MediaError("GET requests cannot carry a body")
    with make_payload(
        args.json, fields, files, int(args.max_upload_mib * 1024 * 1024)
    ) as payload:
        if not args.execute:
            return {
                "state": "preview_only",
                "method": args.method,
                "path": args.path,
                "request_bytes": payload.size,
                "uploads": len(files),
                "note": "No network call. --execute confirms the scoped request, not a spending limit.",
            }
        if args.out is None:
            raise MediaError("--out is required for execution")
        headers = client.headers()
        headers.update(payload.headers)
        return save_response(
            transport,
            args.method,
            url,
            headers,
            payload,
            args.out,
            args.expect,
            args.timeout,
            int(args.max_output_mib * 1024 * 1024),
        )


def main() -> int:
    try:
        result = run(parser().parse_args(), HttpsTransport())
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except MediaError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, http.client.HTTPException, UnicodeError, ValueError):
        # Exception strings can include signed URLs or other request material.
        print(
            "I/O or response failure; outcome may be unknown. Inspect local receipt/partial; no automatic retry.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

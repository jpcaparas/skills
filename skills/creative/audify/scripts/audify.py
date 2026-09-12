#!/usr/bin/env python3
"""Clean readable resources and synthesize Gemini TTS output bundles."""

from __future__ import annotations

import argparse
import base64
import dataclasses
import datetime as dt
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Callable
import urllib.error
import urllib.parse
import urllib.request
import zipfile


DEFAULT_MODEL = "gemini-3.1-flash-tts-preview"
DEFAULT_VOICE = "Kore"
DEFAULT_NUANCE = "Clear, neutral narrator for long-form listening."
DEFAULT_OUTPUT_ROOT = "audify-output"
DEFAULT_MAX_CHUNK_CHARS = 5500
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_RETRIES = 3
MIN_FALLBACK_CHUNK_CHARS = 200
USER_AGENT = "audify-skill/1.0"
MODEL_LIST_URL = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200"

SUPPORTED_TEXT_SUFFIXES = {
    ".txt",
    ".text",
    ".md",
    ".markdown",
    ".html",
    ".htm",
    ".xhtml",
    ".xml",
    ".json",
    ".yml",
    ".yaml",
    ".csv",
    ".rst",
    ".adoc",
}
SUPPORTED_DOC_SUFFIXES = {".docx"}
BLOCK_TAGS = {
    "article",
    "aside",
    "blockquote",
    "br",
    "div",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}
SKIP_TAGS = {"script", "style", "noscript", "svg", "template", "iframe", "nav", "footer", "header", "aside", "form"}
URL_RE = re.compile(r"https?://[^\s)>]+")
MARKDOWN_LINK_RE = re.compile(r"!?(\[([^\]]+)\])\(([^)]+)\)")
REFERENCE_LINK_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s+\S+.*$", re.MULTILINE)
CODE_FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(?:[A-Za-z0-9_-]+:\s.*\n)+---\s*\n", re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"[ \t]+")
LONG_BREAK_RE = re.compile(r"\n{3,}")
CODE_SIGNAL_RE = re.compile(
    r"\b(import|from|class|def|return|const|let|var|function|SELECT|INSERT|UPDATE|DELETE)\b"
)


class AudifyError(RuntimeError):
    """Base audify error."""


class ResourceReadError(AudifyError):
    """Raised when a resource cannot be read or cleaned."""


class SuitabilityError(AudifyError):
    """Raised when content is not meant for narration."""


class ApiError(AudifyError):
    """Raised for Gemini API failures."""

    def __init__(self, status: int, message: str, body: str | None = None):
        super().__init__(message)
        self.status = status
        self.body = body


@dataclasses.dataclass
class ResourceResult:
    source: str
    source_kind: str
    extracted_text: str
    cleaned_text: str
    read_attempts: list[str]
    cleaning_stats: dict[str, int]


@dataclasses.dataclass
class SuitabilityReport:
    ok: bool
    reasons: list[str]
    metrics: dict[str, float | int]


class HTMLTextExtractor(HTMLParser):
    """Convert HTML to readable text with a small amount of structure."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in BLOCK_TAGS:
            self.chunks.append("\n")
        if tag == "img":
            attrs_map = dict(attrs)
            alt = attrs_map.get("alt")
            if alt:
                self.chunks.append(alt)

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in BLOCK_TAGS:
            self.chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.chunks.append(data)

    def get_text(self) -> str:
        return "".join(self.chunks)


def looks_like_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def slugify(text: str, *, fallback: str = "resource", max_length: int = 48) -> str:
    lowered = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not lowered:
        return fallback
    return lowered[:max_length].strip("-") or fallback


def ensure_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudifyError("ffmpeg is required for MP3 or WAV output but was not found in PATH.")
    return ffmpeg


def require_gemini_api_key() -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise AudifyError("GEMINI_API_KEY is required.")
    return api_key


def decode_bytes(payload: bytes, *, hint: str | None = None, attempts: list[str] | None = None) -> str:
    encodings = []
    if hint:
        encodings.append(hint)
    encodings.extend(["utf-8", "utf-8-sig", "utf-16", "cp1252"])

    for encoding in encodings:
        try:
            text = payload.decode(encoding)
            if attempts is not None:
                attempts.append(f"decoded bytes using {encoding}")
            return text
        except UnicodeDecodeError:
            if attempts is not None:
                attempts.append(f"failed decoding bytes using {encoding}")
            continue

    raise ResourceReadError("exhausted resource read attempts while decoding bytes")


def fetch_text_from_url(url: str, *, timeout: int, attempts: list[str]) -> tuple[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    attempts.append(f"fetching URL {url}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            charset = response.headers.get_content_charset()
            payload = response.read()
    except (TimeoutError, socket.timeout) as exc:
        attempts.append(f"URL fetch timed out: {exc}")
        raise ResourceReadError(f"could not fetch URL {url}: {exc}") from exc
    except urllib.error.URLError as exc:
        attempts.append(f"URL fetch failed: {exc}")
        raise ResourceReadError(f"could not fetch URL {url}: {exc}") from exc

    lowered = content_type.lower()
    if any(token in lowered for token in ("html", "xml", "json", "text", "markdown")):
        text = decode_bytes(payload, hint=charset, attempts=attempts)
        return text, content_type

    attempts.append(f"unsupported content type from URL: {content_type or 'unknown'}")
    raise ResourceReadError(f"URL does not expose a text-like content type: {content_type or 'unknown'}")


def extract_docx_text(path: Path) -> str:
    parts: list[str] = []
    with zipfile.ZipFile(path) as archive:
        xml_names = [
            "word/document.xml",
            "word/footnotes.xml",
            "word/endnotes.xml",
        ]
        for name in xml_names:
            if name not in archive.namelist():
                continue
            xml = archive.read(name).decode("utf-8")
            xml = re.sub(r"</w:p>", "\n\n", xml)
            xml = re.sub(r"</w:tr>", "\n", xml)
            xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
            xml = re.sub(r"<[^>]+>", "", xml)
            parts.append(html.unescape(xml))
    if not parts:
        raise ResourceReadError(f"{path.name} did not contain readable DOCX text.")
    return "\n".join(parts)


def extract_best_html_fragment(raw_html: str) -> str:
    cleaned = raw_html
    for tag in SKIP_TAGS:
        cleaned = re.sub(
            rf"<{tag}\b.*?</{tag}>",
            " ",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )

    for tag in ("article", "main", "body"):
        matches = re.findall(rf"<{tag}\b.*?</{tag}>", cleaned, flags=re.IGNORECASE | re.DOTALL)
        if matches:
            cleaned = max(matches, key=len)
            break

    parser = HTMLTextExtractor()
    parser.feed(cleaned)
    parser.close()
    return parser.get_text()


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def strip_markdown(text: str, stats: dict[str, int]) -> str:
    if FRONTMATTER_RE.search(text):
        text = FRONTMATTER_RE.sub("", text, count=1)
        stats["frontmatter_blocks_removed"] += 1

    for _ in CODE_FENCE_RE.finditer(text):
        stats["code_fences_removed"] += 1
    text = CODE_FENCE_RE.sub("\n", text)

    text, inline_count = INLINE_CODE_RE.subn(r"\1", text)
    stats["inline_code_runs_unwrapped"] += inline_count

    def replace_link(match: re.Match[str]) -> str:
        label = match.group(2) or ""
        url = match.group(3) or ""
        if match.group(0).startswith("!"):
            if label:
                stats["images_converted_to_alt_text"] += 1
                return label
            stats["urls_removed"] += 1
            return ""
        stats["markdown_links_preserved"] += 1
        if url:
            stats["urls_removed"] += 1
        return label

    text = MARKDOWN_LINK_RE.sub(replace_link, text)

    link_definitions = REFERENCE_LINK_RE.findall(text)
    stats["reference_links_removed"] += len(link_definitions)
    text = REFERENCE_LINK_RE.sub("", text)

    # Strip common Markdown syntax while preserving visible words.
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = text.replace(">", "")
    return text


def strip_urls(text: str, stats: dict[str, int]) -> str:
    urls = URL_RE.findall(text)
    stats["urls_removed"] += len(urls)
    return URL_RE.sub("", text)


def clean_text(text: str, *, source_kind: str) -> tuple[str, dict[str, int]]:
    stats = {
        "frontmatter_blocks_removed": 0,
        "code_fences_removed": 0,
        "inline_code_runs_unwrapped": 0,
        "markdown_links_preserved": 0,
        "images_converted_to_alt_text": 0,
        "reference_links_removed": 0,
        "urls_removed": 0,
        "html_tags_removed": 0,
    }

    text = normalize_newlines(text)
    text = html.unescape(text)

    if source_kind in {"url-html", "html"} or ("<html" in text.lower() or "<body" in text.lower()):
        text = extract_best_html_fragment(text)
        stats["html_tags_removed"] += 1
    elif HTML_TAG_RE.search(text):
        text = HTML_TAG_RE.sub(" ", text)
        stats["html_tags_removed"] += 1

    text = strip_markdown(text, stats)
    text = strip_urls(text, stats)
    text = html.unescape(text)
    text = normalize_newlines(text)
    text = WHITESPACE_RE.sub(" ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = LONG_BREAK_RE.sub("\n\n", text)
    return text.strip(), stats


def assess_tts_suitability(text: str) -> SuitabilityReport:
    lowered = text.lower()
    word_count = len(re.findall(r"\b[\w'-]+\b", text))
    char_count = len(text)
    line_count = max(1, text.count("\n") + 1)
    alpha_count = sum(ch.isalpha() for ch in text)
    digit_count = sum(ch.isdigit() for ch in text)
    symbol_count = sum(not ch.isalnum() and not ch.isspace() for ch in text)
    alpha_ratio = alpha_count / char_count if char_count else 0.0
    symbol_ratio = symbol_count / char_count if char_count else 0.0
    code_signals = len(CODE_SIGNAL_RE.findall(text))

    reasons: list[str] = []
    if word_count < 2 and char_count < 12:
        reasons.append("too little readable text remains after cleaning")
    if alpha_ratio < 0.45 and char_count > 80:
        reasons.append("plain-language ratio is too low for natural narration")
    if symbol_ratio > 0.18 and char_count > 120:
        reasons.append("symbol density suggests code, logs, or tabular data")
    if code_signals >= 3 and symbol_ratio > 0.08:
        reasons.append("content still looks like code or query syntax")
    if "traceback" in lowered or "stack trace" in lowered:
        reasons.append("content looks like an error log, not prose")

    metrics = {
        "word_count": word_count,
        "char_count": char_count,
        "line_count": line_count,
        "alpha_ratio": round(alpha_ratio, 4),
        "digit_count": digit_count,
        "symbol_ratio": round(symbol_ratio, 4),
        "code_signal_count": code_signals,
    }
    return SuitabilityReport(ok=not reasons, reasons=reasons, metrics=metrics)


def read_resource(
    *,
    resource: str | None,
    file_path: str | None,
    url: str | None,
    text: str | None,
    read_stdin: bool,
    timeout: int,
) -> ResourceResult:
    attempts: list[str] = []

    if sum(bool(item) for item in (file_path, url, text, read_stdin)) > 1:
        raise ResourceReadError("provide only one of --file, --url, --text, or --stdin")

    if read_stdin:
        attempts.append("reading stdin")
        extracted = sys.stdin.read()
        source = "stdin"
        source_kind = "text"
    elif text is not None:
        attempts.append("using explicit --text input")
        extracted = text
        source = "inline-text"
        source_kind = "text"
    elif file_path is not None:
        path = Path(file_path).expanduser()
        attempts.append(f"reading file {path}")
        if not path.exists():
            raise ResourceReadError(f"file does not exist: {path}")
        suffix = path.suffix.lower()
        source = str(path)
        if suffix in SUPPORTED_DOC_SUFFIXES:
            extracted = extract_docx_text(path)
            source_kind = "docx"
            attempts.append("extracted DOCX text")
        elif suffix in SUPPORTED_TEXT_SUFFIXES or not suffix:
            payload = path.read_bytes()
            extracted = decode_bytes(payload, attempts=attempts)
            source_kind = "html" if suffix in {".html", ".htm", ".xhtml"} else "text"
        else:
            raise ResourceReadError(f"unsupported file type for audify: {suffix or 'unknown'}")
    elif url is not None:
        extracted, content_type = fetch_text_from_url(url, timeout=timeout, attempts=attempts)
        source = url
        source_kind = "url-html" if "html" in content_type.lower() else "text"
    elif resource is not None:
        candidate_path = Path(resource).expanduser()
        if looks_like_url(resource):
            extracted, content_type = fetch_text_from_url(resource, timeout=timeout, attempts=attempts)
            source = resource
            source_kind = "url-html" if "html" in content_type.lower() else "text"
        elif candidate_path.exists():
            return read_resource(
                resource=None,
                file_path=resource,
                url=None,
                text=None,
                read_stdin=False,
                timeout=timeout,
            )
        else:
            attempts.append("treating positional argument as raw text")
            extracted = resource
            source = "inline-text"
            source_kind = "text"
    else:
        raise ResourceReadError("no resource was provided")

    cleaned, stats = clean_text(extracted, source_kind=source_kind)
    if not cleaned:
        raise ResourceReadError("cleaning removed all readable text from the resource")

    return ResourceResult(
        source=source,
        source_kind=source_kind,
        extracted_text=extracted,
        cleaned_text=cleaned,
        read_attempts=attempts,
        cleaning_stats=stats,
    )


def split_into_chunks(text: str, *, max_chars: int = DEFAULT_MAX_CHUNK_CHARS) -> list[str]:
    paragraphs = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    def add_piece(piece: str) -> None:
        nonlocal current
        proposed = f"{current}\n\n{piece}".strip() if current else piece
        if len(proposed) <= max_chars:
            current = proposed
            return
        flush()
        if len(piece) <= max_chars:
            current = piece
            return
        sentences = re.split(r"(?<=[.!?])\s+", piece)
        sentence_buffer = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            trial = f"{sentence_buffer} {sentence}".strip()
            if len(trial) <= max_chars:
                sentence_buffer = trial
                continue
            if sentence_buffer:
                chunks.append(sentence_buffer)
                sentence_buffer = ""
            if len(sentence) <= max_chars:
                sentence_buffer = sentence
                continue
            start = 0
            while start < len(sentence):
                part = sentence[start : start + max_chars]
                chunks.append(part.strip())
                start += max_chars
        if sentence_buffer:
            current = sentence_buffer

    for paragraph in paragraphs:
        add_piece(paragraph)

    flush()
    return chunks


def split_chunk_for_fallback(
    text: str,
    *,
    current_max_chars: int,
    min_chunk_chars: int = MIN_FALLBACK_CHUNK_CHARS,
) -> tuple[list[str], int] | None:
    if len(text) <= min_chunk_chars:
        return None

    candidate_limits = []
    for candidate in (
        len(text) // 2,
        len(text) // 3,
        max(current_max_chars // 2, min_chunk_chars),
        max(current_max_chars // 3, min_chunk_chars),
    ):
        bounded = max(min_chunk_chars, min(len(text) - 1, candidate))
        if bounded < len(text) and bounded not in candidate_limits:
            candidate_limits.append(bounded)

    for candidate_limit in candidate_limits:
        subchunks = split_into_chunks(text, max_chars=candidate_limit)
        if len(subchunks) > 1:
            return subchunks, candidate_limit

    return None


def estimate_runtime_expectation(*, word_count: int, chunk_count: int) -> dict[str, object]:
    if chunk_count <= 1 and word_count <= 250:
        label = "usually under 1 minute"
        poll_seconds = 45
    elif chunk_count <= 2 and word_count <= 600:
        label = "often 1-3 minutes"
        poll_seconds = 60
    elif chunk_count <= 4 and word_count <= 1500:
        label = "often 2-6 minutes"
        poll_seconds = 90
    else:
        label = "can take 5-10+ minutes"
        poll_seconds = 120

    return {
        "label": label,
        "recommended_poll_interval_seconds": poll_seconds,
        "chunk_count": chunk_count,
        "word_count": word_count,
        "note": "Longer TTS jobs can stay quiet between chunk completions. Do not treat 30-90 seconds of silence as failure.",
    }


def is_auto_split_candidate(exc: Exception, transcript: str) -> bool:
    if len(transcript) <= MIN_FALLBACK_CHUNK_CHARS:
        return False
    if isinstance(exc, ApiError):
        return exc.status in {0, 408, 500, 502, 503, 504}
    return False


def build_prompt(transcript: str, *, nuance: str, title: str | None = None) -> str:
    title_line = f"Context: {title}\n" if title else ""
    return (
        "Synthesize speech only.\n"
        "Do not read instructions, labels, URLs, or metadata aloud.\n"
        f"{title_line}"
        "### DIRECTOR NOTES\n"
        f"Performance: {nuance.strip() or DEFAULT_NUANCE}\n"
        "Keep the reading natural and faithful to the transcript.\n"
        "### TRANSCRIPT\n"
        f"{transcript.strip()}"
    )


def request_json(
    url: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=payload, headers=request_headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except (TimeoutError, socket.timeout) as exc:
        raise ApiError(408, f"Gemini API request timed out: {exc}") from exc
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw)
            message = parsed.get("error", {}).get("message") or raw
        except json.JSONDecodeError:
            parsed = None
            message = raw or exc.reason
        raise ApiError(exc.code, f"Gemini API request failed with {exc.code}: {message}", raw) from exc
    except urllib.error.URLError as exc:
        raise ApiError(0, f"Gemini API request failed: {exc}") from exc


def list_tts_models(*, api_key: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> list[str]:
    data = request_json(MODEL_LIST_URL, headers={"x-goog-api-key": api_key}, timeout=timeout)
    names = [model.get("name", "") for model in data.get("models", [])]
    return sorted(name for name in names if "tts" in name.lower())


def ensure_model_available(*, api_key: str, model: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> list[str]:
    names = list_tts_models(api_key=api_key, timeout=timeout)
    expected_name = f"models/{model}"
    if expected_name not in names:
        raise AudifyError(
            f"{model} is not available for the current GEMINI_API_KEY. Visible TTS models: {', '.join(names) or 'none'}"
        )
    return names


def synthesize_chunk(
    transcript: str,
    *,
    api_key: str,
    model: str,
    voice: str,
    nuance: str,
    timeout: int,
    retries: int,
    title: str | None,
) -> tuple[bytes, int]:
    payload = {
        "contents": [{"parts": [{"text": build_prompt(transcript, nuance=nuance, title=title)}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice},
                }
            },
        },
        "model": model,
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    last_error: ApiError | None = None
    for attempt in range(1, retries + 1):
        try:
            data = request_json(
                url,
                method="POST",
                body=payload,
                headers={"x-goog-api-key": api_key},
                timeout=timeout,
            )
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            inline = next((part.get("inlineData") for part in parts if "inlineData" in part), None)
            if not inline or "data" not in inline:
                raise AudifyError("Gemini returned no inline audio payload.")
            return base64.b64decode(inline["data"]), attempt
        except ApiError as exc:
            last_error = exc
            if exc.status not in {429, 500, 502, 503, 504} or attempt == retries:
                raise
            time.sleep(min(2 ** (attempt - 1), 4))

    assert last_error is not None
    raise last_error


def synthesize_text(
    cleaned_text: str,
    *,
    api_key: str,
    model: str,
    voice: str,
    nuance: str,
    timeout: int,
    retries: int,
    max_chunk_chars: int,
    title: str | None = None,
    precomputed_chunks: list[str] | None = None,
    progress: Callable[[str], None] | None = None,
) -> tuple[bytes, dict[str, object]]:
    chunks = precomputed_chunks or split_into_chunks(cleaned_text, max_chars=max_chunk_chars)
    if not chunks:
        raise AudifyError("no transcript chunks were created")

    fallback_events: list[dict[str, object]] = []
    combined = bytearray()
    attempts_per_chunk: list[int] = []
    actual_chunk_lengths: list[int] = []
    total_chunks = len(chunks)

    def synthesize_with_fallback(
        transcript: str,
        *,
        chunk_label: str,
        current_max_chars: int,
    ) -> None:
        if progress is not None:
            progress(f"audify: synthesizing chunk {chunk_label} ({len(transcript)} chars)")
        try:
            audio, attempts_used = synthesize_chunk(
                transcript,
                api_key=api_key,
                model=model,
                voice=voice,
                nuance=nuance,
                timeout=timeout,
                retries=retries,
                title=title,
            )
        except ApiError as exc:
            fallback = split_chunk_for_fallback(
                transcript,
                current_max_chars=current_max_chars,
            )
            if not is_auto_split_candidate(exc, transcript) or fallback is None:
                raise
            subchunks, new_max_chars = fallback
            fallback_events.append(
                {
                    "chunk_label": chunk_label,
                    "reason": str(exc),
                    "original_length": len(transcript),
                    "split_into": len(subchunks),
                    "new_max_chunk_chars": new_max_chars,
                    "subchunk_lengths": [len(piece) for piece in subchunks],
                }
            )
            if progress is not None:
                progress(
                    "audify: "
                    f"chunk {chunk_label} hit a transient failure; retrying as {len(subchunks)} smaller chunks "
                    "while keeping model, voice, and nuance unchanged"
                )
            for sub_index, subchunk in enumerate(subchunks, start=1):
                synthesize_with_fallback(
                    subchunk,
                    chunk_label=f"{chunk_label}.{sub_index}",
                    current_max_chars=new_max_chars,
                )
            return

        combined.extend(audio)
        attempts_per_chunk.append(attempts_used)
        actual_chunk_lengths.append(len(transcript))
        if progress is not None:
            progress(f"audify: finished chunk {chunk_label} in {attempts_used} attempt(s)")

    for index, chunk in enumerate(chunks, start=1):
        synthesize_with_fallback(
            chunk,
            chunk_label=f"{index}/{total_chunks}",
            current_max_chars=max_chunk_chars,
        )

    return bytes(combined), {
        "planned_chunk_count": len(chunks),
        "planned_chunk_lengths": [len(chunk) for chunk in chunks],
        "chunk_count": len(actual_chunk_lengths),
        "chunk_lengths": actual_chunk_lengths,
        "attempts_per_chunk": attempts_per_chunk,
        "fallback_used": bool(fallback_events),
        "fallback_events": fallback_events,
    }


def convert_pcm_to_output(pcm_path: Path, output_path: Path, *, fmt: str) -> None:
    ffmpeg = ensure_ffmpeg()
    command = [
        ffmpeg,
        "-y",
        "-f",
        "s16le",
        "-ar",
        "24000",
        "-ac",
        "1",
        "-i",
        str(pcm_path),
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise AudifyError(f"ffmpeg conversion to {fmt} failed: {result.stderr.strip()}")


def write_output_bundle(
    pcm_data: bytes,
    *,
    resource_result: ResourceResult,
    output_root: Path,
    voice: str,
    nuance: str,
    model: str,
    fmt: str,
    synthesis_meta: dict[str, object],
) -> dict[str, str]:
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    source_value = resource_result.source or "resource"
    parsed = urllib.parse.urlparse(source_value)
    if parsed.scheme in {"http", "https"}:
        base_seed = Path(parsed.path).stem or parsed.netloc
    else:
        base_seed = Path(source_value).stem or source_value.split()[0]
    base_name = slugify(base_seed)
    bundle_dir = output_root / f"{timestamp}-{base_name}"
    bundle_dir.mkdir(parents=True, exist_ok=False)

    cleaned_path = bundle_dir / "cleaned.txt"
    manifest_path = bundle_dir / "manifest.json"
    output_path = bundle_dir / f"audio.{fmt}"

    cleaned_path.write_text(resource_result.cleaned_text + "\n", encoding="utf-8")

    with tempfile.NamedTemporaryFile(prefix="audify-", suffix=".pcm", delete=False) as handle:
        temp_pcm_path = Path(handle.name)
        handle.write(pcm_data)

    try:
        convert_pcm_to_output(temp_pcm_path, output_path, fmt=fmt)
    finally:
        temp_pcm_path.unlink(missing_ok=True)

    manifest = {
        "source": resource_result.source,
        "source_kind": resource_result.source_kind,
        "voice": voice,
        "nuance": nuance,
        "model": model,
        "output_format": fmt,
        "cleaning_stats": resource_result.cleaning_stats,
        "read_attempts": resource_result.read_attempts,
        "synthesis": synthesis_meta,
        "cleaned_word_count": len(re.findall(r"\b[\w'-]+\b", resource_result.cleaned_text)),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return {
        "bundle_dir": str(bundle_dir),
        "audio_path": str(output_path),
        "cleaned_path": str(cleaned_path),
        "manifest_path": str(manifest_path),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean a readable resource and audify it with Gemini TTS.")
    parser.add_argument("resource", nargs="?", help="URL, file path, or raw text")
    parser.add_argument("--file", dest="file_path")
    parser.add_argument("--url")
    parser.add_argument("--text")
    parser.add_argument("--stdin", action="store_true", dest="read_stdin")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--nuance", default=DEFAULT_NUANCE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--format", default="mp3", choices=["mp3", "wav"])
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--max-chunk-chars", type=int, default=DEFAULT_MAX_CHUNK_CHARS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--title", help="Optional context label for the narration")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    try:
        resource_result = read_resource(
            resource=args.resource,
            file_path=args.file_path,
            url=args.url,
            text=args.text,
            read_stdin=args.read_stdin,
            timeout=args.timeout,
        )
        suitability = assess_tts_suitability(resource_result.cleaned_text)
        if not suitability.ok:
            raise SuitabilityError("; ".join(suitability.reasons))

        word_count = len(re.findall(r"\b[\w'-]+\b", resource_result.cleaned_text))
        planned_chunks = split_into_chunks(
            resource_result.cleaned_text,
            max_chars=max(500, args.max_chunk_chars),
        )
        runtime_expectation = estimate_runtime_expectation(
            word_count=word_count,
            chunk_count=len(planned_chunks),
        )

        report = {
            "source": resource_result.source,
            "source_kind": resource_result.source_kind,
            "cleaning_stats": resource_result.cleaning_stats,
            "suitability": dataclasses.asdict(suitability),
            "cleaned_preview": resource_result.cleaned_text[:300],
            "runtime_expectation": runtime_expectation,
        }

        if args.check_only:
            print(json.dumps(report, indent=2))
            return 0

        api_key = require_gemini_api_key()
        ensure_model_available(api_key=api_key, model=args.model, timeout=args.timeout)
        print(
            (
                "audify: "
                f"{runtime_expectation['word_count']} words across {runtime_expectation['chunk_count']} chunk(s); "
                f"expected runtime {runtime_expectation['label']}. "
                f"Wait about {runtime_expectation['recommended_poll_interval_seconds']} seconds between status checks."
            ),
            file=sys.stderr,
            flush=True,
        )
        print(
            f"audify: {runtime_expectation['note']}",
            file=sys.stderr,
            flush=True,
        )
        pcm_data, synthesis_meta = synthesize_text(
            resource_result.cleaned_text,
            api_key=api_key,
            model=args.model,
            voice=args.voice,
            nuance=args.nuance,
            timeout=args.timeout,
            retries=max(1, args.retries),
            max_chunk_chars=max(500, args.max_chunk_chars),
            title=args.title,
            precomputed_chunks=planned_chunks,
            progress=lambda message: print(message, file=sys.stderr, flush=True),
        )
        output_paths = write_output_bundle(
            pcm_data,
            resource_result=resource_result,
            output_root=Path(args.output_root).expanduser(),
            voice=args.voice,
            nuance=args.nuance,
            model=args.model,
            fmt=args.format,
            synthesis_meta=synthesis_meta,
        )
        report.update(output_paths)
        report["synthesis"] = synthesis_meta
        report["runtime_expectation"] = runtime_expectation
        print(json.dumps(report, indent=2))
        return 0
    except AudifyError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

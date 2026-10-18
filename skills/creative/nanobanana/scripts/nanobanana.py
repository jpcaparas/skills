#!/usr/bin/env python3
"""Generate and edit images with Nano Banana (Gemini Nano Banana 2.1) through the Gemini API.

The model is pinned on purpose: older Nano Banana models cost more for worse results, so this
helper never calls them. Every request is validated locally before any paid call is made.

Routes (see references/api.md):
- Interactions API (`POST /v1beta/interactions`) for generation, editing, references and
  multi-turn `--continue`. It is Google's recommended API and accepts the 512 size.
- generateContent for `--search` / `--image-search`. Live tests on 2026-10-18 showed Google
  Search grounding there searched reliably and returned grounding metadata, while the
  Interactions API often skipped the search or stopped with a client-side function call.

Standard library only; Python 3.11+.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

MODEL = "gemini-nano-banana-2.1"
API_ROOT = os.environ.get("NANOBANANA_API_ROOT", "https://generativelanguage.googleapis.com").rstrip("/")

ASPECT_RATIOS = ("1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9", "1:4", "4:1", "1:8", "8:1")
IMAGE_SIZES = ("512", "1K", "2K", "4K")
THINKING_LEVELS = ("minimal", "medium", "high")
MAX_REFERENCES = 14
# Inline requests are limited to about 100 MB; larger single files go through the Files API.
INLINE_FILE_LIMIT_BYTES = 20 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 300
RETRY_DELAYS_SECONDS = (5, 15)
RETRYABLE_STATUSES = {429, 500, 503, 504}

# List prices in USD per token (Gemini API pricing page, checked 2026-10-18). Batch is half.
PRICE_INPUT = 1.50 / 1_000_000
PRICE_TEXT_AND_THINKING = 7.50 / 1_000_000
PRICE_IMAGE_OUTPUT = 30.00 / 1_000_000

Route = Literal["interactions", "generateContent"]


class UsageError(Exception):
    """Invalid input detected before any request; exit code 2."""


class ApiError(Exception):
    """The API rejected the request or returned no image; exit code 1."""


@dataclass(frozen=True)
class Reference:
    path: Path
    mime_type: str

    @property
    def kind(self) -> Literal["image", "video", "document"]:
        if self.mime_type.startswith("image/"):
            return "image"
        if self.mime_type.startswith("video/"):
            return "video"
        return "document"


@dataclass(frozen=True)
class GenerateOptions:
    prompt: str
    references: tuple[Reference, ...]
    aspect_ratio: str | None
    image_size: str
    thinking: str
    web_search: bool
    image_search: bool
    continue_from: str | None
    store: bool
    system: str | None
    out: Path
    dry_run: bool

    @property
    def route(self) -> Route:
        return "generateContent" if (self.web_search or self.image_search) else "interactions"


@dataclass
class Usage:
    input_tokens: int = 0
    image_output_tokens: int = 0
    non_image_output_tokens: int = 0
    thought_tokens: int = 0

    def cost_usd(self, batch: bool = False) -> float:
        cost = (self.input_tokens * PRICE_INPUT
                + self.image_output_tokens * PRICE_IMAGE_OUTPUT
                + (self.non_image_output_tokens + self.thought_tokens) * PRICE_TEXT_AND_THINKING)
        return round(cost / 2 if batch else cost, 4)


@dataclass
class Result:
    route: Route
    images: list[bytes]
    text: list[str]
    usage: Usage
    interaction_id: str | None = None
    status: str | None = None
    search_queries: list[str] = field(default_factory=list)
    sources: list[dict[str, str]] = field(default_factory=list)
    search_suggestions_html: str | None = None


# --------------------------------------------------------------------------- HTTP


def api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise UsageError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set.")
    return key


def request_json(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call the Gemini API, retrying throttles and transient server errors."""
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(len(RETRY_DELAYS_SECONDS) + 1):
        request = urllib.request.Request(
            f"{API_ROOT}/{path}", data=data, method=method,
            headers={"x-goog-api-key": api_key(), "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                text = response.read().decode()
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as error:
            text = error.read().decode(errors="replace")
            if error.code in RETRYABLE_STATUSES and attempt < len(RETRY_DELAYS_SECONDS):
                delay = RETRY_DELAYS_SECONDS[attempt]
                print(f"HTTP {error.code}; retrying in {delay}s...", file=sys.stderr)
                time.sleep(delay)
                continue
            raise ApiError(describe_http_error(error.code, text)) from None
    raise AssertionError("unreachable")


def describe_http_error(status: int, text: str) -> str:
    try:
        message = json.loads(text).get("error", {}).get("message", text)
    except json.JSONDecodeError:
        message = text[:300]
    hint = ""
    if "safety" in message.lower() or "prohibited use" in message.lower():
        hint = "\nHint: the request was blocked by Google's safety filters. Rephrase the prompt; retrying unchanged will fail again."
    elif status in (401, 403):
        hint = "\nHint: check GEMINI_API_KEY and that its project has billing enabled (this model has no free tier)."
    elif status == 404:
        hint = f"\nHint: {MODEL} was not found. Report it; do not substitute another model."
    return f"Gemini API HTTP {status}: {message}{hint}"


def upload_file(reference: Reference) -> str:
    """Upload a large file with the Files API resumable protocol and return its URI."""
    size = reference.path.stat().st_size
    start = urllib.request.Request(
        f"{API_ROOT}/upload/v1beta/files", method="POST",
        data=json.dumps({"file": {"display_name": reference.path.name}}).encode(),
        headers={"x-goog-api-key": api_key(), "Content-Type": "application/json",
                 "X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                 "X-Goog-Upload-Header-Content-Length": str(size),
                 "X-Goog-Upload-Header-Content-Type": reference.mime_type},
    )
    try:
        with urllib.request.urlopen(start, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            upload_url = response.headers["X-Goog-Upload-URL"]
        finish = urllib.request.Request(
            upload_url, method="POST", data=reference.path.read_bytes(),
            headers={"Content-Length": str(size), "X-Goog-Upload-Offset": "0",
                     "X-Goog-Upload-Command": "upload, finalize"},
        )
        with urllib.request.urlopen(finish, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.load(response)["file"]["uri"]
    except urllib.error.HTTPError as error:
        raise ApiError(describe_http_error(error.code, error.read().decode(errors="replace"))) from None


# --------------------------------------------------------------------------- request building


def reference_payload(reference: Reference, route: Route, dry_run: bool) -> dict[str, Any]:
    large = reference.path.stat().st_size > INLINE_FILE_LIMIT_BYTES
    if large:
        uri = "<files-api-upload>" if dry_run else upload_file(reference)
        if route == "interactions":
            return {"type": reference.kind, "uri": uri, "mime_type": reference.mime_type}
        return {"fileData": {"fileUri": uri, "mimeType": reference.mime_type}}
    data = "<base64>" if dry_run else base64.b64encode(reference.path.read_bytes()).decode()
    if route == "interactions":
        return {"type": reference.kind, "mime_type": reference.mime_type, "data": data}
    return {"inlineData": {"mimeType": reference.mime_type, "data": data}}


def build_interactions_body(options: GenerateOptions) -> dict[str, Any]:
    image_format: dict[str, str] = {"type": "image", "image_size": options.image_size}
    if options.aspect_ratio:
        image_format["aspect_ratio"] = options.aspect_ratio
    content = [reference_payload(r, "interactions", options.dry_run) for r in options.references]
    body: dict[str, Any] = {
        "model": MODEL,
        "input": [*content, {"type": "text", "text": options.prompt}],
        # response_format and generation_config are interaction-scoped: resend them every turn.
        # An image-only format skips the conversational caption, which only adds text tokens.
        "response_format": image_format,
        "generation_config": {"thinking_level": options.thinking},
        "store": options.store,
    }
    if options.continue_from:
        body["previous_interaction_id"] = options.continue_from
    if options.system:
        body["system_instruction"] = options.system
    return body


def build_generate_content_body(options: GenerateOptions) -> dict[str, Any]:
    image_config: dict[str, str] = {"imageSize": options.image_size}
    if options.aspect_ratio:
        image_config["aspectRatio"] = options.aspect_ratio
    search_types: dict[str, dict[str, Any]] = {}
    if options.web_search:
        search_types["webSearch"] = {}
    if options.image_search:
        search_types["imageSearch"] = {}
    parts = [reference_payload(r, "generateContent", options.dry_run) for r in options.references]
    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [*parts, {"text": options.prompt}]}],
        "tools": [{"googleSearch": {"searchTypes": search_types}}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": image_config,
            "thinkingConfig": {"thinkingLevel": options.thinking},
        },
    }
    if options.system:
        body["systemInstruction"] = {"parts": [{"text": options.system}]}
    return body


# --------------------------------------------------------------------------- response parsing


def parse_interaction(data: dict[str, Any]) -> Result:
    usage = data.get("usage") or {}
    image_tokens = sum(m.get("tokens", 0) for m in usage.get("output_tokens_by_modality") or [] if m.get("modality") == "image")
    result = Result(
        route="interactions", images=[], text=[], interaction_id=data.get("id"), status=data.get("status"),
        usage=Usage(
            input_tokens=usage.get("total_input_tokens", 0),
            image_output_tokens=image_tokens,
            non_image_output_tokens=max(usage.get("total_output_tokens", 0) - image_tokens, 0),
            thought_tokens=usage.get("total_thought_tokens", 0),
        ),
    )
    for step in data.get("steps") or []:
        if step.get("type") != "model_output":
            continue
        for block in step.get("content") or []:
            if block.get("type") == "image" and block.get("data"):
                result.images.append(base64.b64decode(block["data"]))
            elif block.get("type") == "text" and block.get("text", "").strip():
                result.text.append(block["text"].strip())
    return result


def parse_generate_content(data: dict[str, Any]) -> Result:
    meta = data.get("usageMetadata") or {}
    image_tokens = sum(d.get("tokenCount", 0) for d in meta.get("candidatesTokensDetails") or [] if d.get("modality") == "IMAGE")
    candidate = (data.get("candidates") or [{}])[0]
    grounding = candidate.get("groundingMetadata") or {}
    result = Result(
        route="generateContent", images=[], text=[], status=candidate.get("finishReason"),
        usage=Usage(
            input_tokens=meta.get("promptTokenCount", 0),
            image_output_tokens=image_tokens,
            non_image_output_tokens=max(meta.get("candidatesTokenCount", 0) - image_tokens, 0),
            thought_tokens=meta.get("thoughtsTokenCount", 0),
        ),
        search_queries=[*(grounding.get("webSearchQueries") or []), *(grounding.get("imageSearchQueries") or [])],
        search_suggestions_html=(grounding.get("searchEntryPoint") or {}).get("renderedContent"),
    )
    for chunk in grounding.get("groundingChunks") or []:
        source = chunk.get("web") or chunk.get("image") or {}
        uri = source.get("uri") or source.get("sourceUri")
        if uri:
            result.sources.append({"kind": "web" if "web" in chunk else "image", "title": source.get("title", ""), "uri": uri})
    for part in (candidate.get("content") or {}).get("parts") or []:
        if part.get("thought"):
            continue
        if "inlineData" in part:
            result.images.append(base64.b64decode(part["inlineData"]["data"]))
        elif part.get("text", "").strip():
            result.text.append(part["text"].strip())
    return result


def image_dimensions(data: bytes) -> tuple[int, int] | None:
    """Read width and height from a JPEG (the only format this model returns) or PNG."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        return width, height
    index = 2
    while data[:2] == b"\xff\xd8" and index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            height, width = struct.unpack(">HH", data[index + 5:index + 9])
            return width, height
        index += 2 + struct.unpack(">H", data[index + 2:index + 4])[0]
    return None


# --------------------------------------------------------------------------- commands


def parse_references(paths: list[str]) -> tuple[Reference, ...]:
    if len(paths) > MAX_REFERENCES:
        raise UsageError(f"{len(paths)} references given; the documented maximum is {MAX_REFERENCES} (up to 4 characters and 10 objects).")
    references = []
    for raw in paths:
        path = Path(raw).expanduser()
        if not path.is_file():
            raise UsageError(f"Reference not found: {raw}")
        mime_type = mimetypes.guess_type(path.name)[0] or ""
        if not re.match(r"^(image/(png|jpeg|webp|heic|heif)|video/.+|application/pdf)$", mime_type):
            raise UsageError(f"Unsupported reference type for {raw} ({mime_type or 'unknown'}). Use PNG, JPEG, WebP, HEIC, a video, or a PDF.")
        references.append(Reference(path=path, mime_type=mime_type))
    return tuple(references)


def build_options(args: argparse.Namespace) -> GenerateOptions:
    prompt = Path(args.prompt_file).read_text(encoding="utf-8") if args.prompt_file else " ".join(args.prompt)
    if not prompt.strip():
        raise UsageError("A prompt is required (positional text or --prompt-file).")
    out = Path(args.out) if args.out else Path(f"nanobanana-{time.strftime('%Y%m%d-%H%M%S')}.jpg")
    if out.suffix.lower() not in (".jpg", ".jpeg"):
        raise UsageError(f"--out must end in .jpg: {MODEL} only returns JPEG. Convert afterwards if another format is needed.")
    options = GenerateOptions(
        prompt=prompt.strip(), references=parse_references(args.ref), aspect_ratio=args.ratio,
        image_size=args.size, thinking=args.thinking, web_search=args.search, image_search=args.image_search,
        continue_from=args.continue_from, store=not args.no_store, system=args.system, out=out, dry_run=args.dry_run,
    )
    if options.route == "generateContent" and options.continue_from:
        raise UsageError("--continue cannot be combined with --search/--image-search. Generate the grounded image first, then edit it with --ref in a new conversation.")
    if options.route == "generateContent" and options.image_size == "512":
        raise UsageError("Size 512 is only accepted by the Interactions API; use 1K or larger with --search/--image-search.")
    return options


def output_paths(base: Path, count: int) -> list[Path]:
    if count == 1:
        return [base]
    return [base.with_name(f"{base.stem}-{index}{base.suffix}") for index in range(1, count + 1)]


def run_generate(args: argparse.Namespace) -> int:
    options = build_options(args)
    body = build_interactions_body(options) if options.route == "interactions" else build_generate_content_body(options)
    if options.dry_run:
        print(json.dumps({"route": options.route, "model": MODEL, "request": body}, indent=2, ensure_ascii=False))
        return 0
    started = time.monotonic()
    if options.route == "interactions":
        result = parse_interaction(request_json("POST", "v1beta/interactions", body))
    else:
        result = parse_generate_content(request_json("POST", f"v1beta/models/{MODEL}:generateContent", body))
    seconds = round(time.monotonic() - started, 1)

    if result.status == "requires_action":
        raise ApiError("The model stopped with a client-side tool call instead of an image (status requires_action). Retry once; if it repeats, simplify the prompt.")
    if not result.images:
        said = f" The model replied: {' '.join(result.text)[:400]}" if result.text else ""
        raise ApiError(f"No image was returned (status {result.status}).{said} Rephrase the request as an explicit image description.")

    options.out.parent.mkdir(parents=True, exist_ok=True)
    saved = []
    for path, data in zip(output_paths(options.out, len(result.images)), result.images):
        path.write_bytes(data)
        size = image_dimensions(data)
        saved.append({"path": str(path), "width": size[0] if size else None, "height": size[1] if size else None, "bytes": len(data)})
    suggestions_path = None
    if result.search_suggestions_html:
        suggestions_path = options.out.with_suffix(".search.html")
        suggestions_path.write_text(result.search_suggestions_html, encoding="utf-8")

    summary: dict[str, Any] = {
        "model": MODEL, "route": result.route, "seconds": seconds, "images": saved,
        "settings": {"aspect_ratio": options.aspect_ratio, "image_size": options.image_size, "thinking": options.thinking},
        "usage": vars(result.usage), "estimated_cost_usd": result.usage.cost_usd(),
    }
    if result.interaction_id:
        summary["interaction_id"] = result.interaction_id if options.store else None
        if not options.store:
            summary["note"] = "store=false: this turn cannot be continued with --continue."
    if result.text:
        summary["model_text"] = result.text
    if options.route == "generateContent":
        summary["search"] = {"queries": result.search_queries, "sources": result.sources,
                             "suggestions_html": str(suggestions_path) if suggestions_path else None}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def run_batch_submit(args: argparse.Namespace) -> int:
    requests = []
    for number, line in enumerate(Path(args.jobs).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        job = json.loads(line)
        key, prompt = str(job.get("key") or number), str(job.get("prompt") or "").strip()
        ratio, size, thinking = job.get("ratio"), job.get("size", "1K"), job.get("thinking", "medium")
        if not prompt:
            raise UsageError(f"Line {number}: prompt is required.")
        if ratio is not None and ratio not in ASPECT_RATIOS:
            raise UsageError(f"Line {number}: unsupported ratio {ratio!r}.")
        if size not in ("1K", "2K", "4K"):
            raise UsageError(f"Line {number}: batch uses generateContent, which accepts 1K, 2K or 4K (got {size!r}).")
        if thinking not in THINKING_LEVELS:
            raise UsageError(f"Line {number}: thinking must be one of {', '.join(THINKING_LEVELS)}.")
        image_config = {"imageSize": size, **({"aspectRatio": ratio} if ratio else {})}
        requests.append({"metadata": {"key": key}, "request": {
            "contents": [{"parts": [{"text": prompt}]}],
            "generation_config": {"responseModalities": ["IMAGE"], "imageConfig": image_config, "thinkingConfig": {"thinkingLevel": thinking}},
        }})
    if not requests:
        raise UsageError("The jobs file has no requests.")
    body = {"batch": {"display_name": args.name, "input_config": {"requests": {"requests": requests}}}}
    if args.dry_run:
        print(json.dumps(body, indent=2, ensure_ascii=False))
        return 0
    data = request_json("POST", f"v1beta/models/{MODEL}:batchGenerateContent", body)
    print(json.dumps({"batch": data.get("name"), "state": (data.get("metadata") or {}).get("state"), "requests": len(requests)}, indent=2))
    return 0


def run_batch_fetch(args: argparse.Namespace) -> int:
    name = args.batch if args.batch.startswith("batches/") else f"batches/{args.batch}"
    deadline = time.monotonic() + args.wait
    while True:
        data = request_json("GET", f"v1beta/{name}")
        metadata = data.get("metadata") or {}
        state = metadata.get("state", "")
        if data.get("done") or state in ("BATCH_STATE_SUCCEEDED", "BATCH_STATE_FAILED", "BATCH_STATE_CANCELLED", "BATCH_STATE_EXPIRED"):
            break
        if time.monotonic() >= deadline:
            print(json.dumps({"batch": name, "state": state, "done": False}, indent=2))
            return 3
        time.sleep(30)
    if state != "BATCH_STATE_SUCCEEDED":
        raise ApiError(f"Batch {name} finished with state {state}.")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    items = []
    responses = ((metadata.get("output") or {}).get("inlinedResponses") or {}).get("inlinedResponses") or []
    for entry in responses:
        key = str((entry.get("metadata") or {}).get("key", len(items) + 1))
        if entry.get("error"):
            items.append({"key": key, "error": entry["error"].get("message")})
            continue
        result = parse_generate_content(entry.get("response") or {})
        paths = output_paths(out_dir / f"{key}.jpg", len(result.images))
        for path, image in zip(paths, result.images):
            path.write_bytes(image)
        items.append({"key": key, "images": [str(p) for p in paths], "estimated_cost_usd": result.usage.cost_usd(batch=True)})
    print(json.dumps({"batch": name, "state": state, "stats": metadata.get("batchStats"), "items": items}, indent=2))
    return 0


def run_delete(args: argparse.Namespace) -> int:
    request_json("DELETE", f"v1beta/interactions/{args.interaction_id}")
    print(json.dumps({"deleted": args.interaction_id}))
    return 0


SUPPORTED_VALUES = re.compile(r"Supported values: (.+?)\.?$")


def run_contract(_: argparse.Namespace) -> int:
    """Free contract check: invalid values are rejected with HTTP 400 before any generation."""
    probes = {
        "aspect_ratio": {"response_format": {"type": "image", "aspect_ratio": "0:0"}},
        "image_size": {"response_format": {"type": "image", "image_size": "0K"}},
        "thinking_level": {"generation_config": {"thinking_level": "invalid"}},
        "mime_type": {"response_format": {"type": "image", "mime_type": "image/invalid"}},
    }
    expected = {"aspect_ratio": set(ASPECT_RATIOS), "image_size": set(IMAGE_SIZES), "mime_type": {"image/jpeg"},
                "thinking_level": {*THINKING_LEVELS, "low"}}  # the schema lists "low"; the model rejects it
    report: dict[str, Any] = {"model": MODEL}
    model = request_json("GET", f"v1beta/models/{MODEL}")
    report["metadata"] = {k: model.get(k) for k in ("displayName", "inputTokenLimit", "outputTokenLimit", "supportedGenerationMethods")}
    drift = False
    for name, extra in probes.items():
        try:
            request_json("POST", "v1beta/interactions", {"model": MODEL, "input": "contract probe", **extra})
            report[name] = {"error": "request unexpectedly succeeded"}
            drift = True
            continue
        except ApiError as error:
            match = SUPPORTED_VALUES.search(str(error).splitlines()[0])
        live = {v.strip().strip("'") for v in match.group(1).split(",")} if match else set()
        report[name] = {"live": sorted(live), "matches_helper": live == expected[name]}
        drift |= live != expected[name]
    report["drift"] = drift
    print(json.dumps(report, indent=2))
    return 4 if drift else 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"Nano Banana helper pinned to {MODEL}.")
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate", help="Generate or edit one image.")
    generate.add_argument("prompt", nargs="*", help="Prompt text (or use --prompt-file).")
    generate.add_argument("--prompt-file", help="Read the prompt from a UTF-8 file.")
    generate.add_argument("--ref", action="append", default=[], help="Reference image, video, or PDF (repeatable, up to 14).")
    generate.add_argument("--ratio", choices=ASPECT_RATIOS, help="Aspect ratio. Omit to match the first reference image (or the model's default).")
    generate.add_argument("--size", choices=IMAGE_SIZES, default="1K", help="Output size (default 1K).")
    generate.add_argument("--thinking", choices=THINKING_LEVELS, default="medium", help="Thinking level (default medium).")
    generate.add_argument("--search", action="store_true", help="Ground with Google web search (uses generateContent).")
    generate.add_argument("--image-search", action="store_true", help="Ground with Google image search (uses generateContent).")
    generate.add_argument("--continue", dest="continue_from", metavar="INTERACTION_ID", help="Continue a stored conversation.")
    generate.add_argument("--no-store", action="store_true", help="Do not store the interaction (cannot be continued).")
    generate.add_argument("--system", help="System instruction, such as a house style.")
    generate.add_argument("--out", help="Output .jpg path (default: nanobanana-<timestamp>.jpg).")
    generate.add_argument("--dry-run", action="store_true", help="Print the request without sending it.")
    generate.set_defaults(handler=run_generate)

    submit = commands.add_parser("batch-submit", help="Submit a JSONL file of prompts as a half-price batch job.")
    submit.add_argument("jobs", help="JSONL: one {\"key\", \"prompt\", \"ratio\", \"size\", \"thinking\"} object per line.")
    submit.add_argument("--name", default="nanobanana-batch", help="Batch display name.")
    submit.add_argument("--dry-run", action="store_true")
    submit.set_defaults(handler=run_batch_submit)

    fetch = commands.add_parser("batch-fetch", help="Check a batch and save its images when done.")
    fetch.add_argument("batch", help="Batch name (batches/...).")
    fetch.add_argument("--out-dir", default="nanobanana-batch")
    fetch.add_argument("--wait", type=int, default=0, help="Seconds to keep polling (default: check once).")
    fetch.set_defaults(handler=run_batch_fetch)

    delete = commands.add_parser("delete", help="Delete a stored interaction.")
    delete.add_argument("interaction_id")
    delete.set_defaults(handler=run_delete)

    contract = commands.add_parser("contract", help="Free check that the live API still matches this helper's limits.")
    contract.set_defaults(handler=run_contract)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if not getattr(args, "dry_run", False):
            api_key()
        return args.handler(args)
    except UsageError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    except ApiError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

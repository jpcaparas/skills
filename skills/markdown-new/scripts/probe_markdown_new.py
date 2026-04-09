#!/usr/bin/env python3
"""
probe_markdown_new.py - Minimal probe client for markdown.new.

Examples:
    python3 probe_markdown_new.py --mode get 'https://example.com'
    python3 probe_markdown_new.py --mode get 'https://example.com' --json-response
    python3 probe_markdown_new.py --mode post 'https://httpbin.org/anything?foo=bar&baz=qux'
    python3 probe_markdown_new.py --mode post 'https://www.python.org/' --force-method browser --retain-images
    python3 probe_markdown_new.py --mode crawl-start 'https://example.com' --limit 1 --depth 1
    python3 probe_markdown_new.py --mode crawl-status 'job-id' --json-response
    python3 probe_markdown_new.py --mode upload ./notes.md
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


BASE_URL = "https://markdown.new"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36",
    "Accept": "*/*",
}
HEADER_WHITELIST = {
    "content-type",
    "content-length",
    "cache-control",
    "x-markdown-tokens",
    "x-rate-limit-remaining",
}


def read_response(response: urllib.response.addinfourl) -> tuple[int, dict[str, str], str]:
    body = response.read().decode("utf-8", errors="replace")
    headers = {k.lower(): v for k, v in response.headers.items() if k.lower() in HEADER_WHITELIST}
    return response.status, headers, body


def http_json_error(exc: urllib.error.HTTPError) -> tuple[int, dict[str, str], str]:
    headers = {k.lower(): v for k, v in exc.headers.items() if k.lower() in HEADER_WHITELIST}
    body = exc.read().decode("utf-8", errors="replace")
    return exc.code, headers, body


def maybe_parse_json(text: str) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def normalize_target(target: str) -> str:
    if target.startswith("http://") or target.startswith("https://"):
        return target
    if "/" not in target and "." in target:
        return f"https://{target}"
    return target


def request_get(target: str, json_response: bool) -> tuple[int, dict[str, str], str]:
    target = normalize_target(target)
    path = f"/{target}"
    if json_response:
        path += "?format=json"
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=dict(DEFAULT_HEADERS), method="GET")
    return execute(req)


def request_post(target: str, force_method: str | None, retain_images: bool) -> tuple[int, dict[str, str], str]:
    payload: dict[str, object] = {"url": normalize_target(target)}
    if force_method:
        payload["method"] = force_method
    if retain_images:
        payload["retain_images"] = True
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/",
        data=data,
        headers={**DEFAULT_HEADERS, "Content-Type": "application/json"},
        method="POST",
    )
    return execute(req)


def request_crawl_start(
    target: str,
    limit: int | None,
    depth: int | None,
    render: bool,
) -> tuple[int, dict[str, str], str]:
    payload: dict[str, object] = {"url": normalize_target(target)}
    if limit is not None:
        payload["limit"] = limit
    if depth is not None:
        payload["depth"] = depth
    if render:
        payload["render"] = True
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/crawl",
        data=data,
        headers={**DEFAULT_HEADERS, "Content-Type": "application/json"},
        method="POST",
    )
    return execute(req)


def request_crawl_status(job_id: str, json_response: bool) -> tuple[int, dict[str, str], str]:
    suffix = "?format=json" if json_response else ""
    req = urllib.request.Request(f"{BASE_URL}/crawl/status/{job_id}{suffix}", headers=dict(DEFAULT_HEADERS), method="GET")
    return execute(req)


def request_upload(file_path: str) -> tuple[int, dict[str, str], str]:
    with open(file_path, "rb") as handle:
        payload = MIMEMultipart("form-data")
        part = MIMEBase(*((mimetypes.guess_type(file_path)[0] or "application/octet-stream").split("/", 1)))
        part.set_payload(handle.read())
        encoders.encode_noop(part)
        part.add_header("Content-Disposition", "form-data", name="file", filename=os.path.basename(file_path))
        payload.attach(part)
        body = payload.as_bytes()

    headers = {**DEFAULT_HEADERS, "Content-Type": payload["Content-Type"]}
    req = urllib.request.Request(f"{BASE_URL}/convert", data=body, headers=headers, method="POST")
    return execute(req)


def execute(req: urllib.request.Request) -> tuple[int, dict[str, str], str]:
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return read_response(response)
    except urllib.error.HTTPError as exc:
        return http_json_error(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe markdown.new endpoints and return structured output.")
    parser.add_argument("--mode", required=True, choices=["get", "post", "crawl-start", "crawl-status", "upload"])
    parser.add_argument("value", help="Target URL, crawl job ID, or local file path depending on --mode")
    parser.add_argument("--json-response", action="store_true", help="Ask GET or crawl-status for JSON output")
    parser.add_argument("--force-method", choices=["auto", "ai", "browser"], help="Force markdown.new conversion method for --mode post")
    parser.add_argument("--retain-images", action="store_true", help="Ask markdown.new to retain images for --mode post")
    parser.add_argument("--limit", type=int, help="Crawl page limit for --mode crawl-start")
    parser.add_argument("--depth", type=int, help="Crawl depth for --mode crawl-start")
    parser.add_argument("--render", action="store_true", help="Enable crawl rendering for SPAs")
    args = parser.parse_args()

    if args.mode == "get":
        status, headers, body = request_get(args.value, args.json_response)
    elif args.mode == "post":
        status, headers, body = request_post(args.value, args.force_method, args.retain_images)
    elif args.mode == "crawl-start":
        status, headers, body = request_crawl_start(args.value, args.limit, args.depth, args.render)
    elif args.mode == "crawl-status":
        status, headers, body = request_crawl_status(args.value, args.json_response)
    else:
        status, headers, body = request_upload(args.value)

    result = {
        "status": status,
        "headers": headers,
        "body": maybe_parse_json(body),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if status < 400 else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Snapshot Jev's public Markdown index and pages; never read API credentials.

Exit 0: all indexed pages fetched. Exit 1: incomplete snapshot (see manifest).
Exit 2: invalid arguments/output or local I/O failure. No automatic retries.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import http.client
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit, urlunsplit


ORIGIN = "https://docs.typesafe.ai"
INDEX_URL = ORIGIN + "/llms.txt"
MAX_BYTES = 2 * 1024 * 1024
WORKERS = 4


@dataclass(frozen=True)
class Page:
    url: str
    body: bytes
    fetched_at: str


@dataclass(frozen=True)
class FetchFailure:
    url: str
    error: str
    fetched_at: str


@dataclass(frozen=True)
class SavedPage:
    url: str
    path: str
    fetched_at: str
    sha256: str
    bytes: int


@dataclass(frozen=True)
class PageIndex:
    urls: list[str]
    unsupported_urls: list[str]


@dataclass(frozen=True)
class Snapshot:
    index_url: str
    started_at: str
    finished_at: str
    complete: bool
    discovered_pages: int
    files: list[SavedPage]
    failures: list[FetchFailure]
    omitted_urls: list[str]
    unsupported_urls: list[str]


Fetch = Callable[[str], Page | FetchFailure]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def docs_url(raw: str) -> str | None:
    """Allow only simple HTTPS documentation paths, never credentials or queries."""
    try:
        url = urlsplit(raw)
    except ValueError:
        return None
    if url.scheme != "https" or url.netloc != "docs.typesafe.ai" or url.query:
        return None
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", url.path):
        return None
    if any(part in (".", "..", "") for part in url.path[1:].split("/")):
        return None
    return urlunsplit((url.scheme, url.netloc, url.path, "", ""))


def indexed_pages(index: str) -> PageIndex:
    urls: set[str] = set()
    unsupported: set[str] = set()
    for raw in re.findall(r"\[[^\]\n]*\]\(([^)\s]+)\)", index):
        url = docs_url(raw)
        if url is not None and url.endswith(".md"):
            urls.add(url)
        else:
            unsupported.add(raw)
    return PageIndex(sorted(urls), sorted(unsupported))


def decode_document(body: bytes, content_type: str) -> str:
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type not in {"text/plain", "text/markdown", "text/x-markdown"}:
        raise ValueError("expected Markdown/plain text, received " + media_type)
    if len(body) > MAX_BYTES:
        raise ValueError("document exceeds the 2 MiB limit")
    text = body.decode("utf-8")
    if not text.strip() or "\x00" in text:
        raise ValueError("empty or binary document")
    if re.match(r"\s*(?:<!doctype\s+html|<html\b)", text, re.IGNORECASE):
        raise ValueError("received an HTML page instead of documentation text")
    return text


class PublicDocsClient:
    """Credential-free adapter with bounded reads and no redirect following.

    Direct HTTPS avoids ambient proxy/auth configuration. A moved docs URL is
    an explicit coverage failure for the agent to inspect, not a new trust root.
    """

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    def fetch(self, url: str) -> Page | FetchFailure:
        if docs_url(url) != url:
            return FetchFailure(
                url, "refusing URL outside the docs allowlist", utc_now()
            )
        connection = http.client.HTTPSConnection(
            "docs.typesafe.ai", timeout=self.timeout
        )
        try:
            connection.request(
                "GET",
                urlsplit(url).path,
                headers={
                    "User-Agent": "jev-opportunities-docs/1.0",
                    "Accept": "text/markdown, text/plain",
                    "Accept-Encoding": "identity",
                    "Cache-Control": "no-cache",
                },
            )
            response = connection.getresponse()
            if response.status != 200:
                raise ValueError(
                    f"HTTP {response.status}; redirects and retries are disabled"
                )
            body = response.read(MAX_BYTES + 1)
            decode_document(body, response.getheader("Content-Type", ""))
            return Page(url, body, utc_now())
        except (OSError, http.client.HTTPException, ValueError) as exc:
            return FetchFailure(url, f"{type(exc).__name__}: {exc}", utc_now())
        finally:
            connection.close()


def scrape(output: Path, fetch: Fetch, max_pages: int) -> Snapshot:
    """Save a fresh snapshot, preserving partial evidence on remote failures."""
    if not 1 <= max_pages <= 512:
        raise ValueError("max_pages must be 1..512")
    # mkdir is the no-clobber boundary, including dangling destination symlinks.
    output.mkdir(parents=True, exist_ok=False)
    started = utc_now()
    files: list[SavedPage] = []
    failures: list[FetchFailure] = []
    page_index = PageIndex([], [])

    def save(result: Page | FetchFailure, relative: str) -> None:
        if isinstance(result, FetchFailure):
            failures.append(result)
            return
        (output / relative).write_bytes(result.body)
        files.append(
            SavedPage(
                url=result.url,
                path=relative,
                fetched_at=result.fetched_at,
                sha256=hashlib.sha256(result.body).hexdigest(),
                bytes=len(result.body),
            )
        )

    index = fetch(INDEX_URL)
    save(index, "llms.txt")
    if isinstance(index, Page):
        page_index = indexed_pages(index.body.decode("utf-8"))
        if not page_index.urls:
            failures.append(
                FetchFailure(
                    INDEX_URL, "index contains no supported Markdown links", utc_now()
                )
            )
    selected = page_index.urls[:max_pages]
    if selected:
        (output / "pages").mkdir()
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            # Batches also bound retained response bodies, not just open sockets.
            for start in range(0, len(selected), WORKERS):
                batch = selected[start : start + WORKERS]
                for number, result in enumerate(
                    pool.map(fetch, batch), start=start + 1
                ):
                    save(result, f"pages/{number:04d}.md")

    snapshot = Snapshot(
        index_url=INDEX_URL,
        started_at=started,
        finished_at=utc_now(),
        complete=bool(selected)
        and not failures
        and not page_index.unsupported_urls
        and len(selected) == len(page_index.urls),
        discovered_pages=len(page_index.urls),
        files=files,
        failures=failures,
        omitted_urls=page_index.urls[max_pages:],
        unsupported_urls=page_index.unsupported_urls,
    )
    (output / "manifest.json").write_text(
        json.dumps(asdict(snapshot), indent=2) + "\n", encoding="utf-8"
    )
    return snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output", type=Path, help="New scratch directory; must not exist"
    )
    parser.add_argument(
        "--max-pages", type=int, default=256, help="Page cap, 1..512 (default: 256)"
    )
    parser.add_argument(
        "--timeout", type=float, default=20, help="Socket timeout in seconds, 1..60"
    )
    args = parser.parse_args(argv)
    if not 1 <= args.max_pages <= 512:
        parser.error("--max-pages must be 1..512")
    if not math.isfinite(args.timeout) or not 1 <= args.timeout <= 60:
        parser.error("--timeout must be finite and 1..60 seconds")
    try:
        snapshot = scrape(
            args.output, PublicDocsClient(args.timeout).fetch, args.max_pages
        )
    except (OSError, ValueError) as exc:
        print(f"Cannot write snapshot: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "complete": snapshot.complete,
                "discovered_pages": snapshot.discovered_pages,
                "saved_files_including_index": len(snapshot.files),
                "failures": len(snapshot.failures),
                "omitted_pages": len(snapshot.omitted_urls),
                "unsupported_index_links": len(snapshot.unsupported_urls),
                "manifest": str(args.output / "manifest.json"),
            },
            indent=2,
        )
    )
    return 0 if snapshot.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())

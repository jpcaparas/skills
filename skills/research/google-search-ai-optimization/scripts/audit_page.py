#!/usr/bin/env python3
"""Static page signal audit for Google Search AI optimization work."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class SignalParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.in_title = False
        self.current_heading: str | None = None
        self.heading_parts: list[str] = []
        self.headings: list[dict[str, str]] = []
        self.metas: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.anchors: list[dict[str, str]] = []
        self.text_parts: list[str] = []
        self.in_jsonld = False
        self.jsonld_parts: list[str] = []
        self.jsonld_blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = {name.lower(): value or "" for name, value in attrs}
        if tag == "title":
            self.in_title = True
        elif re.fullmatch(r"h[1-6]", tag):
            self.current_heading = tag
            self.heading_parts = []
        elif tag == "meta":
            self.metas.append(attr)
        elif tag == "link":
            self.links.append(attr)
        elif tag == "img":
            self.images.append(attr)
        elif tag == "a":
            self.anchors.append(attr)
        elif tag == "script" and attr.get("type", "").lower() == "application/ld+json":
            self.in_jsonld = True
            self.jsonld_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif self.current_heading == tag:
            text = clean_text(" ".join(self.heading_parts))
            self.headings.append({"level": tag, "text": text})
            self.current_heading = None
            self.heading_parts = []
        elif tag == "script" and self.in_jsonld:
            self.jsonld_blocks.append("".join(self.jsonld_parts).strip())
            self.in_jsonld = False
            self.jsonld_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        elif self.current_heading:
            self.heading_parts.append(data)
        elif self.in_jsonld:
            self.jsonld_parts.append(data)
        elif data.strip():
            self.text_parts.append(data)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def read_input(target: str, timeout: int) -> tuple[str, dict[str, Any]]:
    if re.match(r"^https?://", target):
        req = urllib.request.Request(
            target,
            headers={"User-Agent": "google-search-ai-optimization-skill/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
                return body, {
                    "source": target,
                    "status": getattr(response, "status", None),
                    "content_type": response.headers.get("content-type", ""),
                }
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return body, {"source": target, "status": exc.code, "content_type": exc.headers.get("content-type", "")}

    path = Path(target)
    return path.read_text(encoding="utf-8"), {"source": str(path), "status": None, "content_type": "text/html"}


def first_meta(metas: list[dict[str, str]], key: str, value: str) -> str:
    for meta in metas:
        if meta.get(key, "").lower() == value:
            return meta.get("content", "").strip()
    return ""


def link_values(links: list[dict[str, str]], rel_name: str) -> list[str]:
    found = []
    for link in links:
        rels = {part.lower() for part in link.get("rel", "").split()}
        if rel_name in rels and link.get("href"):
            found.append(link["href"])
    return found


def crawlable_href(href: str) -> bool:
    lowered = href.strip().lower()
    return bool(lowered) and not lowered.startswith(("javascript:", "mailto:", "tel:", "#"))


def parse_jsonld(blocks: list[str]) -> tuple[list[Any], list[str]]:
    parsed: list[Any] = []
    errors: list[str] = []
    for index, block in enumerate(blocks, start=1):
        if not block:
            continue
        try:
            parsed.append(json.loads(block))
        except json.JSONDecodeError as exc:
            errors.append(f"JSON-LD block {index}: {exc.msg} at line {exc.lineno}")
    return parsed, errors


def collect_types(value: Any) -> list[str]:
    types: list[str] = []
    if isinstance(value, dict):
        raw_type = value.get("@type")
        if isinstance(raw_type, str):
            types.append(raw_type)
        elif isinstance(raw_type, list):
            types.extend(str(item) for item in raw_type)
        for nested in value.values():
            types.extend(collect_types(nested))
    elif isinstance(value, list):
        for item in value:
            types.extend(collect_types(item))
    return types


def add_finding(findings: list[dict[str, str]], severity: str, check: str, message: str) -> None:
    findings.append({"severity": severity, "check": check, "message": message})


def analyze(html: str, meta: dict[str, Any], expect_indexable: bool) -> dict[str, Any]:
    parser = SignalParser()
    parser.feed(html)

    title = clean_text(" ".join(parser.title_parts))
    description = first_meta(parser.metas, "name", "description")
    robots_values = [
        meta_tag.get("content", "")
        for meta_tag in parser.metas
        if meta_tag.get("name", "").lower() in {"robots", "googlebot"}
    ]
    robots = ", ".join(value.lower() for value in robots_values)
    canonicals = link_values(parser.links, "canonical")
    h1s = [heading["text"] for heading in parser.headings if heading["level"] == "h1" and heading["text"]]
    crawlable_links = [anchor for anchor in parser.anchors if crawlable_href(anchor.get("href", ""))]
    images_missing_alt = [img for img in parser.images if "alt" not in img]
    text = clean_text(" ".join(parser.text_parts))
    parsed_jsonld, jsonld_errors = parse_jsonld(parser.jsonld_blocks)
    jsonld_types = sorted(set(collect_types(parsed_jsonld)))

    findings: list[dict[str, str]] = []
    status = meta.get("status")

    if status and int(status) >= 400:
        add_finding(findings, "error", "status", f"HTTP status is {status}.")
    elif status and int(status) >= 300:
        add_finding(findings, "warning", "status", f"HTTP status is {status}; confirm the final canonical URL.")

    if not title:
        add_finding(findings, "error", "title", "Missing <title>.")
    elif len(title) > 70:
        add_finding(findings, "info", "title", "Title is longer than typical search-result display space; check quality manually.")

    if not description:
        add_finding(findings, "warning", "description", "Missing meta description.")

    if not h1s:
        add_finding(findings, "warning", "h1", "No H1 found.")
    elif len(h1s) > 1:
        add_finding(findings, "info", "h1", f"Multiple H1s found: {len(h1s)}.")

    if not canonicals:
        add_finding(findings, "warning", "canonical", "Missing canonical link.")
    elif len(canonicals) > 1:
        add_finding(findings, "warning", "canonical", f"Multiple canonical links found: {len(canonicals)}.")

    if expect_indexable and re.search(r"\b(noindex|none)\b", robots):
        add_finding(findings, "error", "robots", "Expected indexable page has noindex/none robots directive.")

    if re.search(r"\bnosnippet\b", robots) or re.search(r"\bmax-snippet\s*:\s*0\b", robots):
        add_finding(findings, "warning", "preview-controls", "Snippet restrictions may limit direct use in AI Overviews and AI Mode.")

    if not crawlable_links:
        add_finding(findings, "warning", "links", "No crawlable <a href> links found.")

    if len(text) < 300:
        add_finding(findings, "warning", "content", "Rendered text appears thin; verify the page satisfies the user need.")

    if images_missing_alt:
        add_finding(findings, "info", "images", f"{len(images_missing_alt)} image(s) lack an alt attribute.")

    for error in jsonld_errors:
        add_finding(findings, "warning", "json-ld", error)

    if not parser.jsonld_blocks:
        add_finding(findings, "info", "json-ld", "No JSON-LD structured data found; this is acceptable unless a supported rich result/entity pattern is needed.")

    severity_order = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda item: (severity_order.get(item["severity"], 9), item["check"]))

    return {
        "source": meta["source"],
        "status": status,
        "signals": {
            "title": title,
            "description": description,
            "robots": robots_values,
            "canonical": canonicals,
            "h1": h1s,
            "heading_count": len(parser.headings),
            "crawlable_link_count": len(crawlable_links),
            "image_count": len(parser.images),
            "images_missing_alt": len(images_missing_alt),
            "text_characters": len(text),
            "jsonld_block_count": len(parser.jsonld_blocks),
            "jsonld_types": jsonld_types,
        },
        "findings": findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit one URL or HTML file for Google Search AI optimization signals.")
    parser.add_argument("--input", required=True, help="HTTP(S) URL or local HTML file path.")
    parser.add_argument("--expect-indexable", action="store_true", help="Treat noindex/none as an error.")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds.")
    parser.add_argument("--fail-on", choices=["error", "warning", "never"], default="never", help="Exit non-zero at or above this severity.")
    args = parser.parse_args()

    html, meta = read_input(args.input, args.timeout)
    result = analyze(html, meta, args.expect_indexable)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")

    severities = {finding["severity"] for finding in result["findings"]}
    if args.fail_on == "error" and "error" in severities:
        raise SystemExit(2)
    if args.fail_on == "warning" and ("error" in severities or "warning" in severities):
        raise SystemExit(2)


if __name__ == "__main__":
    main()

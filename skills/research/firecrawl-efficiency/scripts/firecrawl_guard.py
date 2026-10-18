#!/usr/bin/env python3
"""Price a Firecrawl v2 request before sending it, and refuse the shapes that cause bill shock.

    firecrawl_guard.py estimate crawl request.json --budget 50
    echo '{"url": "https://example.com"}' | firecrawl_guard.py estimate scrape -
    firecrawl_guard.py balance            # GET /v2/team/credit-usage (free)

`estimate` never touches the network. It prints a JSON verdict with a worst-case credit
figure and exits 0 (ok), 2 (warnings), or 3 (blocked: do not send). Prices are the
2026-10-18 snapshot documented in references/pricing.md; recheck them when Firecrawl
changes its billing page.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urlparse

API_ROOT = os.environ.get("FIRECRAWL_API_ROOT", "https://api.firecrawl.dev").rstrip("/")

# Endpoints this skill never calls. /agent and its wrappers are banned outright; /extract is
# its token-billed predecessor whose docs point to /agent; the v1 research endpoints are deprecated.
FORBIDDEN_ENDPOINTS = {
    "agent": "/agent is banned: dynamic billing (a few hundred credits per run, maxCredits defaults to 2,500). Use map + scrape with a json format instead.",
    "extract": "/extract is banned: token-billed (15 tokens = 1 credit), includeSubdomains defaults to true, and the docs steer it to /agent. Use scrape with a json format.",
    "deep-research": "/v1/deep-research is deprecated and bills per URL analysed. Use search, then scrape the chosen URLs.",
    "llmstxt": "/v1/llmstxt is deprecated. Use map, then scrape the pages you need.",
}

# Hosts routed to paid third parties (X via Grok: 30 credits; LinkedIn via data providers: 5-40)
# and excluded by policy. Subdomains match too.
PREMIUM_HOSTS = ("x.com", "twitter.com", "t.co", "twimg.com", "linkedin.com", "lnkd.in")

LLM_FORMATS = {"json", "question", "query", "highlights", "audio", "video"}  # +4 credits/page each
FREE_FORMATS = {"markdown", "html", "rawHtml", "links", "images", "screenshot", "summary", "branding", "changeTracking", "product", "attributes"}
DEFAULT_CRAWL_LIMIT = 10_000
INTERACT_PROMPT_PER_MIN = 7
INTERACT_CODE_PER_MIN = 2
INTERACT_DEFAULT_TTL_SECONDS = 600


class Level(str, Enum):
    BLOCK = "block"
    WARN = "warn"
    NOTE = "note"


@dataclass
class Finding:
    level: Level
    message: str


@dataclass
class Estimate:
    endpoint: str
    worst_case_credits: int | None
    per_page_credits: int | None = None
    findings: list[Finding] = field(default_factory=list)

    def block(self, message: str) -> None:
        self.findings.append(Finding(Level.BLOCK, message))

    def warn(self, message: str) -> None:
        self.findings.append(Finding(Level.WARN, message))

    def note(self, message: str) -> None:
        self.findings.append(Finding(Level.NOTE, message))

    @property
    def exit_code(self) -> int:
        levels = {f.level for f in self.findings}
        if Level.BLOCK in levels:
            return 3
        return 2 if Level.WARN in levels else 0

    def as_json(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "verdict": {0: "ok", 2: "warn", 3: "blocked"}[self.exit_code],
            "worst_case_credits": self.worst_case_credits,
            "per_page_credits": self.per_page_credits,
            "findings": [{"level": f.level.value, "message": f.message} for f in self.findings],
        }


def host_is_premium(url: str) -> bool:
    host = (urlparse(url if "//" in url else f"https://{url}").hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in PREMIUM_HOSTS)


def looks_like_pdf(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(".pdf") or "/pdf/" in path


def format_names(formats: list[Any]) -> list[str]:
    names: list[str] = []
    for item in formats:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict) and isinstance(item.get("type"), str):
            names.append(item["type"])
    return names


def per_page_cost(options: dict[str, Any], estimate: Estimate) -> int:
    """Credits for one scraped page under these scrape options, excluding PDF page parsing."""
    formats = format_names(options.get("formats") or ["markdown"])
    llm = [f for f in formats if f in LLM_FORMATS]
    unknown = [f for f in formats if f not in LLM_FORMATS and f not in FREE_FORMATS]
    cost = 1
    # Live 2026-10-18: markdown + summary + json cost 5, so each *LLM* format adds 4 once.
    cost += 4 * len(set(llm))
    if llm:
        estimate.note(f"LLM formats {sorted(set(llm))} add 4 credits per page each; markdown alone is 1.")
    if unknown:
        estimate.warn(f"Unknown formats {unknown}: price not in this guard's table; check the billing page.")
    if options.get("zeroDataRetention"):
        cost += 1
    for flag in ("redactPII", "checkPromptInjection", "lockdown"):
        if options.get(flag):
            cost += 4
            estimate.warn(f"{flag} adds 4 credits per page.")
    if options.get("actions"):
        estimate.note("actions have no documented surcharge, but each wait adds latency and timeout risk.")
    return cost


def pdf_pages_cap(options: dict[str, Any]) -> int | None:
    """Return the PDF page cap: 0 when parsing is off, an int when maxPages is set, None when unbounded."""
    parsers = options.get("parsers")
    if parsers == []:
        return 0
    for parser in parsers or []:
        if isinstance(parser, dict) and parser.get("type") == "pdf" and isinstance(parser.get("maxPages"), int):
            return parser["maxPages"]
    return None


def check_urls(urls: list[str], estimate: Estimate) -> None:
    premium = [u for u in urls if host_is_premium(u)]
    if premium:
        estimate.block(f"Premium/provider-routed hosts are excluded (X costs 30 credits, LinkedIn 5-40, and policy forbids them): {premium[:5]}")


def estimate_scrape_like(endpoint: str, urls: list[str], options: dict[str, Any]) -> Estimate:
    estimate = Estimate(endpoint, None)
    check_urls(urls, estimate)
    page = per_page_cost(options, estimate)
    estimate.per_page_credits = page
    total = page * len(urls)
    pdfs = [u for u in urls if looks_like_pdf(u)]
    cap = pdf_pages_cap(options)
    if pdfs:
        if cap is None:
            estimate.warn("PDF URL with unbounded parsing: every PDF page is billed (a 15-page paper cost 15 credits). Set parsers: [{type: pdf, maxPages: N}].")
            total = None
        elif cap == 0:
            estimate.warn("parsers: [] bills 1 credit but returns the raw PDF as base64 in the markdown field (2.9 MB for a 15-page paper). Never print it into context.")
        else:
            # Live: maxPages 2 cost 2 and an uncapped 15-page PDF cost 15, so parsed pages replace the base credit.
            pdf_cost = page - 1 + cap
            total = page * (len(urls) - len(pdfs)) + pdf_cost * len(pdfs)
    estimate.worst_case_credits = total
    if options.get("maxAge") == 0:
        estimate.note("maxAge: 0 forces a fresh fetch. Cache hits cost the same 1 credit, so it changes freshness and speed, not price.")
    return estimate


def estimate_crawl(body: dict[str, Any]) -> Estimate:
    estimate = Estimate("crawl", None)
    check_urls([str(body.get("url", ""))], estimate)
    options = body.get("scrapeOptions") or {}
    page = per_page_cost(options, estimate)
    estimate.per_page_credits = page
    limit = body.get("limit")
    if not isinstance(limit, int) or limit <= 0:
        estimate.block(f"No explicit limit: crawl defaults to {DEFAULT_CRAWL_LIMIT:,} pages and pay-as-you-go keeps billing past zero. Map first, then set limit.")
        limit = DEFAULT_CRAWL_LIMIT
    estimate.worst_case_credits = page * limit
    if body.get("ignoreQueryParameters") is not True and body.get("sitemap") != "skip":
        estimate.warn("Set ignoreQueryParameters: true. Live 2026-10-18: a one-page site crawled with defaults returned 809 query-string variants (809 credits).")
    for flag, why in (("crawlEntireDomain", "follows sibling and parent paths"), ("allowSubdomains", "follows every subdomain"), ("allowExternalLinks", "follows links off the site")):
        if body.get(flag):
            estimate.warn(f"{flag} {why}; expect the full limit to be used.")
    if pdf_pages_cap(options) is None:
        estimate.note("PDFs reached by the crawl bill per page; add scrapeOptions.parsers maxPages or [] if PDFs are irrelevant.")
    if body.get("prompt"):
        estimate.warn("A natural-language prompt lets Firecrawl choose paths and depth; set includePaths/limit explicitly instead.")
    return estimate


def estimate_search(body: dict[str, Any]) -> Estimate:
    estimate = Estimate("search", None)
    limit = body.get("limit", 5)
    sources = body.get("sources") or ["web"]
    results = int(limit) * len(sources)
    # Live 2026-10-18: limit 5 with web+news returned 10 results for 2 credits; 11 results cost 4.
    credits = 2 * math.ceil(results / 10)
    if (body.get("enterprise") or []) and "zdr" in body["enterprise"]:
        credits = 10 * math.ceil(results / 10)
        estimate.warn("enterprise zdr search costs 10 credits per 10 results.")
    options = body.get("scrapeOptions")
    if options:
        page = per_page_cost(options, estimate)
        estimate.per_page_credits = page
        credits += page * results
        estimate.warn(f"scrapeOptions scrapes every result: +{page} x {results}. Search first, then scrape only the URLs you need.")
        if pdf_pages_cap(options) is None:
            estimate.note("Add parsers: [] (or maxPages) so PDF results are not parsed page by page.")
    if results % 10:
        estimate.note(f"Billing rounds up per 10 results: {results} results cost the same as {math.ceil(results / 10) * 10}.")
    estimate.worst_case_credits = credits
    return estimate


def estimate_interact(body: dict[str, Any]) -> Estimate:
    estimate = Estimate("interact", None)
    rate = INTERACT_PROMPT_PER_MIN if body.get("prompt") else INTERACT_CODE_PER_MIN
    if body.get("zeroDataRetention"):
        rate += 2
    ttl = body.get("ttl") or body.get("timeout") or INTERACT_DEFAULT_TTL_SECONDS
    minutes = math.ceil(int(ttl) / 60)  # ttl is 30-3600 s, so this is at least the 1-minute minimum
    estimate.worst_case_credits = rate * minutes
    estimate.warn(f"Interact bills {rate} credits per browser minute (1-minute minimum) until the session is deleted or expires; worst case {minutes} min. DELETE the session when done.")
    if body.get("prompt"):
        estimate.note("Playwright code costs 2 credits/min against 7 for a prompt.")
    return estimate


def estimate_request(endpoint: str, body: dict[str, Any]) -> Estimate:
    key = endpoint.strip("/").replace("v2/", "").replace("v1/", "").replace("/", "-")
    for banned, why in FORBIDDEN_ENDPOINTS.items():
        if key == banned or key.startswith(banned + "-") or key.endswith("-" + banned):
            estimate = Estimate(key, None)
            estimate.block(why)
            return estimate
    if key == "scrape":
        return estimate_scrape_like("scrape", [str(body.get("url", ""))], body)
    if key in ("batch-scrape", "batch"):
        urls = [str(u) for u in body.get("urls") or []]
        estimate = estimate_scrape_like("batch-scrape", urls, body)
        estimate.note("Batch scrape bills per URL like scrape; status polling is free.")
        return estimate
    if key == "crawl":
        return estimate_crawl(body)
    if key == "map":
        estimate = Estimate("map", 1)
        estimate.note("Map costs 1 credit per call whatever the limit (1,612 URLs for 1 credit, live). Its count does not predict crawl size.")
        return estimate
    if key == "search":
        return estimate_search(body)
    if key == "parse":
        estimate = Estimate("parse", None)
        cap = pdf_pages_cap(body)
        estimate.worst_case_credits = None if cap is None else max(1, cap)
        if cap is None:
            estimate.warn("/parse bills 1 credit per PDF page; set parsers maxPages to bound it.")
        return estimate
    if key == "interact" or key.endswith("-interact"):
        return estimate_interact(body)
    estimate = Estimate(key, None)
    estimate.warn(f"No price model for '{endpoint}'. Read references/pricing.md before sending it.")
    return estimate


def apply_budget(estimate: Estimate, budget: int | None) -> None:
    if budget is None:
        return
    if estimate.worst_case_credits is None:
        estimate.block(f"Worst case is unbounded, so it cannot be proven under the {budget}-credit budget.")
    elif estimate.worst_case_credits > budget:
        estimate.block(f"Worst case {estimate.worst_case_credits} credits exceeds the {budget}-credit budget.")


def fetch_balance() -> dict[str, Any]:
    key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if not key:
        raise SystemExit("FIRECRAWL_API_KEY is not set.")
    request = urllib.request.Request(f"{API_ROOT}/v2/team/credit-usage", headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"credit-usage returned HTTP {exc.code}") from exc
    data = payload.get("data") or {}
    return {
        "remaining_credits": data.get("remainingCredits"),
        "plan_credits": data.get("planCredits"),
        "billing_period_end": data.get("billingPeriodEnd"),
    }


def load_body(source: str) -> dict[str, Any]:
    raw = sys.stdin.read() if source == "-" else open(source, encoding="utf-8").read()
    body = json.loads(raw or "{}")
    if not isinstance(body, dict):
        raise SystemExit("The request body must be a JSON object.")
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    est = commands.add_parser("estimate", help="Offline worst-case credit estimate and policy check")
    est.add_argument("endpoint", help="scrape, batch-scrape, crawl, map, search, parse, interact (agent/extract are refused)")
    est.add_argument("body", help="Path to the JSON request body, or - for stdin")
    est.add_argument("--budget", type=int, help="Block when the worst case exceeds this many credits")
    commands.add_parser("balance", help="Remaining credits via GET /v2/team/credit-usage (free)")
    args = parser.parse_args(argv)

    if args.command == "balance":
        print(json.dumps(fetch_balance()))
        return 0
    estimate = estimate_request(args.endpoint, load_body(args.body))
    apply_budget(estimate, args.budget)
    print(json.dumps(estimate.as_json(), indent=2))
    return estimate.exit_code


if __name__ == "__main__":
    sys.exit(main())

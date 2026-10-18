#!/usr/bin/env python3
"""
probe_synthetic_search.py - Re-verify Synthetic Search behaviour against the live API.

Every successful search, and every blank 500, costs one unit of the hourly search quota.
/quotas and 400/401 responses are free. Each mode reports its quota cost.

Usage:
    python3 probe_synthetic_search.py --mode search --query "rust async await"   # 1 search
    python3 probe_synthetic_search.py --mode quotas                               # free
    python3 probe_synthetic_search.py --mode errors                               # 1 search
    python3 probe_synthetic_search.py --mode limits                               # 4 searches
    python3 probe_synthetic_search.py --mode all                                  # 6 searches
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

BASE_URL = os.environ.get("SYNTHETIC_API_BASE_URL", "https://api.synthetic.new/v2").rstrip("/")
DOCUMENTED_QUERY_LIMIT = 4096


def require_api_key() -> str:
    api_key = os.environ.get("SYNTHETIC_API_KEY")
    if not api_key:
        print("ERROR: SYNTHETIC_API_KEY environment variable is required.", file=sys.stderr)
        raise SystemExit(1)
    return api_key


def request(path: str, *, method: str = "GET", body: object = None, api_key: str | None = None) -> dict:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {api_key or require_api_key()}"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
    text = raw.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text) if text else None
    except json.JSONDecodeError:
        parsed = text[:300]
    return {"status": status, "body": parsed, "bytes": len(raw), "sha1": hashlib.sha1(raw).hexdigest()[:12]}


def search(body: object) -> dict:
    return request("/search", method="POST", body=body)


def results_of(response: dict) -> list[dict]:
    body = response.get("body")
    return body.get("results", []) if isinstance(body, dict) else []


def probe_search(query: str) -> dict:
    response = search({"query": query})
    results = results_of(response)
    text_lengths = [len(item.get("text") or "") for item in results]
    return {
        "status": response["status"],
        "response_bytes": response["bytes"],
        "result_count": len(results),
        "result_keys": sorted({key for item in results for key in item}),
        "published_present": sum(1 for item in results if item.get("published")),
        "highlights_per_result": [len(item.get("highlights") or []) for item in results],
        "text_chars": {"min": min(text_lengths), "median": statistics.median(text_lengths), "max": max(text_lengths)}
        if text_lengths
        else None,
        "results": [{"title": item.get("title"), "url": item.get("url")} for item in results],
    }


def probe_quotas() -> dict:
    response = request("/quotas")
    body = response.get("body") if isinstance(response.get("body"), dict) else {}
    return {"status": response["status"], "top_level_keys": sorted(body), "search": body.get("search")}


def probe_errors() -> dict:
    def summary(response: dict) -> dict:
        return {"status": response["status"], "body": response["body"]}

    return {
        "bad_auth (free)": summary(
            request("/search", method="POST", body={"query": "rust async await"}, api_key="obviously-wrong-key")
        ),
        "missing_query (free)": summary(search({})),
        "non_string_query (free)": summary(search({"query": 123})),
        "empty_query (costs 1)": summary(search({"query": ""})),
    }


def probe_limits() -> dict:
    """Checks the two facts most likely to drift: ignored body parameters and the 4,096-char cut."""
    query = "python retry backoff library"
    plain = search({"query": query})
    with_params = search({"query": query, "numResults": 10, "includeDomains": ["pypi.org"]})

    def site_filter_survives(total_chars: int) -> bool:
        operator = " site:github.com"
        filler = ("python retry backoff " * 400)[: total_chars - len(operator)]
        domains = [urlparse(item.get("url", "")).netloc for item in results_of(search({"query": filler + operator}))]
        return bool(domains) and all(domain == "github.com" or domain.endswith(".github.com") for domain in domains)

    return {
        "body_parameters_ignored": plain["sha1"] == with_params["sha1"] and len(results_of(with_params)) == 5,
        f"site_filter_honoured_at_{DOCUMENTED_QUERY_LIMIT}_chars": site_filter_survives(DOCUMENTED_QUERY_LIMIT),
        f"site_filter_honoured_at_{DOCUMENTED_QUERY_LIMIT + 1}_chars": site_filter_survives(DOCUMENTED_QUERY_LIMIT + 1),
        "expected": {
            "body_parameters_ignored": True,
            f"site_filter_honoured_at_{DOCUMENTED_QUERY_LIMIT}_chars": True,
            f"site_filter_honoured_at_{DOCUMENTED_QUERY_LIMIT + 1}_chars": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-verify Synthetic Search behaviour against the live API.")
    parser.add_argument("--mode", choices=["search", "quotas", "errors", "limits", "all"], default="search")
    parser.add_argument("--query", default="rust async await")
    args = parser.parse_args()

    report: dict = {"mode": args.mode}
    if args.mode in {"search", "all"}:
        report["search"] = probe_search(args.query)
    if args.mode in {"errors", "all"}:
        report["errors"] = probe_errors()
    if args.mode in {"limits", "all"}:
        report["limits"] = probe_limits()
    if args.mode in {"quotas", "search", "errors", "limits", "all"}:
        report["quotas_after"] = probe_quotas()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

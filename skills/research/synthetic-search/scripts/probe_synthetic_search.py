#!/usr/bin/env python3
"""
probe_synthetic_search.py - Run structured live probes against Synthetic Search.

Usage:
    python3 probe_synthetic_search.py --mode all --query "rust async await"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = "https://api.synthetic.new/v2"


def require_api_key() -> str:
    api_key = os.environ.get("SYNTHETIC_API_KEY")
    if not api_key:
        print("ERROR: SYNTHETIC_API_KEY environment variable is required.", file=sys.stderr)
        raise SystemExit(1)
    return api_key


def request(path: str, *, method: str = "GET", body: dict | None = None, api_key: str | None = None) -> dict:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {api_key or require_api_key()}",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=payload, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return {
                "ok": True,
                "status": response.status,
                "body": json.loads(raw) if raw else None,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        parsed = None
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
        return {
            "ok": False,
            "status": exc.code,
            "body": parsed,
            "raw_body_length": len(raw),
        }


def probe_search(query: str) -> dict:
    result = request("/search", method="POST", body={"query": query})
    body = result.get("body") or {}
    first = (body.get("results") or [None])[0] if isinstance(body, dict) else None
    return {
        "status": result["status"],
        "result_count": len(body.get("results", [])) if isinstance(body, dict) else 0,
        "first_result_keys": sorted(first.keys()) if isinstance(first, dict) else [],
        "published_present": bool(isinstance(first, dict) and "published" in first),
        "sample": {
            "title": first.get("title") if isinstance(first, dict) else None,
            "url": first.get("url") if isinstance(first, dict) else None,
            "text_preview": (first.get("text", "")[:160] if isinstance(first, dict) else None),
        },
    }


def probe_quotas() -> dict:
    result = request("/quotas")
    body = result.get("body") or {}
    return {
        "status": result["status"],
        "top_level_keys": sorted(body.keys()) if isinstance(body, dict) else [],
        "search_keys": sorted(body.get("search", {}).keys()) if isinstance(body, dict) else [],
        "subscription_keys": sorted(body.get("subscription", {}).keys()) if isinstance(body, dict) else [],
    }


def probe_errors() -> dict:
    return {
        "bad_auth": request("/search", method="POST", body={"query": "rust async await"}, api_key="obviously-wrong-key"),
        "missing_query": request("/search", method="POST", body={}),
        "empty_query": request("/search", method="POST", body={"query": ""}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run structured live probes against Synthetic Search.")
    parser.add_argument("--mode", choices=["search", "quotas", "errors", "all"], default="all")
    parser.add_argument("--query", default="rust async await")
    args = parser.parse_args()

    report = {"mode": args.mode}
    if args.mode in {"search", "all"}:
        report["search"] = probe_search(args.query)
    if args.mode in {"quotas", "all"}:
        report["quotas"] = probe_quotas()
    if args.mode in {"errors", "all"}:
        report["errors"] = probe_errors()

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

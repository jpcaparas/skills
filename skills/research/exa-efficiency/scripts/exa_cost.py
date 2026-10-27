#!/usr/bin/env python3
"""Price an Exa (exa.ai) API request before sending it, and flag expensive defaults.

    exa_cost.py estimate search request.json
    echo '{"query": "...", "effort": "auto"}' | exa_cost.py estimate agent/runs - --budget-usd 1
    exa_cost.py estimate monitors monitor.json          # also prints monthly_usd

Offline only. Prints a JSON verdict with a worst-case USD figure and exits 0 (ok),
2 (warnings: read them), or 3 (blocked: do not send). Prices are the 2026-10-27 snapshot
of https://exa.ai/docs/admin/pricing, cross-checked against the costDollars that Exa
returned in a live spike (references/evidence.md). Recheck when Exa changes its pricing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# USD per request unless noted. Each base price covers up to 10 results.
SEARCH_TYPE_PRICE = {
    "lite": 0.004, "instant": 0.004,
    "auto": 0.007, "fast": 0.007,
    "deep-lite": 0.012, "deep": 0.012,
    "deep-reasoning": 0.015,
}
DEFAULT_SEARCH_TYPE = "auto"
LEGACY_SEARCH_TYPES = {"fast": "lite", "instant": "lite", "deep-reasoning": "deep"}
DEEP_SEARCH_TYPES = {"deep-lite", "deep", "deep-reasoning"}
INCLUDED_RESULTS = 10
MAX_RESULTS = 100
EXTRA_RESULT = 0.001
SUMMARY_PER_PAGE = 0.001
CONTENTS_PER_PAGE_PER_TYPE = 0.001
CONTENT_TYPES = ("text", "highlights", "summary")
MAX_CONTENTS_URLS = 100
ANSWER_PRICE = 0.005
MONITOR_RUN = 0.015
AGENT_FIXED_EFFORT = {"minimal": 0.012, "low": 0.025, "medium": 0.10, "high": 0.50, "xhigh": 1.00}
AGENT_METERED_DEFAULT_CAP = {"auto": 5.0, "ultra": 20.0}
AGENT_BUDGET_RANGE = (1.0, 100.0)
DEFAULT_AGENT_EFFORT = "auto"
CONTACT_PRICE = {"email": 0.02, "phone": 0.07}
DAYS_PER_MONTH = 30
PERIOD_HOURS = {"h": 1, "d": 24, "w": 168}

# /search parameters that `type: "lite"` rejects with 400 INVALID_REQUEST_BODY (any non-null value).
LITE_REJECTED_TOP = ("outputSchema", "systemPrompt", "stream", "additionalQueries",
                     "includeText", "excludeText", "startCrawlDate", "endCrawlDate")
LITE_REJECTED_CONTENTS = ("summary", "extras", "subpages", "subpageTarget",
                          "maxAgeHours", "livecrawl", "livecrawlTimeout", "context")
CONTACT_WORDS = re.compile(r"\b(e-?mails?|phones?|phone numbers?|contact (details|info))\b", re.I)


class Level(str, Enum):
    BLOCK = "block"
    WARN = "warn"
    NOTE = "note"


@dataclass
class Estimate:
    api: str
    worst_case_usd: float | None = None
    monthly_usd: float | None = None
    findings: list[tuple[Level, str]] = field(default_factory=list)

    def block(self, message: str) -> None:
        self.findings.append((Level.BLOCK, message))

    def warn(self, message: str) -> None:
        self.findings.append((Level.WARN, message))

    def note(self, message: str) -> None:
        self.findings.append((Level.NOTE, message))

    @property
    def exit_code(self) -> int:
        levels = {level for level, _ in self.findings}
        if Level.BLOCK in levels:
            return 3
        return 2 if Level.WARN in levels else 0

    def as_json(self) -> dict[str, Any]:
        verdict: dict[str, Any] = {
            "api": self.api,
            "verdict": {0: "ok", 2: "warn", 3: "blocked"}[self.exit_code],
            "worst_case_usd": usd(self.worst_case_usd),
        }
        if self.monthly_usd is not None:
            verdict["monthly_usd"] = usd(self.monthly_usd)
        verdict["findings"] = [{"level": level.value, "message": message} for level, message in self.findings]
        return verdict


def usd(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def is_set(value: Any) -> bool:
    """Exa treats null as unset and every other value, including false and [], as set."""
    return value is not None


def requested_results(body: dict[str, Any], estimate: Estimate) -> int:
    count = body.get("numResults", INCLUDED_RESULTS)
    if not isinstance(count, int) or count < 1:
        estimate.block("numResults must be an integer from 1 to 100.")
        return INCLUDED_RESULTS
    if count > MAX_RESULTS:
        estimate.block(f"numResults {count} exceeds the public maximum of {MAX_RESULTS} (Enterprise only above that).")
        return MAX_RESULTS
    return count


def check_text_budget(text: Any, estimate: Estimate, where: str) -> None:
    if text is True or (isinstance(text, dict) and "maxCharacters" not in text):
        estimate.warn(f"{where} text has no maxCharacters: live, 5 results returned 172 KB. Prefer highlights, or set text.maxCharacters.")


def estimate_search(body: dict[str, Any], channel: str) -> Estimate:
    estimate = Estimate("search")
    search_type = body.get("type")
    if search_type is None:
        estimate.warn(f"type is unset, so Exa runs '{DEFAULT_SEARCH_TYPE}' at ${SEARCH_TYPE_PRICE['auto']}. Send type 'lite' ($0.004) unless you need an auto-only parameter.")
        search_type = DEFAULT_SEARCH_TYPE
    if search_type not in SEARCH_TYPE_PRICE:
        estimate.warn(f"Unknown search type '{search_type}': not in this script's price table; check references/pricing.md.")
        return estimate
    if search_type in LEGACY_SEARCH_TYPES:
        estimate.warn(f"'{search_type}' is a legacy type; use '{LEGACY_SEARCH_TYPES[search_type]}' instead (fast costs $0.007 for the same search lite runs at $0.004).")

    contents = body.get("contents") if isinstance(body.get("contents"), dict) else {}
    if search_type == "lite":
        rejected = [key for key in LITE_REJECTED_TOP if is_set(body.get(key))]
        rejected += [f"contents.{key}" for key in LITE_REJECTED_CONTENTS if is_set(contents.get(key))]
        if rejected:
            estimate.block(f"type 'lite' returns 400 for {rejected}. Remove them or use type 'auto'.")

    count = requested_results(body, estimate)
    if channel != "api" and count > INCLUDED_RESULTS:
        estimate.note(f"x402/MPP silently clamps numResults to {INCLUDED_RESULTS}.")
        count = INCLUDED_RESULTS
    cost = SEARCH_TYPE_PRICE[search_type] + EXTRA_RESULT * max(0, count - INCLUDED_RESULTS)
    if count > INCLUDED_RESULTS:
        estimate.note(f"{count - INCLUDED_RESULTS} results above 10 add ${EXTRA_RESULT} each; Exa bills results returned, so this is the ceiling.")
    if is_set(contents.get("summary")):
        cost += SUMMARY_PER_PAGE * count
        estimate.note("contents.summary runs an LLM per result at $0.001 each and adds seconds of latency; highlights are free.")
    estimate.worst_case_usd = cost

    if not contents:
        estimate.note("No contents requested: results carry metadata only. contents.highlights is free and usually enough.")
    check_text_budget(contents.get("text"), estimate, "contents.")
    if is_set(contents.get("subpages")) and contents.get("subpages"):
        estimate.warn("subpages is deprecated on /search and its billing was not measured; send chosen URLs to /contents instead.")
    if contents.get("maxAgeHours") == 0 or contents.get("livecrawl") in ("always", "preferred"):
        estimate.note("Forcing a live fetch adds no charge but added ~9 s of latency live; only do it when freshness matters.")
    if is_set(body.get("additionalQueries")) and search_type not in DEEP_SEARCH_TYPES:
        estimate.note("additionalQueries only works with deep search types.")
    if is_set(body.get("outputSchema")) and search_type not in DEEP_SEARCH_TYPES:
        estimate.note("outputSchema on auto added no charge live (synthesis is included in the $0.007).")
    return estimate


def content_types(options: dict[str, Any]) -> list[str]:
    return [name for name in CONTENT_TYPES if is_set(options.get(name)) and options.get(name) is not False]


def estimate_contents(body: dict[str, Any]) -> Estimate:
    estimate = Estimate("contents")
    if isinstance(body.get("contents"), dict):
        estimate.block("/contents has no 'contents' wrapper: put text/highlights/summary at the top level next to urls.")
    urls = body.get("urls") or body.get("ids") or []
    if not isinstance(urls, list) or not urls:
        estimate.block("Provide a non-empty urls (or ids) list.")
        return estimate
    if len(urls) > MAX_CONTENTS_URLS:
        estimate.block(f"{len(urls)} URLs exceeds the {MAX_CONTENTS_URLS}-URL limit per request; split it.")
    types = content_types(body)
    if not types:
        estimate.warn("No content type set, so /contents returns full text (45 KB for one page live). Ask for highlights or text.maxCharacters.")
        types = ["text"]
    elif "text" in types:
        check_text_budget(body.get("text"), estimate, "")
    if len(types) > 1:
        estimate.note(f"/contents bills each content type separately: {types} costs {len(types)}x per page.")
    pages = len(urls)
    subpages = body.get("subpages") or 0
    if isinstance(subpages, int) and subpages > 0:
        pages *= 1 + subpages
        estimate.warn("subpages billing was not measured (live calls returned no subpages); priced as one extra page each, an inferred ceiling.")
    estimate.worst_case_usd = CONTENTS_PER_PAGE_PER_TYPE * pages * len(types)
    estimate.note("URLs that fail (404, DNS, malformed) were not billed live; this figure is the ceiling.")
    return estimate


def estimate_answer(body: dict[str, Any]) -> Estimate:
    estimate = Estimate("answer")
    estimate.worst_case_usd = ANSWER_PRICE
    if body.get("text") is True:
        estimate.warn("answer text: true returns every source's full text (278 KB live) at no extra charge. Leave it off.")
    if body.get("stream"):
        estimate.note("Streaming changes delivery only; the price is the same.")
    return estimate


def asks_for_contacts(body: dict[str, Any]) -> bool:
    blob = json.dumps({k: body.get(k) for k in ("query", "systemPrompt", "outputSchema", "input")})
    return bool(CONTACT_WORDS.search(blob))


def estimate_agent(body: dict[str, Any], effort_field: str = "effort") -> Estimate:
    estimate = Estimate("agent")
    effort = body.get("effort") if effort_field == "effort" else (body.get("reasoning") or {}).get("effort")
    if effort is None:
        estimate.warn(f"effort is unset, so the run is metered '{DEFAULT_AGENT_EFFORT}' with a $5 cap. Send a fixed effort ('minimal' $0.012, 'low' $0.025) when the scope is known.")
        effort = DEFAULT_AGENT_EFFORT
    budget = body.get("budget") or {}
    cap = budget.get("maxCostDollars")
    if effort in AGENT_FIXED_EFFORT:
        if cap is not None:
            estimate.block("budget.maxCostDollars is rejected (400) on fixed efforts; remove it or use effort 'auto'.")
        estimate.worst_case_usd = AGENT_FIXED_EFFORT[effort]
        if effort in ("high", "xhigh"):
            estimate.warn(f"effort '{effort}' is ${AGENT_FIXED_EFFORT[effort]:.2f} a run; confirm with the user and try 'medium' or lower first.")
    elif effort in AGENT_METERED_DEFAULT_CAP:
        if effort_field != "effort":
            estimate.warn("/responses has no budget field, so the default cap applies. Use /agent/runs with budget.maxCostDollars instead.")
            cap = None
        if cap is None:
            cap = AGENT_METERED_DEFAULT_CAP[effort]
            if effort_field == "effort":
                estimate.warn(f"No budget.maxCostDollars: '{effort}' can spend up to the ${cap:.0f} default. Set it (minimum $1).")
        elif not isinstance(cap, (int, float)) or not AGENT_BUDGET_RANGE[0] <= cap <= AGENT_BUDGET_RANGE[1]:
            estimate.block("budget.maxCostDollars must be from 1 to 100.")
        estimate.worst_case_usd = float(cap)
        estimate.note("Metered runs bill the cap if they reach it; trivial auto runs cost $0.02-0.03 live, list-building ~$0.67.")
        if effort == "ultra":
            estimate.warn("ultra is for exhaustive list building (default cap $20); confirm with the user. Only ultra supports /stop.")
    else:
        estimate.warn(f"Unknown effort '{effort}'; check references/pricing.md.")
        return estimate
    if body.get("dataSources"):
        estimate.warn("Exa Connect dataSources bill per provider call on top of the run (Similarweb $0.30/credit, Baselayer up to $4/order) and may sit outside the cap.")
        estimate.worst_case_usd = None
    if asks_for_contacts(body):
        estimate.warn("Contact enrichment bills $0.02 per email and $0.07 per phone found, on top of fixed-effort prices.")
    return estimate


def period_hours(period: Any) -> float | None:
    match = re.fullmatch(r"(\d+)([hdw])", str(period or ""))
    return None if not match else int(match.group(1)) * PERIOD_HOURS[match.group(2)]


def estimate_monitor(body: dict[str, Any]) -> Estimate:
    estimate = Estimate("monitors")
    search = body.get("search") or {}
    if not body.get("webhook"):
        estimate.block("Monitors require a public HTTPS webhook (create returns 400 without one).")
    count = requested_results(search, estimate)
    per_run = MONITOR_RUN + EXTRA_RESULT * max(0, count - INCLUDED_RESULTS)
    if is_set((search.get("contents") or {}).get("summary")):
        per_run += SUMMARY_PER_PAGE * count
    estimate.worst_case_usd = per_run
    trigger = body.get("trigger")
    if not trigger:
        estimate.note("No trigger: a manual-only monitor; it did not run at creation live. Each /trigger is a paid run.")
        estimate.monthly_usd = 0.0
    else:
        hours = period_hours(trigger.get("period"))
        if hours is None:
            estimate.warn(f"Cannot parse trigger.period {trigger.get('period')!r}; use a single unit such as '1d'.")
        elif hours < 1:
            estimate.block("trigger.period minimum is 1h.")
        else:
            estimate.monthly_usd = per_run * DAYS_PER_MONTH * 24 / hours
            if hours < 24:
                estimate.warn(f"Every {trigger['period']} is ${estimate.monthly_usd:.2f} a month per monitor; daily is ${per_run * DAYS_PER_MONTH:.2f}.")
    estimate.warn("Monitors bill every run until paused or deleted, and run objects report no cost. Agree a delete date with the user before creating one.")
    return estimate


def estimate_batch(body: dict[str, Any], channel: str) -> Estimate:
    estimate = Estimate("batches")
    estimate.note("The Batch API is Enterprise-only (403 FEATURE_DISABLED otherwise) and has no documented discount.")
    total: float | None = 0.0
    for item in body.get("requests") or []:
        url = str(item.get("url", "")).strip("/")
        sub = estimate_request(url, item.get("body") or {}, channel)
        for level, message in sub.findings:
            estimate.findings.append((level, f"[{item.get('customId', url)}] {message}"))
        total = None if total is None or sub.worst_case_usd is None else total + sub.worst_case_usd
    estimate.worst_case_usd = total
    return estimate


def normalise(endpoint: str) -> str:
    """Strip slashes and replace concrete IDs (agent_run_7be6..., 01m5xr...) with {id}."""
    segments = endpoint.strip().strip("/").split("/")
    return "/".join("{id}" if len(s) >= 10 and re.search(r"\d", s) else s for s in segments)


def estimate_request(endpoint: str, body: dict[str, Any], channel: str = "api") -> Estimate:
    path = normalise(endpoint)
    routes = {
        "search": lambda: estimate_search(body, channel),
        "contents": lambda: estimate_contents(body),
        "answer": lambda: estimate_answer(body),
        "chat/completions": lambda: estimate_answer(body),
        "agent/runs": lambda: estimate_agent(body),
        "responses": lambda: estimate_agent(body, effort_field="reasoning.effort"),
        "monitors": lambda: estimate_monitor(body),
        "batches": lambda: estimate_batch(body, channel),
    }
    if path in routes:
        return routes[path]()
    estimate = Estimate(path)
    if path.endswith("/trigger"):
        estimate.worst_case_usd = MONITOR_RUN
        estimate.note("A manual monitor trigger is one paid run.")
    elif path.endswith(("/cancel", "/stop")) or re.fullmatch(r"(agent/runs|monitors|batches)(/\{id\}(/runs|/events)?)?", path):
        estimate.worst_case_usd = 0.0
        estimate.note("Status, list, cancel, and stop calls carry no charge; polling does not count against QPS.")
    elif path.startswith("websets"):
        estimate.warn("Websets uses separate plan credits with no public per-credit price. Prefer Agent for list building.")
    else:
        estimate.warn(f"No price model for '{endpoint}'. Read references/pricing.md before sending it.")
    return estimate


def apply_budget(estimate: Estimate, budget: float | None) -> None:
    if budget is None:
        return
    if estimate.worst_case_usd is None:
        estimate.block(f"Worst case is unknown, so it cannot be proven under the ${budget} budget.")
    elif estimate.worst_case_usd > budget + 1e-12:
        estimate.block(f"Worst case ${estimate.worst_case_usd:.4f} exceeds the ${budget} budget.")


def load_body(source: str) -> dict[str, Any]:
    raw = sys.stdin.read() if source == "-" else open(source, encoding="utf-8").read()
    body = json.loads(raw or "{}")
    if not isinstance(body, dict):
        raise SystemExit("The request body must be a JSON object.")
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    est = commands.add_parser("estimate", help="Offline worst-case USD estimate and default check")
    est.add_argument("endpoint", help="search, contents, answer, agent/runs, responses, monitors, batches, or a status path")
    est.add_argument("body", help="Path to the JSON request body, or - for stdin")
    est.add_argument("--budget-usd", type=float, help="Block when the worst case exceeds this many dollars")
    est.add_argument("--channel", choices=("api", "x402"), default="api", help="x402/MPP keyless payments clamp numResults to 10")
    args = parser.parse_args(argv)
    estimate = estimate_request(args.endpoint, load_body(args.body), args.channel)
    apply_budget(estimate, args.budget_usd)
    print(json.dumps(estimate.as_json(), indent=2))
    return estimate.exit_code


if __name__ == "__main__":
    sys.exit(main())

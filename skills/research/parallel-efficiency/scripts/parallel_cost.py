#!/usr/bin/env python3
"""Price a Parallel (parallel.ai) API request before sending it, and flag expensive defaults.

    parallel_cost.py estimate search request.json
    echo '{"processor": "ultra", "input": "..."}' | parallel_cost.py estimate tasks/runs - --budget-usd 0.05
    parallel_cost.py estimate findall/runs/ID/enrich body.json --matches 40

Offline only. Prints a JSON verdict with a worst-case USD figure and exits 0 (ok),
2 (warnings: read them), or 3 (blocked: do not send). Prices are the 2026-10-18 snapshot
of https://docs.parallel.ai/getting-started/pricing documented in references/pricing.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# USD per request/run/URL/check unless noted.
SEARCH_MODE_PRICE = {"turbo": 0.001, "fast": 0.001, "basic": 0.005, "advanced": 0.005}
IMAGE_SEARCH_MODE_PRICE = {"fast": 0.001, "advanced": 0.005}
EXTRA_SEARCH_RESULT = 0.001
EXTRACT_PER_URL = 0.001
TASK_PROCESSOR_PRICE = {
    "lite": 0.005, "base": 0.010, "core": 0.025, "core2x": 0.050, "pro": 0.100,
    "ultra": 0.300, "ultra2x": 0.600, "ultra4x": 1.200, "ultra8x": 2.400,
}
RESPONSES_EFFORT_PRICE = {"low": 0.010, "medium": 0.050, "high": 0.250}
FINDALL_GENERATOR = {  # (fixed, per match)
    "preview": (0.10, 0.0), "base": (0.25, 0.03), "core": (2.00, 0.15), "pro": (10.00, 1.00),
}
ENTITY_SEARCH_REQUEST, ENTITY_SEARCH_EXTRA_RESULT = 0.005, 0.00005
MONITOR_PROCESSOR_PRICE = {"lite": 0.003, "base": 0.010}
FREQUENCY_SECONDS = {"h": 3600, "d": 86400, "w": 604800}
DAYS_PER_MONTH = 30
EXPENSIVE_TASK_PROCESSORS = {"pro", "ultra", "ultra2x", "ultra4x", "ultra8x"}


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
        return {
            "api": self.api,
            "verdict": {0: "ok", 2: "warn", 3: "blocked"}[self.exit_code],
            "worst_case_usd": None if self.worst_case_usd is None else round(self.worst_case_usd, 6),
            "monthly_usd": None if self.monthly_usd is None else round(self.monthly_usd, 4),
            "findings": [{"level": level.value, "message": message} for level, message in self.findings],
        }


def normalise(endpoint: str) -> str:
    path = endpoint.strip().strip("/")
    path = re.sub(r"^(v1beta|v1alpha|v1)/", "", path)
    # Resource IDs (trun_..., tgrp_..., or a placeholder such as ID) contain a digit or are a placeholder;
    # API words such as "search" or "entity-search" never do.
    segments = ["{id}" if s in ("ID", "{id}", ":id") or re.search(r"\d", s) else s for s in path.split("/")]
    return "/".join(segments)


def advanced(body: dict[str, Any]) -> dict[str, Any]:
    value = body.get("advanced_settings")
    return value if isinstance(value, dict) else {}


def estimate_search(body: dict[str, Any], image: bool) -> Estimate:
    prices = IMAGE_SEARCH_MODE_PRICE if image else SEARCH_MODE_PRICE
    estimate = Estimate("image-search" if image else "search")
    mode = body.get("mode")
    if mode is None:
        estimate.warn("mode is unset, so Parallel uses 'advanced' at $5/1K. Set mode: 'fast' ($1/1K) unless multi-hop quality is needed.")
        mode = "advanced"
    if mode not in prices:
        estimate.block(f"Unknown mode {mode!r}; valid: {sorted(prices)}.")
        return estimate
    price = prices[mode]
    if not image:
        results = advanced(body).get("max_results", body.get("max_results", 10))
        results = min(int(results), 20)
        extra = max(0, results - 10)
        price += extra * EXTRA_SEARCH_RESULT
        if extra:
            estimate.note(f"{extra} results beyond the included 10 add ${extra * EXTRA_SEARCH_RESULT:.3f}.")
        if (advanced(body).get("fetch_policy") or {}).get("max_age_seconds") is not None:
            estimate.note("fetch_policy forces live fetches: slower, and its pricing effect is undocumented.")
        if mode == "turbo":
            estimate.note("turbo supports English and Japanese queries only, and no path prefixes.")
    queries = body.get("search_queries") or []
    if len(queries) > 5:
        estimate.note("search_queries are bundled into one request, so many queries do not multiply cost; keep each to 3-6 words.")
    estimate.worst_case_usd = price
    return estimate


def estimate_extract(body: dict[str, Any]) -> Estimate:
    estimate = Estimate("extract")
    urls = body.get("urls") or []
    if len(urls) > 20:
        estimate.block(f"{len(urls)} URLs: Extract accepts at most 20 per request.")
    estimate.worst_case_usd = EXTRACT_PER_URL * len(urls)
    if advanced(body).get("full_content") or body.get("full_content"):
        estimate.warn("full_content returns whole pages (tens of thousands of tokens each). Prefer excerpts with an objective.")
    if not body.get("objective") and not body.get("search_queries"):
        estimate.warn("Without objective or search_queries, Extract returns whole-page markdown including boilerplate.")
    for key in ("excerpts", "full_content", "fetch_policy"):
        if key in body:
            estimate.block(f"Top-level '{key}' is the v1beta shape; /v1/extract returns 422. Move it into advanced_settings.")
    return estimate


def estimate_task(body: dict[str, Any], runs: int) -> Estimate:
    estimate = Estimate("task" if runs == 1 else "task-group")
    processor = body.get("processor") or (body.get("default_task_spec") or {}).get("processor")
    if processor is None:
        estimate.block("processor is required; pick the cheapest that fits (lite <=2 fields, base <=5, core <=10).")
        return estimate
    if processor.endswith("-fast"):
        estimate.warn(f"'{processor}' is not in the current processor list; it may be rejected.")
        processor = processor.removesuffix("-fast")
    if processor not in TASK_PROCESSOR_PRICE:
        estimate.block(f"Unknown processor {processor!r}.")
        return estimate
    estimate.worst_case_usd = TASK_PROCESSOR_PRICE[processor] * runs
    if processor in EXPENSIVE_TASK_PROCESSORS:
        estimate.warn(f"{processor} costs ${TASK_PROCESSOR_PRICE[processor] * 1000:,.0f}/1K runs and Task runs cannot be cancelled. Confirm the depth is needed; try core or base first.")
    if runs > 1:
        estimate.note(f"{runs} runs; Task Groups check balance for the whole batch up front.")
    if body.get("task_spec") is None and processor in EXPENSIVE_TASK_PROCESSORS:
        estimate.note("No task_spec: pro/ultra default to auto schema (deep research output).")
    sources = advanced(body).get("data_sources") or {}
    if sources.get("pay_per_use"):
        estimate.warn("pay_per_use data connectors bill per successful tool call on top of the processor price.")
    return estimate


def estimate_responses(body: dict[str, Any]) -> Estimate:
    estimate = Estimate("responses")
    effort = (body.get("reasoning") or {}).get("effort")
    if effort is None:
        estimate.warn("reasoning.effort is unset, so it defaults to 'medium' at $50/1K. Use 'low' ($10/1K) for fact lookups.")
        effort = "medium"
    if effort not in RESPONSES_EFFORT_PRICE:
        estimate.block(f"Unknown effort {effort!r}.")
        return estimate
    estimate.worst_case_usd = RESPONSES_EFFORT_PRICE[effort]
    if body.get("previous_response_id"):
        estimate.note("Each follow-up is billed as a new request; use low effort for follow-ups.")
    return estimate


def estimate_findall(body: dict[str, Any]) -> Estimate:
    estimate = Estimate("findall")
    generator = body.get("generator")
    limit = body.get("match_limit")
    if generator not in FINDALL_GENERATOR:
        estimate.block(f"generator must be one of {sorted(FINDALL_GENERATOR)}.")
        return estimate
    if not isinstance(limit, int):
        estimate.block("match_limit is required and bounds the per-match charge.")
        return estimate
    fixed, per_match = FINDALL_GENERATOR[generator]
    estimate.worst_case_usd = fixed + per_match * limit
    if generator != "preview":
        estimate.warn("Run generator 'preview' ($0.10, ~10 candidates) first to check the query, then a small match_limit and /extend.")
    if generator == "pro":
        estimate.warn("pro bills $1 per match.")
    estimate.note("Enrichments are billed separately: Task processor price x matches (enrich defaults to core).")
    return estimate


def estimate_enrich(body: dict[str, Any], matches: int | None) -> Estimate:
    estimate = Estimate("findall-enrich")
    processor = body.get("processor")
    if processor is None:
        estimate.warn("processor is unset, so enrich uses 'core' ($25/1K matches). Use lite or base for 1-5 simple fields.")
        processor = "core"
    if processor not in TASK_PROCESSOR_PRICE:
        estimate.block(f"Unknown processor {processor!r}.")
        return estimate
    if matches is None:
        estimate.block("Pass --matches N (the run's match count) so the per-match enrichment cost is bounded.")
        return estimate
    estimate.worst_case_usd = TASK_PROCESSOR_PRICE[processor] * matches
    estimate.note("Adding an enrichment to a finished run requeues it.")
    return estimate


def estimate_entity_search(body: dict[str, Any]) -> Estimate:
    estimate = Estimate("entity-search")
    limit = body.get("match_limit", 100)
    estimate.worst_case_usd = ENTITY_SEARCH_REQUEST + ENTITY_SEARCH_EXTRA_RESULT * max(0, int(limit) - 100)
    return estimate


def frequency_seconds(text: str) -> int | None:
    match = re.fullmatch(r"(\d+)([hdw])", text.strip())
    return int(match.group(1)) * FREQUENCY_SECONDS[match.group(2)] if match else None


def estimate_monitor(body: dict[str, Any]) -> Estimate:
    estimate = Estimate("monitor")
    processor = body.get("processor", "lite")
    seconds = frequency_seconds(str(body.get("frequency", "")))
    if seconds is None:
        estimate.block("frequency must look like 1h, 6h, 1d, or 1w.")
        return estimate
    if processor not in MONITOR_PROCESSOR_PRICE:
        estimate.warn(f"Monitor processor {processor!r} has no published price; assuming base.")
        processor = "base"
    per_check = MONITOR_PROCESSOR_PRICE[processor]
    checks = DAYS_PER_MONTH * 86400 / seconds
    estimate.worst_case_usd = per_check  # the immediate first run
    estimate.monthly_usd = per_check * checks
    estimate.warn(f"Bills every check whether or not anything changed: ~{checks:.0f} checks/month, ~${estimate.monthly_usd:.2f}/month until cancelled.")
    if seconds < 86400:
        estimate.note("Sub-daily checks are rarely needed; '1d' suits most news, '1w' slow pages.")
    if body.get("type") == "snapshot":
        estimate.note("Snapshot monitors also need the initial Task run, billed at its processor price.")
    return estimate


def estimate_request(endpoint: str, body: dict[str, Any], matches: int | None) -> Estimate:
    path = normalise(endpoint)
    if path.startswith("service") or "balance/add" in path:
        estimate = Estimate(path)
        if "add" in path:
            estimate.block("balance/add charges the organisation's card. Never call it; ask the user to top up.")
        else:
            estimate.note("Account balance read (OAuth account token, not an API key).")
            estimate.worst_case_usd = 0.0
        return estimate
    routes = {
        "search": lambda: estimate_search(body, image=False),
        "images/search": lambda: estimate_search(body, image=True),
        "extract": lambda: estimate_extract(body),
        "tasks/runs": lambda: estimate_task(body, 1),
        "tasks/groups/{id}/runs": lambda: estimate_task(body, len(body.get("inputs") or [])),
        "responses": lambda: estimate_responses(body),
        "findall/runs": lambda: estimate_findall(body),
        "findall/runs/{id}/enrich": lambda: estimate_enrich(body, matches),
        "findall/entity-search": lambda: estimate_entity_search(body),
        "monitors": lambda: estimate_monitor(body),
    }
    if path in routes:
        return routes[path]()
    if path in ("findall/runs/{id}/extend",):
        estimate = Estimate("findall-extend")
        estimate.note("Extend has no fixed fee; new matches bill at the run's per-match rate (bound it with additional_match_limit).")
        return estimate
    if path.startswith("monitors/{id}/trigger"):
        estimate = Estimate("monitor-trigger")
        estimate.note("A manual trigger is a billed execution at the monitor's processor price.")
        return estimate
    estimate = Estimate(path)
    if path.startswith("chat"):
        estimate.warn("The Chat API is not on the current pricing page. Prefer Search, or Responses with low effort.")
    elif re.search(r"(^|/)(runs|groups|monitors)(/\{id\})?(/(result|events|input|runs))?$", path) or path.endswith("/cancel"):
        estimate.note("Status, results, events, and cancel calls carry no documented charge.")
        estimate.worst_case_usd = 0.0
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
    est.add_argument("endpoint", help="API path such as search, extract, tasks/runs, tasks/groups/ID/runs, responses, findall/runs, monitors")
    est.add_argument("body", help="Path to the JSON request body, or - for stdin")
    est.add_argument("--budget-usd", type=float, help="Block when the worst case exceeds this many dollars")
    est.add_argument("--matches", type=int, help="Match count, required to price a FindAll enrichment")
    args = parser.parse_args(argv)
    estimate = estimate_request(args.endpoint, load_body(args.body), args.matches)
    apply_budget(estimate, args.budget_usd)
    print(json.dumps(estimate.as_json(), indent=2))
    return estimate.exit_code


if __name__ == "__main__":
    sys.exit(main())

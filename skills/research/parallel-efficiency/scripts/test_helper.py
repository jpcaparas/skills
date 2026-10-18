#!/usr/bin/env python3
"""Offline tests for parallel_cost.py.

Expected dollar figures are computed by hand from https://docs.parallel.ai/getting-started/pricing
(2026-10-18), not from the script, so a pricing or default-handling regression fails here.
Nothing here touches the network.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).with_name("parallel_cost.py")
spec = importlib.util.spec_from_file_location("parallel_cost", SCRIPT)
cost = importlib.util.module_from_spec(spec)
sys.modules["parallel_cost"] = cost
spec.loader.exec_module(cost)


def run(endpoint: str, body: dict, *extra: str) -> tuple[int, dict]:
    out = io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(json.dumps(body))), contextlib.redirect_stdout(out):
        code = cost.main(["estimate", endpoint, "-", *extra])
    return code, json.loads(out.getvalue())


class SearchAndExtract(unittest.TestCase):
    def test_unset_mode_is_priced_as_advanced_and_warns(self) -> None:
        code, verdict = run("/v1/search", {"objective": "x", "search_queries": ["a b c"]})
        self.assertEqual((code, verdict["worst_case_usd"]), (2, 0.005))

    def test_fast_mode_is_a_fifth_of_the_default(self) -> None:
        code, verdict = run("search", {"mode": "fast", "search_queries": ["a b c"]})
        self.assertEqual((code, verdict["worst_case_usd"]), (0, 0.001))

    def test_results_beyond_ten_cost_extra_and_cap_at_twenty(self) -> None:
        _, fifteen = run("search", {"mode": "fast", "advanced_settings": {"max_results": 15}})
        _, fifty = run("search", {"mode": "fast", "advanced_settings": {"max_results": 50}})
        self.assertEqual((fifteen["worst_case_usd"], fifty["worst_case_usd"]), (0.006, 0.011))

    def test_image_search_also_defaults_to_advanced(self) -> None:
        code, verdict = run("v1/images/search", {"search_queries": ["red panda"]})
        self.assertEqual((code, verdict["worst_case_usd"]), (2, 0.005))

    def test_extract_bills_per_url_and_rejects_oversized_or_v1beta_bodies(self) -> None:
        _, three = run("extract", {"urls": ["https://a.test/1", "https://a.test/2", "https://a.test/3"], "objective": "pricing"})
        self.assertEqual(three["worst_case_usd"], 0.003)
        code, _ = run("extract", {"urls": [f"https://a.test/{i}" for i in range(21)], "objective": "x"})
        self.assertEqual(code, 3)
        code, _ = run("extract", {"urls": ["https://a.test/"], "objective": "x", "full_content": True})
        self.assertEqual(code, 3, "top-level full_content is the v1beta shape and returns 422 on /v1/extract")


class TasksAndResponses(unittest.TestCase):
    def test_processor_prices_span_lite_to_ultra8x(self) -> None:
        code, lite = run("tasks/runs", {"processor": "lite", "input": "x"})
        code_u, ultra = run("tasks/runs", {"processor": "ultra8x", "input": "x"})
        self.assertEqual((code, lite["worst_case_usd"]), (0, 0.005))
        self.assertEqual((code_u, ultra["worst_case_usd"]), (2, 2.4))

    def test_missing_or_unknown_processor_is_blocked(self) -> None:
        self.assertEqual(run("tasks/runs", {"input": "x"})[0], 3)
        self.assertEqual(run("tasks/runs", {"processor": "turbo", "input": "x"})[0], 3)

    def test_task_group_multiplies_by_inputs_and_resolves_ids(self) -> None:
        body = {"default_task_spec": {"processor": "core"}, "inputs": [{"input": str(i)} for i in range(1000)]}
        _, verdict = run("/v1beta/tasks/groups/tgrp_8f3a2c91/runs", body)
        self.assertEqual(verdict["api"], "task-group")
        self.assertAlmostEqual(verdict["worst_case_usd"], 25.0)

    def test_responses_default_effort_is_medium(self) -> None:
        code, default = run("responses", {"model": "parallel", "input": "q"})
        _, low = run("responses", {"model": "parallel", "input": "q", "reasoning": {"effort": "low"}})
        self.assertEqual((code, default["worst_case_usd"], low["worst_case_usd"]), (2, 0.05, 0.01))


class FindAllEntityMonitor(unittest.TestCase):
    def test_findall_is_fixed_plus_per_match_at_the_limit(self) -> None:
        _, core = run("findall/runs", {"generator": "core", "match_limit": 100, "objective": "x"})
        _, pro = run("findall/runs", {"generator": "pro", "match_limit": 1000, "objective": "x"})
        code, preview = run("findall/runs", {"generator": "preview", "match_limit": 10, "objective": "x"})
        self.assertAlmostEqual(core["worst_case_usd"], 17.0)
        self.assertAlmostEqual(pro["worst_case_usd"], 1010.0)
        self.assertEqual((code, preview["worst_case_usd"]), (0, 0.1))

    def test_findall_without_match_limit_is_blocked(self) -> None:
        self.assertEqual(run("findall/runs", {"generator": "base", "objective": "x"})[0], 3)

    def test_enrichment_defaults_to_core_and_needs_a_match_count(self) -> None:
        code, verdict = run("findall/runs/findall_9a1b2c/enrich", {"output_schema": {}}, "--matches", "40")
        self.assertEqual((code, verdict["worst_case_usd"]), (2, 1.0))
        self.assertEqual(run("findall/runs/findall_9a1b2c/enrich", {"output_schema": {}})[0], 3)

    def test_entity_search_extra_results(self) -> None:
        _, default = run("v1beta/findall/entity-search", {"entity_type": "companies", "objective": "x"})
        _, maximum = run("findall/entity-search", {"entity_type": "companies", "objective": "x", "match_limit": 1000})
        self.assertEqual((default["worst_case_usd"], maximum["worst_case_usd"]), (0.005, 0.05))

    def test_monitor_monthly_cost_follows_frequency_and_processor(self) -> None:
        code, hourly = run("v1/monitors", {"type": "event_stream", "frequency": "1h", "settings": {"query": "x"}})
        _, daily_base = run("monitors", {"frequency": "1d", "processor": "base"})
        self.assertEqual(code, 2, "every monitor warns that it bills until cancelled")
        self.assertAlmostEqual(hourly["monthly_usd"], 2.16)
        self.assertAlmostEqual(daily_base["monthly_usd"], 0.30)
        self.assertEqual(run("monitors", {"frequency": "hourly"})[0], 3)


class AccountAndBudget(unittest.TestCase):
    def test_balance_add_is_blocked_but_balance_read_is_free(self) -> None:
        self.assertEqual(run("service/v1/balance/add", {"amount_cents": 1000})[0], 3)
        code, read = run("service/v1/balance", {})
        self.assertEqual((code, read["worst_case_usd"]), (0, 0.0))

    def test_status_and_cancel_calls_are_free(self) -> None:
        for path in ("tasks/runs/trun_ab12cd/result", "findall/runs/findall_77aa/cancel", "monitors/mon_123abc"):
            code, verdict = run(path, {})
            self.assertEqual((code, verdict["worst_case_usd"]), (0, 0.0), path)

    def test_budget_blocks_only_when_the_worst_case_exceeds_it(self) -> None:
        body = {"processor": "pro", "input": "x"}
        self.assertEqual(run("tasks/runs", body, "--budget-usd", "0.05")[0], 3)
        self.assertEqual(run("tasks/runs", body, "--budget-usd", "0.10")[0], 2)
        self.assertEqual(run("chat/completions", {"model": "speed"}, "--budget-usd", "1")[0], 3, "unpriced calls cannot be proven under a budget")


if __name__ == "__main__":
    unittest.main()

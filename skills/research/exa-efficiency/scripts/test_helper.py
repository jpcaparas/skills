#!/usr/bin/env python3
"""Offline tests for exa_cost.py.

Expected dollar figures are the costDollars.total values Exa returned for the same
request bodies in the 2026-10-27 live spike (references/evidence.md), not values read
back from the script, so a pricing or default-handling regression fails here.
Nothing here touches the network or reads EXA_API_KEY.
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

SCRIPT = Path(__file__).with_name("exa_cost.py")
spec = importlib.util.spec_from_file_location("exa_cost", SCRIPT)
cost = importlib.util.module_from_spec(spec)
sys.modules["exa_cost"] = cost
spec.loader.exec_module(cost)

QUERY = "postgres 18 release notes logical replication"
PAGE = "https://www.postgresql.org/docs/release/18.0/"


def run(endpoint: str, body: dict, *extra: str) -> tuple[int, dict]:
    out = io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(json.dumps(body))), contextlib.redirect_stdout(out):
        code = cost.main(["estimate", endpoint, "-", *extra])
    return code, json.loads(out.getvalue())


def messages(verdict: dict) -> str:
    return " ".join(f["message"] for f in verdict["findings"])


class LiveBilledSearch(unittest.TestCase):
    """Each case is a request sent in the spike and the costDollars.total it returned."""

    def assert_billed(self, body: dict, billed: float, endpoint: str = "search") -> dict:
        _, verdict = run(endpoint, body)
        self.assertAlmostEqual(verdict["worst_case_usd"], billed, places=6, msg=verdict)
        return verdict

    def test_unset_type_is_billed_as_auto_and_warns(self) -> None:
        code, verdict = run("search", {"query": QUERY})
        self.assertEqual((code, verdict["worst_case_usd"]), (2, 0.007))
        self.assertIn("lite", messages(verdict))

    def test_lite_is_cheaper_and_highlights_or_bounded_text_are_free(self) -> None:
        self.assert_billed({"query": QUERY, "type": "lite"}, 0.004)
        self.assert_billed({"query": QUERY, "type": "lite", "contents": {"highlights": True}}, 0.004)
        self.assert_billed({"query": QUERY, "type": "lite", "numResults": 5,
                            "contents": {"text": {"maxCharacters": 1000}, "highlights": True}}, 0.004)

    def test_fewer_than_ten_results_cost_the_full_base_price(self) -> None:
        self.assert_billed({"query": QUERY, "type": "lite", "numResults": 5}, 0.004)

    def test_each_result_above_ten_adds_a_tenth_of_a_cent(self) -> None:
        self.assert_billed({"query": QUERY, "type": "lite", "numResults": 11}, 0.005)
        self.assert_billed({"query": QUERY, "type": "lite", "numResults": 20}, 0.014)
        self.assert_billed({"query": QUERY, "type": "lite", "numResults": 100}, 0.094)
        self.assert_billed({"query": QUERY, "type": "auto", "numResults": 25}, 0.022)
        self.assert_billed({"query": QUERY, "type": "auto", "numResults": 50,
                            "contents": {"highlights": {"maxCharacters": 300}}}, 0.047)

    def test_summaries_bill_per_result_on_top_of_extra_results(self) -> None:
        self.assert_billed({"query": QUERY, "type": "auto", "numResults": 5, "contents": {"summary": True}}, 0.012)
        self.assert_billed({"query": QUERY, "type": "auto", "numResults": 15, "contents": {"summary": True}}, 0.027)

    def test_deep_types_and_free_add_ons(self) -> None:
        self.assert_billed({"query": QUERY, "type": "deep-lite"}, 0.012)
        self.assert_billed({"query": QUERY, "type": "deep", "additionalQueries": ["a", "b", "c"]}, 0.012)
        self.assert_billed({"query": QUERY, "type": "deep-reasoning"}, 0.015)
        self.assert_billed({"query": QUERY, "type": "auto", "outputSchema": {"type": "text"}}, 0.007)
        self.assert_billed({"query": QUERY, "type": "auto", "numResults": 3,
                            "contents": {"text": {"maxCharacters": 500}, "maxAgeHours": 0}}, 0.007)

    def test_legacy_fast_costs_auto_price_and_points_to_lite(self) -> None:
        code, verdict = run("search", {"query": QUERY, "type": "fast"})
        self.assertEqual((code, verdict["worst_case_usd"]), (2, 0.007))
        self.assertIn("'lite'", messages(verdict))
        self.assert_billed({"query": QUERY, "type": "instant"}, 0.004)

    def test_category_searches_bill_at_the_type_price(self) -> None:
        self.assert_billed({"query": "dev tools startups in Auckland", "type": "lite", "category": "company"}, 0.004)
        self.assert_billed({"query": "SREs in Wellington", "type": "lite", "category": "people", "numResults": 30}, 0.024)


class LiveBilledOtherEndpoints(unittest.TestCase):
    def test_contents_bills_each_content_type_per_page(self) -> None:
        _, one = run("contents", {"urls": [PAGE], "highlights": True})
        _, two = run("contents", {"urls": [PAGE], "text": {"maxCharacters": 3000}, "highlights": True})
        _, three = run("contents", {"urls": [PAGE], "text": {"maxCharacters": 2000}, "highlights": True, "summary": True})
        self.assertEqual([v["worst_case_usd"] for v in (one, two, three)], [0.001, 0.002, 0.003])

    def test_contents_without_options_defaults_to_full_text_and_warns(self) -> None:
        code, verdict = run("contents", {"urls": [PAGE]})
        self.assertEqual((code, verdict["worst_case_usd"]), (2, 0.001))
        self.assertIn("full text", messages(verdict))

    def test_contents_wrapper_on_contents_endpoint_is_blocked(self) -> None:
        code, _ = run("contents", {"urls": [PAGE], "contents": {"highlights": True}})
        self.assertEqual(code, 3)

    def test_answer_is_flat_for_every_model_but_text_true_warns(self) -> None:
        for model in ("exa", "exa-pro", "exa-research", "exa-fast"):
            code, verdict = run("answer", {"query": "q", "model": model})
            self.assertEqual((code, verdict["worst_case_usd"]), (0, 0.005), model)
        code, _ = run("answer", {"query": "q", "text": True})
        self.assertEqual(code, 2)

    def test_agent_fixed_efforts_bill_their_flat_price(self) -> None:
        for effort, billed in (("minimal", 0.012), ("low", 0.025)):
            code, verdict = run("agent/runs", {"query": "Which Postgres version added pg_stat_io?", "effort": effort})
            self.assertEqual((code, verdict["worst_case_usd"]), (0, billed), effort)

    def test_agent_default_effort_is_metered_with_a_five_dollar_ceiling(self) -> None:
        code, verdict = run("agent/runs", {"query": "q"})
        self.assertEqual((code, verdict["worst_case_usd"]), (2, 5.0))
        code, verdict = run("agent/runs", {"query": "q", "effort": "auto", "budget": {"maxCostDollars": 1}})
        self.assertEqual((code, verdict["worst_case_usd"]), (0, 1.0))
        _, ultra = run("agent/runs", {"query": "q", "effort": "ultra"})
        self.assertEqual(ultra["worst_case_usd"], 20.0)

    def test_budget_on_a_fixed_effort_is_blocked_because_exa_returns_400(self) -> None:
        code, _ = run("agent/runs", {"query": "q", "effort": "low", "budget": {"maxCostDollars": 1}})
        self.assertEqual(code, 3)

    def test_agent_budget_outside_one_to_one_hundred_is_blocked(self) -> None:
        for cap in (0.5, 101):
            code, _ = run("agent/runs", {"query": "q", "effort": "auto", "budget": {"maxCostDollars": cap}})
            self.assertEqual(code, 3, cap)


class Guards(unittest.TestCase):
    def test_lite_rejected_parameters_block_including_false_and_empty_values(self) -> None:
        for body in ({"contents": {"summary": True}}, {"contents": {"maxAgeHours": -1}},
                     {"outputSchema": {"type": "text"}}, {"additionalQueries": []}, {"contents": {"extras": {"links": 0}}}):
            code, _ = run("search", {"query": QUERY, "type": "lite", **body})
            self.assertEqual(code, 3, body)
        code, _ = run("search", {"query": QUERY, "type": "lite", "outputSchema": None, "contents": {"highlights": True}})
        self.assertEqual(code, 0, "null counts as unset")

    def test_unbounded_text_warns_but_bounded_text_does_not(self) -> None:
        code, _ = run("search", {"query": QUERY, "type": "lite", "contents": {"text": True}})
        self.assertEqual(code, 2)
        code, _ = run("search", {"query": QUERY, "type": "lite", "contents": {"text": {"maxCharacters": 2000}}})
        self.assertEqual(code, 0)

    def test_num_results_above_public_limit_is_blocked(self) -> None:
        code, _ = run("search", {"query": QUERY, "type": "lite", "numResults": 101})
        self.assertEqual(code, 3)

    def test_x402_channel_clamps_results_to_ten(self) -> None:
        _, verdict = run("search", {"query": QUERY, "type": "lite", "numResults": 50}, "--channel", "x402")
        self.assertEqual(verdict["worst_case_usd"], 0.004)

    def test_budget_blocks_over_limit_and_unknown_worst_cases(self) -> None:
        code, _ = run("search", {"query": QUERY, "type": "lite", "numResults": 20}, "--budget-usd", "0.013")
        self.assertEqual(code, 3)
        code, _ = run("search", {"query": QUERY, "type": "lite", "numResults": 20}, "--budget-usd", "0.014")
        self.assertEqual(code, 0)
        code, verdict = run("agent/runs", {"query": "q", "effort": "low", "dataSources": [{"provider": "similarweb"}]}, "--budget-usd", "5")
        self.assertEqual(code, 3, "Connect calls make the worst case unknown")
        self.assertIsNone(verdict["worst_case_usd"])

    def test_contact_enrichment_requests_warn_on_fixed_effort(self) -> None:
        code, verdict = run("agent/runs", {"query": "Find the CTO's email address at stripe.com", "effort": "low"})
        self.assertEqual((code, verdict["worst_case_usd"]), (2, 0.025))
        self.assertIn("$0.02 per email", messages(verdict))

    def test_monitor_monthly_cost_and_required_webhook(self) -> None:
        hook = {"url": "https://hooks.example.org/exa"}
        _, hourly = run("monitors", {"search": {"query": "q"}, "webhook": hook, "trigger": {"type": "interval", "period": "1h"}})
        self.assertEqual((hourly["worst_case_usd"], hourly["monthly_usd"]), (0.015, 10.8))
        _, daily = run("monitors", {"search": {"query": "q", "numResults": 20}, "webhook": hook, "trigger": {"period": "1d"}})
        self.assertEqual(daily["monthly_usd"], 0.75)
        _, manual = run("monitors", {"search": {"query": "q"}, "webhook": hook})
        self.assertEqual(manual["monthly_usd"], 0.0)
        code, _ = run("monitors", {"search": {"query": "q"}})
        self.assertEqual(code, 3)

    def test_batch_sums_items_and_surfaces_their_findings(self) -> None:
        body = {"requests": [
            {"customId": "r1", "method": "POST", "url": "/search", "body": {"query": "q", "type": "lite"}},
            {"customId": "r2", "method": "POST", "url": "/agent/runs", "body": {"query": "q"}},
        ]}
        code, verdict = run("batches", body)
        self.assertEqual((code, verdict["worst_case_usd"]), (2, 5.004))
        self.assertIn("[r2]", messages(verdict))

    def test_concrete_ids_normalise_to_status_and_trigger_routes(self) -> None:
        code, verdict = run("/agent/runs/agent_run_7be6bd32b5594f06b3cbc67c5fcd6455/cancel", {})
        self.assertEqual((code, verdict["worst_case_usd"]), (0, 0.0))
        code, status = run("agent/runs/agent_run_7be6bd32b5594f06b3cbc67c5fcd6455", {})
        self.assertEqual((code, status["worst_case_usd"]), (0, 0.0), "polling a run is free")
        _, trigger = run("monitors/01m5xraxx17qk1j04rgyhdapv6/trigger", {})
        self.assertEqual(trigger["worst_case_usd"], 0.015)

    def test_responses_has_no_budget_so_the_default_cap_applies(self) -> None:
        code, verdict = run("responses", {"model": "exa-agent", "input": "q", "reasoning": {"effort": "auto"}})
        self.assertEqual((code, verdict["worst_case_usd"]), (2, 5.0))

    def test_unknown_endpoint_warns_instead_of_guessing(self) -> None:
        code, verdict = run("findSimilar", {"url": PAGE})
        self.assertEqual(code, 2)
        self.assertIsNone(verdict["worst_case_usd"])


if __name__ == "__main__":
    unittest.main()

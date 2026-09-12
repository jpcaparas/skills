#!/usr/bin/env python3
"""Run deterministic packaging, query-plan, and URL-guard tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_research
import check_benchmark_evidence
import validate


@dataclass(slots=True)
class TestReport:
    """Machine-readable result for the local regression suite."""

    skill: str
    passed: bool = True
    checks_passed: int = 0
    checks_total: int = 0
    errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)

    def check(self, condition: bool, message: str) -> None:
        self.checks_total += 1
        if condition:
            self.checks_passed += 1
            return
        self.passed = False
        self.errors.append(message)


def json_mapping(text: str) -> dict[str, object] | None:
    """Parse CLI JSON and narrow it to a string-keyed mapping."""

    try:
        raw: object = json.loads(text)
    except json.JSONDecodeError:
        return None
    return validate.string_keyed_mapping(raw)


def test_url_guard(report: TestReport) -> None:
    """Exercise exact hosts, subdomains, deceptive names, and invalid URLs."""

    blocked_urls = (
        "https://namethatui.com/",
        "http://www.namethatui.com/path",
        "https://docs.namethatui.com/example",
        "https://NAMETHATUI.COM./",
        "https://foo。namethatui.com/path",
    )
    for url in blocked_urls:
        decision = prepare_research.inspect_url(url)
        report.check(
            decision.status is prepare_research.DecisionStatus.BLOCKED,
            f"URL guard failed to block: {url}",
        )

    invalid_urls = (
        "",
        "ftp://namethatui.com/file",
        "https://namethatui.com@example.com/",
        "https://%6eamethatui.com/",
        "https://namethatui.com\\evil.example/",
        "https://example.com/path with spaces",
        "/relative/path",
    )
    for url in invalid_urls:
        decision = prepare_research.inspect_url(url)
        report.check(
            decision.status is prepare_research.DecisionStatus.INVALID,
            f"URL guard failed to reject invalid input: {url}",
        )

    allowed_urls = (
        "https://www.w3.org/WAI/ARIA/apg/patterns/combobox/",
        "https://open-ui.org/research/component-matrix/",
        "https://namethatui.com.evil.example/",
        "https://notnamethatui.com/",
    )
    for url in allowed_urls:
        decision = prepare_research.inspect_url(url)
        report.check(
            decision.status is prepare_research.DecisionStatus.ALLOWED,
            f"URL guard over-blocked an unrelated hostname: {url}",
        )


def test_research_plan(report: TestReport) -> None:
    """Verify bounded, deduplicated queries and explicit exclusion metadata."""

    plan = prepare_research.build_plan(
        clue="A field filters suggestions as I type from https://namethatui.com/example",
        candidates=("Combobox", "autocomplete", "combobox"),
        platform="Web",
        max_queries=4,
    )
    report.check(
        plan.clue == "A field filters suggestions as I type from",
        "Research plan did not remove the blocked-origin URL from the clue.",
    )
    report.check(
        plan.candidates == ("Combobox", "autocomplete"),
        "Research plan did not deduplicate candidate aliases.",
    )
    report.check(
        plan.exclude_domains == (prepare_research.BLOCKED_HOST,),
        "Research plan omitted the provider-native exclusion domain.",
    )
    report.check(
        1 <= len(plan.queries) <= 4,
        "Research plan ignored the configured query bound.",
    )
    report.check(
        all("-site:namethatui.com" in query or query.startswith("site:w3.org") for query in plan.queries),
        "A general research query omitted the negative-site guard.",
    )
    report.check(
        len(set(query.casefold() for query in plan.queries)) == len(plan.queries),
        "Research plan emitted duplicate queries.",
    )
    report.check(
        all(len(query) <= prepare_research.MAX_QUERY_LENGTH for query in plan.queries),
        "Research plan emitted an overlong query.",
    )

    long_plan = prepare_research.build_plan(
        clue="anchored interactive surface " * 80,
        candidates=("popover",),
        platform="web",
        max_queries=4,
    )
    report.check(
        all(
            query.startswith("site:w3.org") or "-site:namethatui.com" in query
            for query in long_plan.queries
        ),
        "An oversized clue displaced the required negative-site suffix.",
    )
    report.check(
        all(len(query) <= prepare_research.MAX_QUERY_LENGTH for query in long_plan.queries),
        "An oversized clue produced an overlong query.",
    )

    filtered_clue = prepare_research.remove_blocked_reference(
        "Keep https://notnamethatui.com/ and https://namethatui.com.evil.example/ "
        "but remove https://docs.namethatui.com/example and namethatui.com/reference."
    )
    report.check(
        "https://notnamethatui.com/" in filtered_clue
        and "https://namethatui.com.evil.example/" in filtered_clue,
        "Blocked-reference filtering corrupted an allowed deceptive-name hostname.",
    )
    report.check(
        "docs.namethatui.com" not in filtered_clue
        and "namethatui.com/reference" not in filtered_clue,
        "Blocked-reference filtering retained a blocked hostname.",
    )

    try:
        prepare_research.build_plan(
            clue="https://namethatui.com/",
            candidates=(),
            platform=None,
            max_queries=2,
        )
    except ValueError:
        report.check(True, "Blocked-only clue is rejected.")
    else:
        report.check(False, "A blocked-only clue should be rejected rather than searched.")


def run_cli(root: Path, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the helper in a subprocess to verify its public CLI contract."""

    return subprocess.run(
        [sys.executable, str(root / "scripts" / "prepare_research.py"), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli(root: Path, report: TestReport) -> None:
    """Verify help, JSON output, and documented exit semantics."""

    help_result = run_cli(root, ["--help"])
    report.check(help_result.returncode == 0, "prepare_research.py --help failed.")

    plan_result = run_cli(
        root,
        [
            "plan",
            "--clue",
            "three-dot button opens secondary actions",
            "--candidate",
            "overflow menu",
        ],
    )
    plan_payload = json_mapping(plan_result.stdout)
    report.check(
        plan_result.returncode == 0 and plan_payload is not None,
        "prepare_research.py plan did not emit successful JSON.",
    )
    if plan_payload is not None:
        report.check(
            isinstance(plan_payload.get("queries"), list),
            "Plan JSON is missing the queries array.",
        )

    blocked_result = run_cli(
        root,
        ["check-url", "https://namethatui.com/", "https://www.w3.org/WAI/"],
    )
    blocked_payload = json_mapping(blocked_result.stdout)
    report.check(
        blocked_result.returncode == 2 and blocked_payload is not None,
        "check-url must return exit 2 when any URL is blocked.",
    )

    allowed_result = run_cli(
        root,
        ["check-url", "https://www.w3.org/WAI/", "https://open-ui.org/"],
    )
    report.check(
        allowed_result.returncode == 0 and json_mapping(allowed_result.stdout) is not None,
        "check-url must return success and JSON when every URL is allowed.",
    )


def synthetic_benchmark(root: Path) -> dict[str, object]:
    """Build one complete in-memory benchmark from the current eval contract."""

    raw_contract: object = json.loads(
        (root / "evals" / "evals.json").read_text(encoding="utf-8")
    )
    contract = validate.string_keyed_mapping(raw_contract)
    if contract is None or not isinstance(contract.get("evals"), list):
        raise ValueError("Current eval contract is not structurally valid.")

    runs: list[dict[str, object]] = []
    for raw_eval in contract["evals"]:
        eval_item = validate.string_keyed_mapping(raw_eval)
        if eval_item is None or not isinstance(eval_item.get("id"), int):
            raise ValueError("Current eval contract contains an invalid eval id.")
        raw_assertions = eval_item.get("assertions")
        if not isinstance(raw_assertions, list):
            raise ValueError("Current eval contract contains an invalid assertions array.")
        expectations: list[dict[str, object]] = []
        for raw_assertion in raw_assertions:
            assertion = validate.string_keyed_mapping(raw_assertion)
            text = assertion.get("text") if assertion is not None else None
            if not isinstance(text, str):
                raise ValueError("Current eval contract contains an assertion without text.")
            expectations.append(
                {
                    "text": text,
                    "passed": True,
                    "evidence": "Synthetic evidence for consistency-check regression coverage.",
                }
            )
        for configuration in check_benchmark_evidence.REQUIRED_CONFIGURATIONS:
            runs.append(
                {
                    "eval_id": eval_item["id"],
                    "configuration": configuration,
                    "run_number": 1,
                    "expectations": expectations,
                }
            )

    return {
        "metadata": {
            "executor_model": "test-executor",
            "analyzer_model": "test-analyzer",
            "runs_per_configuration": 1,
        },
        "runs": runs,
    }


def add_unavailable_resource_metrics(benchmark: dict[str, object]) -> None:
    """Add an internally consistent all-unavailable resource-metric contract."""

    metadata = validate.string_keyed_mapping(benchmark.get("metadata"))
    raw_runs = benchmark.get("runs")
    if metadata is None or not isinstance(raw_runs, list):
        raise ValueError("Synthetic benchmark cannot accept resource metrics.")
    metadata["resource_metrics_note"] = (
        "Comparable timings, token counts, and tool-call counts were not captured; "
        "null means unavailable."
    )
    benchmark["metadata"] = metadata
    for index, raw_run in enumerate(raw_runs):
        run = validate.string_keyed_mapping(raw_run)
        if run is None:
            raise ValueError("Synthetic benchmark contains an invalid run.")
        run["result"] = {
            "time_seconds": None,
            "tokens": None,
            "tool_calls": None,
        }
        raw_runs[index] = run
    benchmark["run_summary"] = {
        configuration: {metric: None for metric in check_benchmark_evidence.RESOURCE_METRICS}
        for configuration in check_benchmark_evidence.REQUIRED_CONFIGURATIONS
    }
    run_summary = validate.string_keyed_mapping(benchmark["run_summary"])
    if run_summary is None:
        raise ValueError("Synthetic run summary could not be constructed.")
    run_summary["delta"] = {
        metric: None for metric in check_benchmark_evidence.RESOURCE_METRICS
    }
    benchmark["run_summary"] = run_summary


def test_benchmark_evidence(root: Path, report: TestReport) -> None:
    """Prove stale or missing benchmark assertions fail deterministically."""

    benchmark = synthetic_benchmark(root)
    with tempfile.TemporaryDirectory(prefix="namethatui-benchmark-") as temporary:
        benchmark_path = Path(temporary) / "benchmark.json"
        benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
        valid_report = check_benchmark_evidence.validate_benchmark(root, benchmark_path)
        report.check(valid_report.valid, "Exact-current synthetic benchmark was rejected.")

        raw_runs = benchmark.get("runs")
        if not isinstance(raw_runs, list) or not raw_runs:
            raise ValueError("Synthetic benchmark unexpectedly has no runs.")
        first_run = validate.string_keyed_mapping(raw_runs[0])
        raw_expectations = first_run.get("expectations") if first_run is not None else None
        if not isinstance(raw_expectations, list) or not raw_expectations:
            raise ValueError("Synthetic benchmark unexpectedly has no expectations.")
        raw_expectations.pop()
        benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
        stale_report = check_benchmark_evidence.validate_benchmark(root, benchmark_path)
        report.check(
            not stale_report.valid
            and any("missing assertions" in error for error in stale_report.errors),
            "Evidence checker did not reject a benchmark with a missing current assertion.",
        )

        wrong_run_count = synthetic_benchmark(root)
        wrong_metadata = validate.string_keyed_mapping(wrong_run_count.get("metadata"))
        if wrong_metadata is None:
            raise ValueError("Synthetic benchmark unexpectedly has no metadata object.")
        wrong_metadata["runs_per_configuration"] = 2
        wrong_run_count["metadata"] = wrong_metadata
        benchmark_path.write_text(json.dumps(wrong_run_count), encoding="utf-8")
        run_count_report = check_benchmark_evidence.validate_benchmark(root, benchmark_path)
        report.check(
            not run_count_report.valid
            and any("expected 2" in error for error in run_count_report.errors),
            "Evidence checker did not reject overstated runs_per_configuration metadata.",
        )

        placeholder_model = synthetic_benchmark(root)
        placeholder_metadata = validate.string_keyed_mapping(placeholder_model.get("metadata"))
        if placeholder_metadata is None:
            raise ValueError("Synthetic benchmark unexpectedly has no metadata object.")
        placeholder_metadata["executor_model"] = "<model-name>"
        placeholder_model["metadata"] = placeholder_metadata
        benchmark_path.write_text(json.dumps(placeholder_model), encoding="utf-8")
        model_report = check_benchmark_evidence.validate_benchmark(root, benchmark_path)
        report.check(
            not model_report.valid
            and any("placeholder text" in error for error in model_report.errors),
            "Evidence checker did not reject placeholder model provenance.",
        )

        unavailable_metrics = synthetic_benchmark(root)
        add_unavailable_resource_metrics(unavailable_metrics)
        benchmark_path.write_text(json.dumps(unavailable_metrics), encoding="utf-8")
        unavailable_report = check_benchmark_evidence.validate_benchmark(
            root, benchmark_path
        )
        report.check(
            unavailable_report.valid,
            "Evidence checker rejected honestly unavailable resource metrics.",
        )

        inconsistent_summary = synthetic_benchmark(root)
        add_unavailable_resource_metrics(inconsistent_summary)
        run_summary = validate.string_keyed_mapping(inconsistent_summary.get("run_summary"))
        with_skill_summary = (
            validate.string_keyed_mapping(run_summary.get("with_skill"))
            if run_summary is not None
            else None
        )
        if with_skill_summary is None:
            raise ValueError("Synthetic benchmark has no with-skill summary.")
        with_skill_summary["time_seconds"] = {"mean": 1.0}
        if run_summary is None:
            raise ValueError("Synthetic benchmark has no run summary.")
        run_summary["with_skill"] = with_skill_summary
        inconsistent_summary["run_summary"] = run_summary
        benchmark_path.write_text(json.dumps(inconsistent_summary), encoding="utf-8")
        summary_report = check_benchmark_evidence.validate_benchmark(root, benchmark_path)
        report.check(
            not summary_report.valid
            and any("must be null" in error for error in summary_report.errors),
            "Evidence checker accepted an aggregate for unavailable run timings.",
        )

        contradictory_timing = synthetic_benchmark(root)
        add_unavailable_resource_metrics(contradictory_timing)
        contradictory_runs = contradictory_timing.get("runs")
        if not isinstance(contradictory_runs, list) or not contradictory_runs:
            raise ValueError("Synthetic benchmark unexpectedly has no runs.")
        first_timing_run = validate.string_keyed_mapping(contradictory_runs[0])
        first_result = (
            validate.string_keyed_mapping(first_timing_run.get("result"))
            if first_timing_run is not None
            else None
        )
        if first_result is None:
            raise ValueError("Synthetic benchmark unexpectedly has no result object.")
        first_result["time_seconds"] = 0.001
        if first_timing_run is None:
            raise ValueError("Synthetic benchmark unexpectedly has no first run.")
        first_timing_run["result"] = first_result
        contradictory_runs[0] = first_timing_run
        timing_dir = (
            Path(temporary)
            / "eval-1-timing-regression"
            / "with_skill"
            / "run-1"
        )
        timing_dir.mkdir(parents=True)
        (timing_dir / "timing.json").write_text(
            json.dumps(
                {
                    "total_duration_seconds": 0.001,
                    "measured": {"duration_ms": 5500},
                }
            ),
            encoding="utf-8",
        )
        benchmark_path.write_text(json.dumps(contradictory_timing), encoding="utf-8")
        timing_report = check_benchmark_evidence.validate_benchmark(root, benchmark_path)
        report.check(
            not timing_report.valid
            and any("contradicts" in error for error in timing_report.errors),
            "Evidence checker accepted contradictory nested duration evidence.",
        )

        recovery_timing = synthetic_benchmark(root)
        add_unavailable_resource_metrics(recovery_timing)
        recovery_runs = recovery_timing.get("runs")
        if not isinstance(recovery_runs, list) or not recovery_runs:
            raise ValueError("Synthetic benchmark unexpectedly has no recovery run.")
        recovery_run = validate.string_keyed_mapping(recovery_runs[0])
        recovery_result = (
            validate.string_keyed_mapping(recovery_run.get("result"))
            if recovery_run is not None
            else None
        )
        if recovery_run is None or recovery_result is None:
            raise ValueError("Synthetic recovery run has no result object.")
        recovery_result["time_seconds"] = 0.01
        recovery_run["result"] = recovery_result
        recovery_runs[0] = recovery_run
        (timing_dir / "timing.json").write_text(
            json.dumps(
                {
                    "total_duration_seconds": 0.01,
                    "measurement": "Recovery artifact write duration",
                }
            ),
            encoding="utf-8",
        )
        benchmark_path.write_text(json.dumps(recovery_timing), encoding="utf-8")
        recovery_report = check_benchmark_evidence.validate_benchmark(root, benchmark_path)
        report.check(
            not recovery_report.valid
            and any("recovery-only" in error for error in recovery_report.errors),
            "Evidence checker accepted a recovery-only executor duration.",
        )


def test_skill(skill_path: str | Path) -> TestReport:
    """Run all deterministic checks for one skill directory."""

    root = Path(skill_path).resolve()
    report = TestReport(skill=root.name)

    validation_report = validate.validate_skill(root)
    report.validation_warnings.extend(validation_report.warnings)
    report.check(validation_report.valid, "Package validation failed.")
    report.errors.extend(validation_report.errors)
    if validation_report.errors:
        report.passed = False

    test_url_guard(report)
    test_research_plan(report)
    test_cli(root, report)
    test_benchmark_evidence(root, report)
    return report


def main() -> None:
    """CLI entry point."""

    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        raise SystemExit(1)
    report = test_skill(sys.argv[1])
    print(json.dumps(asdict(report), indent=2))
    raise SystemExit(0 if report.passed else 1)


if __name__ == "__main__":
    main()

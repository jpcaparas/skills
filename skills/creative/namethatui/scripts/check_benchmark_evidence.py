#!/usr/bin/env python3
"""Verify that a benchmark grades the exact current namethatui eval contract."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Sequence


REQUIRED_CONFIGURATIONS: tuple[str, ...] = ("with_skill", "without_skill")
RESOURCE_METRICS: tuple[str, ...] = ("time_seconds", "tokens", "tool_calls")


@dataclass(slots=True)
class EvidenceReport:
    """Machine-readable benchmark consistency result."""

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    expected_eval_count: int = 0
    expected_assertion_count: int = 0
    runs_checked: int = 0
    runs_per_configuration: int = 0

    def error(self, message: str) -> None:
        self.valid = False
        self.errors.append(message)


def string_mapping(value: object) -> dict[str, object] | None:
    """Narrow an untrusted JSON object to a string-keyed mapping."""

    if not isinstance(value, dict):
        return None
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            return None
        result[key] = item
    return result


def load_json(path: Path, report: EvidenceReport) -> object | None:
    """Load a JSON file and convert read/parse failures into report errors."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        report.error(f"Cannot read {path}: {exc}")
    except json.JSONDecodeError as exc:
        report.error(f"Invalid JSON in {path}: {exc}")
    return None


def eval_key(value: object) -> str | None:
    """Return a stable key for integer or non-empty string eval identifiers."""

    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def expected_assertions(skill_path: Path, report: EvidenceReport) -> dict[str, tuple[str, ...]]:
    """Load the canonical assertion text for every committed eval."""

    raw = load_json(skill_path / "evals" / "evals.json", report)
    root = string_mapping(raw)
    if root is None:
        if raw is not None:
            report.error("evals/evals.json must contain an object.")
        return {}

    raw_evals = root.get("evals")
    if not isinstance(raw_evals, list):
        report.error("evals/evals.json has no evals array.")
        return {}

    result: dict[str, tuple[str, ...]] = {}
    for index, raw_eval in enumerate(raw_evals):
        eval_item = string_mapping(raw_eval)
        if eval_item is None:
            report.error(f"Canonical eval at index {index} is not an object.")
            continue
        key = eval_key(eval_item.get("id"))
        if key is None:
            report.error(f"Canonical eval at index {index} has no valid id.")
            continue
        raw_assertions = eval_item.get("assertions")
        if not isinstance(raw_assertions, list):
            report.error(f"Canonical eval {key} has no assertions array.")
            continue
        texts: list[str] = []
        for assertion_index, raw_assertion in enumerate(raw_assertions):
            assertion = string_mapping(raw_assertion)
            text = assertion.get("text") if assertion is not None else None
            if not isinstance(text, str) or not text.strip():
                report.error(
                    f"Canonical eval {key} assertion {assertion_index} has no text."
                )
                continue
            texts.append(text)
        if len(texts) != len(set(texts)):
            report.error(f"Canonical eval {key} contains duplicate assertion text.")
        result[key] = tuple(texts)

    report.expected_eval_count = len(result)
    report.expected_assertion_count = sum(len(texts) for texts in result.values())
    return result


def validate_metadata(metadata: dict[str, object], report: EvidenceReport) -> int:
    """Validate benchmark provenance fields used by the evidence checker."""

    raw_runs = metadata.get("runs_per_configuration")
    if not isinstance(raw_runs, int) or isinstance(raw_runs, bool) or raw_runs < 1:
        report.error("Benchmark metadata needs a positive runs_per_configuration integer.")
        expected_runs = 0
    else:
        expected_runs = raw_runs
        report.runs_per_configuration = raw_runs

    for field_name in ("executor_model", "analyzer_model"):
        value = metadata.get(field_name)
        if not isinstance(value, str) or not value.strip() or "<" in value or ">" in value:
            report.error(f"Benchmark metadata field {field_name} is missing or placeholder text.")
    return expected_runs


def finite_number(value: object) -> float | None:
    """Return a finite number while rejecting booleans and non-numeric values."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def duration_candidates(timing: dict[str, object]) -> tuple[list[float], float | None]:
    """Extract independently recorded durations and a nested-wait lower bound."""

    candidates: list[float] = []
    for field_name in ("elapsed_seconds", "duration_seconds"):
        value = finite_number(timing.get(field_name))
        if value is not None:
            candidates.append(value)

    for start_name, end_name in (
        ("start_epoch", "end_epoch"),
        ("started_at_epoch_seconds", "ended_at_epoch_seconds"),
    ):
        start = finite_number(timing.get(start_name))
        end = finite_number(timing.get(end_name))
        if start is not None and end is not None:
            candidates.append(end - start)

    duration_ms = finite_number(timing.get("duration_ms"))
    if duration_ms is not None:
        candidates.append(duration_ms / 1000)

    measured = string_mapping(timing.get("measured"))
    if measured is not None:
        measured_ms = finite_number(measured.get("duration_ms"))
        if measured_ms is not None:
            candidates.append(measured_ms / 1000)
        started_at = measured.get("started_at")
        completed_at = measured.get("completed_at")
        if isinstance(started_at, str) and isinstance(completed_at, str):
            try:
                start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            except ValueError:
                pass
            else:
                candidates.append((end_time - start_time).total_seconds())

    wait_lower_bound: float | None = None
    raw_steps = timing.get("runs")
    if isinstance(raw_steps, list):
        waits = [
            value
            for raw_step in raw_steps
            if (step := string_mapping(raw_step)) is not None
            if (value := finite_number(step.get("open_wait_seconds"))) is not None
        ]
        if waits:
            wait_lower_bound = sum(waits)
    return candidates, wait_lower_bound


def find_timing_file(
    benchmark_root: Path,
    *,
    eval_id: str,
    configuration: str,
    run_number: int,
) -> Path | None:
    """Find one run timing file from the standard benchmark workspace layout."""

    matches = sorted(
        benchmark_root.glob(
            f"eval-{eval_id}-*/{configuration}/run-{run_number}/timing.json"
        )
    )
    return matches[0] if len(matches) == 1 else None


def validate_timing_evidence(
    benchmark_root: Path,
    *,
    eval_id: str,
    configuration: str,
    run_number: int,
    benchmark_seconds: float,
    report: EvidenceReport,
) -> None:
    """Reject recovery-only or internally contradictory published timings."""

    label = f"eval {eval_id}/{configuration}/run-{run_number}"
    timing_path = find_timing_file(
        benchmark_root,
        eval_id=eval_id,
        configuration=configuration,
        run_number=run_number,
    )
    if timing_path is None:
        report.error(f"{label} publishes time_seconds without one unambiguous timing.json.")
        return
    try:
        timing_raw: object = json.loads(timing_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.error(f"{label} timing evidence is unreadable: {exc}")
        return
    timing = string_mapping(timing_raw)
    if timing is None:
        report.error(f"{label} timing.json must contain an object.")
        return

    recorded_total = finite_number(timing.get("total_duration_seconds"))
    if recorded_total is None or recorded_total <= 0:
        report.error(f"{label} has no positive total_duration_seconds evidence.")
        return
    tolerance = max(0.01, recorded_total * 0.01)
    if abs(recorded_total - benchmark_seconds) > tolerance:
        report.error(f"{label} benchmark time does not match timing.json.")

    measurement = timing.get("measurement")
    if isinstance(measurement, str) and "recovery" in measurement.casefold():
        report.error(f"{label} publishes a recovery-only duration as executor time.")

    candidates, wait_lower_bound = duration_candidates(timing)
    for candidate in candidates:
        candidate_tolerance = max(0.01, abs(candidate) * 0.01)
        if candidate <= 0 or abs(recorded_total - candidate) > candidate_tolerance:
            report.error(
                f"{label} total_duration_seconds contradicts another recorded duration."
            )
            break
    if wait_lower_bound is not None and recorded_total + tolerance < wait_lower_bound:
        report.error(f"{label} total duration is shorter than its recorded wait steps.")


def validate_resource_metrics(
    benchmark: dict[str, object],
    benchmark_path: Path,
    runs: list[dict[str, object]],
    report: EvidenceReport,
) -> None:
    """Validate unavailable metrics and any published wall-clock evidence."""

    explicit_metrics = False
    null_metrics = False
    values: dict[tuple[str, str], list[object]] = {}
    for run in runs:
        result = string_mapping(run.get("result"))
        configuration = run.get("configuration")
        key = eval_key(run.get("eval_id"))
        run_number = run.get("run_number")
        if result is None or not isinstance(configuration, str):
            continue
        result_has_metrics = any(metric in result for metric in RESOURCE_METRICS)
        explicit_metrics = explicit_metrics or result_has_metrics
        for metric in RESOURCE_METRICS:
            value = result.get(metric)
            values.setdefault((configuration, metric), []).append(value)
            if value is None:
                null_metrics = True
                continue
            number = finite_number(value)
            if number is None or number < 0:
                report.error(
                    f"Benchmark eval {key}/{configuration} has invalid {metric}."
                )
                continue
            if metric == "time_seconds" and key is not None and isinstance(run_number, int):
                validate_timing_evidence(
                    benchmark_path.parent,
                    eval_id=key,
                    configuration=configuration,
                    run_number=run_number,
                    benchmark_seconds=number,
                    report=report,
                )

    if not explicit_metrics:
        return
    metadata = string_mapping(benchmark.get("metadata"))
    note = metadata.get("resource_metrics_note") if metadata is not None else None
    if null_metrics and (not isinstance(note, str) or not note.strip()):
        report.error("Null resource metrics require a non-empty resource_metrics_note.")

    run_summary = string_mapping(benchmark.get("run_summary"))
    if run_summary is None:
        report.error("Benchmarks with resource metrics need a run_summary object.")
        return
    for configuration in REQUIRED_CONFIGURATIONS:
        summary = string_mapping(run_summary.get(configuration))
        if summary is None:
            report.error(f"run_summary is missing configuration {configuration}.")
            continue
        for metric in RESOURCE_METRICS:
            observed = values.get((configuration, metric), [])
            if observed and any(value is None for value in observed) and summary.get(metric) is not None:
                report.error(
                    f"run_summary {configuration}/{metric} must be null when a run is unavailable."
                )
    delta = string_mapping(run_summary.get("delta"))
    if delta is None:
        report.error("run_summary is missing delta metrics.")
        return
    for metric in RESOURCE_METRICS:
        unavailable = any(
            value is None
            for configuration in REQUIRED_CONFIGURATIONS
            for value in values.get((configuration, metric), [])
        )
        if unavailable and delta.get(metric) is not None:
            report.error(f"run_summary delta/{metric} must be null when a run is unavailable.")


def expectation_texts(
    raw_expectations: object,
    *,
    run_label: str,
    report: EvidenceReport,
) -> tuple[str, ...]:
    """Validate and return one run's graded expectation texts."""

    if not isinstance(raw_expectations, list):
        report.error(f"{run_label} has no expectations array.")
        return ()
    texts: list[str] = []
    for index, raw_expectation in enumerate(raw_expectations):
        expectation = string_mapping(raw_expectation)
        if expectation is None:
            report.error(f"{run_label} expectation {index} is not an object.")
            continue
        text = expectation.get("text")
        passed = expectation.get("passed")
        evidence = expectation.get("evidence")
        if not isinstance(text, str) or not text.strip():
            report.error(f"{run_label} expectation {index} has no text.")
            continue
        if not isinstance(passed, bool):
            report.error(f"{run_label} expectation {index} has no boolean verdict.")
        if not isinstance(evidence, str) or not evidence.strip():
            report.error(f"{run_label} expectation {index} has no evidence.")
        texts.append(text)
    if len(texts) != len(set(texts)):
        report.error(f"{run_label} contains duplicate expectation text.")
    return tuple(texts)


def validate_benchmark(skill_path: Path, benchmark_path: Path) -> EvidenceReport:
    """Compare a benchmark's runs with the canonical committed assertions."""

    report = EvidenceReport()
    canonical = expected_assertions(skill_path.resolve(), report)
    raw = load_json(benchmark_path.resolve(), report)
    benchmark = string_mapping(raw)
    if benchmark is None:
        if raw is not None:
            report.error("Benchmark JSON must contain an object.")
        return report

    metadata = string_mapping(benchmark.get("metadata"))
    expected_runs = validate_metadata(metadata, report) if metadata is not None else 0
    if metadata is None:
        report.error("Benchmark has no metadata object.")

    raw_runs = benchmark.get("runs")
    if not isinstance(raw_runs, list):
        report.error("Benchmark has no runs array.")
        return report

    observed: dict[tuple[str, str], list[tuple[str, ...]]] = {}
    observed_numbers: dict[tuple[str, str], set[int]] = {}
    parsed_runs: list[dict[str, object]] = []
    for index, raw_run in enumerate(raw_runs):
        run = string_mapping(raw_run)
        if run is None:
            report.error(f"Benchmark run at index {index} is not an object.")
            continue
        parsed_runs.append(run)
        key = eval_key(run.get("eval_id"))
        configuration = run.get("configuration")
        run_number = run.get("run_number")
        if key is None:
            report.error(f"Benchmark run at index {index} has no valid eval_id.")
            continue
        if not isinstance(configuration, str) or configuration not in REQUIRED_CONFIGURATIONS:
            report.error(f"Benchmark eval {key} has invalid configuration {configuration!r}.")
            continue
        if not isinstance(run_number, int) or isinstance(run_number, bool) or run_number < 1:
            report.error(f"Benchmark eval {key}/{configuration} has invalid run_number.")
            continue
        label = f"eval {key}/{configuration}/run-{run_number}"
        texts = expectation_texts(run.get("expectations"), run_label=label, report=report)
        pair = (key, configuration)
        observed.setdefault(pair, []).append(texts)
        observed_numbers.setdefault(pair, set()).add(run_number)
        report.runs_checked += 1

    expected_pairs = {
        (key, configuration)
        for key in canonical
        for configuration in REQUIRED_CONFIGURATIONS
    }
    for pair in sorted(set(observed) - expected_pairs):
        report.error(f"Benchmark contains unexpected eval/configuration pair {pair}.")

    for key, expected_texts in canonical.items():
        expected_set = set(expected_texts)
        for configuration in REQUIRED_CONFIGURATIONS:
            pair = (key, configuration)
            runs = observed.get(pair, [])
            if len(runs) != expected_runs:
                report.error(
                    f"Eval {key}/{configuration} has {len(runs)} runs; expected {expected_runs}."
                )
            numbers = observed_numbers.get(pair, set())
            if numbers != set(range(1, expected_runs + 1)):
                report.error(
                    f"Eval {key}/{configuration} run numbers {sorted(numbers)} do not match "
                    f"1..{expected_runs}."
                )
            for run_index, observed_texts in enumerate(runs, start=1):
                observed_set = set(observed_texts)
                missing = expected_set - observed_set
                stale = observed_set - expected_set
                if missing:
                    report.error(
                        f"Eval {key}/{configuration}/run-{run_index} is missing assertions: "
                        + " | ".join(sorted(missing))
                    )
                if stale:
                    report.error(
                        f"Eval {key}/{configuration}/run-{run_index} has stale assertions: "
                        + " | ".join(sorted(stale))
                    )

    validate_resource_metrics(benchmark, benchmark_path.resolve(), parsed_runs, report)

    return report


def run(argv: Sequence[str]) -> int:
    """Run the evidence checker CLI."""

    if len(argv) != 2:
        print(
            "Usage: python3 check_benchmark_evidence.py <skill-path> <benchmark.json>",
            file=sys.stderr,
        )
        return 1
    report = validate_benchmark(Path(argv[0]), Path(argv[1]))
    print(json.dumps(asdict(report), indent=2))
    return 0 if report.valid else 1


def main() -> None:
    """CLI entry point."""

    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()

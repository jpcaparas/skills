#!/usr/bin/env python3
"""Contextual formulaic-language diagnostic for the better-writing skill.

The scanner surfaces revision prompts from an explicit local corpus. It is not
an authorship detector: a signal does not show who wrote a text, and an empty
report does not prove that prose is original, human, or suitable for its genre.

Usage:
    python3 scan_aiisms.py draft.md
    python3 scan_aiisms.py --text "Draft text" --format json
    python3 scan_aiisms.py --gate draft.md
    python3 scan_aiisms.py --self-test
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, Sequence


Severity = Literal["low", "medium", "high"]
EditorialAction = Literal["remove", "rewrite", "review"]
ClusterScope = Literal["document", "paragraph"]

CORPUS_PATH = Path(__file__).resolve().parent.parent / "assets" / "aiisms.json"
SUPPORTED_PROSE_SUFFIXES = {"", ".adoc", ".asciidoc", ".htm", ".html", ".md", ".mdx", ".rst", ".text", ".txt"}
REQUIRED_PATTERN_KEYS = {
    "id",
    "category",
    "kind",
    "action",
    "severity",
    "confidence",
    "minimum_occurrences",
    "cluster",
    "explanation",
    "revision_move",
    "exceptions",
    "positive_examples",
    "counterexamples",
    "evidence",
    "last_reviewed",
}
REQUIRED_CATEGORIES = {
    "lexical",
    "rhetorical_frames",
    "compressed_authority_frames",
    "chat_service_residue",
    "generic_authority",
    "formatting",
    "cadence_structure",
    "punctuation",
}


@dataclass(frozen=True)
class Cluster:
    """A bounded group of related signals that may produce a revision gate."""

    key: str
    minimum_patterns: int
    must_revise: bool
    scope: ClusterScope


@dataclass(frozen=True)
class Metric:
    """A bounded metric implementation supported by this portable scanner."""

    name: Literal["character_count", "repeated_sentence_opener", "short_sentence_run"]
    threshold: int
    character: str | None = None
    max_words: int | None = None


@dataclass(frozen=True)
class Pattern:
    """A schema-validated, evidence-carrying revision prompt."""

    id: str
    category: str
    kind: Literal["regex", "metric"]
    action: EditorialAction
    regex: re.Pattern[str] | None
    metric: Metric | None
    severity: Severity
    confidence: str
    minimum_occurrences: int
    cluster: Cluster
    explanation: str
    revision_move: str
    exceptions: tuple[str, ...]
    positive_examples: tuple[str, ...]
    counterexamples: tuple[str, ...]
    evidence_tier: str
    evidence_urls: tuple[str, ...]
    last_reviewed: str


@dataclass(frozen=True)
class Signal:
    """One observed pattern; it is a review prompt, never a verdict."""

    pattern_id: str
    category: str
    action: EditorialAction
    severity: Severity
    confidence: str
    occurrences: int
    minimum_occurrences: int
    excerpts: tuple[str, ...]
    matched_texts: tuple[str, ...]
    explanation: str
    revision_move: str
    exceptions: tuple[str, ...]
    evidence_tier: str
    evidence_urls: tuple[str, ...]
    cluster_key: str


@dataclass(frozen=True)
class Gate:
    """A narrow, explicit cluster-level revision gate."""

    cluster_key: str
    matched_pattern_ids: tuple[str, ...]
    required_distinct_patterns: int
    message: str


@dataclass(frozen=True)
class ScanMetrics:
    source_characters: int
    scanned_characters: int
    source_words: int
    scanned_words: int
    sentences: int
    skipped_fenced_code_characters: int
    skipped_inline_code_characters: int
    skipped_quote_characters: int
    skipped_url_characters: int


@dataclass(frozen=True)
class ScanReport:
    """Serializable report with uncertainty made explicit."""

    scanner: str
    disclaimer: str
    signals: tuple[Signal, ...]
    must_revise_gates: tuple[Gate, ...]
    metrics: ScanMetrics
    uncertainty: tuple[str, ...]


class CorpusError(ValueError):
    """Raised when the local corpus cannot safely drive diagnostics."""


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item for item in value)


def _validate_date(value: str, location: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise CorpusError(f"{location} must be an ISO date") from exc


def _parse_cluster(value: object, location: str) -> Cluster:
    if not isinstance(value, dict):
        raise CorpusError(f"{location} must be an object")
    key = value.get("key")
    minimum_patterns = value.get("minimum_patterns")
    must_revise = value.get("must_revise")
    scope = value.get("scope")
    if not isinstance(key, str) or not key:
        raise CorpusError(f"{location}.key must be a non-empty string")
    if not isinstance(minimum_patterns, int) or minimum_patterns < 2:
        raise CorpusError(f"{location}.minimum_patterns must be an integer of at least 2")
    if not isinstance(must_revise, bool):
        raise CorpusError(f"{location}.must_revise must be boolean")
    if scope not in {"document", "paragraph"}:
        raise CorpusError(f"{location}.scope must be document or paragraph")
    return Cluster(key=key, minimum_patterns=minimum_patterns, must_revise=must_revise, scope=scope)


def _parse_metric(value: object, location: str) -> Metric:
    if not isinstance(value, dict):
        raise CorpusError(f"{location} must be an object")
    name = value.get("name")
    threshold = value.get("threshold")
    supported = {"character_count", "repeated_sentence_opener", "short_sentence_run"}
    if name not in supported:
        raise CorpusError(f"{location}.name must be one of {sorted(supported)}")
    if not isinstance(threshold, int) or threshold < 1:
        raise CorpusError(f"{location}.threshold must be a positive integer")
    character = value.get("character")
    max_words = value.get("max_words")
    if name == "character_count" and (not isinstance(character, str) or len(character) != 1):
        raise CorpusError(f"{location}.character must be one character for character_count")
    if name == "short_sentence_run" and (not isinstance(max_words, int) or max_words < 1):
        raise CorpusError(f"{location}.max_words must be positive for short_sentence_run")
    return Metric(name=name, threshold=threshold, character=character if isinstance(character, str) else None, max_words=max_words if isinstance(max_words, int) else None)


def _parse_pattern(raw: object, index: int) -> Pattern:
    location = f"patterns[{index}]"
    if not isinstance(raw, dict):
        raise CorpusError(f"{location} must be an object")
    missing = sorted(REQUIRED_PATTERN_KEYS - raw.keys())
    if missing:
        raise CorpusError(f"{location} is missing required keys: {', '.join(missing)}")
    pattern_id = raw.get("id")
    category = raw.get("category")
    kind = raw.get("kind")
    action = raw.get("action")
    severity = raw.get("severity")
    confidence = raw.get("confidence")
    occurrences = raw.get("minimum_occurrences")
    explanation = raw.get("explanation")
    revision_move = raw.get("revision_move")
    if not isinstance(pattern_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", pattern_id):
        raise CorpusError(f"{location}.id must be a stable kebab-case identifier")
    if not isinstance(category, str) or not category:
        raise CorpusError(f"{location}.category must be a non-empty string")
    if kind not in {"regex", "metric"}:
        raise CorpusError(f"{location}.kind must be regex or metric")
    if action not in {"remove", "rewrite", "review"}:
        raise CorpusError(f"{location}.action must be remove, rewrite, or review")
    if severity not in {"low", "medium", "high"}:
        raise CorpusError(f"{location}.severity must be low, medium, or high")
    if not isinstance(confidence, str) or confidence not in {"low", "medium", "high"}:
        raise CorpusError(f"{location}.confidence must be low, medium, or high")
    if not isinstance(occurrences, int) or occurrences < 1:
        raise CorpusError(f"{location}.minimum_occurrences must be a positive integer")
    if not isinstance(explanation, str) or not explanation or not isinstance(revision_move, str) or not revision_move:
        raise CorpusError(f"{location} needs non-empty explanation and revision_move")
    for key in ("exceptions", "positive_examples", "counterexamples"):
        if not _is_string_list(raw.get(key)):
            raise CorpusError(f"{location}.{key} must be a non-empty list of non-empty strings")
    evidence = raw.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("tier") not in {"A", "B", "C"}:
        raise CorpusError(f"{location}.evidence.tier must be A, B, or C")
    urls = evidence.get("urls")
    if not _is_string_list(urls) or not all(url.startswith(("https://", "http://")) for url in urls):
        raise CorpusError(f"{location}.evidence.urls must contain one or more HTTP(S) URLs")
    last_reviewed = raw.get("last_reviewed")
    if not isinstance(last_reviewed, str):
        raise CorpusError(f"{location}.last_reviewed must be a date string")
    _validate_date(last_reviewed, f"{location}.last_reviewed")
    cluster = _parse_cluster(raw["cluster"], f"{location}.cluster")
    compiled_regex: re.Pattern[str] | None = None
    metric: Metric | None = None
    if kind == "regex":
        regex = raw.get("regex")
        if not isinstance(regex, str) or not regex:
            raise CorpusError(f"{location}.regex must be a non-empty string for regex patterns")
        if "metric" in raw:
            raise CorpusError(f"{location} cannot have metric when kind is regex")
        try:
            compiled_regex = re.compile(regex, re.IGNORECASE)
        except re.error as exc:
            raise CorpusError(f"{location}.regex does not compile: {exc}") from exc
    else:
        if "regex" in raw:
            raise CorpusError(f"{location} cannot have regex when kind is metric")
        metric = _parse_metric(raw.get("metric"), f"{location}.metric")
    return Pattern(
        id=pattern_id,
        category=category,
        kind=kind,
        action=action,
        regex=compiled_regex,
        metric=metric,
        severity=severity,
        confidence=confidence,
        minimum_occurrences=occurrences,
        cluster=cluster,
        explanation=explanation,
        revision_move=revision_move,
        exceptions=tuple(raw["exceptions"]),
        positive_examples=tuple(raw["positive_examples"]),
        counterexamples=tuple(raw["counterexamples"]),
        evidence_tier=evidence["tier"],
        evidence_urls=tuple(urls),
        last_reviewed=last_reviewed,
    )


def load_corpus(path: Path = CORPUS_PATH) -> tuple[Pattern, ...]:
    """Load and validate the corpus before it is used to scan any prose."""

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CorpusError(f"Cannot read corpus at {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CorpusError(f"Corpus is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") not in {1, 2}:
        raise CorpusError("Corpus must be an object with schema_version 1 or 2")
    schema_version = raw["schema_version"]
    patterns_raw = raw.get("patterns")
    if not isinstance(patterns_raw, list) or not patterns_raw:
        raise CorpusError("Corpus must contain a non-empty patterns list")
    normalized_patterns: list[object] = []
    for item in patterns_raw:
        if schema_version == 2 or not isinstance(item, dict):
            normalized_patterns.append(item)
            continue
        normalized = dict(item)
        normalized.setdefault("action", "review")
        cluster = normalized.get("cluster")
        if isinstance(cluster, dict):
            normalized_cluster = dict(cluster)
            normalized_cluster.setdefault("scope", "document")
            normalized["cluster"] = normalized_cluster
        evidence = normalized.get("evidence")
        if isinstance(evidence, dict) and evidence.get("tier") == "editorial-heuristic":
            normalized_evidence = dict(evidence)
            normalized_evidence["tier"] = "C"
            normalized["evidence"] = normalized_evidence
        normalized_patterns.append(normalized)
    patterns = tuple(_parse_pattern(item, index) for index, item in enumerate(normalized_patterns))
    ids = [pattern.id for pattern in patterns]
    if len(ids) != len(set(ids)):
        raise CorpusError("Corpus pattern ids must be unique")
    missing_categories = sorted(REQUIRED_CATEGORIES - {pattern.category for pattern in patterns})
    if missing_categories:
        raise CorpusError(f"Corpus is missing required categories: {', '.join(missing_categories)}")
    cluster_contracts: dict[str, tuple[int, bool, ClusterScope]] = {}
    for pattern in patterns:
        contract = (pattern.cluster.minimum_patterns, pattern.cluster.must_revise, pattern.cluster.scope)
        previous = cluster_contracts.setdefault(pattern.cluster.key, contract)
        if previous != contract:
            raise CorpusError(f"Cluster {pattern.cluster.key!r} has inconsistent threshold, gate, or scope settings")
    return patterns


def _replace_and_count(text: str, pattern: re.Pattern[str], replacement: str) -> tuple[str, int]:
    removed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal removed
        removed += len(match.group(0))
        return replacement

    return pattern.sub(replace, text), removed


def prepare_text(text: str) -> tuple[str, dict[str, int]]:
    """Drop material that is usually not prose while preserving word boundaries."""

    skipped = {"fenced_code": 0, "inline_code": 0, "quotes": 0, "urls": 0}
    text, frontmatter = _replace_and_count(
        text,
        re.compile(r"(?ms)\A---\s*\n.*?^---\s*(?:\n|\Z)"),
        "\n",
    )
    skipped["fenced_code"] += frontmatter
    text, fenced_code = _replace_and_count(
        text,
        re.compile(r"(?ms)^(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^(?P=fence)\s*$"),
        "\n",
    )
    skipped["fenced_code"] += fenced_code
    text, html_pre = _replace_and_count(text, re.compile(r"(?is)<pre\b[^>]*>.*?</pre>"), "\n")
    skipped["fenced_code"] += html_pre
    text, html_script = _replace_and_count(text, re.compile(r"(?is)<script\b[^>]*>.*?</script>"), "\n")
    skipped["fenced_code"] += html_script
    text, html_style = _replace_and_count(text, re.compile(r"(?is)<style\b[^>]*>.*?</style>"), "\n")
    skipped["fenced_code"] += html_style
    text, html_code = _replace_and_count(text, re.compile(r"(?is)<code\b[^>]*>.*?</code>"), " ")
    skipped["inline_code"] += html_code
    text, indented_code = _replace_and_count(
        text,
        re.compile(r"(?m)(?:^(?: {4}|\t).*(?:\n|$))+"),
        "\n",
    )
    skipped["fenced_code"] += indented_code
    text, inline_code = _replace_and_count(text, re.compile(r"`[^`\n]+`"), " ")
    skipped["inline_code"] += inline_code
    text, skipped["urls"] = _replace_and_count(text, re.compile(r"!\[[^\]]*\]\([^)]*\)"), " ")
    markdown_link_pattern = re.compile(r"(?<!!)\[([^\]]+)\]\([^)]*\)")
    markdown_urls = 0

    def preserve_link_text(match: re.Match[str]) -> str:
        nonlocal markdown_urls
        markdown_urls += len(match.group(0)) - len(match.group(1))
        return match.group(1)

    text = markdown_link_pattern.sub(preserve_link_text, text)
    skipped["urls"] += markdown_urls
    text, bare_urls = _replace_and_count(text, re.compile(r"https?://[^\s)>]+"), " ")
    skipped["urls"] += bare_urls
    text, curly_quotes = _replace_and_count(text, re.compile(r"“[\s\S]{1,2000}?”"), " ")
    skipped["quotes"] += curly_quotes
    text, curly_single_quotes = _replace_and_count(text, re.compile(r"‘[\s\S]{1,2000}?’"), " ")
    skipped["quotes"] += curly_single_quotes
    text, straight_quotes = _replace_and_count(text, re.compile(r'(?<!\w)"[^"\n]{1,2000}"(?!\w)'), " ")
    skipped["quotes"] += straight_quotes
    text, html_quotes = _replace_and_count(text, re.compile(r"(?is)<blockquote\b[^>]*>.*?</blockquote>"), "\n")
    skipped["quotes"] += html_quotes
    retained: list[str] = []
    for line in text.splitlines(keepends=True):
        if re.match(r"^\s*>+", line):
            skipped["quotes"] += len(line)
            retained.append("\n" if line.endswith("\n") else "")
        else:
            retained.append(line)
    return "".join(retained), skipped


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if re.search(r"\w", sentence)]


def _excerpt(text: str, start: int, end: int, width: int = 100) -> str:
    left = max(0, start - width // 2)
    right = min(len(text), end + width // 2)
    return " ".join(text[left:right].split())


def _metric_matches(metric: Metric, text: str) -> tuple[int, tuple[str, ...]]:
    sentences = _sentences(text)
    if metric.name == "character_count":
        assert metric.character is not None
        count = text.count(metric.character)
        return count, (f"Found {count} instances of {metric.character!r}.",) if count else ()
    if metric.name == "repeated_sentence_opener":
        openers = [match.group(1).lower() for sentence in sentences if (match := re.match(r"\W*([A-Za-z][A-Za-z'-]*)\b", sentence))]
        counts = Counter(openers)
        repeated = [(opener, count) for opener, count in counts.items() if count >= metric.threshold]
        excerpts = tuple(f"Sentence opener {opener!r} appears {count} times." for opener, count in repeated)
        return sum(count for _, count in repeated), excerpts
    assert metric.max_words is not None
    longest_run = 0
    current_run = 0
    for sentence in sentences:
        words = re.findall(r"\b[\w'-]+\b", sentence)
        if 0 < len(words) <= metric.max_words:
            current_run += 1
            longest_run = max(longest_run, current_run)
        else:
            current_run = 0
    return longest_run, (f"Longest run of sentences with at most {metric.max_words} words: {longest_run}.",) if longest_run else ()


def _pattern_signal(pattern: Pattern, text: str) -> Signal | None:
    if pattern.kind == "regex":
        assert pattern.regex is not None
        matches = list(pattern.regex.finditer(text))
        count = len(matches)
        excerpts = tuple(_excerpt(text, match.start(), match.end()) for match in matches[:3])
        matched_texts = tuple(dict.fromkeys(match.group(0) for match in matches[:5]))
    else:
        assert pattern.metric is not None
        count, excerpts = _metric_matches(pattern.metric, text)
        matched_texts = ()
    if count < pattern.minimum_occurrences:
        return None
    return Signal(
        pattern_id=pattern.id,
        category=pattern.category,
        action=pattern.action,
        severity=pattern.severity,
        confidence=pattern.confidence,
        occurrences=count,
        minimum_occurrences=pattern.minimum_occurrences,
        excerpts=excerpts,
        matched_texts=matched_texts,
        explanation=pattern.explanation,
        revision_move=pattern.revision_move,
        exceptions=pattern.exceptions,
        evidence_tier=pattern.evidence_tier,
        evidence_urls=pattern.evidence_urls,
        cluster_key=pattern.cluster.key,
    )


def _cluster_units(text: str, scope: ClusterScope) -> tuple[str, ...]:
    if scope == "document":
        return (text,)
    block_boundary = re.compile(
        r"\n\s*\n|(?=^\s*(?:#{1,6}\s+|(?:[-+*]|\d+[.)])\s+))",
        flags=re.MULTILINE,
    )
    return tuple(part for part in block_boundary.split(text) if re.search(r"\w", part))


def _scoped_pattern_signal(pattern: Pattern, text: str) -> Signal | None:
    """Apply paragraph-density rules within one Markdown-like prose block."""

    for unit in _cluster_units(text, pattern.cluster.scope):
        if signal := _pattern_signal(pattern, unit):
            return signal
    return None


def scan_text(text: str, patterns: Sequence[Pattern] | None = None) -> ScanReport:
    """Return conservative revision prompts and explicit uncertainty notes."""

    active_patterns = tuple(patterns) if patterns is not None else load_corpus()
    scanned_text, skipped = prepare_text(text)
    signals = tuple(
        signal
        for pattern in active_patterns
        if (signal := _scoped_pattern_signal(pattern, scanned_text)) is not None
    )
    by_cluster: dict[str, list[Pattern]] = defaultdict(list)
    for pattern in active_patterns:
        by_cluster[pattern.cluster.key].append(pattern)
    gates: list[Gate] = []
    for cluster_key, cluster_patterns in sorted(by_cluster.items()):
        cluster = cluster_patterns[0].cluster
        if not cluster.must_revise:
            continue
        qualifying_ids: tuple[str, ...] = ()
        for unit in _cluster_units(scanned_text, cluster.scope):
            distinct_ids = tuple(
                sorted(pattern.id for pattern in cluster_patterns if _pattern_signal(pattern, unit) is not None)
            )
            if len(distinct_ids) >= cluster.minimum_patterns:
                qualifying_ids = distinct_ids
                break
        if qualifying_ids:
            gates.append(
                Gate(
                    cluster_key=cluster_key,
                    matched_pattern_ids=qualifying_ids,
                    required_distinct_patterns=cluster.minimum_patterns,
                    message=(
                        f"Must-revise cluster within one {cluster.scope}: inspect these related frames together. "
                        "This gate is triggered only by the corpus's explicit multi-pattern rule."
                    ),
                )
            )
    words = lambda value: len(re.findall(r"\b[\w'-]+\b", value))
    metrics = ScanMetrics(
        source_characters=len(text),
        scanned_characters=len(scanned_text),
        source_words=words(text),
        scanned_words=words(scanned_text),
        sentences=len(_sentences(scanned_text)),
        skipped_fenced_code_characters=skipped["fenced_code"],
        skipped_inline_code_characters=skipped["inline_code"],
        skipped_quote_characters=skipped["quotes"],
        skipped_url_characters=skipped["urls"],
    )
    uncertainty = [
        "Signals are revision prompts, not proof of quality, intent, or authorship.",
        "The scanner intentionally ignores code, quoted blocks, and URL destinations where practical; review them separately when they are in scope.",
        "Remove and rewrite labels express the default editorial move, but the scanner cannot evaluate genre, meaning, or listed exceptions; a human must decide whether each use is exact.",
        "The corpus is a representative diagnostic subset of the broader editorial catalogue, not a complete lexical gate.",
    ]
    if metrics.scanned_words < 80:
        uncertainty.append("Short-text warning: fewer than 80 scannable words makes density and cadence signals especially unstable.")
    if metrics.scanned_characters < metrics.source_characters * 0.55:
        uncertainty.append("More than 45% of the source was skipped, so this report covers only a limited prose sample.")
    return ScanReport(
        scanner="better-writing formulaic-language diagnostic v2",
        disclaimer="This is not authorship detection. It reports conservative prose signals and revision prompts only.",
        signals=signals,
        must_revise_gates=tuple(gates),
        metrics=metrics,
        uncertainty=tuple(uncertainty),
    )


def report_as_dict(report: ScanReport) -> dict[str, object]:
    """Convert immutable report data into JSON-safe standard-library shapes."""

    return {
        "scanner": report.scanner,
        "disclaimer": report.disclaimer,
        "signals": [
            {
                "pattern_id": signal.pattern_id,
                "category": signal.category,
                "action": signal.action,
                "severity": signal.severity,
                "confidence": signal.confidence,
                "occurrences": signal.occurrences,
                "minimum_occurrences": signal.minimum_occurrences,
                "excerpts": list(signal.excerpts),
                "matched_texts": list(signal.matched_texts),
                "explanation": signal.explanation,
                "revision_move": signal.revision_move,
                "exceptions": list(signal.exceptions),
                "evidence": {"tier": signal.evidence_tier, "urls": list(signal.evidence_urls)},
                "cluster_key": signal.cluster_key,
            }
            for signal in report.signals
        ],
        "must_revise_gates": [
            {
                "cluster_key": gate.cluster_key,
                "matched_pattern_ids": list(gate.matched_pattern_ids),
                "required_distinct_patterns": gate.required_distinct_patterns,
                "message": gate.message,
            }
            for gate in report.must_revise_gates
        ],
        "gate_passed": not report.must_revise_gates,
        "metrics": {
            "source_characters": report.metrics.source_characters,
            "scanned_characters": report.metrics.scanned_characters,
            "source_words": report.metrics.source_words,
            "scanned_words": report.metrics.scanned_words,
            "sentences": report.metrics.sentences,
            "skipped": {
                "fenced_code_characters": report.metrics.skipped_fenced_code_characters,
                "inline_code_characters": report.metrics.skipped_inline_code_characters,
                "quote_characters": report.metrics.skipped_quote_characters,
                "url_characters": report.metrics.skipped_url_characters,
            },
        },
        "uncertainty": list(report.uncertainty),
    }


def print_text_report(report: ScanReport) -> None:
    """Render a short terminal report without implying a categorical judgement."""

    print(report.disclaimer)
    print(f"Scanned {report.metrics.scanned_words} words in {report.metrics.sentences} sentences.")
    action_counts = {
        action: sum(1 for signal in report.signals if signal.action == action)
        for action in ("remove", "rewrite", "review")
    }
    print(
        f"Signals: {len(report.signals)} | remove: {action_counts['remove']} "
        f"| rewrite: {action_counts['rewrite']} | review: {action_counts['review']} "
        f"| must-revise clusters: {len(report.must_revise_gates)}"
    )
    if report.signals:
        print("\nRevision prompts:")
        for signal in report.signals:
            print(
                f"- [{signal.action}; {signal.severity}/{signal.confidence}] "
                f"{signal.pattern_id}: {signal.explanation}"
            )
            print(f"  Move: {signal.revision_move}")
            if signal.matched_texts:
                print(f"  Match: {signal.matched_texts[0]}")
            if signal.excerpts:
                print(f"  Evidence: {signal.excerpts[0]}")
    if report.must_revise_gates:
        print("\nMust-revise clusters:")
        for gate in report.must_revise_gates:
            print(f"- {gate.cluster_key}: {', '.join(gate.matched_pattern_ids)}")
    print("\nUncertainty:")
    for note in report.uncertainty:
        print(f"- {note}")


def run_self_tests(patterns: Sequence[Pattern] | None = None) -> dict[str, object]:
    """Exercise the safety properties that keep this a revision diagnostic."""

    active_patterns = tuple(patterns) if patterns is not None else load_corpus()
    samples = {
        "single_authority_frame_does_not_gate": "The pattern that keeps showing up is teams delaying ownership.",
        "authority_stack_gates": "The pattern that keeps showing up is delays. The limitation is scope.",
        "code_quote_and_url_are_skipped": "```\nThe limitation is scope.\n```\n> Network restrictions matter.\nSee https://example.com/The-pattern-that-keeps-showing-up\n",
        "ordinary_words_and_one_em_dash_are_not_banned": "The night shift measured an 8 mm gap before the instrument recorded a phase shift — all expected results.",
        "formulaic_gap_and_shift_are_rewrites": "The platform bridges the gap between planning and delivery and marks a significant shift in how teams collaborate.",
        "inline_quotations_are_skipped": 'Mara wrote, “The platform bridges the gap and marks a significant shift.” He quoted "I hope this helps" exactly.',
        "distant_cluster_does_not_gate": "The platform bridges the gap between planning and delivery.\n\nThis paragraph contains enough ordinary prose to stand alone. It marks a significant shift in how teams collaborate.",
        "code_containers_are_skipped": "````\nThe pattern that keeps showing up is delay.\n````\n    The limitation is scope.\n<pre>Network restrictions matter.</pre>\n<code>The platform bridges the gap.</code>",
        "frontmatter_script_and_style_are_skipped": "---\ndescription: The platform bridges the gap and marks a significant shift.\n---\n<script>const note = 'Research shows this is pivotal.';</script>\n<style>/* Here is the kicker: this changes everything. */</style>\nPlain prose remains.",
        "precise_contextual_uses_are_clear": "This policy represents a shift from annual to quarterly audits. The permission enables users to download reports. No trial has compared the groups; this study addresses the defined research gap.",
        "broad_formulaic_families_are_reported": "But here's the kicker: research shows this study aims to explore the issue. Only time will tell.",
        "paragraph_density_stays_local": "The estimate is pivotal.\n\nThe estimate is robust.\n\nThe estimate is seamless.",
        "separate_list_items_do_not_gate": "- The platform bridges the gap between planning and delivery.\n- The policy marks a significant shift in review.",
    }
    reports = {name: scan_text(sample, active_patterns) for name, sample in samples.items()}
    formulaic_ids = {signal.pattern_id for signal in reports["formulaic_gap_and_shift_are_rewrites"].signals}
    broad_ids = {signal.pattern_id for signal in reports["broad_formulaic_families_are_reported"].signals}
    positive_examples_calibrate = all(
        _pattern_signal(pattern, " ".join([example] * pattern.minimum_occurrences)) is not None
        for pattern in active_patterns
        for example in pattern.positive_examples
    )
    counterexamples_clear = all(
        _pattern_signal(pattern, example) is None
        for pattern in active_patterns
        for example in pattern.counterexamples
    )
    checks = {
        "corpus_loads": bool(active_patterns),
        "single_authority_frame_does_not_gate": not reports["single_authority_frame_does_not_gate"].must_revise_gates,
        "authority_stack_gates": any(gate.cluster_key == "compressed-authority-stack" for gate in reports["authority_stack_gates"].must_revise_gates),
        "code_quote_and_url_are_skipped": not reports["code_quote_and_url_are_skipped"].signals,
        "ordinary_words_and_one_em_dash_are_not_banned": not reports["ordinary_words_and_one_em_dash_are_not_banned"].signals,
        "formulaic_gap_and_shift_are_rewrites": {
            "formulaic-gap-bridge-frame",
            "formulaic-shift-verdict-frame",
        }.issubset(formulaic_ids),
        "formulaic_cluster_gates_locally": any(
            gate.cluster_key == "abstract-change-placeholder"
            for gate in reports["formulaic_gap_and_shift_are_rewrites"].must_revise_gates
        ),
        "inline_quotations_are_skipped": not reports["inline_quotations_are_skipped"].signals,
        "distant_cluster_does_not_gate": not reports["distant_cluster_does_not_gate"].must_revise_gates,
        "code_containers_are_skipped": not reports["code_containers_are_skipped"].signals,
        "frontmatter_script_and_style_are_skipped": not reports["frontmatter_script_and_style_are_skipped"].signals,
        "precise_contextual_uses_are_clear": not reports["precise_contextual_uses_are_clear"].signals,
        "broad_formulaic_families_are_reported": {
            "presenter-staged-pivot",
            "vague-attribution-research-claim",
            "academic-purpose-boilerplate",
            "optimism-reset",
        }.issubset(broad_ids),
        "paragraph_density_stays_local": "lexical-elevated-abstract-noun" not in {
            signal.pattern_id for signal in reports["paragraph_density_stays_local"].signals
        },
        "separate_list_items_do_not_gate": not reports["separate_list_items_do_not_gate"].must_revise_gates,
        "matched_text_is_reported": any(
            signal.matched_texts for signal in reports["formulaic_gap_and_shift_are_rewrites"].signals
        ),
        "positive_examples_calibrate": positive_examples_calibrate,
        "counterexamples_clear": counterexamples_clear,
        "short_text_warning": any("Short-text warning" in note for note in reports["single_authority_frame_does_not_gate"].uncertainty),
    }
    return {"passed": all(checks.values()), "checks": checks}


def _read_input(path: str | None, text: str | None) -> str:
    if text is not None:
        return text
    if path is None or path == "-":
        return sys.stdin.read()
    source_path = Path(path)
    if source_path.suffix.lower() not in SUPPORTED_PROSE_SUFFIXES:
        allowed = ", ".join(sorted(suffix or "extensionless" for suffix in SUPPORTED_PROSE_SUFFIXES))
        raise OSError(
            f"refusing non-prose file {source_path}; supported documentation suffixes: {allowed}. "
            "Pass extracted natural-language prose with --text instead."
        )
    return source_path.read_text(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Surface conservative prose revision prompts; never authorship claims.")
    parser.add_argument("path", nargs="?", help="UTF-8 text or Markdown file; omit or use - for stdin")
    parser.add_argument("--text", help="Text to scan directly")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format")
    parser.add_argument(
        "--gate",
        action="store_true",
        help="Exit 1 only when an explicit multi-pattern must-revise cluster is present",
    )
    parser.add_argument("--self-test", action="store_true", help="Run scanner safety checks")
    args = parser.parse_args(argv)
    if args.self_test:
        result = run_self_tests()
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    if args.text is not None and args.path is not None:
        parser.error("pass either a path or --text, not both")
    try:
        report = scan_text(_read_input(args.path, args.text))
    except (CorpusError, OSError) as exc:
        print(f"scan_aiisms: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report_as_dict(report), indent=2))
    else:
        print_text_report(report)
    return 1 if args.gate and report.must_revise_gates else 0


if __name__ == "__main__":
    raise SystemExit(main())

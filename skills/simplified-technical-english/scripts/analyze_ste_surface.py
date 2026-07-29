#!/usr/bin/env python3
"""Report measurable surface candidates in technical prose.

This diagnostic does not contain the ASD-STE100 dictionary and cannot establish
conformance. It gives a conservative word-count estimate and flags text that
requires review against the official standard and governed terminology.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
import re
import sys
from typing import TypedDict


SCHEMA_VERSION = 1
PROCEDURE_WORD_LIMIT = 20
DESCRIPTION_WORD_LIMIT = 25
DESCRIPTION_PARAGRAPH_SENTENCE_LIMIT = 6

FENCE_RE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
PARENTHETICAL_RE = re.compile(r"\([^()\n]*\)")
QUOTED_TEXT_RE = re.compile(r'"[^"\n]*"|“[^”\n]*”')
UNIT_RE = re.compile(
    r"(?<![\w.-])"
    r"[+-]?\d+(?:[.,]\d+)?\s*"
    r"(?:"
    r"N[·*]?m|kN|N|mm|cm|km|m|in|ft|kg|mg|g|lb|"
    r"MPa|kPa|Pa|psi|mV|kV|V|mA|A|kW|W|MHz|kHz|Hz|"
    r"rpm|°C|°F|%|ms|min|s|h|mL|L"
    r")"
    r"(?![\w.-])",
    re.IGNORECASE,
)
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-/][A-Za-z0-9]+)*")
SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)")
CONTRACTION_RE = re.compile(
    r"\b(?:"
    r"can't|cannot've|couldn't|didn't|doesn't|don't|hadn't|hasn't|haven't|"
    r"isn't|mustn't|shouldn't|wasn't|weren't|won't|wouldn't|"
    r"it's|that's|there's|what's|who's|"
    r"[A-Za-z]+(?:n't|'re|'ve|'ll|'d|'m)"
    r")\b",
    re.IGNORECASE,
)
ING_FORM_RE = re.compile(r"\b[A-Za-z][A-Za-z-]*ing\b", re.IGNORECASE)
PASSIVE_CANDIDATE_RE = re.compile(
    r"\b(?:am|are|be|been|being|is|was|were)\s+"
    r"(?:[A-Za-z-]+\s+){0,2}"
    r"[A-Za-z-]+(?:ed|en)\b",
    re.IGNORECASE,
)
COORDINATED_ACTION_RE = re.compile(r"\b(?:and|then)\b", re.IGNORECASE)
LIST_PREFIX_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")

LIMITATIONS = [
    "Word counts are conservative estimates, not official ASD-STE100 counts.",
    "The scanner does not fully collapse proper nouns, labels, headings, placards, or every abbreviation.",
    "Passive voice, coordinated actions, contractions, and -ing forms are review candidates, not automatic violations.",
    "The scanner does not check approved vocabulary, meaning, part of speech, technical terms, clarity, or technical accuracy.",
]


class TextType(StrEnum):
    """Supported text types and their sentence limits."""

    PROCEDURE = "procedure"
    DESCRIPTION = "description"

    @property
    def word_limit(self) -> int:
        if self is TextType.PROCEDURE:
            return PROCEDURE_WORD_LIMIT
        return DESCRIPTION_WORD_LIMIT


class OutputFormat(StrEnum):
    """CLI output formats."""

    TEXT = "text"
    JSON = "json"


class FindingRecord(TypedDict):
    code: str
    line: int
    classification: str
    message: str
    excerpt: str
    estimated_word_count: int | None


class SummaryRecord(TypedDict):
    sentences: int
    paragraphs: int
    findings: int
    estimated_over_limit_sentences: int


class AnalysisRecord(TypedDict):
    schema_version: int
    text_type: str
    sentence_word_limit: int
    summary: SummaryRecord
    findings: list[FindingRecord]
    limitations: list[str]


@dataclass(frozen=True)
class Sentence:
    """A sentence-like unit with source location and estimated word count."""

    line: int
    text: str
    estimated_word_count: int


@dataclass(frozen=True)
class ProseBlock:
    """A prose block assembled across soft line wraps."""

    text: str
    source_offsets: tuple[tuple[int, int], ...]

    @property
    def start_line(self) -> int:
        return self.source_offsets[0][1]

    def source_line(self, character_offset: int) -> int:
        """Return the source line containing a character offset."""

        line = self.start_line
        for offset, candidate_line in self.source_offsets:
            if offset > character_offset:
                break
            line = candidate_line
        return line


@dataclass(frozen=True)
class Finding:
    """A surface candidate that requires review."""

    code: str
    line: int
    classification: str
    message: str
    excerpt: str
    estimated_word_count: int | None = None

    def as_record(self) -> FindingRecord:
        return {
            "code": self.code,
            "line": self.line,
            "classification": self.classification,
            "message": self.message,
            "excerpt": self.excerpt,
            "estimated_word_count": self.estimated_word_count,
        }


@dataclass(frozen=True)
class Analysis:
    """Complete diagnostic result."""

    text_type: TextType
    sentences: tuple[Sentence, ...]
    paragraph_count: int
    findings: tuple[Finding, ...]

    def as_record(self) -> AnalysisRecord:
        over_limit_count = sum(
            finding.code == "estimated-word-limit" for finding in self.findings
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "text_type": self.text_type.value,
            "sentence_word_limit": self.text_type.word_limit,
            "summary": {
                "sentences": len(self.sentences),
                "paragraphs": self.paragraph_count,
                "findings": len(self.findings),
                "estimated_over_limit_sentences": over_limit_count,
            },
            "findings": [finding.as_record() for finding in self.findings],
            "limitations": list(LIMITATIONS),
        }


def mask_fenced_code(text: str) -> str:
    """Replace fenced-code lines with blank lines while preserving line numbers."""

    masked_lines: list[str] = []
    active_fence: str | None = None

    for line in text.splitlines(keepends=True):
        match = FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if active_fence is None:
                active_fence = marker
            elif marker == active_fence:
                active_fence = None
            masked_lines.append("\n" if line.endswith("\n") else "")
            continue

        if active_fence is not None:
            masked_lines.append("\n" if line.endswith("\n") else "")
        else:
            masked_lines.append(line)

    return "".join(masked_lines)


def mask_counting_units(text: str) -> str:
    """Collapse selected Issue 9 counting units to one placeholder token."""

    masked = INLINE_CODE_RE.sub(" STEUNIT ", text)
    masked = QUOTED_TEXT_RE.sub(" STEUNIT ", masked)

    previous = ""
    while previous != masked:
        previous = masked
        masked = PARENTHETICAL_RE.sub(" STEUNIT ", masked)

    return UNIT_RE.sub(" STEUNIT ", masked)


def estimate_word_count(text: str) -> int:
    """Return a conservative count after masking supported special units."""

    return len(WORD_RE.findall(mask_counting_units(text)))


def make_prose_block(fragments: list[tuple[int, str]]) -> ProseBlock:
    """Join source fragments and retain the offset of each physical line."""

    parts: list[str] = []
    source_offsets: list[tuple[int, int]] = []
    character_offset = 0

    for line, fragment in fragments:
        normalized = fragment.strip()
        if not normalized:
            continue
        if parts:
            parts.append(" ")
            character_offset += 1
        source_offsets.append((character_offset, line))
        parts.append(normalized)
        character_offset += len(normalized)

    return ProseBlock(text="".join(parts), source_offsets=tuple(source_offsets))


def prose_blocks(text: str) -> tuple[ProseBlock, ...]:
    """Return prose blocks while joining soft wraps and separating list items."""

    masked = mask_fenced_code(text)
    blocks: list[ProseBlock] = []
    fragments: list[tuple[int, str]] = []
    list_item_active = False

    def flush() -> None:
        nonlocal list_item_active
        if fragments:
            blocks.append(make_prose_block(fragments))
            fragments.clear()
        list_item_active = False

    for line_number, raw_line in enumerate(masked.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            flush()
            continue

        list_match = LIST_PREFIX_RE.match(raw_line)
        if list_match:
            flush()
            fragments.append(
                (line_number, LIST_PREFIX_RE.sub("", raw_line, count=1))
            )
            list_item_active = True
            continue

        if list_item_active and not raw_line[:1].isspace():
            flush()

        fragments.append((line_number, raw_line))

    flush()
    return tuple(blocks)


def sentence_units(text: str) -> tuple[Sentence, ...]:
    """Split prose blocks into sentence-like units without scanning fenced code."""

    sentences: list[Sentence] = []

    for block in prose_blocks(text):
        for match in SENTENCE_RE.finditer(block.text):
            candidate = match.group(0).strip()
            if not WORD_RE.search(candidate):
                continue
            sentences.append(
                Sentence(
                    line=block.source_line(match.start()),
                    text=candidate,
                    estimated_word_count=estimate_word_count(candidate),
                )
            )

    return tuple(sentences)


def prose_paragraphs(text: str) -> tuple[tuple[int, str], ...]:
    """Return non-code prose paragraphs with their starting line numbers."""

    return tuple((block.start_line, block.text) for block in prose_blocks(text))


def clipped(text: str, limit: int = 160) -> str:
    """Return a compact one-line excerpt."""

    one_line = " ".join(text.split())
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 1].rstrip() + "…"


def sentence_findings(sentence: Sentence, text_type: TextType) -> list[Finding]:
    """Return surface candidates for one sentence."""

    findings: list[Finding] = []
    excerpt = clipped(sentence.text)
    surface_text = INLINE_CODE_RE.sub("", sentence.text)

    if sentence.estimated_word_count > text_type.word_limit:
        findings.append(
            Finding(
                code="estimated-word-limit",
                line=sentence.line,
                classification="candidate",
                message=(
                    f"Estimated {sentence.estimated_word_count} words; "
                    f"{text_type.value} limit is {text_type.word_limit}. "
                    "Confirm with the official counting rules."
                ),
                excerpt=excerpt,
                estimated_word_count=sentence.estimated_word_count,
            )
        )

    if ";" in surface_text:
        findings.append(
            Finding(
                code="semicolon",
                line=sentence.line,
                classification="confirmed",
                message="Natural-language text contains a semicolon.",
                excerpt=excerpt,
            )
        )

    if CONTRACTION_RE.search(surface_text):
        findings.append(
            Finding(
                code="contraction",
                line=sentence.line,
                classification="candidate",
                message="Sentence contains a probable contraction.",
                excerpt=excerpt,
            )
        )

    if ING_FORM_RE.search(surface_text):
        findings.append(
            Finding(
                code="ing-form",
                line=sentence.line,
                classification="candidate",
                message="Review each -ing form for its permitted function.",
                excerpt=excerpt,
            )
        )

    if PASSIVE_CANDIDATE_RE.search(surface_text):
        findings.append(
            Finding(
                code="passive-voice",
                line=sentence.line,
                classification="candidate",
                message="Sentence contains a probable passive construction.",
                excerpt=excerpt,
            )
        )

    if text_type is TextType.PROCEDURE and COORDINATED_ACTION_RE.search(surface_text):
        findings.append(
            Finding(
                code="coordinated-action",
                line=sentence.line,
                classification="candidate",
                message="Review whether this procedure sentence contains independent actions.",
                excerpt=excerpt,
            )
        )

    return findings


def paragraph_findings(
    paragraphs: tuple[tuple[int, str], ...],
    text_type: TextType,
) -> list[Finding]:
    """Return description paragraph-length candidates."""

    if text_type is not TextType.DESCRIPTION:
        return []

    findings: list[Finding] = []
    for line, paragraph in paragraphs:
        sentence_count = sum(
            bool(WORD_RE.search(match.group(0)))
            for match in SENTENCE_RE.finditer(paragraph)
        )
        if sentence_count > DESCRIPTION_PARAGRAPH_SENTENCE_LIMIT:
            findings.append(
                Finding(
                    code="paragraph-sentence-limit",
                    line=line,
                    classification="candidate",
                    message=(
                        f"Estimated {sentence_count} sentences in one paragraph; "
                        f"description limit is {DESCRIPTION_PARAGRAPH_SENTENCE_LIMIT}."
                    ),
                    excerpt=clipped(paragraph),
                )
            )
    return findings


def analyze_text(text: str, text_type: TextType) -> Analysis:
    """Analyze one text string."""

    sentences = sentence_units(text)
    paragraphs = prose_paragraphs(text)
    findings: list[Finding] = []

    for sentence in sentences:
        findings.extend(sentence_findings(sentence, text_type))
    findings.extend(paragraph_findings(paragraphs, text_type))

    findings.sort(key=lambda item: (item.line, item.code))
    return Analysis(
        text_type=text_type,
        sentences=sentences,
        paragraph_count=len(paragraphs),
        findings=tuple(findings),
    )


def render_text(analysis: Analysis) -> str:
    """Render a human-readable diagnostic."""

    record = analysis.as_record()
    summary = record["summary"]
    lines = [
        f"Text type: {record['text_type']}",
        f"Sentence word limit: {record['sentence_word_limit']}",
        f"Sentences: {summary['sentences']}",
        f"Paragraphs: {summary['paragraphs']}",
        f"Findings: {summary['findings']}",
    ]

    for finding in analysis.findings:
        lines.extend(
            [
                "",
                f"[{finding.classification}] {finding.code} at line {finding.line}",
                finding.message,
                f"  {finding.excerpt}",
            ]
        )

    lines.append("")
    lines.append("Limitations:")
    lines.extend(f"- {limitation}" for limitation in LIMITATIONS)
    return "\n".join(lines)


def read_input(path: str) -> str:
    """Read UTF-8 input from a file or standard input."""

    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="UTF-8 text file to inspect, or - for standard input")
    parser.add_argument(
        "--text-type",
        required=True,
        choices=[member.value for member in TextType],
        help="Apply the procedure or description surface limits",
    )
    parser.add_argument(
        "--format",
        default=OutputFormat.TEXT.value,
        choices=[member.value for member in OutputFormat],
        help="Output format. Default: text",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        text = read_input(args.path)
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: cannot read {args.path}: {exc}", file=sys.stderr)
        return 2

    analysis = analyze_text(text, TextType(args.text_type))
    if OutputFormat(args.format) is OutputFormat.JSON:
        print(json.dumps(analysis.as_record(), indent=2, sort_keys=True))
    else:
        print(render_text(analysis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

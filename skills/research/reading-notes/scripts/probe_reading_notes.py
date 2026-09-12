#!/usr/bin/env python3
"""Classify a reading-notes source descriptor and emit an intake checklist."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


AUDIO_VIDEO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".mp4", ".mov", ".webm", ".mkv"}
DOCUMENT_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".rtf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".tiff", ".bmp"}


def classify_source(source: str) -> dict[str, Any]:
    text = source.strip()
    lower = text.lower()
    suffix = Path(text).suffix.lower()

    if re.search(r"(youtube\.com|youtu\.be|vimeo\.com|loom\.com)", lower):
        source_type = "video_url"
        capture_steps = [
            "capture title, URL, speaker/channel, and visible date",
            "prefer transcript or captions before summarizing",
            "use timestamps as source anchors when available",
            "mark missing slides, demos, or captions as limitations",
        ]
        risks = ["transcript may omit visual demos", "captions may mistranscribe jargon"]
    elif re.match(r"https?://", lower):
        source_type = "web_url"
        capture_steps = [
            "capture title, URL, author, and visible publication date",
            "fetch the readable page content",
            "preserve headings, links, code blocks, and named references",
            "record paywall, login, or dynamic-content limitations",
        ]
        risks = ["page content may be dynamic", "cached copies may be stale"]
    elif suffix in AUDIO_VIDEO_EXTENSIONS:
        source_type = "audio_video_file"
        capture_steps = [
            "transcribe or use the provided transcript",
            "preserve speaker labels and timestamps when available",
            "separate spoken material from visual or demo observations",
        ]
        risks = ["transcription can miss proper nouns", "visual context may be absent"]
    elif suffix in IMAGE_EXTENSIONS:
        source_type = "image_file"
        capture_steps = [
            "inspect the image directly with native image analysis where available",
            "extract visible text and describe diagrams, arrows, tables, and layout",
            "ask for a higher-resolution image if important text is unreadable",
        ]
        risks = ["OCR may miss diagram meaning", "cropped images can hide context"]
    elif suffix in DOCUMENT_EXTENSIONS or Path(text).exists():
        source_type = "document_file"
        capture_steps = [
            "extract text with the available document parser",
            "preserve headings, page numbers, tables, links, and code blocks",
            "inspect embedded images when they carry meaning",
        ]
        risks = ["document extraction can reorder columns", "slides may omit speaker rationale"]
    else:
        source_type = "raw_notes"
        capture_steps = [
            "use the pasted notes directly as source material",
            "promote headings and indentation into a topic map",
            "keep shorthand uncertainty visible",
            "convert personal reminders into concrete homework todos",
        ]
        risks = ["notes may be incomplete", "shorthand may be ambiguous"]

    return {
        "source_type": source_type,
        "capture_steps": capture_steps,
        "synthesis_sections": [
            "Snapshot",
            "Topics",
            "Interesting Ideas",
            "Homework / Todos",
            "Further Research",
            "Open Questions",
        ],
        "risk_flags": risks,
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [f"Source type: {result['source_type']}", "", "Capture steps:"]
    lines.extend(f"- {step}" for step in result["capture_steps"])
    lines.append("")
    lines.append("Synthesis sections:")
    lines.extend(f"- {section}" for section in result["synthesis_sections"])
    lines.append("")
    lines.append("Risk flags:")
    lines.extend(f"- {risk}" for risk in result["risk_flags"])
    return "\n".join(lines)


def run_suite() -> dict[str, Any]:
    cases = [
        ("https://www.youtube.com/watch?v=abc123", "video_url"),
        ("https://example.com/article", "web_url"),
        ("slides.pdf", "document_file"),
        ("diagram.png", "image_file"),
        ("Laracon notes about ClickHouse and strict Laravel engineering", "raw_notes"),
    ]
    checks = []
    for source, expected in cases:
        actual = classify_source(source)["source_type"]
        checks.append({"source": source, "expected": expected, "actual": actual, "passed": actual == expected})
    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "summary": {
            "checks_total": len(checks),
            "checks_passed": sum(1 for check in checks if check["passed"]),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify a resource for the reading-notes skill.")
    parser.add_argument("--source", help="Resource descriptor, URL, file path, or pasted-note excerpt")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    parser.add_argument("--self-test", action="store_true", help="Run the built-in classifier checks")
    args = parser.parse_args()

    if args.self_test:
        result = run_suite()
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1

    if not args.source:
        parser.error("--source is required unless --self-test is provided")

    result = classify_source(args.source)
    if args.format == "text":
        print(render_text(result))
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

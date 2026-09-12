#!/usr/bin/env python3
"""
Find Azure DevOps fenced-code language aliases using Highlight.js upstream data.

Usage:
    python3 find_code_language.py <query>
    python3 find_code_language.py --refresh <query>

Examples:
    python3 find_code_language.py typescript
    python3 find_code_language.py bicep
    python3 find_code_language.py ls
    python3 find_code_language.py mermaid
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

RAW_URL = "https://raw.githubusercontent.com/highlightjs/highlight.js/main/SUPPORTED_LANGUAGES.md"
CACHE_PATH = Path(__file__).resolve().parent.parent / "assets" / "highlightjs-supported-languages-cache.md"

FALLBACK_ENTRIES = [
    {"language": "Bash", "aliases": ["bash", "sh", "zsh"], "package": ""},
    {"language": "PowerShell", "aliases": ["powershell", "ps", "ps1"], "package": ""},
    {"language": "JSON", "aliases": ["json", "jsonc", "json5"], "package": ""},
    {"language": "YAML", "aliases": ["yml", "yaml"], "package": ""},
    {"language": "Ini, TOML", "aliases": ["ini", "toml"], "package": ""},
    {"language": "HTML, XML", "aliases": ["xml", "html", "xhtml", "rss", "atom", "svg"], "package": ""},
    {"language": "CSS", "aliases": ["css"], "package": ""},
    {"language": "JavaScript", "aliases": ["javascript", "js", "jsx"], "package": ""},
    {"language": "TypeScript", "aliases": ["typescript", "ts", "tsx", "mts", "cts"], "package": ""},
    {"language": "Python", "aliases": ["python", "py"], "package": ""},
    {"language": "C#", "aliases": ["csharp", "cs"], "package": ""},
    {"language": "C++", "aliases": ["cpp", "hpp", "cc", "hh", "c++", "cxx", "hxx"], "package": ""},
    {"language": "SQL", "aliases": ["sql"], "package": ""},
    {"language": "Markdown", "aliases": ["markdown", "md"], "package": ""},
    {
        "language": "Bicep",
        "aliases": ["bicep"],
        "package": "https://github.com/Azure/bicep/blob/main/docs/highlighting.md#highlightjs"
    }
]

FALLBACK_OVERLAPS = {
    "ls": ["Lasso", "LiveScript"],
    "ml": ["OCaml", "SML"]
}


def fetch_remote_markdown() -> str:
    with urlopen(RAW_URL, timeout=20) as response:
        return response.read().decode("utf-8")


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def parse_line_tables(markdown: str) -> tuple[list[dict], dict[str, list[str]]]:
    entries: list[dict] = []
    overlaps: dict[str, list[str]] = {}
    mode = None

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("| Language") and "Package" in line:
            mode = "entries"
            continue
        if line.startswith("| Language") and "Overlap" in line:
            mode = "overlap"
            continue
        if line.startswith("## "):
            mode = None
            continue
        if not line.startswith("|") or line.startswith("| :"):
            continue

        columns = [part.strip() for part in line.strip("|").split("|")]
        if mode == "entries" and len(columns) >= 3:
            language, aliases, package = columns[:3]
            entries.append(
                {
                    "language": language,
                    "aliases": [alias.strip() for alias in aliases.split(",") if alias.strip()],
                    "package": package
                }
            )
        elif mode == "overlap" and len(columns) >= 2:
            language, alias = columns[:2]
            overlaps.setdefault(normalize(alias), []).append(language)

    return entries, overlaps


def parse_flat_pipe_table(markdown: str, headers: list[str], stop_marker: str | None = None) -> list[list[str]]:
    text = markdown.replace("\r", "\n")
    if stop_marker and stop_marker in text:
        text = text.split(stop_marker, 1)[0]

    flat = text.replace("\n", " ")
    header = "| " + " | ".join(headers) + " |"
    start = flat.find(header)
    if start == -1:
        return []

    data = flat[start + len(header):]
    tokens = [token.strip() for token in data.split("|")]

    while tokens and tokens[0] == "":
        tokens.pop(0)

    alignment = tokens[: len(headers)]
    if alignment and all(token and set(token) <= {"-", ":"} for token in alignment):
        tokens = tokens[len(headers):]
        while tokens and tokens[0] == "":
            tokens.pop(0)

    width = len(headers) + 1
    rows: list[list[str]] = []
    index = 0
    while index + len(headers) <= len(tokens):
        if index < len(tokens) and tokens[index] == "":
            index += 1
            continue

        chunk = tokens[index:index + width]
        values = chunk[: len(headers)]
        if len(values) < len(headers) or not any(values):
            break
        if values[0].startswith("## "):
            break
        rows.append(values)
        index += width

    return rows


def parse_entries(markdown: str) -> list[dict]:
    line_entries, _ = parse_line_tables(markdown)
    if line_entries:
        return line_entries

    rows = parse_flat_pipe_table(markdown, ["Language", "Aliases", "Package"], stop_marker="## Alias Overlap")
    entries = []
    for language, aliases, package in rows:
        if language in {"Language", ""}:
            continue
        alias_list = [alias.strip() for alias in aliases.split(",") if alias.strip()]
        entries.append(
            {
                "language": language,
                "aliases": alias_list,
                "package": package
            }
        )
    return entries


def parse_overlaps(markdown: str) -> dict[str, list[str]]:
    _, line_overlaps = parse_line_tables(markdown)
    if line_overlaps:
        return line_overlaps

    if "## Alias Overlap" not in markdown:
        return {}

    overlap_text = markdown.split("## Alias Overlap", 1)[1]
    rows = parse_flat_pipe_table(overlap_text, ["Language", "Overlap"])
    overlaps: dict[str, list[str]] = {}
    for language, alias in rows:
        if not language or not alias or language == "Language":
            continue
        overlaps.setdefault(normalize(alias), []).append(language)
    return overlaps


def load_entries(refresh: bool) -> tuple[list[dict], dict[str, list[str]], str]:
    if refresh:
        markdown = fetch_remote_markdown()
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(markdown, encoding="utf-8")
        return parse_entries(markdown), parse_overlaps(markdown), "remote"

    if CACHE_PATH.exists():
        markdown = CACHE_PATH.read_text(encoding="utf-8")
        return parse_entries(markdown), parse_overlaps(markdown), "cache"

    try:
        markdown = fetch_remote_markdown()
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(markdown, encoding="utf-8")
        return parse_entries(markdown), parse_overlaps(markdown), "remote"
    except (URLError, TimeoutError, OSError):
        return FALLBACK_ENTRIES, FALLBACK_OVERLAPS, "builtin-fallback"


def find_matches(entries: list[dict], query: str) -> list[dict]:
    normalized_query = normalize(query)
    exact_matches = []
    fuzzy_matches = []
    for entry in entries:
        language = normalize(entry["language"])
        aliases = [normalize(alias) for alias in entry["aliases"]]
        if normalized_query == language or normalized_query in aliases:
            exact_matches.append(entry)
            continue
        if normalized_query in language or any(normalized_query in alias for alias in aliases):
            fuzzy_matches.append(entry)
    return exact_matches or fuzzy_matches


def build_notes(query: str, source: str, matches: list[dict], overlaps: dict[str, list[str]]) -> list[str]:
    notes = []
    if source == "builtin-fallback":
        notes.append("Network lookup failed, so results came from the built-in safe alias list.")
    elif source == "cache":
        notes.append(f"Results came from the cached Highlight.js table at {CACHE_PATH}.")
    else:
        notes.append("Results came from the live official Highlight.js supported-language table.")

    normalized_query = normalize(query)

    if normalized_query == "mermaid":
        notes.append("Mermaid is not a Highlight.js language alias. In Azure DevOps wiki pages, use ::: mermaid blocks instead.")

    if normalized_query in overlaps:
        notes.append(
            "Alias overlap detected for "
            f"'{query}': {', '.join(overlaps[normalized_query])}. Prefer the full language name."
        )

    third_party = [entry["language"] for entry in matches if entry["package"]]
    if third_party:
        notes.append(
            "These matches are third-party Highlight.js packages upstream, not guaranteed core-bundle languages: "
            + ", ".join(third_party)
            + ". Verify them locally before promising highlighting."
        )

    if normalized_query in {"kusto", "kql"} and not matches:
        notes.append("Kusto / KQL was not found in the current upstream table. Prefer sql or plaintext unless the user has verified a working alias.")

    if not matches:
        notes.append("No matching language alias was found.")

    return notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Language name or alias to look up")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh the cached Highlight.js table from the official upstream source"
    )
    args = parser.parse_args()

    try:
        entries, overlaps, source = load_entries(refresh=args.refresh)
    except (URLError, TimeoutError, OSError) as exc:
        print(json.dumps({"error": str(exc), "query": args.query}), file=sys.stderr)
        return 1

    matches = find_matches(entries, args.query)
    payload = {
        "query": args.query,
        "source": source,
        "source_url": RAW_URL,
        "match_count": len(matches),
        "matches": matches,
        "alias_overlap": overlaps.get(normalize(args.query), []),
        "notes": build_notes(args.query, source, matches, overlaps)
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

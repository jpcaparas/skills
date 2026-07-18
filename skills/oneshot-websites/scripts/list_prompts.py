#!/usr/bin/env python3
"""List and search the canonical oneshot-websites prompt catalogue."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from runtime_contract import parse_json_bounded


CATALOGUE_PATH = Path(__file__).resolve().parent.parent / "assets" / "prompt-catalogue.json"


class CatalogueError(ValueError):
    """Raised when the canonical catalogue does not meet its display contract."""


@dataclass(frozen=True)
class Category:
    """Display metadata for a catalogue category."""

    identifier: str
    title: str
    description: str


@dataclass(frozen=True)
class PromptEntry:
    """A validated catalogue prompt, retaining its original JSON shape for output."""

    identifier: str
    slug: str
    title: str
    category: str
    prompt: str
    tags: tuple[str, ...]
    raw: dict[str, Any]


@dataclass(frozen=True)
class Catalogue:
    """Validated catalogue metadata and prompt entries."""

    experience_direction: str
    categories: tuple[Category, ...]
    prompts: tuple[PromptEntry, ...]


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments without imposing a result-size default."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search", metavar="TEXT", help="Search title, slug, tags, and prompt text")
    parser.add_argument(
        "--category",
        action="append",
        nargs="+",
        default=[],
        metavar="CATEGORY",
        help="Keep entries in this category (repeatable)",
    )
    parser.add_argument(
        "--tag",
        action="append",
        nargs="+",
        default=[],
        metavar="TAG",
        help="Keep entries containing this tag (repeatable; all tags must match)",
    )
    parser.add_argument(
        "--ids",
        action="append",
        nargs="+",
        default=[],
        metavar="ID[,ID...]",
        help="Keep these comma-separated prompt IDs (repeatable)",
    )
    parser.add_argument("--limit", type=positive_limit, help="Maximum number of matching prompts to show")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format (default: markdown)",
    )
    return parser.parse_args(argv)


def positive_limit(value: str) -> int:
    """Accept only useful, explicit display limits."""

    try:
        limit = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("limit must be a positive integer") from error
    if limit < 1:
        raise argparse.ArgumentTypeError("limit must be a positive integer")
    return limit


def load_catalogue(path: Path = CATALOGUE_PATH) -> Catalogue:
    """Load the shared direction, categories, and entries from canonical JSON."""

    try:
        loaded = parse_json_bounded(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CatalogueError(f"catalogue file not found: {path}") from error
    except UnicodeDecodeError as error:
        raise CatalogueError(f"catalogue is not valid UTF-8: {path}") from error
    except (json.JSONDecodeError, RecursionError, ValueError) as error:
        raise CatalogueError(f"catalogue is not valid JSON: {error}") from error

    if not isinstance(loaded, dict):
        raise CatalogueError("catalogue root must be a JSON object")

    raw_categories = loaded.get("categories", [])
    raw_entries = loaded.get("prompts", loaded.get("entries", loaded.get("items")))
    if raw_entries is None:
        raise CatalogueError("catalogue must contain a prompts array")
    if not isinstance(raw_categories, list):
        raise CatalogueError("catalogue categories must be an array")
    if not isinstance(raw_entries, list):
        raise CatalogueError("catalogue prompts must be an array")

    experience_direction = required_string(loaded, "experienceDirection", "catalogue")
    categories = tuple(parse_category(item, index) for index, item in enumerate(raw_categories, start=1))
    entries = tuple(parse_entry(item, index) for index, item in enumerate(raw_entries, start=1))
    category_ids = {category.identifier for category in categories}
    undeclared = sorted({entry.category for entry in entries} - category_ids, key=str.casefold)
    if undeclared:
        raise CatalogueError(f"catalogue prompts use undeclared categories: {', '.join(undeclared)}")
    return Catalogue(
        experience_direction=experience_direction,
        categories=categories,
        prompts=entries,
    )


def parse_category(value: object, index: int) -> Category:
    """Validate one category declaration and its display explanation."""

    if not isinstance(value, dict):
        raise CatalogueError(f"category {index} must be an object")
    identifier = required_string(value, "id", f"category {index}")
    title = optional_string(value, "title") or optional_string(value, "name") or humanize(identifier)
    description = required_string(value, "description", f"category {index}")
    return Category(identifier=identifier, title=title, description=description)


def parse_entry(value: object, index: int) -> PromptEntry:
    """Validate one prompt entry while preserving its JSON-compatible fields."""

    if not isinstance(value, dict):
        raise CatalogueError(f"prompt {index} must be an object")
    context = f"prompt {index}"
    tags_value = value.get("tags")
    if not isinstance(tags_value, list) or not tags_value or not all(isinstance(tag, str) and tag.strip() for tag in tags_value):
        raise CatalogueError(f"{context} tags must be a non-empty array of strings")
    return PromptEntry(
        identifier=required_string(value, "id", context),
        slug=required_string(value, "slug", context),
        title=required_string(value, "title", context),
        category=required_string(value, "category", context),
        prompt=required_string(value, "prompt", context),
        tags=tuple(tag.strip() for tag in tags_value),
        raw=value,
    )


def required_string(value: dict[str, Any], field: str, context: str) -> str:
    """Read a non-blank JSON string with a clear validation error."""

    result = value.get(field)
    if not isinstance(result, str) or not result.strip():
        raise CatalogueError(f"{context} {field} must be a non-empty string")
    return result.strip()


def optional_string(value: dict[str, Any], field: str) -> Optional[str]:
    """Read an optional string, rejecting malformed explicit values."""

    result = value.get(field)
    if result is None:
        return None
    if not isinstance(result, str):
        raise CatalogueError(f"{field} must be a string when supplied")
    stripped = result.strip()
    return stripped or None


def humanize(identifier: str) -> str:
    """Produce a stable fallback label for an undeclared category."""

    return re.sub(r"[-_]+", " ", identifier).strip().title() or "Uncategorized"


def one_line(value: str) -> str:
    """Collapse display prose to one readable physical line."""

    return re.sub(r"\s+", " ", value).strip()


def split_values(values: Iterable[Any]) -> set[str]:
    """Normalize repeatable, comma-separated filter values."""

    return {
        part.strip().casefold()
        for value in values
        for item in (value if isinstance(value, list) else [value])
        if isinstance(item, str)
        for part in item.split(",")
        if part.strip()
    }


def select_entries(entries: Sequence[PromptEntry], arguments: argparse.Namespace) -> list[PromptEntry]:
    """Apply all filters, then rank a text search without nondeterministic ties."""

    categories = split_values(arguments.category)
    tags = split_values(arguments.tag)
    identifiers = split_values(arguments.ids)
    search = (arguments.search or "").strip()

    selected = [
        entry
        for entry in entries
        if (not categories or entry.category.casefold() in categories)
        and (not tags or tags.issubset({tag.casefold() for tag in entry.tags}))
        and (not identifiers or entry.identifier.casefold() in identifiers)
        and (not search or search_matches(entry, search))
    ]
    if search:
        selected.sort(key=lambda entry: search_sort_key(entry, search))
    if arguments.limit is not None:
        return selected[: arguments.limit]
    return selected


def search_matches(entry: PromptEntry, search: str) -> bool:
    """Require each search term to appear somewhere in the searchable entry text."""

    terms = search.casefold().split()
    searchable = " ".join((entry.title, entry.slug, " ".join(entry.tags), entry.prompt)).casefold()
    return all(term in searchable for term in terms)


def search_sort_key(entry: PromptEntry, search: str) -> tuple[int, int, int, int, int, str, str, str]:
    """Rank title, slug, tags, and prompt matches in documented priority order."""

    query = search.casefold()
    fields = (entry.title.casefold(), entry.slug.casefold(), " ".join(entry.tags).casefold(), entry.prompt.casefold())
    weights = (400, 300, 200, 100)
    score = sum(field_score(field, query, weight) for field, weight in zip(fields, weights))
    positions = tuple(first_position(field, query) for field in fields)
    return (-score, *positions, entry.title.casefold(), entry.slug.casefold(), entry.identifier.casefold())


def field_score(field: str, query: str, weight: int) -> int:
    """Score exact, prefix, substring, and individual-term field matches."""

    if field == query:
        return weight * 4
    if field.startswith(query):
        return weight * 3
    if query in field:
        return weight * 2
    return weight * sum(term in field for term in query.split())


def first_position(field: str, query: str) -> int:
    """Use an explicit finite sentinel so sort ordering stays deterministic."""

    position = field.find(query)
    return position if position >= 0 else sys.maxsize


def group_entries(
    categories: Sequence[Category], entries: Sequence[PromptEntry]
) -> list[tuple[Category, list[PromptEntry]]]:
    """Keep declared category order and append undeclared categories predictably."""

    grouped: dict[str, list[PromptEntry]] = {}
    for entry in entries:
        grouped.setdefault(entry.category, []).append(entry)

    result: list[tuple[Category, list[PromptEntry]]] = []
    for category in categories:
        if category.identifier in grouped:
            result.append((category, grouped.pop(category.identifier)))
    for identifier in sorted(grouped, key=str.casefold):
        result.append((Category(identifier, humanize(identifier), f"Prompts grouped under {humanize(identifier)}."), grouped[identifier]))
    return result


def markdown_output(catalogue: Catalogue, entries: Sequence[PromptEntry]) -> str:
    """Render a compact option menu grouped by explicit namespace."""

    lines = [
        "# Oneshot Websites Prompt Catalogue",
        "",
        f"{len(entries)} prompt(s), grouped by namespace. Choose an ID or slug, or send a custom brief.",
        "",
        f"Shared experience direction: {one_line(catalogue.experience_direction)}",
    ]
    for category, grouped in group_entries(catalogue.categories, entries):
        lines.extend(("", f"## Namespace `{category.identifier}` — {category.title}"))
        lines.extend(("", one_line(category.description)))
        for entry in grouped:
            lines.append(
                f"- `{entry.identifier}` · `{entry.slug}` — **{entry.title}** — {one_line(entry.prompt)}"
            )
    return "\n".join(lines) + "\n"


def json_output(catalogue: Catalogue, entries: Sequence[PromptEntry]) -> str:
    """Render the same grouped result as machine-readable JSON."""

    groups = []
    for category, grouped in group_entries(catalogue.categories, entries):
        group: dict[str, Any] = {
            "id": category.identifier,
            "title": category.title,
            "description": category.description,
            "prompts": [entry.raw for entry in grouped],
        }
        groups.append(group)
    return json.dumps(
        {
            "count": len(entries),
            "experienceDirection": catalogue.experience_direction,
            "categories": groups,
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the catalogue browser and print a single requested representation."""

    arguments = parse_arguments(argv)
    try:
        catalogue = load_catalogue()
        selected = select_entries(catalogue.prompts, arguments)
    except CatalogueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    output = json_output(catalogue, selected) if arguments.format == "json" else markdown_output(catalogue, selected)
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

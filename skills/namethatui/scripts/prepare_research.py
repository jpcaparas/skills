#!/usr/bin/env python3
"""Build bounded UI-component research queries and reject blocked URLs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Sequence
from urllib.parse import unquote, urlsplit


BLOCKED_HOST = "namethatui.com"
MAX_QUERY_LENGTH = 400
DIRECT_INDEXES: tuple[tuple[str, str], ...] = (
    ("WAI-ARIA APG patterns", "https://www.w3.org/WAI/ARIA/apg/patterns/"),
    ("Open UI component name matrix", "https://open-ui.org/research/component-matrix/"),
    (
        "MDN ARIA roles",
        "https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles",
    ),
)
HTTP_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
DOMAIN_TOKEN_PATTERN = re.compile(
    r"(?<![a-z0-9.-])(?:[a-z0-9-]+\.)+[a-z]{2,}(?::[0-9]+)?(?:/[^\s<>\"']*)?",
    re.IGNORECASE,
)
TRAILING_URL_PUNCTUATION = ".,;:!?)]}"


class DecisionStatus(str, Enum):
    """Stable result states emitted by the URL guard."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class UrlDecision:
    """One URL and the guard decision that applies to it."""

    url: str
    status: DecisionStatus
    reason: str
    hostname: str | None


@dataclass(frozen=True, slots=True)
class ResearchPlan:
    """Structured plan consumed by an agent or search adapter."""

    clue: str
    candidates: tuple[str, ...]
    platform: str | None
    queries: tuple[str, ...]
    exclude_domains: tuple[str, ...]
    direct_indexes: tuple[SourceIndex, ...]
    blocked_host_rule: str


@dataclass(frozen=True, slots=True)
class SourceIndex:
    """One curated index suitable for direct browser inspection."""

    name: str
    url: str


def normalize_whitespace(value: str) -> str:
    """Collapse whitespace so queries remain bounded and predictable."""

    return " ".join(value.split())


def remove_blocked_reference(value: str) -> str:
    """Remove only parsed blocked-host references from user-controlled text."""

    def filter_token(match: re.Match[str], *, prepend_scheme: bool) -> str:
        token = match.group(0)
        core = token.rstrip(TRAILING_URL_PUNCTUATION)
        trailing = token[len(core) :]
        inspected = f"https://{core}" if prepend_scheme else core
        decision = inspect_url(inspected)
        if decision.status is DecisionStatus.BLOCKED:
            return trailing
        if decision.status is DecisionStatus.INVALID and is_blocked_reference_text(core):
            return trailing
        return token

    without_urls = HTTP_URL_PATTERN.sub(
        lambda match: filter_token(match, prepend_scheme=False),
        value,
    )
    without_bare_hosts = DOMAIN_TOKEN_PATTERN.sub(
        lambda match: filter_token(match, prepend_scheme=True),
        without_urls,
    )
    return normalize_whitespace(without_bare_hosts)


def is_blocked_reference_text(value: str) -> bool:
    """Conservatively recognize an exact blocked host inside an invalid URL token."""

    normalized = value.casefold().replace("\u3002", ".").replace("\uff0e", ".").replace("\uff61", ".")
    return normalized.startswith(f"{BLOCKED_HOST}/") or normalized.startswith(
        f"{BLOCKED_HOST}\\"
    ) or normalized == BLOCKED_HOST


def normalize_hostname(hostname: str) -> str:
    """Normalize a parsed hostname for exact and subdomain comparison."""

    dotted = unquote(hostname).replace("\u3002", ".").replace("\uff0e", ".").replace("\uff61", ".")
    return dotted.rstrip(".").lower().encode("idna").decode("ascii")


def is_blocked_hostname(hostname: str) -> bool:
    """Return true for the blocked origin and every real subdomain."""

    normalized = normalize_hostname(hostname)
    return normalized == BLOCKED_HOST or normalized.endswith(f".{BLOCKED_HOST}")


def inspect_url(raw_url: str) -> UrlDecision:
    """Classify a URL without performing network access."""

    candidate = raw_url.strip()
    if not candidate:
        return UrlDecision(raw_url, DecisionStatus.INVALID, "URL is empty.", None)
    if "\\" in candidate:
        return UrlDecision(
            candidate,
            DecisionStatus.INVALID,
            "Backslashes are rejected to avoid browser URL-parser ambiguity.",
            None,
        )
    if any(character.isspace() for character in candidate):
        return UrlDecision(
            candidate,
            DecisionStatus.INVALID,
            "Raw whitespace is not allowed in a research URL.",
            None,
        )

    try:
        parsed = urlsplit(candidate)
    except ValueError as exc:
        return UrlDecision(candidate, DecisionStatus.INVALID, f"URL cannot be parsed: {exc}", None)

    if parsed.scheme.lower() not in {"http", "https"}:
        return UrlDecision(
            candidate,
            DecisionStatus.INVALID,
            "Only HTTP and HTTPS URLs can be researched.",
            None,
        )
    if parsed.username is not None or parsed.password is not None:
        return UrlDecision(
            candidate,
            DecisionStatus.INVALID,
            "URLs with embedded credentials are rejected.",
            parsed.hostname,
        )
    if "%" in parsed.netloc:
        return UrlDecision(
            candidate,
            DecisionStatus.INVALID,
            "Percent-encoded hostnames are rejected.",
            parsed.hostname,
        )
    if parsed.hostname is None:
        return UrlDecision(candidate, DecisionStatus.INVALID, "URL has no hostname.", None)

    try:
        hostname = normalize_hostname(parsed.hostname)
    except UnicodeError:
        return UrlDecision(
            candidate,
            DecisionStatus.INVALID,
            "Hostname cannot be normalized safely.",
            parsed.hostname,
        )

    if is_blocked_hostname(hostname):
        return UrlDecision(
            candidate,
            DecisionStatus.BLOCKED,
            "Hostname is the blocked origin or one of its subdomains.",
            hostname,
        )
    return UrlDecision(candidate, DecisionStatus.ALLOWED, "Hostname passed the guard.", hostname)


def unique_values(values: Sequence[str]) -> tuple[str, ...]:
    """Deduplicate normalized values while preserving input order."""

    seen: set[str] = set()
    result: list[str] = []
    for raw_value in values:
        value = remove_blocked_reference(raw_value)
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return tuple(result)


def truncate_query_segment(value: str, maximum_length: int) -> str:
    """Truncate only user-controlled query text while preserving fixed operators."""

    if maximum_length <= 0:
        return ""
    if len(value) <= maximum_length:
        return value
    if maximum_length == 1:
        return "…"
    return value[: maximum_length - 1].rstrip() + "…"


def bounded_query(
    user_parts: Sequence[str],
    *,
    prefix_parts: Sequence[str] = (),
    suffix_parts: Sequence[str] = (),
) -> str:
    """Bound user text while retaining required query prefixes and suffixes."""

    prefix = tuple(normalize_whitespace(part) for part in prefix_parts if part)
    suffix = tuple(normalize_whitespace(part) for part in suffix_parts if part)
    user_text = normalize_whitespace(" ".join(part for part in user_parts if part))
    fixed_parts = (*prefix, *suffix)
    if not user_text:
        query = " ".join(fixed_parts)
        if len(query) > MAX_QUERY_LENGTH:
            raise ValueError("Fixed query operators exceed the query length ceiling.")
        return query

    separator_count = len(fixed_parts)
    available = MAX_QUERY_LENGTH - sum(len(part) for part in fixed_parts) - separator_count
    bounded_user = truncate_query_segment(user_text, available)
    return " ".join((*prefix, bounded_user, *suffix))


def unique_queries(queries: Sequence[str]) -> tuple[str, ...]:
    """Deduplicate completed queries without removing the exclusion term."""

    seen: set[str] = set()
    result: list[str] = []
    for raw_query in queries:
        query = normalize_whitespace(raw_query)
        key = query.casefold()
        if not query or key in seen:
            continue
        seen.add(key)
        result.append(query)
    return tuple(result)


def build_queries(
    clue: str,
    candidates: Sequence[str],
    platform: str | None,
    max_queries: int,
) -> tuple[str, ...]:
    """Create a small query set that covers description, aliases, and standards."""

    safe_clue = remove_blocked_reference(clue)
    safe_candidates = unique_values(candidates)
    safe_platform = remove_blocked_reference(platform or "")
    exclusion = f"-site:{BLOCKED_HOST}"

    queries: list[str] = [
        bounded_query(
            (safe_clue, safe_platform),
            suffix_parts=("UI component pattern official documentation", exclusion),
        )
    ]
    for candidate in safe_candidates:
        queries.append(
            bounded_query(
                (candidate, safe_clue, safe_platform),
                suffix_parts=("UI component", "official documentation", exclusion),
            )
        )
    if safe_candidates:
        queries.append(
            bounded_query(
                (safe_candidates[0],),
                prefix_parts=("site:w3.org/WAI/ARIA/apg/patterns",),
                suffix_parts=("pattern",),
            )
        )

    return unique_queries(queries)[:max_queries]


def build_plan(
    clue: str,
    candidates: Sequence[str],
    platform: str | None,
    max_queries: int,
) -> ResearchPlan:
    """Build the structured research plan."""

    safe_clue = remove_blocked_reference(clue)
    if not safe_clue:
        raise ValueError("The clue is empty after blocked-origin references are removed.")
    if not 1 <= max_queries <= 12:
        raise ValueError("--max-queries must be between 1 and 12.")

    safe_candidates = unique_values(candidates)
    safe_platform = remove_blocked_reference(platform or "") or None
    indexes = tuple(SourceIndex(name=name, url=url) for name, url in DIRECT_INDEXES)
    return ResearchPlan(
        clue=safe_clue,
        candidates=safe_candidates,
        platform=safe_platform,
        queries=build_queries(safe_clue, safe_candidates, safe_platform, max_queries),
        exclude_domains=(BLOCKED_HOST,),
        direct_indexes=indexes,
        blocked_host_rule=(
            "Reject a hostname equal to namethatui.com or ending in .namethatui.com "
            "before navigation and after redirects."
        ),
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Emit a bounded JSON research plan.")
    plan_parser.add_argument("--clue", required=True, help="Plain-language behavior or visual clue.")
    plan_parser.add_argument(
        "--candidate",
        action="append",
        default=[],
        help="Likely component name or alias. Repeat for multiple candidates.",
    )
    plan_parser.add_argument("--platform", help="Optional platform or design-system context.")
    plan_parser.add_argument(
        "--max-queries",
        type=int,
        default=6,
        help="Maximum queries to emit, from 1 to 12. Default: 6.",
    )

    url_parser = subparsers.add_parser(
        "check-url",
        help="Classify URLs without opening them; exits 2 when any URL is unsafe.",
    )
    url_parser.add_argument("urls", nargs="+", help="One or more HTTP(S) URLs to inspect.")
    return parser


def emit_json(payload: object) -> None:
    """Write stable, UTF-8 JSON to stdout."""

    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def run(argv: Sequence[str]) -> int:
    """Execute the selected command and return its process exit code."""

    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command == "plan":
        try:
            plan = build_plan(
                clue=str(args.clue),
                candidates=tuple(str(value) for value in args.candidate),
                platform=str(args.platform) if args.platform else None,
                max_queries=int(args.max_queries),
            )
        except ValueError as exc:
            parser.error(str(exc))
        emit_json(asdict(plan))
        return 0

    decisions = tuple(inspect_url(str(url)) for url in args.urls)
    emit_json(
        {
            "decisions": [asdict(decision) for decision in decisions],
            "summary": {
                status.value: sum(decision.status is status for decision in decisions)
                for status in DecisionStatus
            },
        }
    )
    return 0 if all(decision.status is DecisionStatus.ALLOWED for decision in decisions) else 2


def main() -> None:
    """CLI entry point."""

    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()

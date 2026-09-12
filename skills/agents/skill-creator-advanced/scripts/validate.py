#!/usr/bin/env python3
"""Validate an installable skill in draft or release mode.

Release is the default and enforces a complete, publishable package. Draft mode
keeps incomplete scaffolds inspectable by turning completion checks into
warnings while retaining structural and containment safety checks.

Usage:
    python3 validate.py <skill-path> [--profile draft|release]

Output:
    Human-readable findings followed by a JSON result for every supplied path.
    Argparse usage errors are written to stderr before validation begins.

Exit codes:
    0 = valid for the selected profile
    1 = invalid skill path or validation failure
    2 = command-line usage error reported by argparse
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import stat
import unicodedata
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable
from urllib.parse import unquote


PROFILES = ("draft", "release")
MAX_INTEROPERABLE_INTEGER = 9_007_199_254_740_991
ASSERTION_TYPES = frozenset(
    {"functional", "structural", "disclosure", "negative", "verification"}
)
ENTRY_MARKDOWN_NAMES = frozenset({"SKILL.md", "README.md", "AGENTS.md"})
SUPPORT_DIRECTORY_NAMES = (
    "references",
    "scripts",
    "templates",
    "evals",
    "assets",
    "agents",
)
EVAL_MANIFEST_KEYS = frozenset({"skill_name", "created_by", "evals"})
EVAL_CASE_KEYS = frozenset(
    {"id", "name", "prompt", "expected_output", "files", "assertions", "tags"}
)
ASSERTION_KEYS = frozenset({"text", "type"})
EVAL_NAME_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")
RUNTIME_TEMPLATE_ACTIONS = frozenset({"break", "continue", "else", "end"})
TEACHING_FENCE_LANGUAGES = frozenset(
    {"example", "json", "markdown", "md", "plaintext", "text"}
)
EXPLICIT_AUTHORING_MARKER_RE = re.compile(
    r"\b(?:TODO|TBD|FIXME)(?:\([^)\n]+\))?\s*:|"
    r"^[ \t]*(?:[-*+]\s+|\d+[.)]\s+)?(?:TODO|TBD|FIXME)"
    r"(?:\([^)\n]+\))?(?=\s)",
    re.IGNORECASE | re.MULTILINE,
)
LEADING_AUTHORING_MARKER_RE = re.compile(
    r"^[ \t]*(?:(?:#|//|--|/\*|\*)[ \t]*)?"
    r"(?:[-*+]\s+|\d+[.)]\s+)?(?:TODO|TBD|FIXME)"
    r"(?:\([^\)\n]+\))?(?=\s|:|$)",
    re.IGNORECASE | re.MULTILINE,
)
LABEL_AUTHORING_MARKER_RE = re.compile(
    r":\s*(?:TODO|TBD|FIXME)(?:\([^\)\n]+\))?(?=\s|[.,;:!?)]|$)",
    re.IGNORECASE,
)
SCRIPT_COMMENT_AUTHORING_MARKER_RE = re.compile(
    r"(?:#|//|--|/\*|\*)[ \t]*(?:TODO|TBD|FIXME)"
    r"(?:\([^\)\n]+\))?(?=\s|:|$)",
    re.IGNORECASE,
)
SCRIPT_BEHAVIOR_AUTHORING_MARKER_RE = re.compile(
    r"^[ \t]*(?:raise\b|throw\b|panic!?\s*\(|die\s*\(|fatal\s*\()[^\n]*?"
    r"(?P<marker>\b(?:TODO|TBD|FIXME)(?:\([^\)\n]+\))?\s*:)",
    re.IGNORECASE | re.MULTILINE,
)
MUSTACHE_TOKEN_RE = re.compile(r"\{\{([^{}\n]+)\}\}")
SIMPLE_AUTHOR_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
YAML_NUMBER_RE = re.compile(
    r"[-+]?[0-9][0-9_]*(?:\.[0-9_]*)?(?:[eE][-+]?[0-9]+)?|"
    r"[-+]?0[xob][0-9A-Fa-f_]+|[-+]?\.(?:inf|nan)",
    re.IGNORECASE,
)
YAML_DATE_RE = re.compile(r"\d{4}-\d{1,2}-\d{1,2}(?:[Tt ]|$)")
EXTERNAL_TARGET_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
REFERENCE_DEFINITION_RE = re.compile(r"^ {0,3}\[([^\]\n]+)\]:\s*(.+?)\s*$", re.MULTILINE)
HTML_ATTRIBUTE_RE = re.compile(
    r"\b(?:href|src)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))",
    re.IGNORECASE,
)
LOCAL_AUTOLINK_RE = re.compile(
    r"<((?:(?:references|scripts|templates|assets|agents|evals)[\\/]|"
    r"\.\.?[\\/]|%2e(?:%2e)?(?:%2f|%5c)|/|[A-Za-z]:[\\/]|"
    r"\\\\|file:)[^<>\s]+)>",
    re.IGNORECASE,
)
INLINE_PATH_RE = re.compile(
    r"`((?:(?:references|scripts|templates|assets|agents|evals)[\\/]|"
    r"\.\.?[\\/]|%2e(?:%2e)?(?:%2f|%5c)|/|"
    r"[A-Za-z]:[\\/]|\\\\|file:)[^`\n]+)`",
    re.IGNORECASE,
)


def strip_frontmatter_inline_comment(value: str) -> str:
    """Strip a YAML-style comment only when it is outside quotes/flow values."""
    quote: str | None = None
    escaped = False
    flow_depth = 0
    index = 0
    while index < len(value):
        character = value[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif quote == '"' and character == "\\":
                escaped = True
            elif character == quote:
                if quote == "'" and index + 1 < len(value) and value[index + 1] == "'":
                    index += 1
                else:
                    quote = None
        elif character in {'"', "'"}:
            quote = character
        elif character in "[{":
            flow_depth += 1
        elif character in "]}" and flow_depth:
            flow_depth -= 1
        elif character == "#" and flow_depth == 0 and (
            index == 0 or value[index - 1].isspace()
        ):
            return value[:index].rstrip()
        index += 1
    return value.rstrip()


def frontmatter_value_diagnostics(value: str, line_number: int) -> list[str]:
    """Catch obvious quote/flow syntax errors without interpreting owner fields."""
    diagnostics: list[str] = []
    quote: str | None = None
    escaped = False
    flow_stack: list[str] = []
    allowed_double_escapes = set('0abtnvfre "\\/N_LPxuU')
    index = 0
    while index < len(value):
        character = value[index]
        if quote is not None:
            if escaped:
                if quote == '"' and character not in allowed_double_escapes:
                    diagnostics.append(
                        f"line {line_number}: unsupported escape \\{character} in quoted value"
                    )
                elif quote == '"' and character in {"x", "u", "U"}:
                    required_digits = {"x": 2, "u": 4, "U": 8}[character]
                    digits = value[index + 1 : index + 1 + required_digits]
                    if len(digits) != required_digits or not all(
                        digit in "0123456789abcdefABCDEF" for digit in digits
                    ):
                        diagnostics.append(
                            f"line {line_number}: \\{character} escape requires "
                            f"{required_digits} hexadecimal digits"
                        )
                escaped = False
            elif quote == '"' and character == "\\":
                escaped = True
            elif character == quote:
                if quote == "'" and index + 1 < len(value) and value[index + 1] == "'":
                    index += 1
                else:
                    quote = None
        elif character in {'"', "'"}:
            quote = character
        elif character in "[{":
            flow_stack.append(character)
        elif character in "]}":
            expected = "[" if character == "]" else "{"
            if not flow_stack or flow_stack[-1] != expected:
                diagnostics.append(
                    f"line {line_number}: unmatched flow delimiter '{character}'"
                )
            else:
                flow_stack.pop()
        index += 1

    if quote is not None or escaped:
        diagnostics.append(f"line {line_number}: unterminated quoted value")
    if flow_stack:
        diagnostics.append(f"line {line_number}: unterminated flow collection")
    return diagnostics


def closing_quote_index(value: str) -> int | None:
    """Locate the closing quote for a scalar that starts with one."""
    if not value or value[0] not in {'"', "'"}:
        return None
    quote = value[0]
    escaped = False
    index = 1
    while index < len(value):
        character = value[index]
        if escaped:
            escaped = False
        elif quote == '"' and character == "\\":
            escaped = True
        elif character == quote:
            if quote == "'" and index + 1 < len(value) and value[index + 1] == "'":
                index += 1
            else:
                return index
        index += 1
    return None


def is_frontmatter_delimiter(line: str) -> bool:
    """Recognize only unindented document delimiters, with optional trailing space."""
    return not line.startswith((" ", "\t")) and line.rstrip() == "---"


def decode_quoted_yaml_scalar(value: str, quote: str) -> str:
    """Decode the portable quoted-scalar subset accepted for required fields."""
    if quote == "'":
        return value.replace("''", "'")

    simple_escapes = {
        "0": "\0",
        "a": "\a",
        "b": "\b",
        "t": "\t",
        "n": "\n",
        "v": "\v",
        "f": "\f",
        "r": "\r",
        "e": "\x1b",
        " ": " ",
        '"': '"',
        "/": "/",
        "\\": "\\",
        "N": "\u0085",
        "_": "\u00a0",
        "L": "\u2028",
        "P": "\u2029",
    }
    decoded: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character != "\\":
            decoded.append(character)
            index += 1
            continue
        if index + 1 >= len(value):
            decoded.append("\\")
            break
        escape = value[index + 1]
        if escape in simple_escapes:
            decoded.append(simple_escapes[escape])
            index += 2
            continue
        if escape not in {"x", "u", "U"}:
            decoded.extend(("\\", escape))
            index += 2
            continue
        width = {"x": 2, "u": 4, "U": 8}[escape]
        digits = value[index + 2 : index + 2 + width]
        try:
            decoded.append(chr(int(digits, 16)))
        except (ValueError, OverflowError):
            decoded.extend(("\\", escape, digits))
        index += 2 + width
    return "".join(decoded)


def parse_frontmatter_details(
    content: str,
) -> tuple[dict[str, str] | None, str, list[str], bool]:
    """Extract and diagnose the supported top-level frontmatter subset."""
    lines = content.splitlines()
    if not lines or not is_frontmatter_delimiter(lines[0]):
        return None, content, [], False

    end_index = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if is_frontmatter_delimiter(line)
        ),
        None,
    )
    if end_index is None:
        return None, content, [], False

    frontmatter: dict[str, str] = {}
    diagnostics: list[str] = []
    optional_or_nested_present = False
    optional_continuation = False
    for line_number, line in enumerate(lines[1:end_index], start=2):
        if "\t" in line:
            diagnostics.append(
                f"line {line_number}: tab characters are not portable YAML indentation or spacing"
            )
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            # Optional owner-specific nested data is intentionally opaque. A
            # target/repository schema validator must validate its semantics.
            optional_or_nested_present = True
            continue
        closing_candidate = strip_frontmatter_inline_comment(line).strip()
        if optional_continuation and closing_candidate in {"]", "}", "],", "},"}:
            optional_continuation = False
            continue
        optional_continuation = False
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if match is None:
            diagnostics.append(
                f"line {line_number}: unsupported top-level syntax; expected key: value"
            )
            continue
        key, value = match.groups()
        if key not in {"name", "description"}:
            optional_or_nested_present = True
        value = strip_frontmatter_inline_comment(value).strip()
        if key not in {"name", "description"}:
            optional_continuation = value == "" or value.startswith(
                ("[", "{", "|", ">")
            )
        else:
            diagnostics.extend(frontmatter_value_diagnostics(value, line_number))
        if key in frontmatter:
            diagnostics.append(f"line {line_number}: duplicate top-level key '{key}'")
            continue
        if key in {"name", "description"}:
            if value.startswith(("[", "{", "|", ">", "&", "*", "!")):
                diagnostics.append(
                    f"line {line_number}: release validation requires '{key}' to use "
                    "a single-line scalar string; validate target-specific YAML with target tooling"
                )
            quoted = False
            quote_character: str | None = None
            if value.startswith(('"', "'")):
                quote_end = closing_quote_index(value)
                if quote_end is None or value[quote_end + 1 :].strip():
                    diagnostics.append(
                        f"line {line_number}: unterminated or trailing content after quoted value"
                    )
                else:
                    quote_character = value[0]
                    value = decode_quoted_yaml_scalar(
                        value[1:quote_end], quote_character
                    )
                    quoted = True
            if not quoted:
                folded_value = value.casefold()
                if (
                    folded_value
                    in {"~", "null", "true", "false", "yes", "no", "on", "off"}
                    or YAML_NUMBER_RE.fullmatch(value)
                    or YAML_DATE_RE.match(value)
                ):
                    diagnostics.append(
                        f"line {line_number}: '{key}' must be a string; quote YAML-like "
                        f"null, boolean, numeric, or date values"
                    )
                if re.search(r":\s", value) or value.startswith(("- ", "? ")):
                    diagnostics.append(
                        f"line {line_number}: '{key}' uses unsupported ambiguous plain-scalar syntax"
                    )
        frontmatter[key] = value

    return (
        frontmatter,
        "\n".join(lines[end_index + 1 :]).strip(),
        diagnostics,
        optional_or_nested_present,
    )


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str]:
    """Compatibility wrapper for callers that only need parsed fields and body."""
    frontmatter, body, diagnostics, _optional = parse_frontmatter_details(content)
    return (None if diagnostics else frontmatter), body


def extract_frontmatter_source(content: str) -> str | None:
    """Return the raw YAML between the first pair of frontmatter delimiters."""
    lines = content.splitlines()
    if not lines or not is_frontmatter_delimiter(lines[0]):
        return None
    end_index = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if is_frontmatter_delimiter(line)
        ),
        None,
    )
    if end_index is None:
        return None
    return "\n".join(lines[1:end_index])


def load_yaml_strict(content: str) -> tuple[bool, Any, str | None]:
    """Parse YAML safely with duplicate-key rejection when PyYAML is available.

    The validator remains dependency-free for the portable two-field
    frontmatter subset. Extended frontmatter and live YAML manifests cannot be
    release-certified without a real YAML parser, so callers must fail safely
    when ``available`` is false.
    """
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return False, None, "PyYAML is unavailable"

    class UniqueKeySafeLoader(yaml.SafeLoader):
        """Safe loader that treats duplicate mappings as invalid contracts."""

    def construct_unique_mapping(
        loader: Any, node: Any, deep: bool = False
    ) -> dict[Any, Any]:
        loader.flatten_mapping(node)
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as exc:
                raise ValueError("YAML mapping keys must be hashable") from exc
            if duplicate:
                raise ValueError(f"duplicate YAML key: {key!r}")
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    UniqueKeySafeLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_unique_mapping,
    )
    try:
        return True, yaml.load(content, Loader=UniqueKeySafeLoader), None
    except (yaml.YAMLError, TypeError, ValueError) as exc:
        return True, None, str(exc)


def reject_json_constant(value: str) -> None:
    """Reject JavaScript numeric constants that are not valid JSON."""
    raise ValueError(f"non-standard JSON constant: {value}")


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject ambiguous JSON objects with duplicate member names."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_strict(content: str) -> Any:
    """Parse standards-compliant JSON with unambiguous object keys."""
    return json.loads(
        content,
        parse_constant=reject_json_constant,
        object_pairs_hook=reject_duplicate_json_keys,
    )


def count_lines(filepath: Path | str) -> int:
    """Count UTF-8 text lines, returning zero for unreadable files."""
    try:
        with Path(filepath).open("r", encoding="utf-8") as handle:
            return sum(1 for _ in handle)
    except (OSError, UnicodeDecodeError):
        return 0


def strip_fenced_code(content: str) -> str:
    """Remove CommonMark-style fenced blocks while preserving other prose."""
    kept: list[str] = []
    active_marker: str | None = None
    active_length = 0
    for line in content.splitlines():
        marker_match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker_match is not None:
            marker = marker_match.group(1)
            remainder = marker_match.group(2)
            marker_char = marker[0]
            if active_marker is None:
                active_marker = marker_char
                active_length = len(marker)
            elif (
                active_marker == marker_char
                and len(marker) >= active_length
                and not remainder.strip()
            ):
                active_marker = None
                active_length = 0
            continue
        if active_marker is None:
            kept.append(line)
    return "\n".join(kept)


def iter_fenced_blocks(content: str) -> Iterable[tuple[str, str]]:
    """Yield CommonMark-style fenced block info strings and bodies."""
    active_marker: str | None = None
    active_length = 0
    info = ""
    body: list[str] = []
    for line in content.splitlines():
        marker_match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker_match is not None:
            marker = marker_match.group(1)
            remainder = marker_match.group(2)
            marker_char = marker[0]
            if active_marker is None:
                active_marker = marker_char
                active_length = len(marker)
                info = remainder.strip().split(maxsplit=1)[0].casefold() if remainder.strip() else ""
                body = []
                continue
            if (
                active_marker == marker_char
                and len(marker) >= active_length
                and not remainder.strip()
            ):
                yield info, "\n".join(body)
                active_marker = None
                active_length = 0
                info = ""
                body = []
                continue
        if active_marker is not None:
            body.append(line)


def find_authoring_debt_markers(content: str) -> set[str]:
    """Find explicit stubs in prose or executable contract text."""
    markers = {
        match.group(0) for match in EXPLICIT_AUTHORING_MARKER_RE.finditer(content)
    }
    markers.update(
        match.group(0) for match in LEADING_AUTHORING_MARKER_RE.finditer(content)
    )
    markers.update(
        match.group(0) for match in LABEL_AUTHORING_MARKER_RE.finditer(content)
    )
    return markers


def find_unresolved_authoring_markers(content: str, *, markdown: bool) -> list[str]:
    """Find explicit author debt without confusing runtime template syntax.

    Prose TODO markers inside fenced examples are illustrative and remain
    ignored. Mustache author tokens are scanned across the whole live document
    because an executable example containing an unresolved scaffold token is
    still incomplete. Runtime expressions remain narrowly exempt below.
    """
    prose = strip_fenced_code(content) if markdown else content
    markers = find_authoring_debt_markers(prose)
    if markdown:
        for language, fenced_body in iter_fenced_blocks(content):
            if language not in TEACHING_FENCE_LANGUAGES:
                markers.update(find_authoring_debt_markers(fenced_body))
    template_surface = content

    for match in MUSTACHE_TOKEN_RE.finditer(template_surface):
        token = match.group(1).strip()
        # Go-template whitespace trimming is syntax, not part of the expression.
        if token.startswith("-"):
            token = token[1:].lstrip()
        if token.endswith("-"):
            token = token[:-1].rstrip()
        folded = token.casefold()
        if (
            not token
            or folded.startswith(("skill:", "agent:"))
            or folded in RUNTIME_TEMPLATE_ACTIONS
            or token.startswith((".", "$"))
        ):
            continue

        # Expressions such as `json .`, `if .Enabled`, property access, and
        # pipelines are runtime templates. A bare identifier is ambiguous.
        if SIMPLE_AUTHOR_TOKEN_RE.fullmatch(token) is None:
            continue
        # A bare identifier is indistinguishable from a forgotten scaffold
        # token, regardless of casing. Runtime templates should use their
        # engine's observable expression syntax (for example `.Name`, `$var`,
        # a helper call, property access, or a pipeline) rather than relying on
        # an ambiguous single identifier in live release guidance.
        markers.add(match.group(0))

    return sorted(markers)


def extract_script_comments(content: str) -> str:
    """Extract common comment forms while ignoring quoted string contents.

    This is deliberately a conservative, language-neutral lexer rather than a
    parser. It recognizes single, double, backtick, and Python-style triple
    quoted strings, plus hash, slash, SQL/Lua dash, and block comments.
    """
    comments: list[str] = []
    index = 0
    quote: str | None = None
    triple_quote: str | None = None
    escaped = False
    length = len(content)

    while index < length:
        if triple_quote is not None:
            if content.startswith(triple_quote, index):
                index += len(triple_quote)
                triple_quote = None
            else:
                index += 1
            continue

        character = content[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            elif character == "\n" and quote != "`":
                # Recover conservatively from a malformed single-line string.
                quote = None
            index += 1
            continue

        if content.startswith(('"""', "'''"), index):
            triple_quote = content[index : index + 3]
            index += 3
            continue
        if character in {'"', "'", "`"}:
            quote = character
            index += 1
            continue

        if content.startswith("/*", index):
            end = content.find("*/", index + 2)
            if end == -1:
                comments.append(content[index:])
                break
            comments.append(content[index : end + 2])
            index = end + 2
            continue

        is_hash_comment = character == "#"
        is_slash_comment = content.startswith("//", index)
        is_dash_comment = content.startswith("--", index) and (
            index == 0 or content[index - 1].isspace()
        )
        if is_hash_comment or is_slash_comment or is_dash_comment:
            end = content.find("\n", index)
            if end == -1:
                end = length
            comments.append(content[index:end])
            index = end
            continue

        index += 1

    return "\n".join(comments)


def find_script_authoring_markers(content: str) -> list[str]:
    """Find unfinished work markers in comments and explicit failure stubs."""
    comment_text = extract_script_comments(content)
    markers = {
        match.group(0)
        for match in SCRIPT_COMMENT_AUTHORING_MARKER_RE.finditer(comment_text)
    }
    markers.update(
        match.group("marker")
        for match in SCRIPT_BEHAVIOR_AUTHORING_MARKER_RE.finditer(content)
    )
    return sorted(markers)


def has_leading_authoring_marker(value: str) -> bool:
    """Return whether an eval contract field still contains explicit author debt."""
    return bool(find_authoring_debt_markers(value))


def is_placeholder_target(target: str) -> bool:
    """Return whether a local-looking target is an illustrative placeholder."""
    return bool(
        re.search(r"\{\{|\}\}|[{}]|<[^>]+>|\$[A-Za-z_]", target)
        or "..." in target
        or re.search(r"(^|/)(?:TODO|PLACEHOLDER|X)(?:\.[^/]*)?$", target, re.I)
    )


def normalize_link_target(raw_target: str) -> str | None:
    """Normalize a Markdown link target, excluding anchors and external URLs."""
    target = raw_target.strip()
    if not target:
        return None

    if target.startswith("<"):
        closing_angle = target.find(">", 1)
        if closing_angle == -1:
            return None
        target = target[1:closing_angle].strip()
    else:
        # Markdown permits an optional quoted title after the destination.
        target = target.split(maxsplit=1)[0]

    target = unquote(target).split("#", 1)[0].split("?", 1)[0]
    scheme_match = EXTERNAL_TARGET_RE.match(target)
    is_windows_drive = re.match(r"^[A-Za-z]:[\\/]", target) is not None
    is_file_uri = target.casefold().startswith("file:")
    if (
        not target
        or target.startswith(("#", "//"))
        or (scheme_match and not is_windows_drive and not is_file_uri)
    ):
        return None

    return target or None


def extract_markdown_link_targets(content: str) -> list[str]:
    """Extract inline and reference-style Markdown destinations.

    A small balanced scanner handles parentheses and escapes in inline links;
    reference definitions are validated whether their label uses full,
    collapsed, or shortcut syntax elsewhere in the document.
    """
    targets: set[str] = set()
    cursor = 0
    while True:
        opener = content.find("](", cursor)
        if opener == -1:
            break
        line_start = content.rfind("\n", 0, opener) + 1
        if content.rfind("[", line_start, opener) == -1:
            cursor = opener + 2
            continue

        index = opener + 2
        destination_start = index
        depth = 1
        escaped = False
        while index < len(content):
            character = content[index]
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    target = normalize_link_target(content[destination_start:index])
                    if target is not None:
                        targets.add(target.replace("\\(", "(").replace("\\)", ")"))
                    break
            index += 1
        cursor = max(opener + 2, index + 1)

    for match in REFERENCE_DEFINITION_RE.finditer(content):
        label = match.group(1).strip()
        if label.startswith("^"):
            continue
        target = normalize_link_target(match.group(2))
        if target is not None:
            targets.add(target)

    return sorted(targets)


def extract_html_link_targets(content: str) -> list[str]:
    """Extract local-looking HTML attributes and angle-bracket autolinks."""
    targets: set[str] = set()
    without_comments = re.sub(r"<!--[\s\S]*?-->", "", content)
    for match in HTML_ATTRIBUTE_RE.finditer(without_comments):
        raw_target = next(
            (group for group in match.groups() if group is not None), ""
        )
        target = normalize_link_target(html.unescape(raw_target))
        if target is not None:
            targets.add(target)
    for match in LOCAL_AUTOLINK_RE.finditer(without_comments):
        target = normalize_link_target(html.unescape(match.group(1)))
        if target is not None:
            targets.add(target)
    return sorted(targets)


def extract_file_references(
    content: str, *, include_inline_paths: bool = True
) -> list[str]:
    """Extract non-placeholder local links outside fenced examples.

    The optional inline-path behavior preserves compatibility with skills that
    route through backticked package paths instead of Markdown links.
    """
    stripped = strip_fenced_code(content)
    references: set[str] = set()

    references.update(extract_markdown_link_targets(stripped))

    if include_inline_paths:
        for match in INLINE_PATH_RE.finditer(stripped):
            target = normalize_link_target(match.group(1))
            if target is not None:
                references.add(target)

    return sorted(references)


def path_is_within(root: Path, candidate: Path) -> bool:
    """Check containment after resolving existing symlinks and parent segments."""
    try:
        return os.path.commonpath((str(root), str(candidate))) == str(root)
    except ValueError:
        return False


def path_is_absolute_any_platform(value: str) -> bool:
    """Reject POSIX, Windows drive, and UNC absolute paths on every host OS."""
    windows_path = PureWindowsPath(value)
    return Path(value).is_absolute() or windows_path.is_absolute() or bool(windows_path.drive)


def audit_package_tree(root: Path) -> tuple[list[str], int]:
    """Reject dangling or escaping package paths before consuming content."""
    errors: list[str] = []
    audited = 0

    def record_walk_error(error: OSError) -> None:
        location = error.filename or str(root)
        try:
            location = Path(location).relative_to(root).as_posix()
        except (TypeError, ValueError):
            location = str(location)
        errors.append(f"Cannot audit package path {location}: {error.strerror or error}")

    for current, directories, filenames in os.walk(
        root, topdown=True, followlinks=False, onerror=record_walk_error
    ):
        directories.sort()
        filenames.sort()
        current_path = Path(current)
        entries = [*(current_path / name for name in directories)]
        entries.extend(current_path / name for name in filenames)

        for path in entries:
            audited += 1
            relative = path.relative_to(root).as_posix()
            try:
                node_stat = path.lstat()
            except OSError as exc:
                errors.append(f"Cannot inspect package path {relative}: {exc}")
                continue

            if path.is_symlink():
                if len(path.relative_to(root).parts) == 1 and path.name in SUPPORT_DIRECTORY_NAMES:
                    errors.append(
                        f"Support directory must be a real directory, not a symlink: {relative}"
                    )
                try:
                    resolved = path.resolve(strict=True)
                except FileNotFoundError:
                    errors.append(f"Dangling package symlink: {relative}")
                    continue
                except (OSError, RuntimeError, ValueError) as exc:
                    errors.append(f"Cannot resolve package symlink {relative}: {exc}")
                    continue
                if not path_is_within(root, resolved):
                    errors.append(
                        f"Package symlink resolves outside skill root: {relative} -> {resolved}"
                    )
                continue

            if not (stat.S_ISREG(node_stat.st_mode) or stat.S_ISDIR(node_stat.st_mode)):
                errors.append(
                    f"Package path is not a regular file or directory: {relative}"
                )
                continue

            try:
                resolved = path.resolve(strict=False)
            except (OSError, RuntimeError, ValueError) as exc:
                errors.append(f"Cannot resolve package path {relative}: {exc}")
                continue
            if not path_is_within(root, resolved):
                errors.append(
                    f"Package path resolves outside skill root: {relative} -> {resolved}"
                )

        # Never traverse a directory through a symlink. Internal targets are
        # reached through their canonical in-root path and audited there.
        directories[:] = [
            name for name in directories if not (current_path / name).is_symlink()
        ]

    return sorted(set(errors)), audited


def resolve_package_reference(
    root: Path, source: Path, target: str, *, package_relative: bool
) -> Path:
    """Resolve an inline package path or a source-relative Markdown link."""
    raw_path = Path(target.replace("\\", "/"))
    base = root if package_relative else source.parent
    return (base / raw_path).resolve(strict=False)


def iter_markdown_files(root: Path) -> Iterable[Path]:
    """Yield live Markdown surfaces, excluding templates and eval fixtures."""
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or path.suffix.casefold() != ".md":
            continue
        relative = path.relative_to(root)
        is_root_surface = len(relative.parts) == 1 and path.name in ENTRY_MARKDOWN_NAMES
        is_routed_surface = relative.parts[0] in {"references", "agents"}
        if not (is_root_surface or is_routed_surface):
            continue
        resolved = path.resolve(strict=False)
        if path_is_within(root, resolved):
            yield path


def iter_live_instruction_files(root: Path) -> Iterable[tuple[Path, bool]]:
    """Yield runtime instruction and publication surfaces deliberately.

    Root wrappers and metadata, references, agent prompts, and agent UI YAML
    are live. Reusable templates, eval fixtures, and card-generation prompts
    are authoring inputs and are intentionally excluded. Scripts use a
    separate comment-aware scan so generators can safely process marker data.
    """
    root_files = (
        (root / "SKILL.md", True),
        (root / "README.md", True),
        (root / "AGENTS.md", True),
        (root / "metadata.json", False),
    )
    for path, markdown in root_files:
        if path.is_file():
            yield path, markdown

    routed_suffixes = (
        (root / "references", frozenset({".md"}), True),
        (root / "agents", frozenset({".md"}), True),
        (root / "agents", frozenset({".yaml", ".yml"}), False),
    )
    for directory, suffixes, markdown in routed_suffixes:
        if not directory.is_dir():
            continue
        candidates = {
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.casefold() in suffixes
        }
        for path in sorted(candidates, key=lambda item: item.as_posix()):
            try:
                resolved = path.resolve(strict=False)
            except (OSError, RuntimeError, ValueError):
                continue
            if path_is_within(root, resolved):
                yield path, markdown


def iter_live_script_files(root: Path) -> Iterable[Path]:
    """Yield content-bearing files under scripts without following escapes."""
    scripts_root = root / "scripts"
    if not scripts_root.is_dir():
        return
    for path in sorted(scripts_root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        try:
            resolved = path.resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            continue
        if path_is_within(root, resolved):
            yield path


def collect_unresolved_authoring_markers(
    root: Path,
) -> tuple[list[tuple[str, list[str]]], list[str]]:
    """Find unfinished markers and fail unreadable live metadata surfaces."""
    findings: list[tuple[str, list[str]]] = []
    errors: list[str] = []
    for path, markdown in iter_live_instruction_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            if not markdown:
                errors.append(f"Cannot read live metadata file {relative}: {exc}")
            continue
        if relative == "metadata.json":
            try:
                metadata_payload = load_json_strict(content)
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append(f"metadata.json is not valid strict JSON: {exc}")
            else:
                if not isinstance(metadata_payload, dict):
                    errors.append("metadata.json must contain a JSON object")
        markers = find_unresolved_authoring_markers(content, markdown=markdown)
        if markers:
            findings.append((relative, markers))

    for path in iter_live_script_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # Binary executables are valid package assets. They remain subject
            # to containment auditing but cannot carry reviewable text debt.
            continue
        markers = find_script_authoring_markers(content)
        if markers:
            findings.append((relative, markers))
    return findings, errors


def validate_yaml_contract(
    *,
    content: str,
    label: str,
    profile: str,
    errors: list[str],
    warnings: list[str],
    require_mapping: bool,
) -> Any:
    """Validate a live YAML surface or fail release when no parser is present."""
    available, payload, diagnostic = load_yaml_strict(content)
    if not available:
        add_profile_issue(
            profile,
            errors,
            warnings,
            f"Cannot validate {label}: {diagnostic}; install PyYAML or use target schema tooling",
        )
        return None
    if diagnostic is not None:
        errors.append(f"{label} is not valid YAML: {diagnostic}")
        return None
    if require_mapping and (not isinstance(payload, dict) or not payload):
        errors.append(f"{label} must contain a non-empty YAML mapping")
        return None
    return payload


def validate_live_agent_yaml(
    root: Path,
    *,
    profile: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    """Syntax-check live agent manifests without inventing owner semantics."""
    agents_root = root / "agents"
    if not agents_root.is_dir():
        return
    candidates = {
        path
        for path in agents_root.rglob("*")
        if path.is_file() and path.suffix.casefold() in {".yaml", ".yml"}
    }
    for path in sorted(candidates, key=lambda item: item.as_posix()):
        try:
            resolved = path.resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            continue
        if not path_is_within(root, resolved):
            continue
        relative = path.relative_to(root).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # The live-surface scan reports this with a stable metadata error.
            continue
        validate_yaml_contract(
            content=content,
            label=relative,
            profile=profile,
            errors=errors,
            warnings=warnings,
            require_mapping=True,
        )


def validate_support_directories(
    root: Path,
    *,
    profile: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    """Reject support directories that contain no earned package content."""
    for directory_name in SUPPORT_DIRECTORY_NAMES:
        directory = root / directory_name
        if not directory.is_dir():
            continue
        content_files = [
            path
            for path in directory.rglob("*")
            if path.is_file() and path.name != ".gitkeep"
        ]
        if content_files:
            continue
        add_profile_issue(
            profile,
            errors,
            warnings,
            f"Support directory '{directory_name}/' is empty or .gitkeep-only; "
            "remove it until content earns the surface",
        )


def collect_cross_reference_issues(root: Path) -> tuple[list[str], list[str], int]:
    """Check local links and separate draft-completion issues from safety errors."""
    errors: list[str] = []
    completion_issues: list[str] = []
    checked = 0

    for source in iter_markdown_files(root):
        try:
            content = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"Cannot read Markdown file {source.relative_to(root)}: {exc}")
            continue

        stripped = strip_fenced_code(content)
        markdown_targets = extract_markdown_link_targets(stripped)
        html_targets = extract_html_link_targets(stripped)
        inline_targets: list[str] = []
        is_root_entry = source.name in ENTRY_MARKDOWN_NAMES and source.parent == root
        is_reference_file = source.is_relative_to(root / "references")
        is_agent_file = source.is_relative_to(root / "agents")
        if is_root_entry or is_reference_file or is_agent_file:
            inline_targets = sorted(
                {
                    target
                    for match in INLINE_PATH_RE.finditer(stripped)
                    if (target := normalize_link_target(match.group(1))) is not None
                }
            )

        source_relative_targets = sorted(set(markdown_targets) | set(html_targets))
        targets = [(item, False) for item in source_relative_targets]
        targets.extend((item, True) for item in inline_targets)
        for target, package_relative in targets:
            checked += 1
            source_label = source.relative_to(root).as_posix()
            if target.casefold().startswith("file:"):
                errors.append(
                    f"Local file URI is not allowed in {source_label}: {target}"
                )
                continue
            if is_placeholder_target(target):
                completion_issues.append(
                    f"Placeholder-looking live local route in {source_label}: {target}"
                )
                continue
            if path_is_absolute_any_platform(target):
                errors.append(
                    f"Local link escapes skill root in {source_label}: {target}"
                )
                continue
            try:
                resolved = resolve_package_reference(
                    root, source, target, package_relative=package_relative
                )
            except (OSError, RuntimeError, ValueError):
                errors.append(f"Invalid local link in {source_label}: {target!r}")
                continue
            if not path_is_within(root, resolved):
                errors.append(
                    f"Local link escapes skill root in {source_label}: {target}"
                )
            elif not resolved.exists():
                errors.append(
                    f"Local link in {source_label} does not exist: {target}"
                )

    return errors, completion_issues, checked


def has_toc_heading(content: str) -> bool:
    """Check for a table-of-contents heading or anchor list."""
    patterns = (
        r"^#+\s+table\s+of\s+contents",
        r"^#+\s+toc\b",
        r"^#+\s+contents\b",
        r"^-\s+\[.*\]\(#",
    )
    return any(
        re.match(pattern, line.strip().lower())
        for line in content.splitlines()
        for pattern in patterns
    )


def add_profile_issue(
    profile: str, errors: list[str], warnings: list[str], message: str
) -> None:
    """Make completeness failures fatal only for release validation."""
    (errors if profile == "release" else warnings).append(message)


def has_visible_text(value: str) -> bool:
    """Reject strings made only of whitespace or zero-width format controls."""
    return any(
        not character.isspace() and unicodedata.category(character) != "Cf"
        for character in value
    )


def normalize_contract_text(value: str) -> str:
    """Normalize case, whitespace, and zero-width controls for identity checks."""
    visible = "".join(
        character
        for character in value
        if unicodedata.category(character) != "Cf"
    )
    return " ".join(visible.split()).casefold()


def is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and has_visible_text(value)


def validate_string_list(
    *,
    value: object,
    field: str,
    label: str,
    errors: list[str],
) -> list[str]:
    """Validate an optional list as a fatal schema invariant."""
    if not isinstance(value, list):
        errors.append(f"{label}: '{field}' must be an array")
        return []

    valid: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not is_nonempty_string(item):
            errors.append(f"{label}: {field}[{index}] must be a non-empty string")
            continue
        item = item.strip()
        if item in seen:
            errors.append(f"{label}: duplicate {field} value '{item}'")
            continue
        seen.add(item)
        valid.append(item)
    return valid


def validate_evals(
    root: Path,
    *,
    profile: str,
    expected_skill_name: str | None,
    errors: list[str],
    warnings: list[str],
    metrics: dict[str, int],
) -> None:
    """Validate eval completeness, assertion schema, and file containment."""
    evals_path = root / "evals" / "evals.json"
    if not evals_path.is_file():
        add_profile_issue(
            profile, errors, warnings, "evals/evals.json is required for release"
        )
        return

    try:
        resolved_evals_path = evals_path.resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        errors.append(f"Cannot resolve evals/evals.json: {exc}")
        return
    if not path_is_within(root, resolved_evals_path):
        errors.append("evals/evals.json resolves outside the skill root")
        return

    try:
        payload: Any = load_json_strict(evals_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        errors.append(f"evals/evals.json is not valid JSON: {exc}")
        return
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"Cannot read evals/evals.json: {exc}")
        return

    if not isinstance(payload, dict):
        errors.append("evals/evals.json must contain a JSON object")
        return

    unknown_manifest_keys = sorted(set(payload) - EVAL_MANIFEST_KEYS)
    if unknown_manifest_keys:
        errors.append(
            "evals/evals.json contains unknown top-level fields: "
            + ", ".join(unknown_manifest_keys)
        )

    declared_name = payload.get("skill_name")
    if "skill_name" not in payload or declared_name == "":
        add_profile_issue(
            profile,
            errors,
            warnings,
            "evals/evals.json: 'skill_name' must be a non-empty string",
        )
    elif not isinstance(declared_name, str):
        errors.append("evals/evals.json: 'skill_name' must be a string")
    elif expected_skill_name is not None and declared_name != expected_skill_name:
        errors.append(
            "evals/evals.json: 'skill_name' does not match SKILL.md frontmatter "
            f"('{declared_name}' != '{expected_skill_name}')"
        )

    if "created_by" in payload and not is_nonempty_string(payload["created_by"]):
        errors.append("evals/evals.json: 'created_by' must be a non-empty string")

    evals = payload.get("evals")
    if not isinstance(evals, list):
        errors.append("evals/evals.json: 'evals' must be an array")
        return
    if not evals:
        add_profile_issue(
            profile,
            errors,
            warnings,
            "evals/evals.json: at least one meaningful eval is required for release",
        )
        return

    metrics["eval_count"] = len(evals)
    seen_ids: dict[int, int] = {}
    seen_names: dict[str, int] = {}

    for index, eval_case in enumerate(evals):
        label = f"Eval index {index}"
        if not isinstance(eval_case, dict):
            errors.append(f"{label}: eval must be an object")
            continue

        unknown_eval_keys = sorted(set(eval_case) - EVAL_CASE_KEYS)
        if unknown_eval_keys:
            errors.append(
                f"{label}: unknown fields: " + ", ".join(unknown_eval_keys)
            )

        eval_id = eval_case.get("id")
        if "id" not in eval_case:
            add_profile_issue(
                profile, errors, warnings, f"{label}: 'id' must be a positive integer"
            )
        elif (
            not isinstance(eval_id, int)
            or isinstance(eval_id, bool)
            or not 1 <= eval_id <= MAX_INTEROPERABLE_INTEGER
        ):
            errors.append(
                f"{label}: 'id' must be an integer from 1 to "
                f"{MAX_INTEROPERABLE_INTEGER}"
            )
        elif eval_id in seen_ids:
            errors.append(
                f"{label}: duplicate id {eval_id} (first used at index {seen_ids[eval_id]})",
            )
        else:
            seen_ids[eval_id] = index

        eval_name = eval_case.get("name")
        if "name" not in eval_case or (
            isinstance(eval_name, str) and not has_visible_text(eval_name)
        ):
            add_profile_issue(
                profile,
                errors,
                warnings,
                f"{label}: 'name' must be a non-empty string",
            )
        elif not isinstance(eval_name, str):
            errors.append(f"{label}: 'name' must be a string")
        else:
            eval_name = eval_name.strip()
            if not eval_name:
                add_profile_issue(
                    profile,
                    errors,
                    warnings,
                    f"{label}: 'name' must be a non-empty string",
                )
            else:
                label = f"Eval '{eval_name}'"
                if (
                    len(eval_name) > 128
                    or EVAL_NAME_RE.fullmatch(eval_name) is None
                    or "--" in eval_name
                ):
                    errors.append(
                        f"{label}: 'name' must be a 1-128 character lowercase slug "
                        "using letters, digits, and single hyphens"
                    )
                elif eval_name in seen_names:
                    errors.append(
                        f"{label}: duplicate name (first used at index {seen_names[eval_name]})",
                    )
                else:
                    seen_names[eval_name] = index

        for field in ("prompt", "expected_output"):
            value = eval_case.get(field)
            if field not in eval_case or (
                isinstance(value, str) and not has_visible_text(value)
            ):
                add_profile_issue(
                    profile,
                    errors,
                    warnings,
                    f"{label}: '{field}' must be a non-empty string",
                )
            elif not isinstance(value, str):
                errors.append(f"{label}: '{field}' must be a string")
            elif has_leading_authoring_marker(value):
                add_profile_issue(
                    profile,
                    errors,
                    warnings,
                    f"{label}: '{field}' contains an unresolved authoring marker",
                )

        assertions = eval_case.get("assertions")
        if "assertions" not in eval_case:
            add_profile_issue(
                profile, errors, warnings, f"{label}: 'assertions' must be an array"
            )
        elif not isinstance(assertions, list):
            errors.append(f"{label}: 'assertions' must be an array")
        elif not assertions:
            add_profile_issue(
                profile,
                errors,
                warnings,
                f"{label}: 'assertions' must contain at least one assertion",
            )
        else:
            for assertion_index, assertion in enumerate(assertions):
                assertion_label = f"{label}: assertion {assertion_index}"
                if not isinstance(assertion, dict):
                    errors.append(f"{assertion_label} must be an object")
                    continue
                unknown_assertion_keys = sorted(set(assertion) - ASSERTION_KEYS)
                if unknown_assertion_keys:
                    errors.append(
                        f"{assertion_label} has unknown fields: "
                        + ", ".join(unknown_assertion_keys)
                    )
                assertion_text = assertion.get("text")
                if "text" not in assertion or (
                    isinstance(assertion_text, str)
                    and not has_visible_text(assertion_text)
                ):
                    add_profile_issue(
                        profile,
                        errors,
                        warnings,
                        f"{assertion_label} 'text' must be a non-empty string",
                    )
                elif not isinstance(assertion_text, str):
                    errors.append(f"{assertion_label} 'text' must be a string")
                elif has_leading_authoring_marker(assertion_text):
                    add_profile_issue(
                        profile,
                        errors,
                        warnings,
                        f"{assertion_label} 'text' contains an unresolved authoring marker",
                    )
                assertion_type = assertion.get("type")
                if "type" not in assertion or assertion_type == "":
                    add_profile_issue(
                        profile,
                        errors,
                        warnings,
                        f"{assertion_label} 'type' must be a non-empty string",
                    )
                elif not isinstance(assertion_type, str):
                    errors.append(f"{assertion_label} 'type' must be a string")
                elif assertion_type not in ASSERTION_TYPES:
                    errors.append(
                        f"{assertion_label} has unknown type '{assertion_type}' "
                        f"(expected: {', '.join(sorted(ASSERTION_TYPES))})"
                    )
                metrics["assertion_count"] += 1

        if "tags" in eval_case:
            validate_string_list(
                value=eval_case["tags"],
                field="tags",
                label=label,
                errors=errors,
            )

        if "files" not in eval_case:
            continue
        files = validate_string_list(
            value=eval_case["files"],
            field="files",
            label=label,
            errors=errors,
        )
        for relative_path in files:
            metrics["eval_file_count"] += 1
            raw_path = Path(relative_path.replace("\\", "/"))
            try:
                resolved = (root / raw_path).resolve(strict=False)
            except (OSError, RuntimeError, ValueError):
                errors.append(f"{label}: invalid eval file path: {relative_path!r}")
                continue
            if path_is_absolute_any_platform(relative_path) or not path_is_within(root, resolved):
                # Containment is a safety invariant in both profiles.
                errors.append(
                    f"{label}: eval file path escapes skill root: {relative_path}"
                )
            elif not resolved.is_file():
                add_profile_issue(
                    profile,
                    errors,
                    warnings,
                    f"{label}: referenced eval file does not exist: {relative_path}",
                )


def validate_trigger_evals(
    root: Path,
    *,
    profile: str,
    errors: list[str],
    warnings: list[str],
    metrics: dict[str, int],
) -> None:
    """Validate an optional static trigger-query corpus without executing it."""
    trigger_path = root / "evals" / "trigger-evals.json"
    if not trigger_path.exists():
        return
    if not trigger_path.is_file():
        errors.append("evals/trigger-evals.json must be a regular file")
        return

    try:
        resolved = trigger_path.resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        errors.append(f"Cannot resolve evals/trigger-evals.json: {exc}")
        return
    if not path_is_within(root, resolved):
        errors.append("evals/trigger-evals.json resolves outside the skill root")
        return

    try:
        payload: Any = load_json_strict(trigger_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        errors.append(f"evals/trigger-evals.json is not valid JSON: {exc}")
        return
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"Cannot read evals/trigger-evals.json: {exc}")
        return

    if not isinstance(payload, list):
        errors.append("evals/trigger-evals.json must contain a JSON array")
        return
    if not payload:
        add_profile_issue(
            profile,
            errors,
            warnings,
            "evals/trigger-evals.json must contain trigger cases for release",
        )
        return

    metrics["trigger_eval_count"] = len(payload)
    seen_queries: dict[str, int] = {}
    positive_count = 0
    negative_count = 0
    required_keys = {"query", "should_trigger"}

    for index, trigger_case in enumerate(payload):
        label = f"Trigger eval index {index}"
        if not isinstance(trigger_case, dict) or not trigger_case:
            errors.append(f"{label}: case must be a non-empty object")
            continue
        actual_keys = set(trigger_case)
        if actual_keys != required_keys:
            missing = sorted(required_keys - actual_keys)
            unknown = sorted(actual_keys - required_keys)
            detail: list[str] = []
            if missing:
                detail.append("missing " + ", ".join(missing))
            if unknown:
                detail.append("unknown " + ", ".join(unknown))
            errors.append(f"{label}: expected exactly query and should_trigger ({'; '.join(detail)})")
            continue

        query = trigger_case["query"]
        if not isinstance(query, str) or not query.strip():
            errors.append(f"{label}: 'query' must be a non-empty string")
        else:
            query = query.strip()
            if query in seen_queries:
                errors.append(
                    f"{label}: duplicate query (first used at index {seen_queries[query]})"
                )
            else:
                seen_queries[query] = index

        should_trigger = trigger_case["should_trigger"]
        if not isinstance(should_trigger, bool):
            errors.append(f"{label}: 'should_trigger' must be a boolean")
        elif should_trigger:
            positive_count += 1
        else:
            negative_count += 1

    metrics["trigger_positive_count"] = positive_count
    metrics["trigger_negative_count"] = negative_count
    if positive_count == 0:
        add_profile_issue(
            profile,
            errors,
            warnings,
            "evals/trigger-evals.json needs at least one should_trigger=true case for release",
        )
    if negative_count == 0:
        add_profile_issue(
            profile,
            errors,
            warnings,
            "evals/trigger-evals.json needs at least one should_trigger=false case for release",
        )


def validate_skill(skill_path: str, profile: str = "release") -> dict[str, object]:
    """Validate a skill and return a stable machine-readable result."""
    if profile not in PROFILES:
        raise ValueError(f"Unknown validation profile: {profile}")

    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, int] = {
        "skill_md_lines": 0,
        "skill_body_lines": 0,
        "reference_count": 0,
        "cross_reference_count": 0,
        "eval_count": 0,
        "assertion_count": 0,
        "eval_file_count": 0,
        "trigger_eval_count": 0,
        "trigger_positive_count": 0,
        "trigger_negative_count": 0,
        "audited_path_count": 0,
        "total_lines": 0,
    }

    root = Path(skill_path).expanduser().resolve(strict=False)
    directory_name = root.name
    skill_md_path = root / "SKILL.md"
    try:
        skill_md_path.lstat()
    except FileNotFoundError:
        errors.append("SKILL.md does not exist")
        return {
            "valid": False,
            "profile": profile,
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics,
        }
    except OSError as exc:
        errors.append(f"Cannot inspect SKILL.md: {exc}")
        return {
            "valid": False,
            "profile": profile,
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics,
        }

    package_errors, audited_paths = audit_package_tree(root)
    metrics["audited_path_count"] = audited_paths
    if package_errors:
        return {
            "valid": False,
            "profile": profile,
            "errors": package_errors,
            "warnings": warnings,
            "metrics": metrics,
        }

    if not skill_md_path.is_file():
        errors.append("SKILL.md must be a regular file")
        return {
            "valid": False,
            "profile": profile,
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics,
        }

    try:
        resolved_skill_md = skill_md_path.resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        errors.append(f"Cannot resolve SKILL.md: {exc}")
        return {
            "valid": False,
            "profile": profile,
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics,
        }
    if not path_is_within(root, resolved_skill_md):
        errors.append("SKILL.md resolves outside the skill root")
        return {
            "valid": False,
            "profile": profile,
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics,
        }

    try:
        content = skill_md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"Cannot read SKILL.md: {exc}")
        return {
            "valid": False,
            "profile": profile,
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics,
        }

    skill_lines = len(content.splitlines())
    metrics["skill_md_lines"] = skill_lines
    metrics["total_lines"] = skill_lines
    (
        frontmatter,
        body,
        frontmatter_diagnostics,
        optional_frontmatter_present,
    ) = parse_frontmatter_details(content)
    body_lines = len(body.splitlines())
    metrics["skill_body_lines"] = body_lines

    expected_skill_name: str | None = None
    if frontmatter is None:
        errors.append(
            "SKILL.md has no supported frontmatter block "
            "(expected top-level key: value lines between standalone --- delimiters)"
        )
    else:
        errors.extend(
            f"Unsupported frontmatter at {diagnostic}"
            for diagnostic in frontmatter_diagnostics
        )
        name = frontmatter.get("name", "")
        if not name.strip():
            errors.append("Frontmatter missing required 'name' field")
        else:
            expected_skill_name = name
            if (
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", name)
                or "--" in name
            ):
                errors.append(
                    f"name '{name}' is invalid: use 1-64 lowercase letters, digits, "
                    "and single hyphens; start and end with an alphanumeric"
                )
            elif len(name) > 64:
                errors.append(f"name '{name}' exceeds 64 character limit ({len(name)} chars)")
            if name != directory_name:
                errors.append(
                    f"name '{name}' does not match directory name '{directory_name}'"
                )

        description = frontmatter.get("description", "")
        if not description.strip():
            errors.append("Frontmatter missing required 'description' field")
        elif len(description) > 1024:
            errors.append(f"description exceeds 1024 chars ({len(description)} chars)")

    if optional_frontmatter_present:
        frontmatter_source = extract_frontmatter_source(content)
        if frontmatter_source is not None:
            parsed_frontmatter = validate_yaml_contract(
                content=frontmatter_source,
                label="SKILL.md frontmatter",
                profile=profile,
                errors=errors,
                warnings=warnings,
                require_mapping=True,
            )
            if isinstance(parsed_frontmatter, dict):
                for portable_key in ("name", "description"):
                    if portable_key in parsed_frontmatter and not isinstance(
                        parsed_frontmatter[portable_key], str
                    ):
                        errors.append(
                            f"SKILL.md frontmatter '{portable_key}' must be a string"
                        )
                warnings.append(
                    "Extended frontmatter YAML syntax was parsed, but owner-specific field "
                    "semantics still require target and repository schema tooling."
                )

    if not body.strip():
        add_profile_issue(
            profile,
            errors,
            warnings,
            "SKILL.md body must contain non-whitespace instructions for release",
        )

    if body_lines > 500:
        add_profile_issue(
            profile,
            errors,
            warnings,
            f"SKILL.md body is {body_lines} lines; release limit is 500",
        )

    marker_findings, live_metadata_errors = collect_unresolved_authoring_markers(root)
    errors.extend(live_metadata_errors)
    for instruction_path, unresolved in marker_findings:
        add_profile_issue(
            profile,
            errors,
            warnings,
            f"{instruction_path} contains unresolved authoring markers: "
            + ", ".join(unresolved),
        )

    validate_live_agent_yaml(
        root,
        profile=profile,
        errors=errors,
        warnings=warnings,
    )
    validate_support_directories(
        root,
        profile=profile,
        errors=errors,
        warnings=warnings,
    )

    cross_reference_errors, placeholder_routes, checked = collect_cross_reference_issues(root)
    errors.extend(cross_reference_errors)
    for placeholder_route in placeholder_routes:
        add_profile_issue(profile, errors, warnings, placeholder_route)
    metrics["cross_reference_count"] = checked

    references_dir = root / "references"
    if references_dir.is_dir():
        for path in sorted(references_dir.rglob("*"), key=lambda item: item.as_posix()):
            if not path.is_file() or path.name == ".gitkeep":
                continue
            lines = count_lines(path)
            metrics["reference_count"] += 1
            metrics["total_lines"] += lines
            relative = path.relative_to(root).as_posix()
            if lines > 1000:
                add_profile_issue(
                    profile,
                    errors,
                    warnings,
                    f"Reference file exceeds 1000 lines: {relative} ({lines} lines)",
                )
            elif lines > 300:
                try:
                    reference_content = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                if not has_toc_heading(reference_content):
                    warnings.append(
                        f"Reference file >300 lines without TOC: {relative} ({lines} lines)"
                    )

    scripts_dir = root / "scripts"
    if scripts_dir.is_dir():
        for path in sorted(scripts_dir.iterdir(), key=lambda item: item.name):
            if path.is_file() and path.name != ".gitkeep":
                metrics["total_lines"] += count_lines(path)

    validate_evals(
        root,
        profile=profile,
        expected_skill_name=expected_skill_name,
        errors=errors,
        warnings=warnings,
        metrics=metrics,
    )
    validate_trigger_evals(
        root,
        profile=profile,
        errors=errors,
        warnings=warnings,
        metrics=metrics,
    )

    return {
        "valid": not errors,
        "profile": profile,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate an installable skill; release is the default profile."
    )
    parser.add_argument("skill_path", help="Path to the skill directory")
    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default="release",
        help="draft warns on incomplete content; release rejects it (default: release)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    skill_path = Path(args.skill_path).expanduser()
    result = validate_skill(str(skill_path), profile=args.profile)
    metrics = result["metrics"]
    assert isinstance(metrics, dict)
    status = "VALID" if result["valid"] else "INVALID"

    print(f"\nSkill: {skill_path.resolve().name}")
    print(f"Profile: {args.profile}")
    print(f"Status: {status}")
    print(f"SKILL.md lines: {metrics['skill_md_lines']}")
    print(f"SKILL.md body lines: {metrics['skill_body_lines']}")
    print(f"Reference files: {metrics['reference_count']}")
    print(f"Package paths audited: {metrics['audited_path_count']}")
    print(f"Evals: {metrics['eval_count']}")
    print(f"Assertions: {metrics['assertion_count']}")
    print(
        "Trigger evals: "
        f"{metrics['trigger_eval_count']} "
        f"({metrics['trigger_positive_count']} positive, "
        f"{metrics['trigger_negative_count']} negative)"
    )
    print(f"Total lines: {metrics['total_lines']}")

    errors = result["errors"]
    warnings = result["warnings"]
    assert isinstance(errors, list) and isinstance(warnings, list)
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for error in errors:
            print(f"  ERROR: {error}")
    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  WARN: {warning}")
    if result["valid"] and not warnings:
        print("\nNo issues found.")

    print("\n--- JSON ---")
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

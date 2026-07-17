#!/usr/bin/env python3
"""Markdown visibility helpers shared by README validators."""

from __future__ import annotations

import re


FENCE_PATTERN = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
FENCE_CLOSE_PATTERN = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})[ \t]*$")


def _mask_text(text: str) -> str:
    """Replace visible characters with spaces while retaining line endings."""

    return "".join(character if character in "\r\n" else " " for character in text)


def _mask_html_comments(text: str, in_comment: bool) -> tuple[str, bool]:
    """Mask HTML comments in one line and carry multiline comment state."""

    masked = list(text)
    cursor = 0
    while cursor < len(text):
        if in_comment:
            comment_end = text.find("-->", cursor)
            end = len(text) if comment_end == -1 else comment_end + 3
            masked[cursor:end] = " " * (end - cursor)
            if comment_end == -1:
                return "".join(masked), True
            cursor = end
            in_comment = False
            continue

        comment_start = text.find("<!--", cursor)
        if comment_start == -1:
            break
        cursor = comment_start
        in_comment = True

    return "".join(masked), in_comment


def markdown_visible_text(markdown: str) -> str:
    """Mask HTML comments and fenced examples while preserving line shape.

    Neither construct is rendered as README catalog evidence. Preserving line
    breaks prevents text on either side from joining into a validator match,
    while recognizing fences first keeps a literal ``<!--`` example from
    hiding later visible content.
    """

    visible_lines: list[str] = []
    active_fence: tuple[str, int] | None = None
    in_comment = False

    for line in markdown.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        line_ending = line[len(body) :]

        if active_fence is not None:
            visible_lines.append(_mask_text(line))
            closing_match = FENCE_CLOSE_PATTERN.match(body)
            if closing_match is not None:
                closing = closing_match.group("fence")
                if closing[0] == active_fence[0] and len(closing) >= active_fence[1]:
                    active_fence = None
            continue

        comment_masked, in_comment = _mask_html_comments(body, in_comment)
        opening_match = FENCE_PATTERN.match(comment_masked)
        if opening_match is not None:
            opening = opening_match.group("fence")
            active_fence = (opening[0], len(opening))
            visible_lines.append(_mask_text(line))
            continue

        visible_lines.append(comment_masked + line_ending)

    return "".join(visible_lines)

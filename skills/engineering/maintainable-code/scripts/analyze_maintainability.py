#!/usr/bin/env python3
"""Conservative, deterministic maintainability smell scanner.

The scanner emits review prompts, not verdicts. Syntax-sensitive checks are
limited to source forms that can be recognized without guessing.
"""

from __future__ import annotations

import argparse
import ast
import codecs
import io
import json
import os
import stat
import sys
import tokenize
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_EXTENSIONS = {
    ".bash",
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".hcl",
    ".html",
    ".java",
    ".js",
    ".mjs",
    ".cjs",
    ".jsx",
    ".kt",
    ".php",
    ".ps1",
    ".py",
    ".rb",
    ".rs",
    ".scss",
    ".sh",
    ".sql",
    ".swift",
    ".tf",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
    ".zsh",
}

COMMENT_DEBT_EXTENSIONS = {
    ".bash",
    ".css",
    ".hcl",
    ".html",
    ".ps1",
    ".scss",
    ".sh",
    ".sql",
    ".tf",
    ".yaml",
    ".yml",
    ".zsh",
}

OPERATIONAL_HINTS = (
    "<<",
    "<<<",
    " aws ",
    " az ",
    "artifact",
    "awk ",
    "cache",
    "concurrency:",
    "curl ",
    "docker ",
    "gcloud ",
    "gh ",
    "gh api",
    "grep ",
    "ifs=",
    "jq ",
    "jq -",
    "kubectl ",
    "matrix:",
    "permissions:",
    "read -r",
    "run:",
    "sed ",
    "sort -u",
    "terraform ",
    "uses:",
    "while ",
    "xargs ",
)

SKIP_DIRS = {
    ".git",
    ".hg",
    ".next",
    ".nuxt",
    ".svn",
    ".turbo",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}

VAGUE_NAMES = {
    "common",
    "data",
    "handler",
    "helper",
    "helpers",
    "manager",
    "misc",
    "process",
    "processor",
    "stuff",
    "thing",
    "util",
    "utils",
}

CONTROL_FLOW_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".mjs",
    ".cjs",
    ".py",
    ".rs",
    ".swift",
    ".ts",
    ".tsx",
}

CONTROL_FLOW_WORDS = {
    "case",
    "catch",
    "elif",
    "else",
    "elseif",
    "elsif",
    "except",
    "for",
    "foreach",
    "guard",
    "if",
    "loop",
    "match",
    "repeat",
    "rescue",
    "switch",
    "try",
    "unless",
    "when",
    "while",
}

TYPESCRIPT_EXTENSIONS = {".ts", ".tsx"}
JAVASCRIPT_EXTENSIONS = {".cjs", ".js", ".jsx", ".mjs", ".ts", ".tsx"}
TODO_EXTENSIONS = CONTROL_FLOW_EXTENSIONS | {".css", ".html", ".scss", ".sql"}
WEAK_TYPE_NAMES = {"any", "dict", "object"}

REGEX_PREFIX_KEYWORDS = {
    "await",
    "case",
    "delete",
    "do",
    "else",
    "in",
    "instanceof",
    "new",
    "of",
    "return",
    "throw",
    "typeof",
    "void",
    "yield",
}

REGEX_CONTROL_PAREN_KEYWORDS = {"catch", "for", "if", "switch", "while", "with"}

COMMENT_EXPLANATION_HINTS = {
    "api",
    "because",
    "constraint",
    "contract",
    "external",
    "order",
    "phase",
    "preserve",
    "requires",
    "retry",
    "workaround",
}

COMMENT_HEADER_HINTS = {
    "copyright",
    "generated",
    "license",
    "lint",
    "noqa",
    "prettier",
    "region",
    "spdx",
}

MIN_OPERATIONAL_LINES = 8
MIN_OPERATIONAL_HINTS = 3
MAX_OPERATIONAL_HINT_GAP = 5
COMMENT_COVERAGE_CODE_LINES = 8


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str
    message: str


@dataclass(frozen=True)
class ReadError:
    path: str
    message: str = "Could not read source file."


@dataclass(frozen=True)
class LexedSource:
    code: list[str]
    comments: list[str]


@dataclass(frozen=True)
class Identifier:
    value: str
    start: int
    end: int


@dataclass(frozen=True)
class SyntaxToken:
    value: str
    start: int
    end: int
    depth: tuple[int, int, int]


def positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def parse_extensions(value: str) -> set[str]:
    extensions: set[str] = set()
    for item in value.split(","):
        normalized = item.strip().casefold()
        if normalized:
            extensions.add(normalized if normalized.startswith(".") else f".{normalized}")
    return extensions


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def iter_files(
    root: Path,
    extensions: set[str],
) -> tuple[list[Path], list[ReadError]]:
    """Walk below root without opening symlinks or non-regular entries."""
    files: list[Path] = []
    diagnostics: list[ReadError] = []

    def record_walk_error(error: OSError) -> None:
        raw_path = Path(error.filename) if error.filename else root
        diagnostics.append(
            ReadError(relative_path(raw_path, root), "Could not traverse directory.")
        )

    for current, directory_names, file_names in os.walk(
        root,
        topdown=True,
        followlinks=False,
        onerror=record_walk_error,
    ):
        current_path = Path(current)
        kept_directories: list[str] = []
        for name in sorted(directory_names, key=lambda item: (item.casefold(), item)):
            candidate = current_path / name
            if name.casefold() in SKIP_DIRS:
                continue
            if candidate.is_symlink():
                diagnostics.append(
                    ReadError(
                        relative_path(candidate, root),
                        "Skipped a directory symlink during traversal.",
                    )
                )
                continue
            kept_directories.append(name)
        directory_names[:] = kept_directories

        for name in sorted(file_names, key=lambda item: (item.casefold(), item)):
            path = current_path / name
            if path.suffix.casefold() not in extensions:
                continue
            try:
                mode = path.lstat().st_mode
            except OSError:
                diagnostics.append(ReadError(relative_path(path, root)))
                continue
            if stat.S_ISLNK(mode):
                diagnostics.append(
                    ReadError(
                        relative_path(path, root),
                        "Skipped a source-file symlink before reading.",
                    )
                )
                continue
            if not stat.S_ISREG(mode):
                diagnostics.append(
                    ReadError(
                        relative_path(path, root),
                        "Skipped a non-regular filesystem entry before reading.",
                    )
                )
                continue
            files.append(path)

    ordered_files = sorted(
        files,
        key=lambda path: (
            relative_path(path, root).casefold(),
            relative_path(path, root),
        ),
    )
    ordered_diagnostics = sorted(
        set(diagnostics),
        key=lambda error: (error.path.casefold(), error.path, error.message),
    )
    return ordered_files, ordered_diagnostics


def read_source(path: Path, relative: str) -> tuple[list[str] | None, ReadError | None]:
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY
        flags |= getattr(os, "O_NONBLOCK", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            return None, ReadError(
                relative,
                "Skipped a non-regular filesystem entry before reading.",
            )
        with os.fdopen(descriptor, "rb") as source:
            descriptor = None
            data = source.read()
    except OSError:
        return None, ReadError(relative)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    encodings_by_bom = (
        (codecs.BOM_UTF32_LE, "utf-32"),
        (codecs.BOM_UTF32_BE, "utf-32"),
        (codecs.BOM_UTF8, "utf-8-sig"),
        (codecs.BOM_UTF16_LE, "utf-16"),
        (codecs.BOM_UTF16_BE, "utf-16"),
    )
    encoding = next(
        (name for bom, name in encodings_by_bom if data.startswith(bom)),
        "utf-8",
    )
    text = data.decode(encoding, errors="replace")
    return text.splitlines(), None


def _blank_lines(lines: list[str]) -> list[list[str]]:
    return [[" " for _ in line] for line in lines]


def _apply_token_span(
    lines: list[str],
    code: list[list[str]],
    comments: list[list[str]],
    start: tuple[int, int],
    end: tuple[int, int],
    capture_comment: bool,
) -> None:
    start_row, start_column = start
    end_row, end_column = end
    for row in range(start_row, end_row + 1):
        if not 1 <= row <= len(lines):
            continue
        first = start_column if row == start_row else 0
        last = end_column if row == end_row else len(lines[row - 1])
        for column in range(first, min(last, len(lines[row - 1]))):
            if capture_comment:
                comments[row - 1][column] = lines[row - 1][column]
            code[row - 1][column] = " "


def lex_python(lines: list[str]) -> LexedSource | None:
    code = [list(line) for line in lines]
    comments = _blank_lines(lines)
    source = "\n".join(lines)
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (IndentationError, SyntaxError, tokenize.TokenError):
        return None
    for token in tokens:
        if token.type == tokenize.STRING:
            _apply_token_span(lines, code, comments, token.start, token.end, False)
        elif token.type == tokenize.COMMENT:
            _apply_token_span(lines, code, comments, token.start, token.end, True)
    return LexedSource(
        ["".join(line) for line in code],
        ["".join(line) for line in comments],
    )


def comment_markers(suffix: str) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    if suffix == ".html":
        return (), (("<!--", "-->"),)
    if suffix == ".ps1":
        return ("#",), (("<#", "#>"),)
    if suffix in {".css", ".scss"}:
        return (), (("/*", "*/"),)
    if suffix == ".sql":
        return ("--",), (("/*", "*/"),)
    if suffix in {".hcl", ".tf"}:
        return ("#", "//"), (("/*", "*/"),)
    if suffix == ".rb":
        return ("#",), (("=begin", "=end"),)
    if suffix in {".bash", ".py", ".sh", ".yaml", ".yml", ".zsh"}:
        return ("#",), ()
    if suffix == ".php":
        return ("//", "#"), (("/*", "*/"),)
    return ("//",), (("/*", "*/"),)


def javascript_regex_end(line: str, start: int) -> int:
    """Return the first position after a JavaScript-family regex literal."""
    index = start + 1
    escaped = False
    in_character_class = False
    while index < len(line):
        character = line[index]
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == "[":
            in_character_class = True
        elif character == "]":
            in_character_class = False
        elif character == "/" and not in_character_class:
            index += 1
            while index < len(line) and line[index].isalpha():
                index += 1
            return index
        index += 1
    return len(line)


def _mask_range(code: list[list[str]], row: int, start: int, end: int) -> None:
    for column in range(start, min(end, len(code[row]))):
        code[row][column] = " "


def lex_generic(lines: list[str], suffix: str) -> LexedSource:
    line_markers, block_markers = comment_markers(suffix)
    code = [list(line) for line in lines]
    comments = _blank_lines(lines)
    block_end: str | None = None
    quote: str | None = None
    powershell_here_end: str | None = None
    template_stack: list[int] = []
    can_start_regex = True
    control_parentheses: list[bool] = []
    pending_control_parenthesis = False
    javascript_family = suffix in JAVASCRIPT_EXTENSIONS

    for row, line in enumerate(lines):
        if powershell_here_end is not None:
            _mask_range(code, row, 0, len(line))
            if line.startswith(powershell_here_end):
                powershell_here_end = None
            continue
        index = 0
        escaped = False
        while index < len(line):
            if block_end is not None:
                if line.startswith(block_end, index):
                    for column in range(index, min(index + len(block_end), len(line))):
                        comments[row][column] = line[column]
                        code[row][column] = " "
                    index += len(block_end)
                    block_end = None
                else:
                    comments[row][index] = line[index]
                    code[row][index] = " "
                    index += 1
                continue

            if template_stack and template_stack[-1] == 0:
                code[row][index] = " "
                character = line[index]
                if escaped:
                    escaped = False
                    index += 1
                elif character == "\\":
                    escaped = True
                    index += 1
                elif line.startswith("${", index):
                    _mask_range(code, row, index, index + 2)
                    template_stack[-1] = 1
                    can_start_regex = True
                    index += 2
                elif character == "`":
                    template_stack.pop()
                    can_start_regex = False
                    index += 1
                else:
                    index += 1
                continue

            if quote is not None:
                code[row][index] = " "
                character = line[index]
                if escaped:
                    escaped = False
                elif (
                    suffix == ".ps1"
                    and quote == '"'
                    and character == "`"
                ) or (suffix != ".ps1" and character == "\\"):
                    escaped = True
                elif character == quote:
                    quote = None
                    if javascript_family:
                        can_start_regex = False
                index += 1
                continue

            line_marker = next(
                (marker for marker in line_markers if line.startswith(marker, index)),
                None,
            )
            if line_marker is not None:
                for column in range(index, len(line)):
                    comments[row][column] = line[column]
                    code[row][column] = " "
                break

            block_marker = next(
                (marker for marker in block_markers if line.startswith(marker[0], index)),
                None,
            )
            if block_marker is not None:
                block_start, block_end = block_marker
                for column in range(index, min(index + len(block_start), len(line))):
                    comments[row][column] = line[column]
                    code[row][column] = " "
                index += len(block_start)
                continue

            if javascript_family and line[index] == "/" and can_start_regex:
                end = javascript_regex_end(line, index)
                _mask_range(code, row, index, end)
                can_start_regex = False
                index = end
                continue

            if javascript_family and line[index] == "`":
                code[row][index] = " "
                template_stack.append(0)
                index += 1
                continue

            if suffix == ".ps1" and line.startswith(("@'", '@"'), index):
                powershell_here_end = "'@" if line.startswith("@'", index) else '"@'
                _mask_range(code, row, index, len(line))
                index = len(line)
                continue

            if suffix == ".ps1" and line[index] == "`":
                index += 1
                if index < len(line):
                    # PowerShell uses the backtick to escape the next character,
                    # including a # that would otherwise start a comment.
                    index += 1
                continue

            quote_characters = {"'", '"'}
            if not javascript_family and suffix != ".ps1":
                quote_characters.add("`")
            if line[index] in quote_characters:
                quote = line[index]
                code[row][index] = " "
                index += 1
                continue

            if template_stack and template_stack[-1] > 0:
                if line[index] == "{":
                    template_stack[-1] += 1
                elif line[index] == "}":
                    if template_stack[-1] == 1:
                        code[row][index] = " "
                        template_stack[-1] = 0
                        can_start_regex = False
                        index += 1
                        continue
                    template_stack[-1] -= 1

            if javascript_family:
                character = line[index]
                if character.isalpha() or character in {"_", "$"}:
                    end = index + 1
                    while end < len(line) and (
                        line[end].isalnum() or line[end] in {"_", "$"}
                    ):
                        end += 1
                    word = line[index:end].casefold()
                    pending_control_parenthesis = word in REGEX_CONTROL_PAREN_KEYWORDS
                    can_start_regex = word in REGEX_PREFIX_KEYWORDS
                    index = end
                    continue
                if character.isdigit():
                    end = index + 1
                    while end < len(line) and (
                        line[end].isalnum() or line[end] in {".", "_"}
                    ):
                        end += 1
                    can_start_regex = False
                    index = end
                    continue
                if character == "(":
                    control_parentheses.append(pending_control_parenthesis)
                    pending_control_parenthesis = False
                    can_start_regex = True
                elif character == ")":
                    closed_control = control_parentheses.pop() if control_parentheses else False
                    can_start_regex = closed_control
                elif character == "/":
                    can_start_regex = True
                elif character in {"(", "[", "{", ",", ":", ";", "=", "!", "?", "&", "|", "+", "-", "*", "%", "^", "~", "<", ">"}:
                    if line.startswith(("++", "--"), index):
                        # Prefix increments keep expression-start state; postfix
                        # increments keep expression-end state.
                        pass
                    else:
                        can_start_regex = True
                elif character in {"]", "}", "."}:
                    can_start_regex = False
            index += 1

        if quote is not None and (javascript_family or suffix == ".ps1") and not escaped:
            quote = None
        elif quote not in {None, "`"} and not escaped:
            quote = None

    return LexedSource(
        ["".join(line) for line in code],
        ["".join(line) for line in comments],
    )


def lex_source(lines: list[str], suffix: str) -> LexedSource:
    if suffix == ".py":
        python_source = lex_python(lines)
        if python_source is not None:
            return python_source
        blanks = [" " * len(line) for line in lines]
        return LexedSource(blanks, blanks.copy())
    return lex_generic(lines, suffix)


def identifier_tokens(line: str) -> list[Identifier]:
    tokens: list[Identifier] = []
    index = 0
    while index < len(line):
        if line[index].isalpha() or line[index] in {"_", "$"}:
            start = index
            index += 1
            while index < len(line) and (line[index].isalnum() or line[index] in {"_", "$"}):
                index += 1
            tokens.append(Identifier(line[start:index], start, index))
        else:
            index += 1
    return tokens


def indentation_depth(line: str) -> int:
    expanded = line.replace("\t", "    ")
    return (len(expanded) - len(expanded.lstrip(" "))) // 2


def continuation_lines(code: list[str], suffix: str) -> list[bool]:
    results: list[bool] = []
    round_depth = 0
    square_depth = 0
    curly_depth = 0
    explicit_continuation = False
    for line in code:
        results.append(
            explicit_continuation
            or ((round_depth > 0 or square_depth > 0) and curly_depth == 0)
            or (suffix == ".py" and curly_depth > 0)
        )
        for character in line:
            if character == "(":
                round_depth += 1
            elif character == ")":
                round_depth = max(0, round_depth - 1)
            elif character == "[":
                square_depth += 1
            elif character == "]":
                square_depth = max(0, square_depth - 1)
            elif character == "{":
                curly_depth += 1
            elif character == "}":
                curly_depth = max(0, curly_depth - 1)
        stripped = line.rstrip()
        continuation_character = "`" if suffix == ".ps1" else "\\"
        trailing_characters = len(stripped) - len(
            stripped.rstrip(continuation_character)
        )
        explicit_continuation = trailing_characters % 2 == 1
    return results


def begins_control_flow(code: str, suffix: str) -> bool:
    stripped = code.lstrip()
    while stripped.startswith("}"):
        stripped = stripped[1:].lstrip()
    tokens = identifier_tokens(stripped)
    if not (
        tokens
        and tokens[0].start == 0
        and tokens[0].value.casefold() in CONTROL_FLOW_WORDS
    ):
        return False
    after_keyword = stripped[tokens[0].end :].lstrip()
    if suffix in JAVASCRIPT_EXTENSIONS:
        if after_keyword.startswith((":", "?:", "!:")):
            return False
        if after_keyword.startswith("("):
            closing = after_keyword.find(")")
            if closing != -1 and not after_keyword[1:closing].strip():
                return False
    return True


def comment_has_debt_marker(comment: str) -> bool:
    return any(token.value in {"TODO", "FIXME"} for token in identifier_tokens(comment))


def operational_hint_count(code: str) -> int:
    lowered = f" {code.strip().lower()} "
    return int(any(hint in lowered for hint in OPERATIONAL_HINTS))


def is_explanatory_comment(comment: str, *, before_first_code: bool) -> bool:
    stripped = comment.strip()
    if not stripped or stripped.startswith("#!"):
        return False
    words = [token.value.casefold() for token in identifier_tokens(stripped)]
    if len(words) < 3:
        return False
    word_set = set(words)
    if word_set & {"todo", "fixme"}:
        return False
    if word_set & COMMENT_HEADER_HINTS:
        return False
    if before_first_code and not (
        word_set & COMMENT_EXPLANATION_HINTS
        or operational_hint_count(stripped)
    ):
        return False
    return True


def scan_comment_debt(
    lines: list[str],
    lexed: LexedSource,
    suffix: str,
    relative: str,
) -> list[Finding]:
    if suffix not in COMMENT_DEBT_EXTENSIONS:
        return []

    findings: list[Finding] = []
    chunk: list[tuple[int, str, str]] = []

    def flush_chunk() -> None:
        nonlocal chunk
        code_entries = [entry for entry in chunk if entry[1].strip()]
        if len(code_entries) < MIN_OPERATIONAL_LINES:
            chunk = []
            return

        hint_positions = [
            position
            for position, (_, code, _) in enumerate(code_entries)
            if operational_hint_count(code)
        ]
        if len(hint_positions) < MIN_OPERATIONAL_HINTS:
            chunk = []
            return

        first_code_line = code_entries[0][0]
        covered_positions: set[int] = set()
        for line_number, _, comment in chunk:
            if not is_explanatory_comment(
                comment,
                before_first_code=line_number < first_code_line,
            ):
                continue
            anchor = next(
                (
                    position
                    for position, (code_line, _, _) in enumerate(code_entries)
                    if code_line >= line_number
                ),
                None,
            )
            if anchor is None:
                continue
            covered_positions.update(
                range(
                    anchor,
                    min(len(code_entries), anchor + COMMENT_COVERAGE_CODE_LINES),
                )
            )

        uncovered_hints = [
            position for position in hint_positions if position not in covered_positions
        ]
        groups: list[list[int]] = []
        for position in uncovered_hints:
            if not groups or position - groups[-1][-1] > MAX_OPERATIONAL_HINT_GAP:
                groups.append([position])
            else:
                groups[-1].append(position)
        for group in groups:
            if len(group) < MIN_OPERATIONAL_HINTS:
                continue
            findings.append(
                Finding(
                    relative,
                    code_entries[group[0]][0],
                    "comment-debt",
                    "Dense operational/config block has no explanatory comments.",
                )
            )
        chunk = []

    for index, (line, code, comment) in enumerate(
        zip(lines, lexed.code, lexed.comments),
        start=1,
    ):
        if not line.strip():
            flush_chunk()
            continue
        chunk.append((index, code, comment))
    flush_chunk()
    return findings


def weak_python_lines(tree: ast.AST) -> set[int]:
    annotations: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            annotations.extend(argument.annotation for argument in node.args.posonlyargs if argument.annotation)
            annotations.extend(argument.annotation for argument in node.args.args if argument.annotation)
            annotations.extend(argument.annotation for argument in node.args.kwonlyargs if argument.annotation)
            if node.args.vararg and node.args.vararg.annotation:
                annotations.append(node.args.vararg.annotation)
            if node.args.kwarg and node.args.kwarg.annotation:
                annotations.append(node.args.kwarg.annotation)
            if node.returns:
                annotations.append(node.returns)
        elif isinstance(node, ast.AnnAssign):
            annotations.append(node.annotation)

    weak_lines: set[int] = set()
    for annotation in annotations:
        for node in ast.walk(annotation):
            name = None
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            if name and name.casefold() in WEAK_TYPE_NAMES:
                weak_lines.add(node.lineno)
    return weak_lines


def scan_python(
    lines: list[str],
    relative: str,
    max_function_lines: int,
) -> list[Finding]:
    try:
        tree = ast.parse("\n".join(lines))
    except SyntaxError:
        return []

    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.casefold() in VAGUE_NAMES:
            findings.append(
                Finding(relative, node.lineno, "vague-function-name", f"Function name '{node.name}' is vague.")
            )
        if node.end_lineno is not None:
            length = node.end_lineno - node.lineno + 1
            if length > max_function_lines:
                findings.append(
                    Finding(relative, node.lineno, "large-function", f"Function '{node.name}' spans {length} lines.")
                )

    for line_number in sorted(weak_python_lines(tree)):
        findings.append(
            Finding(relative, line_number, "weak-type-signal", "Inspect whether this weak type hides a real contract.")
        )
    return findings


def typescript_tokens(code: str) -> list[SyntaxToken]:
    tokens: list[SyntaxToken] = []
    index = 0
    round_depth = 0
    square_depth = 0
    curly_depth = 0
    compound_tokens = (
        "===",
        "!==",
        "...",
        "=>",
        "==",
        "!=",
        "<=",
        ">=",
        "&&",
        "||",
        "??",
        "?.",
        "++",
        "--",
    )
    while index < len(code):
        if code[index].isspace():
            index += 1
            continue
        start = index
        if code[index].isalpha() or code[index] in {"_", "$"}:
            index += 1
            while index < len(code) and (
                code[index].isalnum() or code[index] in {"_", "$"}
            ):
                index += 1
            value = code[start:index]
        elif code[index].isdigit():
            index += 1
            while index < len(code) and (
                code[index].isalnum() or code[index] in {".", "_"}
            ):
                index += 1
            value = code[start:index]
        else:
            value = next(
                (token for token in compound_tokens if code.startswith(token, index)),
                code[index],
            )
            index += len(value)
        depth = (round_depth, square_depth, curly_depth)
        tokens.append(SyntaxToken(value, start, index, depth))
        if value == "(":
            round_depth += 1
        elif value == ")":
            round_depth = max(0, round_depth - 1)
        elif value == "[":
            square_depth += 1
        elif value == "]":
            square_depth = max(0, square_depth - 1)
        elif value == "{":
            curly_depth += 1
        elif value == "}":
            curly_depth = max(0, curly_depth - 1)
    return tokens


def is_typescript_declaration_keyword(
    tokens: list[SyntaxToken],
    index: int,
) -> bool:
    if tokens[index].value.casefold() not in {"interface", "type"}:
        return False
    if index + 1 >= len(tokens):
        return False
    next_value = tokens[index + 1].value
    if not (next_value[0].isalpha() or next_value[0] in {"_", "$"}):
        return False
    if index == 0:
        return True
    previous = tokens[index - 1]
    if previous.depth != tokens[index].depth:
        return True
    return previous.value.casefold() in {"declare", "default", "export"} or previous.value in {
        ";",
        "{",
        "}",
    }


def typescript_context_positions(
    code_lines: list[str],
) -> tuple[list[set[int]], list[set[int]]]:
    """Locate weak-name tokens in multiline runtime and definite type contexts."""
    runtime_positions: list[set[int]] = []
    type_positions: list[set[int]] = []
    brace_stack: list[str] = []
    type_angle_stack: list[bool] = []
    previous_value: str | None = None
    pending_type_alias = False
    pending_type_brace = False
    pending_interface = False
    pending_class_body = False
    type_expression_active = False

    for code in code_lines:
        line_runtime_positions: set[int] = set()
        line_type_positions: set[int] = set()
        tokens = typescript_tokens(code)
        for index, token in enumerate(tokens):
            lowered = token.value.casefold()
            if lowered in {"any", "object"} and brace_stack and brace_stack[-1] == "runtime":
                line_runtime_positions.add(token.start)
            if lowered in {"any", "object"} and (
                type_expression_active
                or bool(type_angle_stack and type_angle_stack[-1])
                or bool(brace_stack and brace_stack[-1] == "type")
            ):
                line_type_positions.add(token.start)

            if is_typescript_declaration_keyword(tokens, index):
                if lowered == "type":
                    pending_type_alias = True
                else:
                    pending_interface = True
            if (
                lowered == "class"
                and index + 1 < len(tokens)
                and (
                    tokens[index + 1].value[0].isalpha()
                    or tokens[index + 1].value[0] in {"_", "$"}
                    or tokens[index + 1].value == "{"
                )
            ):
                pending_class_body = True

            if token.value == "=" and pending_type_alias:
                pending_type_brace = True
                pending_type_alias = False
                type_expression_active = True
            elif token.value == "=" and not type_angle_stack:
                type_expression_active = False
            elif token.value == ":" and (
                not brace_stack or brace_stack[-1] != "runtime"
            ) and colon_introduces_type(tokens, index):
                type_expression_active = True
            elif lowered in {"as", "extends", "implements", "satisfies"}:
                type_expression_active = True
            elif token.value == "<":
                type_angle_stack.append(
                    type_expression_active
                    or bool(brace_stack and brace_stack[-1] == "type")
                )
            elif token.value == ">" and type_angle_stack:
                type_angle_stack.pop()
            elif token.value == "{":
                if brace_stack and brace_stack[-1] == "runtime":
                    brace_kind = "block" if previous_value in {")", "=>"} else "runtime"
                    brace_stack.append(brace_kind)
                elif pending_class_body:
                    brace_stack.append("block")
                    pending_class_body = False
                elif pending_interface or pending_type_brace or type_expression_active or previous_value in {
                    ":",
                    "as",
                    "satisfies",
                }:
                    brace_stack.append("type")
                elif previous_value in {"=", "return", "=>", "(", "[", ",", "?"}:
                    brace_stack.append("runtime")
                else:
                    brace_stack.append("block")
                pending_interface = False
                pending_type_brace = False
            elif token.value == "}" and brace_stack:
                brace_stack.pop()
            elif token.value == ";":
                pending_type_alias = False
                pending_type_brace = False
                pending_interface = False
                pending_class_body = False
                type_expression_active = False

            previous_value = lowered if lowered in {"as", "return", "satisfies"} else token.value
        last_value = tokens[-1].value.casefold() if tokens else ""
        if type_angle_stack and not any(type_angle_stack):
            type_angle_stack.clear()
        if not type_angle_stack and not (
            brace_stack and brace_stack[-1] == "type"
        ) and last_value not in {
            "=",
            ":",
            "|",
            "&",
            ",",
            "<",
            "as",
            "extends",
            "implements",
            "satisfies",
        }:
            type_expression_active = False
        runtime_positions.append(line_runtime_positions)
        type_positions.append(line_type_positions)
    return runtime_positions, type_positions


def anchor_reaches_candidate(
    tokens: list[SyntaxToken],
    anchor_index: int,
    candidate_index: int,
) -> bool:
    anchor_depth = tokens[anchor_index].depth
    terminators = {",", ";", "=", "=>", ")", "]", "}"}
    for token in tokens[anchor_index + 1 : candidate_index]:
        if token.depth == anchor_depth and token.value in terminators:
            return False
        if any(
            token.depth[dimension] < anchor_depth[dimension]
            for dimension in range(3)
        ):
            return False
    return True


def colon_introduces_type(
    tokens: list[SyntaxToken],
    colon_index: int,
) -> bool:
    colon = tokens[colon_index]
    if colon.depth[2] > 0:
        # Object literal values and type-literal properties are lexically
        # identical. An outer annotation or type alias handles the latter.
        return False

    previous_index = colon_index - 1
    if previous_index >= 0 and tokens[previous_index].value == "?":
        optional_property = (
            previous_index >= 1
            and tokens[previous_index - 1].value[0].isidentifier()
        )
        if not optional_property:
            return False

    for token in reversed(tokens[:colon_index]):
        if token.depth != colon.depth:
            continue
        if token.value == "?":
            return False
        if token.value in {",", ";", "{", "}"}:
            break

    if colon.depth[0] > 0:
        return True
    if previous_index >= 0 and tokens[previous_index].value == ")":
        return True
    for token in reversed(tokens[:colon_index]):
        if token.depth != colon.depth:
            continue
        if token.value in {",", ";", "{", "}"}:
            break
        if token.value == "=":
            return False
    return True


def has_non_generic_type_context(
    tokens: list[SyntaxToken],
    candidate_index: int,
    runtime_value_positions: set[int],
) -> bool:
    declaration_modifiers = {"declare", "default", "export"}
    declaration_index = next(
        (
            index
            for index, token in enumerate(tokens[:candidate_index])
            if token.value.casefold() in {"interface", "type"}
            and all(
                prefix.value.casefold() in declaration_modifiers
                for prefix in tokens[:index]
            )
        ),
        None,
    )
    if (
        declaration_index is not None
        and tokens[declaration_index].value.casefold() == "interface"
    ):
        return True
    if (
        declaration_index is not None
        and tokens[declaration_index].value.casefold() == "type"
    ):
        for index, token in enumerate(tokens[:candidate_index]):
            if token.value == "=":
                return not any(
                    later.value == ";" and later.depth == token.depth
                    for later in tokens[index + 1 : candidate_index]
                )

    for index, token in enumerate(tokens[:candidate_index]):
        lowered = token.value.casefold()
        if lowered in {"as", "extends", "implements", "satisfies"}:
            if anchor_reaches_candidate(tokens, index, candidate_index):
                return True
        if (
            token.value == ":"
            and tokens[candidate_index].start not in runtime_value_positions
            and colon_introduces_type(tokens, index)
        ):
            if anchor_reaches_candidate(tokens, index, candidate_index):
                return True
    return False


def generic_pair_for_candidate(
    tokens: list[SyntaxToken],
    candidate_index: int,
) -> tuple[int, int] | None:
    stack: list[int] = []
    pairs: list[tuple[int, int]] = []
    for index, token in enumerate(tokens):
        if token.value == "<":
            stack.append(index)
        elif token.value == ">" and stack:
            pairs.append((stack.pop(), index))
    containing = [
        pair for pair in pairs if pair[0] < candidate_index < pair[1]
    ]
    if not containing:
        return None
    return max(containing, key=lambda pair: pair[0])


def candidate_is_generic_type(
    tokens: list[SyntaxToken],
    candidate_index: int,
    suffix: str,
    runtime_value_positions: set[int],
) -> bool:
    pair = generic_pair_for_candidate(tokens, candidate_index)
    if pair is None:
        return False
    opening, closing = pair
    content = tokens[opening + 1 : closing]
    if any(token.value in {"=", "=>", "{", "}"} for token in content):
        return False

    if has_non_generic_type_context(
        tokens,
        candidate_index,
        runtime_value_positions,
    ):
        return True

    previous = tokens[opening - 1] if opening > 0 else None
    following = tokens[closing + 1] if closing + 1 < len(tokens) else None
    if previous is not None and (
        previous.value[0].isalpha() or previous.value[0] in {"_", "$"}
    ):
        attached = previous.end == tokens[opening].start
        if not attached:
            return False
        if (
            suffix == ".tsx"
            and opening >= 2
            and tokens[opening - 2].value == "<"
        ):
            return True
        if following is None:
            return True
        if following.value in {
            "(",
            ")",
            "[",
            "]",
            ".",
            "?.",
            ",",
            ";",
            ":",
            "?",
            "=",
            "=>",
            "{",
            "}",
            "|",
            "&",
            ">",
        }:
            return True
        return False

    expression_starts = {None, "=", "(", "[", "{", ",", ":", ";", "=>", "return"}
    previous_value = previous.value.casefold() if previous is not None else None
    return suffix == ".ts" and previous_value in expression_starts


def weak_typescript_line(
    code: str,
    suffix: str,
    runtime_value_positions: set[int] | None = None,
    known_type_positions: set[int] | None = None,
) -> bool:
    tokens = typescript_tokens(code)
    runtime_positions = runtime_value_positions or set()
    definite_type_positions = known_type_positions or set()
    context_tokens = {"<", ":", "as", "extends", "implements", "interface", "satisfies", "type"}
    if not definite_type_positions and not any(
        token.value.casefold() in context_tokens for token in tokens
    ):
        return False
    for index, token in enumerate(tokens):
        if token.value.casefold() not in {"any", "object"}:
            continue
        previous = tokens[index - 1].value.casefold() if index > 0 else ""
        following = tokens[index + 1].value if index + 1 < len(tokens) else ""
        after_following = tokens[index + 2].value if index + 2 < len(tokens) else ""
        if previous in {"typeof", ".", "?."}:
            continue
        if (
            following in {":", "("}
            or (following in {"?", "!"} and after_following == ":")
        ):
            continue
        if (
            token.start in runtime_positions
            and previous == ":"
        ):
            continue
        if token.start in definite_type_positions:
            return True
        if has_non_generic_type_context(tokens, index, runtime_positions):
            return True
        if candidate_is_generic_type(
            tokens,
            index,
            suffix,
            runtime_positions,
        ):
            return True
    return False


def scan_line_signals(
    lines: list[str],
    lexed: LexedSource,
    suffix: str,
    relative: str,
) -> list[Finding]:
    findings: list[Finding] = []
    continuations = continuation_lines(lexed.code, suffix)
    if suffix in TYPESCRIPT_EXTENSIONS:
        runtime_positions, type_positions = typescript_context_positions(lexed.code)
    else:
        runtime_positions = [set() for _ in lines]
        type_positions = [set() for _ in lines]
    for index, (
        line,
        code,
        comment,
        is_continuation,
        line_runtime_positions,
        line_type_positions,
    ) in enumerate(
        zip(
            lines,
            lexed.code,
            lexed.comments,
            continuations,
            runtime_positions,
            type_positions,
        ),
        start=1,
    ):
        if suffix in TODO_EXTENSIONS and comment_has_debt_marker(comment):
            findings.append(
                Finding(relative, index, "todo", "TODO/FIXME marker merits follow-up review.")
            )
        if (
            suffix in CONTROL_FLOW_EXTENSIONS
            and not is_continuation
            and indentation_depth(line) >= 8
            and begins_control_flow(code, suffix)
        ):
            findings.append(
                Finding(relative, index, "deep-nesting", "Deep indentation increases cognitive load.")
            )
        if suffix in TYPESCRIPT_EXTENSIONS and weak_typescript_line(
            code,
            suffix,
            line_runtime_positions,
            line_type_positions,
        ):
            findings.append(
                Finding(relative, index, "weak-type-signal", "Inspect whether this weak type hides a real contract.")
            )
    return findings


def scan_file(
    path: Path,
    root: Path,
    max_file_lines: int,
    max_function_lines: int,
) -> tuple[list[Finding], ReadError | None]:
    relative = path.relative_to(root).as_posix()
    lines, read_error = read_source(path, relative)
    if lines is None:
        return [], read_error

    suffix = path.suffix.casefold()
    lexed = lex_source(lines, suffix)
    findings: list[Finding] = []
    findings.extend(scan_comment_debt(lines, lexed, suffix, relative))
    if suffix == ".py":
        findings.extend(scan_python(lines, relative, max_function_lines))

    if len(lines) > max_file_lines:
        findings.append(
            Finding(
                relative,
                1,
                "large-file",
                f"{len(lines)} lines; inspect whether responsibilities can be split.",
            )
        )
    if path.stem.casefold() in VAGUE_NAMES:
        findings.append(
            Finding(relative, 1, "vague-file-name", f"File name '{path.name}' is vague.")
        )
    findings.extend(scan_line_signals(lines, lexed, suffix, relative))
    return findings, None


def finding_sort_key(finding: Finding) -> tuple[str, str, int, str, str]:
    return (
        finding.path.casefold(),
        finding.path,
        finding.line,
        finding.kind,
        finding.message,
    )


def scan_paths(
    files: list[Path],
    root: Path,
    max_file_lines: int,
    max_function_lines: int,
) -> tuple[list[Finding], list[ReadError]]:
    findings: list[Finding] = []
    read_errors: list[ReadError] = []
    for path in files:
        file_findings, read_error = scan_file(
            path,
            root,
            max_file_lines,
            max_function_lines,
        )
        findings.extend(file_findings)
        if read_error is not None:
            read_errors.append(read_error)
    return (
        sorted(set(findings), key=finding_sort_key),
        sorted(read_errors, key=lambda error: (error.path.casefold(), error.path)),
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Scan source files for maintainability review prompts.",
    )
    parser.add_argument("path", help="Project, package, or source directory to scan.")
    parser.add_argument("--json", action="store_true", help="Print findings as JSON.")
    parser.add_argument(
        "--extensions",
        default=",".join(sorted(DEFAULT_EXTENSIONS)),
        help="Comma-separated extensions to include.",
    )
    parser.add_argument("--max-file-lines", type=positive_integer, default=500)
    parser.add_argument(
        "--max-function-lines",
        type=positive_integer,
        default=80,
        help="Maximum Python function length; other languages omit function-span checks.",
    )
    args = parser.parse_args(argv)

    requested = Path(args.path).expanduser()
    if not requested.exists():
        print(f"not found: {requested.resolve()}", file=sys.stderr)
        return 1
    root = requested.resolve()

    extensions = parse_extensions(args.extensions)
    discovery_errors: list[ReadError] = []
    try:
        root_mode = root.stat().st_mode
    except OSError:
        print(f"could not inspect: {root}", file=sys.stderr)
        return 1
    if stat.S_ISREG(root_mode):
        files = [root] if root.suffix.casefold() in extensions else []
        relative_root = root.parent
    elif stat.S_ISDIR(root_mode):
        files, discovery_errors = iter_files(root, extensions)
        relative_root = root
    else:
        files = []
        relative_root = root.parent
        discovery_errors = [
            ReadError(
                root.name,
                "Skipped an explicit path that is neither a regular file nor a directory.",
            )
        ]

    findings, file_read_errors = scan_paths(
        files,
        relative_root,
        args.max_file_lines,
        args.max_function_lines,
    )
    read_errors = sorted(
        set(discovery_errors + file_read_errors),
        key=lambda error: (error.path.casefold(), error.path, error.message),
    )
    files_scanned = len(files) - len(file_read_errors)
    if args.json:
        print(
            json.dumps(
                {
                    "root": str(root),
                    "files_scanned": files_scanned,
                    "read_errors": [asdict(error) for error in read_errors],
                    "findings": [asdict(item) for item in findings],
                },
                indent=2,
            )
        )
    else:
        print(f"Scanned {files_scanned} files under {root}")
        if read_errors:
            print(f"Reported {len(read_errors)} filesystem diagnostics.")
        if not findings:
            print("No maintainability prompts found by the lightweight scanner.")
        for item in findings:
            print(f"{item.path}:{item.line}: {item.kind}: {item.message}")

    for error in read_errors:
        print(f"{error.path}: {error.message}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Scan conventional test files for maintainability review prompts.

The scanner is intentionally heuristic. It recognizes a bounded set of test,
assertion, test-double, coupling, setup, time, sleep, randomness, and legacy
syntax. Findings are review prompts rather than verdicts.
"""

from __future__ import annotations

import argparse
import bisect
import json
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


TEST_EXTENSIONS = {
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".ts",
    ".tsx",
}
EXCLUDED_DIRECTORIES = {
    ".git",
    ".next",
    ".venv",
    "__pycache__",
    "__snapshots__",
    "build",
    "coverage",
    "dist",
    "fixtures",
    "generated",
    "node_modules",
    "snapshots",
    "target",
    "vendor",
}
TEST_DIRECTORIES = {"test", "tests", "spec", "specs", "__tests__"}
MAX_FILES = 2_000
MAX_VISITED_ENTRIES = 10_000
MAX_FILE_BYTES = 2_000_000
MAX_TOTAL_BYTES = 50_000_000
MAX_FINDINGS = 5_000
MAX_DIAGNOSTICS = 2_000
MAX_TEST_BLOCKS = 20_000
MAX_SETUP_WINDOW_LINES = 40

VAGUE_NAMES = {
    "edge case",
    "failure",
    "handles error",
    "handles errors",
    "happy path",
    "invalid input",
    "it works",
    "payment",
    "success",
    "test",
    "valid input",
    "withdrawal",
    "works",
}

JAVASCRIPT_TEST_RE = re.compile(
    r"(?<![.\w$])(?P<keyword>it|test|specify)(?:\.(?:only|skip|todo|concurrent))?"
    r"\s*\(\s*(?P<quote>['\"])(?P<name>(?:\\.|(?!\2).)*?)(?P=quote)",
    re.DOTALL,
)
JAVASCRIPT_EACH_TEST_RE = re.compile(
    r"(?<![.\w$])(?P<keyword>it|test)\.each\s*\("
    r"[\s\S]{0,4000}?\)\s*\(\s*(?P<quote>['\"])"
    r"(?P<name>(?:\\.|(?!\2).)*?)(?P=quote)",
)
DENO_TEST_RE = re.compile(
    r"(?P<keyword>\bDeno\.test)\s*\(\s*(?P<quote>['\"])"
    r"(?P<name>(?:\\.|(?!\2).)*?)(?P=quote)",
    re.DOTALL,
)
RUBY_TEST_RE = re.compile(
    r"(?m)^[ \t]*(?P<keyword>it|specify|test)\s+"
    r"(?P<quote>['\"])(?P<name>(?:\\.|(?!\2).)*?)(?P=quote)\s+do\b"
)
RUBY_PAREN_TEST_RE = re.compile(
    r"(?m)^[ \t]*(?P<keyword>it|specify|test)\s*\(\s*"
    r"(?P<quote>['\"])(?P<name>(?:\\.|(?!\2).)*?)(?P=quote)\s*\)\s+do\b"
)
PYTHON_TEST_RE = re.compile(
    r"(?m)^[ \t]*(?:async\s+)?def\s+(?P<name>test_[A-Za-z0-9_]+)\s*\("
)
PHP_FUNCTION_TEST_RE = re.compile(
    r"(?m)^[ \t]*(?:(?:public|protected|private|static|final)\s+)*"
    r"function\s+(?P<name>test[A-Za-z0-9_]*)\s*\("
)
PHP_ATTRIBUTE_TEST_RE = re.compile(
    r"(?m)^[ \t]*#\[(?:PHPUnit\\Framework\\Attributes\\)?Test\]"
    r"(?:\s*#\[[^\]\n]+\])*\s*"
    r"(?:(?:public|protected|private|static|final)\s+)*function\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
)
RUBY_METHOD_TEST_RE = re.compile(
    r"(?m)^[ \t]*def\s+(?P<name>test_[A-Za-z0-9_]+)\b"
)
GO_TEST_RE = re.compile(
    r"(?m)^[ \t]*func\s+(?P<name>Test[A-Z][A-Za-z0-9_]*)\s*"
    r"\(\s*[A-Za-z_][A-Za-z0-9_]*\s+\*testing\.T\s*\)"
)
RUST_TEST_RE = re.compile(
    r"(?m)^[ \t]*(?P<attributes>(?:#\[[^\]\n]+\][ \t]*(?:\n[ \t]*)?)+)"
    r"(?:async\s+)?fn\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
)
CSHARP_TEST_RE = re.compile(
    r"(?m)^[ \t]*\[(?:[A-Za-z_][A-Za-z0-9_]*\.)*"
    r"(?:Fact|Theory|Test|TestCase|TestMethod|DataTestMethod)"
    r"(?:\([^\]\n]*\))?\](?:\s*\[[^\]\n]+\])*\s*"
    r"(?:(?:public|private|protected|internal|static|async|virtual|override|sealed|new)\s+)*"
    r"[A-Za-z_][A-Za-z0-9_<>,.?\[\]]*\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
)
KOTEST_STRING_TEST_RE = re.compile(
    r"(?m)^[ \t]*(?P<quote>['\"])(?P<name>(?:\\.|(?!\1).)*?)"
    r"(?P=quote)\s*\{"
)
JAVA_TEST_RE = re.compile(
    r"(?m)^[ \t]*\@(?:Test|ParameterizedTest|RepeatedTest)\b[^\n]*"
    r"(?:\s*@[A-Za-z_][A-Za-z0-9_.]*(?:\([^\n]*\))?\s*)*\s*"
    r"(?:(?:public|private|protected|static|final|synchronized|default)\s+)*"
    r"[A-Za-z_][A-Za-z0-9_<>,.?\[\]]*\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
)
KOTLIN_TEST_RE = re.compile(
    r"(?m)^[ \t]*\@(?:Test|ParameterizedTest|RepeatedTest)\b[^\n]*"
    r"(?:\s*@[A-Za-z_][A-Za-z0-9_.]*(?:\([^\n]*\))?\s*)*\s*"
    r"(?:(?:public|private|protected|internal|suspend|open|final)\s+)*fun\s+"
    r"(?:`(?P<backtick>[^`]+)`|(?P<name>[A-Za-z_][A-Za-z0-9_]*))\s*\("
)
DISPLAY_NAME_RE = re.compile(
    r"@DisplayName\s*\(\s*(?P<quote>['\"])"
    r"(?P<name>(?:\\.|(?!\1).)*?)(?P=quote)\s*\)",
    re.DOTALL,
)

ASSERTION_PATTERNS = {
    ".py": re.compile(
        r"(?m)^\s*assert\b|\b(?:self\.)?assert[A-Z][A-Za-z0-9_]*\s*\(|"
        r"\b(?:pytest\.)?raises\s*\(|\bassertRaises(?:Regex)?\s*\("
    ),
    ".js": re.compile(
        r"\bexpect(?:\.(?:soft|poll))?\s*\(|\bassert(?:\.\w+)?\s*\(|"
        r"\b(?:toThrow|toThrowError)\s*\("
    ),
    ".jsx": re.compile(
        r"\bexpect(?:\.(?:soft|poll))?\s*\(|\bassert(?:\.\w+)?\s*\(|"
        r"\b(?:toThrow|toThrowError)\s*\("
    ),
    ".ts": re.compile(
        r"\bexpect(?:\.(?:soft|poll))?\s*\(|\bassert(?:\.\w+)?\s*\(|"
        r"\b(?:toThrow|toThrowError)\s*\("
    ),
    ".tsx": re.compile(
        r"\bexpect(?:\.(?:soft|poll))?\s*\(|\bassert(?:\.\w+)?\s*\(|"
        r"\b(?:toThrow|toThrowError)\s*\("
    ),
    ".php": re.compile(
        r"\bexpect\s*\(|(?:\$this->|::)\s*assert[A-Za-z0-9_]*\s*\(|"
        r"\$this->expectException(?:Message|Code)?\s*\(|\bassert\s*\("
    ),
    ".go": re.compile(
        r"\b[A-Za-z_][A-Za-z0-9_]*\.(?:Error|Errorf|Fatal|Fatalf|Fail|FailNow)\s*\(|"
        r"\b(?:assert|require)\.[A-Za-z_][A-Za-z0-9_]*\s*\("
    ),
    ".rs": re.compile(
        r"\b(?:assert|assert_eq|assert_ne|debug_assert|debug_assert_eq|debug_assert_ne)\s*!\s*\(|"
        r"#\[should_panic(?:\([^\]]*\))?\]"
    ),
    ".java": re.compile(
        r"\b(?:Assertions\.)?assert[A-Za-z0-9_]*\s*\(|\bassertThat\s*\("
    ),
    ".kt": re.compile(
        r"\b(?:Assertions\.)?assert[A-Za-z0-9_]*\s*\(|\bassertThat\s*\(|"
        r"\bshould(?:Not)?Be\b|\bshouldThrow(?:Any|Exactly)?\s*[<{(]"
    ),
    ".cs": re.compile(
        r"\bAssert\.[A-Za-z_][A-Za-z0-9_]*(?:<[^>\n]+>)?\s*\(|\.Should\s*\(\)\s*\."
        r"[A-Za-z_][A-Za-z0-9_]*(?:<[^>\n]+>)?\s*\(|\bShould[A-Z][A-Za-z0-9_]*(?:<[^>\n]+>)?\s*\(|"
        r"\bRecord\.Exception(?:Async)?\s*\("
    ),
    ".rb": re.compile(
        r"\b(?:assert|refute)(?:_[a-z_]+)?\s*(?:\(|\s)|\bexpect\s*(?:\(|\{)"
    ),
}
VERIFICATION_ASSERTION_PATTERNS = {
    ".py": re.compile(
        r"\b(?:pytest\.)?warns\s*\(|\b[A-Za-z_][A-Za-z0-9_]*\.assert_[a-z_]+\s*\("
    ),
    ".js": re.compile(
        r"\bassert(?:Equals|StrictEquals|NotEquals|ObjectMatch|Throws|Rejects|Exists|Match)\s*\("
    ),
    ".jsx": re.compile(
        r"\bassert(?:Equals|StrictEquals|NotEquals|ObjectMatch|Throws|Rejects|Exists|Match)\s*\("
    ),
    ".ts": re.compile(
        r"\bassert(?:Equals|StrictEquals|NotEquals|ObjectMatch|Throws|Rejects|Exists|Match)\s*\("
    ),
    ".tsx": re.compile(
        r"\bassert(?:Equals|StrictEquals|NotEquals|ObjectMatch|Throws|Rejects|Exists|Match)\s*\("
    ),
    ".php": re.compile(
        r"\$[A-Za-z_][A-Za-z0-9_]*->assert[A-Z][A-Za-z0-9_]*\s*\(|"
        r"->shouldHaveReceived\s*\(|"
        r"->shouldReceive\s*\([^)]*\)[\s\S]{0,300}?"
        r"->(?:once|twice|never|times)\s*\("
    ),
    ".go": re.compile(r"\b(?:Expect|Eventually|Consistently|Ω)\s*\("),
    ".java": re.compile(r"\b(?:Mockito\.)?verify\s*\("),
    ".kt": re.compile(
        r"\b(?:co)?verify\s*\{|\bshould(?:Contain|HaveSize|StartWith|EndWith)\b"
    ),
    ".cs": re.compile(
        r"\.Verify(?:All|NoOtherCalls)?\s*\(|"
        r"\b(?:StringAssert|CollectionAssert|FileAssert|DirectoryAssert)\."
        r"[A-Za-z_][A-Za-z0-9_]*\s*\("
    ),
    ".rb": re.compile(
        r"\bis_expected\.(?:to|not_to)\b|\.(?:must|wont)_[a-z_]+\b"
    ),
}
WEAK_ASSERTION_RE = re.compile(
    r"\b(?:assertNotNull|toBeTruthy|toBeFalsy|toBeDefined)\s*\(|"
    r"\.not\.toBeNull\s*\(|\bAssert\.NotNull\s*\("
)
MOCK_PATTERNS = {
    ".py": re.compile(r"\b(?:Mock|MagicMock|AsyncMock|create_autospec|patch)\s*\("),
    ".js": re.compile(r"\b(?:jest|vi)\.(?:fn|mock|spyOn)\s*\(|\bsinon\.(?:mock|spy|stub)\s*\("),
    ".jsx": re.compile(r"\b(?:jest|vi)\.(?:fn|mock|spyOn)\s*\(|\bsinon\.(?:mock|spy|stub)\s*\("),
    ".ts": re.compile(r"\b(?:jest|vi)\.(?:fn|mock|spyOn)\s*\(|\bsinon\.(?:mock|spy|stub)\s*\("),
    ".tsx": re.compile(r"\b(?:jest|vi)\.(?:fn|mock|spyOn)\s*\(|\bsinon\.(?:mock|spy|stub)\s*\("),
    ".php": re.compile(r"\bMockery::mock\s*\(|->(?:shouldReceive|expects)\s*\("),
    ".java": re.compile(r"\b(?:Mockito\.)?(?:mock|spy|when)\s*\("),
    ".kt": re.compile(r"\b(?:mockk|spyk|every|coEvery)\s*(?:<[^>]+>)?\s*\{"),
    ".cs": re.compile(r"\b(?:Mock|Substitute)\s*<|\bA\.Fake\s*<"),
    ".rb": re.compile(r"\b(?:allow|expect)\s*\([^)]*\)\.(?:to\s+receive|to_have_received)|\b(?:double|instance_double)\s*\("),
    ".go": re.compile(r"\bmock\.[A-Za-z_][A-Za-z0-9_]*\s*\(|\.EXPECT\s*\(\)"),
    ".rs": re.compile(r"\bmockall\b|\bMock[A-Z][A-Za-z0-9_]*::new\s*\("),
}
IMPLEMENTATION_COUPLING_RE = re.compile(
    r"\b(?:setAccessible|Reflection(?:Class|Method|Property)?|_under_test|_internal)\b|"
    r"\btoHaveBeenCalledBefore\s*\(|\bordered\s*\("
)
NONDETERMINISM_PATTERNS = {
    "direct-time-access": re.compile(
        r"\b(?:Date\.now|Carbon::now|datetime\.now|System\.currentTimeMillis|"
        r"time\.Now|SystemTime::now|Time\.now|Instant\.now)\s*\(|"
        r"\bnew\s+Date\s*\(\s*\)|(?<![.\w])time\s*\(\s*\)|"
        r"\bDateTime\.(?:UtcNow|Now)\b"
    ),
    "real-sleep": re.compile(
        r"(?<![.\w])(?:sleep|usleep)\s*\(|"
        r"\b(?:time\.sleep|time\.Sleep|Thread\.sleep|Task\.Delay|tokio::time::sleep)\s*\("
    ),
    "uncontrolled-randomness": re.compile(
        r"\b(?:Math\.random|random\.random|secrets\.[A-Za-z_][A-Za-z0-9_]*|"
        r"random_int|UUID\.randomUUID|Guid\.NewGuid|rand::random)\s*\("
    ),
}
LEGACY_RE = re.compile(
    r"\b(?:legacy|regressions?|backward|backwards|compatib(?:ility|le)?|"
    r"historical|pre-20\d\d|bug|incident)\b",
    re.IGNORECASE,
)
RATIONALE_RE = re.compile(
    r"\b(?:because|due\s+to|to\s+preserve|customer\s+contract|data\s+migration|"
    r"characterization|temporary\s+until|issue\s*#?\s*[A-Za-z0-9_-]+|"
    r"ticket\s*#?\s*[A-Za-z0-9_-]+|incident\s*#?\s*[A-Za-z0-9_-]+)\b",
    re.IGNORECASE,
)
SETUP_START_RE = re.compile(
    r"\b(?:beforeEach|beforeAll|setUp|setup|before_all)\s*\(|"
    r"@(?:Before|BeforeEach|BeforeAll)\b|"
    r"\[(?:SetUp|OneTimeSetUp|TestInitialize|ClassInitialize)\]",
    re.IGNORECASE,
)
SETUP_ASSIGNMENT_RE = re.compile(
    r"^\s*[$A-Za-z_][A-Za-z0-9_.$>:-]*\s*="
)
SETUP_FACTORY_RE = re.compile(
    r"\b(?:new\s+[A-Za-z_]|create\s*\(|factory\s*\()"
)


@dataclass(frozen=True)
class Finding:
    severity: str
    kind: str
    path: str
    line: int
    message: str
    suggestion: str


@dataclass(frozen=True)
class Diagnostic:
    kind: str
    path: str
    message: str


@dataclass(frozen=True)
class Declaration:
    name: str
    start: int
    name_offset: int
    body_search_start: int
    body_style: str


@dataclass(frozen=True)
class TestBlock:
    name: str
    start: int
    end: int
    name_offset: int
    raw: str
    code: str
    comments: str


@dataclass(frozen=True)
class SourceView:
    raw: str
    comments_masked: str
    code_masked: str
    comments_only: str
    line_starts: tuple[int, ...]

    def line(self, offset: int) -> int:
        return bisect.bisect_right(self.line_starts, max(0, offset))


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def is_conventional_test_directory(name: str) -> bool:
    normalized = name.casefold()
    return (
        normalized in TEST_DIRECTORIES
        or normalized.endswith(".tests")
        or normalized.endswith("_tests")
    )


def looks_like_test_path(path: Path, root: Path) -> bool:
    suffix = path.suffix.casefold()
    if suffix not in TEST_EXTENSIONS:
        return False
    relative = path.relative_to(root) if path.is_relative_to(root) else path
    parts = tuple(part.casefold() for part in relative.parts[:-1])
    filename = path.name.casefold()
    stem = path.stem.casefold()
    in_test_directory = is_conventional_test_directory(root.name) or any(
        is_conventional_test_directory(part) for part in parts
    )
    if suffix == ".go":
        return filename.endswith("_test.go")
    if suffix == ".py":
        return filename.startswith("test_") or filename.endswith("_test.py") or in_test_directory
    if suffix == ".rb":
        return filename.endswith(("_spec.rb", "_test.rb")) or in_test_directory
    if suffix == ".rs":
        # Rust commonly co-locates #[test] functions with production code. The
        # annotation recognizer is comment/string-masked before accepting them.
        return True
    filename_convention = (
        ".test." in filename
        or ".spec." in filename
        or stem.endswith("test")
        or stem.endswith("tests")
        or stem.endswith("spec")
    )
    return in_test_directory or filename_convention


def discover_files(root: Path) -> tuple[list[Path], list[Diagnostic]]:
    if root.is_file():
        return ([root] if root.suffix.casefold() in TEST_EXTENSIONS else []), []
    if not root.is_dir():
        diagnostic = Diagnostic(
            "non-regular-file",
            root.name,
            "Skipped an explicit path that is neither a regular file nor a directory.",
        )
        return [], [diagnostic]

    files: list[Path] = []
    diagnostics: list[Diagnostic] = []
    seen_targets: set[Path] = set()
    resolved_root = root.resolve()
    total_bytes = 0
    visited_entries = 0
    diagnostics_limited = False

    def record_diagnostic(diagnostic: Diagnostic) -> None:
        nonlocal diagnostics_limited
        if len(diagnostics) < MAX_DIAGNOSTICS - 2:
            diagnostics.append(diagnostic)
        elif not diagnostics_limited:
            diagnostics.append(
                Diagnostic(
                    "diagnostic-limit",
                    ".",
                    f"Further diagnostics were omitted after the deterministic limit of {MAX_DIAGNOSTICS - 2} details.",
                )
            )
            diagnostics_limited = True

    def record_terminal_diagnostic(diagnostic: Diagnostic) -> None:
        if len(diagnostics) < MAX_DIAGNOSTICS:
            diagnostics.append(diagnostic)
        elif diagnostics:
            diagnostics[-1] = diagnostic

    def record_walk_error(error: OSError) -> None:
        error_path = Path(error.filename) if error.filename else root
        record_diagnostic(
            Diagnostic(
                "unreadable-directory",
                relative_path(error_path, root),
                str(error),
            )
        )

    for current, directories, filenames in os.walk(
        root, followlinks=False, onerror=record_walk_error
    ):
        current_path = Path(current)
        kept_directories: list[str] = []
        for name in sorted(directories, key=lambda value: (value.casefold(), value)):
            visited_entries += 1
            if visited_entries > MAX_VISITED_ENTRIES:
                record_terminal_diagnostic(
                    Diagnostic(
                        "entry-limit",
                        ".",
                        f"Stopped discovery after visiting {MAX_VISITED_ENTRIES} filesystem entries.",
                    )
                )
                return files, diagnostics
            candidate = current_path / name
            if name.casefold() in EXCLUDED_DIRECTORIES:
                continue
            if candidate.is_symlink():
                try:
                    target = candidate.resolve(strict=True)
                except OSError as exc:
                    record_diagnostic(
                        Diagnostic("unreadable-symlink", relative_path(candidate, root), str(exc))
                    )
                else:
                    if not target.is_relative_to(resolved_root):
                        record_diagnostic(
                            Diagnostic(
                                "outside-root-symlink",
                                relative_path(candidate, root),
                                "Skipped a directory symlink whose target is outside the scan root.",
                            )
                        )
                continue
            kept_directories.append(name)
        directories[:] = kept_directories

        for name in sorted(filenames, key=lambda value: (value.casefold(), value)):
            visited_entries += 1
            if visited_entries > MAX_VISITED_ENTRIES:
                record_terminal_diagnostic(
                    Diagnostic(
                        "entry-limit",
                        ".",
                        f"Stopped discovery after visiting {MAX_VISITED_ENTRIES} filesystem entries.",
                    )
                )
                return files, diagnostics
            candidate = current_path / name
            if candidate.suffix.casefold() not in TEST_EXTENSIONS:
                continue
            try:
                target = candidate.resolve(strict=True)
            except OSError as exc:
                record_diagnostic(
                    Diagnostic("unreadable-file", relative_path(candidate, root), str(exc))
                )
                continue
            if not target.is_relative_to(resolved_root):
                record_diagnostic(
                    Diagnostic(
                        "outside-root-symlink",
                        relative_path(candidate, root),
                        "Skipped a file whose resolved target is outside the scan root.",
                    )
                )
                continue
            try:
                target_stat = target.stat()
            except OSError as exc:
                record_diagnostic(
                    Diagnostic("unreadable-file", relative_path(candidate, root), str(exc))
                )
                continue
            if not stat.S_ISREG(target_stat.st_mode):
                record_diagnostic(
                    Diagnostic(
                        "non-regular-file",
                        relative_path(candidate, root),
                        "Skipped a non-regular filesystem entry before reading.",
                    )
                )
                continue
            if not looks_like_test_path(candidate, root):
                continue
            if target in seen_targets:
                continue
            if total_bytes + target_stat.st_size > MAX_TOTAL_BYTES:
                record_terminal_diagnostic(
                    Diagnostic(
                        "total-byte-limit",
                        ".",
                        f"Stopped discovery at the deterministic {MAX_TOTAL_BYTES}-byte scan budget.",
                    )
                )
                return files, diagnostics
            if len(files) == MAX_FILES:
                record_terminal_diagnostic(
                    Diagnostic(
                        "file-limit",
                        ".",
                        f"Stopped discovery after the deterministic limit of {MAX_FILES} test candidates.",
                    )
                )
                return files, diagnostics
            files.append(candidate)
            seen_targets.add(target)
            total_bytes += target_stat.st_size
    return files, diagnostics


def rust_character_literal_end(text: str, opening: int) -> int | None:
    """Return a Rust character literal end without mistaking lifetimes for strings."""

    cursor = opening + 1
    if cursor >= len(text) or text[cursor] in {"\n", "\r", "'"}:
        return None
    if text[cursor] == "\\":
        cursor += 1
        if cursor >= len(text):
            return None
        if text[cursor] == "u" and cursor + 1 < len(text) and text[cursor + 1] == "{":
            closing_brace = text.find("}", cursor + 2)
            if closing_brace == -1:
                return None
            cursor = closing_brace + 1
        else:
            cursor += 1
    else:
        cursor += 1
    return cursor + 1 if cursor < len(text) and text[cursor] == "'" else None


def javascript_regex_literal_end(text: str, opening: int) -> int | None:
    """Return a likely JavaScript regex end without treating division as regex."""

    previous = opening - 1
    while previous >= 0 and text[previous].isspace():
        previous -= 1
    allowed_after_character = previous < 0 or text[previous] in "([{:;,=!?&|+-*%^~<>"
    previous_word = ""
    if previous >= 0 and (text[previous].isalnum() or text[previous] in "_$"):
        word_start = previous
        while word_start >= 0 and (
            text[word_start].isalnum() or text[word_start] in "_$"
        ):
            word_start -= 1
        previous_word = text[word_start + 1 : previous + 1]
    allowed_after_word = previous_word in {
        "await",
        "case",
        "in",
        "instanceof",
        "of",
        "return",
        "throw",
        "typeof",
        "yield",
    }
    if not (allowed_after_character or allowed_after_word):
        return None

    cursor = opening + 1
    in_character_class = False
    while cursor < len(text):
        character = text[cursor]
        if character in {"\n", "\r"}:
            return None
        if character == "\\" and cursor + 1 < len(text):
            cursor += 2
            continue
        if character == "[":
            in_character_class = True
        elif character == "]":
            in_character_class = False
        elif character == "/" and not in_character_class:
            cursor += 1
            while cursor < len(text) and text[cursor].isalpha():
                cursor += 1
            return cursor
        cursor += 1
    return None


def ruby_percent_literal_end(text: str, opening: int) -> int | None:
    cursor = opening + 1
    if cursor >= len(text):
        return None
    literal_type = ""
    if text[cursor] in "qQrwWiIxs":
        literal_type = text[cursor]
        cursor += 1
    if cursor >= len(text) or text[cursor].isalnum() or text[cursor].isspace():
        return None
    opening_delimiter = text[cursor]
    closing_delimiter = {"(": ")", "[": "]", "{": "}", "<": ">"}.get(
        opening_delimiter, opening_delimiter
    )
    paired = opening_delimiter != closing_delimiter
    depth = 1
    cursor += 1
    while cursor < len(text):
        if text[cursor] == "\\" and cursor + 1 < len(text):
            cursor += 2
            continue
        if paired and text[cursor] == opening_delimiter:
            depth += 1
        elif text[cursor] == closing_delimiter:
            depth -= 1
            if depth == 0:
                cursor += 1
                if literal_type == "r":
                    while cursor < len(text) and text[cursor].isalpha():
                        cursor += 1
                return cursor
        cursor += 1
    return None


def php_heredoc_end(text: str, opening: int) -> int | None:
    header = re.match(
        r"<<<[ \t]*(?:'(?P<single>[A-Za-z_][A-Za-z0-9_]*)'|"
        r'"(?P<double>[A-Za-z_][A-Za-z0-9_]*)"|(?P<bare>[A-Za-z_][A-Za-z0-9_]*))[^\n]*\n',
        text[opening:],
    )
    if not header:
        return None
    label = next(value for value in header.groupdict().values() if value)
    content_start = opening + header.end()
    terminator = re.search(
        rf"(?m)^[ \t]*{re.escape(label)};?[ \t]*(?:\r?\n|$)",
        text[content_start:],
    )
    return content_start + terminator.end() if terminator else None


def ruby_heredoc_end(text: str, opening: int) -> int | None:
    header = re.match(
        r"<<[-~]?[ \t]*(?:'(?P<single>[A-Za-z_][A-Za-z0-9_]*)'|"
        r'"(?P<double>[A-Za-z_][A-Za-z0-9_]*)"|`(?P<command>[A-Za-z_][A-Za-z0-9_]*)`|'
        r"(?P<bare>[A-Za-z_][A-Za-z0-9_]*))[^\n]*\n",
        text[opening:],
    )
    if not header:
        return None
    label = next(value for value in header.groupdict().values() if value)
    content_start = opening + header.end()
    terminator = re.search(
        rf"(?m)^[ \t]*{re.escape(label)}[ \t]*(?:\r?\n|$)",
        text[content_start:],
    )
    return content_start + terminator.end() if terminator else None


def rust_raw_string_end(text: str, opening: int) -> int | None:
    header = re.match(r"(?:br|rb|r)(?P<hashes>#+)?\"", text[opening:])
    if not header:
        return None
    hashes = header.group("hashes") or ""
    closing = '"' + hashes
    content_start = opening + header.end()
    close = text.find(closing, content_start)
    return close + len(closing) if close != -1 else None


def mask_source(text: str, suffix: str) -> tuple[str, str, str]:
    """Return stable-offset code and comment views of source text."""

    comments = list(text)
    code = list(text)
    comments_only = [character if character in {"\n", "\r"} else " " for character in text]
    slash_comments = suffix in {".cs", ".go", ".java", ".js", ".jsx", ".kt", ".php", ".rs", ".ts", ".tsx"}
    hash_comments = suffix in {".php", ".py", ".rb"}
    block_comments = slash_comments
    slash_regex_family = suffix in {".js", ".jsx", ".rb", ".ts", ".tsx"}
    index = 0
    length = len(text)

    def blank(target: list[str], start: int, end: int) -> None:
        for position in range(start, end):
            if target[position] not in {"\n", "\r"}:
                target[position] = " "

    def retain_comment(start: int, end: int) -> None:
        comments_only[start:end] = text[start:end]

    while index < length:
        if suffix == ".php" and text.startswith("<<<", index):
            heredoc_end = php_heredoc_end(text, index)
            if heredoc_end is not None:
                blank(comments, index, heredoc_end)
                blank(code, index, heredoc_end)
                index = heredoc_end
                continue
        if suffix == ".rb" and text.startswith("<<", index):
            heredoc_end = ruby_heredoc_end(text, index)
            if heredoc_end is not None:
                blank(comments, index, heredoc_end)
                blank(code, index, heredoc_end)
                index = heredoc_end
                continue
        if suffix == ".rs" and text[index] in {"b", "r"}:
            raw_end = rust_raw_string_end(text, index)
            if raw_end is not None:
                blank(comments, index, raw_end)
                blank(code, index, raw_end)
                index = raw_end
                continue
        if suffix == ".rb" and text[index] == "%":
            percent_end = ruby_percent_literal_end(text, index)
            if percent_end is not None:
                blank(comments, index, percent_end)
                blank(code, index, percent_end)
                index = percent_end
                continue
        if slash_comments and text.startswith("//", index):
            end = text.find("\n", index)
            end = length if end == -1 else end
            retain_comment(index, end)
            blank(comments, index, end)
            blank(code, index, end)
            index = end
            continue
        if block_comments and text.startswith("/*", index):
            close = text.find("*/", index + 2)
            end = length if close == -1 else close + 2
            retain_comment(index, end)
            blank(comments, index, end)
            blank(code, index, end)
            index = end
            continue
        if slash_regex_family and text[index] == "/":
            regex_end = javascript_regex_literal_end(text, index)
            if regex_end is not None:
                blank(comments, index, regex_end)
                blank(code, index, regex_end)
                index = regex_end
                continue
        if hash_comments and text[index] == "#" and not (
            suffix == ".php" and index + 1 < length and text[index + 1] == "["
        ):
            end = text.find("\n", index)
            end = length if end == -1 else end
            retain_comment(index, end)
            blank(comments, index, end)
            blank(code, index, end)
            index = end
            continue
        if text[index] in {"'", '"', "`"}:
            quote = text[index]
            if suffix == ".rs" and quote == "'":
                rust_end = rust_character_literal_end(text, index)
                if rust_end is None:
                    index += 1
                    continue
                blank(code, index, rust_end)
                index = rust_end
                continue
            delimiter = quote * 3 if text.startswith(quote * 3, index) else quote
            cursor = index + len(delimiter)
            while cursor < length:
                if text.startswith(delimiter, cursor):
                    cursor += len(delimiter)
                    break
                if text[cursor] == "\\" and cursor + 1 < length:
                    cursor += 2
                else:
                    cursor += 1
            blank(code, index, cursor)
            index = cursor
            continue
        index += 1
    return "".join(comments), "".join(code), "".join(comments_only)


def build_source_view(text: str, suffix: str) -> SourceView:
    comments_masked, code_masked, comments_only = mask_source(text, suffix)
    line_starts = [0]
    line_starts.extend(match.end() for match in re.finditer("\n", text))
    return SourceView(text, comments_masked, code_masked, comments_only, tuple(line_starts))


def declaration_from_match(
    match: re.Match[str], body_style: str = "function"
) -> Declaration:
    name_group = "backtick" if match.groupdict().get("backtick") else "name"
    return Declaration(
        match.group(name_group),
        match.start(),
        match.start(name_group),
        match.end(),
        body_style,
    )


def annotated_declaration(
    match: re.Match[str], view: SourceView
) -> Declaration:
    display_name = DISPLAY_NAME_RE.search(
        view.comments_masked, match.start(), match.end()
    )
    if display_name:
        return Declaration(
            display_name.group("name"),
            match.start(),
            display_name.start("name"),
            match.end(),
            "function",
        )
    return declaration_from_match(match)


def quoted_declarations(
    pattern: re.Pattern[str], view: SourceView, body_style: str
) -> Iterable[Declaration]:
    for match in pattern.finditer(view.comments_masked):
        start = match.start("keyword")
        end = match.end("keyword")
        if view.code_masked[start:end] == match.group("keyword"):
            yield declaration_from_match(match, body_style)


def find_declarations(
    view: SourceView, suffix: str, limit: int
) -> tuple[list[Declaration], bool]:
    matches: list[Declaration] = []

    def collect(items: Iterable[Declaration]) -> bool:
        for item in items:
            if len(matches) == limit:
                return True
            matches.append(item)
        return False

    limited = False
    if suffix in {".js", ".jsx", ".ts", ".tsx"}:
        limited = collect(quoted_declarations(DENO_TEST_RE, view, "callback"))
        if not limited:
            limited = collect(
                quoted_declarations(JAVASCRIPT_EACH_TEST_RE, view, "callback")
            )
        if not limited:
            limited = collect(
                quoted_declarations(JAVASCRIPT_TEST_RE, view, "callback")
            )
    elif suffix == ".php":
        limited = collect(quoted_declarations(JAVASCRIPT_TEST_RE, view, "callback"))
        if not limited:
            limited = collect(
                declaration_from_match(match)
                for match in PHP_ATTRIBUTE_TEST_RE.finditer(view.code_masked)
            )
        if not limited:
            limited = collect(
                declaration_from_match(match)
                for match in PHP_FUNCTION_TEST_RE.finditer(view.code_masked)
            )
    elif suffix == ".rb":
        limited = collect(quoted_declarations(RUBY_TEST_RE, view, "ruby"))
        if not limited:
            limited = collect(
                quoted_declarations(RUBY_PAREN_TEST_RE, view, "ruby")
            )
        if not limited:
            limited = collect(
                declaration_from_match(match, "ruby")
                for match in RUBY_METHOD_TEST_RE.finditer(view.code_masked)
            )
    elif suffix == ".py":
        limited = collect(
            declaration_from_match(match)
            for match in PYTHON_TEST_RE.finditer(view.code_masked)
        )
    elif suffix == ".go":
        limited = collect(
            declaration_from_match(match)
            for match in GO_TEST_RE.finditer(view.code_masked)
        )
    elif suffix == ".rs":
        for match in RUST_TEST_RE.finditer(view.code_masked):
            if re.search(r"#\[(?:(?:tokio::)?test|rstest)\b", match.group("attributes")):
                if len(matches) == limit:
                    limited = True
                    break
                matches.append(declaration_from_match(match))
    elif suffix == ".cs":
        limited = collect(
            declaration_from_match(match)
            for match in CSHARP_TEST_RE.finditer(view.code_masked)
        )
    elif suffix == ".java":
        for match in JAVA_TEST_RE.finditer(view.comments_masked):
            annotation = view.comments_masked.find("@", match.start(), match.end())
            if annotation != -1 and view.code_masked[annotation] == "@":
                if len(matches) == limit:
                    limited = True
                    break
                matches.append(annotated_declaration(match, view))
    elif suffix == ".kt":
        for match in KOTLIN_TEST_RE.finditer(view.comments_masked):
            annotation = view.comments_masked.find("@", match.start(), match.end())
            if annotation != -1 and view.code_masked[annotation] == "@":
                if len(matches) == limit:
                    limited = True
                    break
                matches.append(annotated_declaration(match, view))
        if not limited and re.search(r"\bStringSpec\s*\(", view.code_masked):
            for match in KOTEST_STRING_TEST_RE.finditer(view.comments_masked):
                if len(matches) == limit:
                    limited = True
                    break
                matches.append(
                    Declaration(
                        match.group("name"),
                        match.start(),
                        match.start("name"),
                        match.end(),
                        "direct-brace",
                    )
                )
    unique = {(item.name_offset, item.name): item for item in matches}
    ordered = sorted(unique.values(), key=lambda item: (item.start, item.name.casefold()))
    return ordered, limited


KNOWN_FRAMEWORK_MARKERS = {
    ".py": re.compile(r"(?m)^[ \t]*(?:async[ \t]+)?def[ \t]+test_"),
    ".js": re.compile(r"\bDeno\.test\s*\(|(?<![.\w$])(?:it|test|specify)(?:\.each|\s*\()"),
    ".jsx": re.compile(r"\bDeno\.test\s*\(|(?<![.\w$])(?:it|test|specify)(?:\.each|\s*\()"),
    ".ts": re.compile(r"\bDeno\.test\s*\(|(?<![.\w$])(?:it|test|specify)(?:\.each|\s*\()"),
    ".tsx": re.compile(r"\bDeno\.test\s*\(|(?<![.\w$])(?:it|test|specify)(?:\.each|\s*\()"),
    ".php": re.compile(r"#\[(?:[^\]\n]*\\)?Test\]|(?<![.\w$])(?:it|test)\s*\("),
    ".rb": re.compile(r"(?m)^[ \t]*(?:it|specify|test)(?:\s*\(|\s+['\"])"),
    ".go": re.compile(r"(?m)^[ \t]*func[ \t]+Test[A-Z]"),
    ".rs": re.compile(r"#\[(?:(?:tokio::)?test|rstest)\b"),
    ".java": re.compile(r"(?m)^[ \t]*@(?:Test|ParameterizedTest|RepeatedTest)\b"),
    ".kt": re.compile(r"(?m)^[ \t]*@(?:Test|ParameterizedTest|RepeatedTest)\b|\bStringSpec\s*\("),
    ".cs": re.compile(r"(?m)^[ \t]*\[(?:[A-Za-z_]\w*\.)*(?:Fact|Theory|Test)\b"),
}


def has_known_framework_marker(view: SourceView, suffix: str) -> bool:
    marker = KNOWN_FRAMEWORK_MARKERS.get(suffix)
    return bool(marker and marker.search(view.code_masked))


def find_matching_delimiter(
    code: str, opening: int, fallback: int
) -> int | None:
    opening_character = code[opening]
    closing_character = {"(": ")", "{": "}"}[opening_character]
    depth = 0
    for offset in range(opening, fallback):
        if code[offset] == opening_character:
            depth += 1
        elif code[offset] == closing_character:
            depth -= 1
            if depth == 0:
                return offset
    return None


def find_callback_body_opening(code: str, start: int, fallback: int) -> int | None:
    paren_depth = 1
    bracket_depth = 0
    brace_depth = 0
    argument_start = start
    for offset in range(start, fallback):
        character = code[offset]
        if character == "(":
            paren_depth += 1
        elif character == ")":
            paren_depth -= 1
            if paren_depth == 0:
                return None
        elif character == "[":
            bracket_depth += 1
        elif character == "]":
            bracket_depth = max(0, bracket_depth - 1)
        elif character == "{":
            if paren_depth == 1 and bracket_depth == 0 and brace_depth == 0:
                prefix = code[argument_start:offset].rstrip()
                if prefix.endswith("=>") or re.search(
                    r"\bfunction(?:\s+[A-Za-z_][A-Za-z0-9_]*)?\s*"
                    r"\([^)]*\)(?:\s*use\s*\([^)]*\))?\s*$",
                    prefix,
                ):
                    return offset
            brace_depth += 1
        elif character == "}":
            brace_depth = max(0, brace_depth - 1)
        elif (
            character == ","
            and paren_depth == 1
            and bracket_depth == 0
            and brace_depth == 0
        ):
            argument_start = offset + 1
    return None


def find_braced_block_end(
    code: str, declaration: Declaration, fallback: int
) -> int:
    if declaration.body_style == "direct-brace":
        opening = declaration.body_search_start - 1
    elif declaration.body_style == "callback":
        opening = find_callback_body_opening(
            code, declaration.body_search_start, fallback
        )
    else:
        signature_tail = declaration.body_search_start - 1
        if code[signature_tail] == ")":
            signature_close = signature_tail
        else:
            signature_opening = code.rfind(
                "(", declaration.name_offset, declaration.body_search_start
            )
            signature_close = (
                find_matching_delimiter(code, signature_opening, fallback)
                if signature_opening != -1
                else None
            )
        opening = (
            code.find("{", signature_close + 1, fallback)
            if signature_close is not None
            else -1
        )
    if opening is None or opening == -1:
        return fallback
    closing = find_matching_delimiter(code, opening, fallback)
    return closing + 1 if closing is not None else fallback


def find_python_block_end(view: SourceView, declaration: Declaration, fallback: int) -> int:
    line_start = view.line_starts[view.line(declaration.start) - 1]
    signature_opening = declaration.body_search_start - 1
    signature_close = find_matching_delimiter(
        view.code_masked, signature_opening, fallback
    )
    if signature_close is None:
        return fallback
    declaration_line_end = view.raw.find("\n", signature_close, fallback)
    if declaration_line_end == -1:
        return fallback
    declaration_line = view.raw[line_start:declaration_line_end]
    base_indent = len(declaration_line) - len(declaration_line.lstrip(" \t"))
    cursor = declaration_line_end + 1
    while cursor < fallback:
        end = view.raw.find("\n", cursor, fallback)
        end = fallback if end == -1 else end
        line = view.code_masked[cursor:end]
        if line.strip():
            indent = len(line) - len(line.lstrip(" \t"))
            if indent <= base_indent:
                return cursor
        cursor = end + 1
    return fallback


RUBY_BLOCK_TOKEN_RE = re.compile(
    r"\b(?:do|def|class|module|if|unless|case|begin|while|until|for|end)\b"
)


def find_ruby_block_end(code: str, declaration: Declaration, fallback: int) -> int:
    depth = 1
    always_open = {"do", "def", "class", "module", "case", "begin", "for"}
    conditional_open = {"if", "unless", "while", "until"}
    for token in RUBY_BLOCK_TOKEN_RE.finditer(
        code, declaration.body_search_start, fallback
    ):
        word = token.group(0)
        if word == "end":
            depth -= 1
            if depth == 0:
                return token.end()
            continue
        line_start = code.rfind("\n", declaration.body_search_start, token.start()) + 1
        prefix = code[line_start:token.start()].strip()
        if word in always_open or (
            word in conditional_open and (not prefix or prefix.endswith("="))
        ):
            depth += 1
    return fallback


def segment_tests(
    view: SourceView, declarations: list[Declaration], suffix: str
) -> list[TestBlock]:
    blocks: list[TestBlock] = []
    for index, declaration in enumerate(declarations):
        fallback = declarations[index + 1].start if index + 1 < len(declarations) else len(view.raw)
        if suffix in {".cs", ".go", ".java", ".js", ".jsx", ".kt", ".php", ".rs", ".ts", ".tsx"}:
            end = find_braced_block_end(view.code_masked, declaration, fallback)
        elif suffix == ".py":
            end = find_python_block_end(view, declaration, fallback)
        elif suffix == ".rb":
            end = find_ruby_block_end(view.code_masked, declaration, fallback)
        else:
            end = fallback
        blocks.append(
            TestBlock(
                name=declaration.name,
                start=declaration.start,
                end=end,
                name_offset=declaration.name_offset,
                raw=view.raw[declaration.start:end],
                code=view.code_masked[declaration.start:end],
                comments=view.comments_only[declaration.start:end],
            )
        )
    return blocks


def normalize_name(name: str) -> str:
    value = re.sub(r"^(?:test_|test)", "", name)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[_-]+", " ", value).strip().lower()


def normalize_signal_text(text: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.sub(r"[_-]+", " ", value)


def add_finding(
    findings: list[Finding],
    *,
    severity: str,
    kind: str,
    path: Path,
    root: Path,
    line: int,
    message: str,
    suggestion: str,
) -> None:
    findings.append(
        Finding(
            severity=severity,
            kind=kind,
            path=relative_path(path, root),
            line=line,
            message=message,
            suggestion=suggestion,
        )
    )


def scan_block(
    block: TestBlock,
    *,
    suffix: str,
    view: SourceView,
    path: Path,
    root: Path,
    findings: list[Finding],
) -> None:
    normalized = normalize_name(block.name)
    if normalized in VAGUE_NAMES or len(normalized.split()) < 3:
        add_finding(
            findings,
            severity="medium",
            kind="vague-test-name",
            path=path,
            root=root,
            line=view.line(block.name_offset),
            message=f"Test name is too vague to document behavior: {block.name!r}.",
            suggestion="Rename it to describe the condition and expected outcome in domain language.",
        )

    assertion_pattern = ASSERTION_PATTERNS[suffix]
    assertions = list(assertion_pattern.finditer(block.code))
    verification_pattern = VERIFICATION_ASSERTION_PATTERNS.get(suffix)
    if verification_pattern:
        assertions.extend(verification_pattern.finditer(block.code))
    if not assertions:
        add_finding(
            findings,
            severity="medium",
            kind="missing-recognized-assertion",
            path=path,
            root=root,
            line=view.line(block.name_offset),
            message=f"Test {block.name!r} has no assertion recognized by this scanner.",
            suggestion="Confirm the block proves an observable result, state change, effect, or error contract.",
        )
    weak = list(WEAK_ASSERTION_RE.finditer(block.code))
    if weak and len(assertions) <= 2:
        add_finding(
            findings,
            severity="medium",
            kind="weak-assertion",
            path=path,
            root=root,
            line=view.line(block.start + weak[0].start()),
            message="A broad truthiness or nullness assertion may pass while behavior is wrong.",
            suggestion="Prefer an expected value, domain error, state transition, or emitted effect.",
        )

    mock_pattern = MOCK_PATTERNS.get(suffix)
    mocks = list(mock_pattern.finditer(block.code)) if mock_pattern else []
    if len(mocks) >= 4:
        add_finding(
            findings,
            severity="medium",
            kind="over-mocking",
            path=path,
            root=root,
            line=view.line(block.start + mocks[0].start()),
            message=f"Test {block.name!r} contains {len(mocks)} recognized mock, spy, or stub signals.",
            suggestion="Check whether behavior assertions, a fake, or a clearer production boundary tells the story better.",
        )

    coupling = IMPLEMENTATION_COUPLING_RE.search(block.code)
    if coupling:
        add_finding(
            findings,
            severity="medium",
            kind="implementation-coupling",
            path=path,
            root=root,
            line=view.line(block.start + coupling.start()),
            message="The test uses a recognized private-access or interaction-order signal.",
            suggestion="Prefer observable behavior or a narrow adapter contract where practical.",
        )

    for kind, pattern in NONDETERMINISM_PATTERNS.items():
        match = pattern.search(block.code)
        if not match:
            continue
        messages = {
            "direct-time-access": "The test reads a recognized wall-clock API directly.",
            "real-sleep": "The test calls a recognized real sleep or delay API.",
            "uncontrolled-randomness": "The test calls a recognized randomness API directly.",
        }
        suggestions = {
            "direct-time-access": "Inject or freeze a clock at the boundary used by the behavior.",
            "real-sleep": "Use a controllable scheduler, fake timer, or observable completion signal.",
            "uncontrolled-randomness": "Inject a seeded generator or deterministic value source.",
        }
        add_finding(
            findings,
            severity="medium",
            kind=kind,
            path=path,
            root=root,
            line=view.line(block.start + match.start()),
            message=messages[kind],
            suggestion=suggestions[kind],
        )

    legacy_scope = normalize_signal_text(
        f"{block.name}\n{block.code}\n{block.comments}"
    )
    legacy = LEGACY_RE.search(legacy_scope)
    if legacy and not RATIONALE_RE.search(legacy_scope):
        add_finding(
            findings,
            severity="medium",
            kind="missing-legacy-rationale",
            path=path,
            root=root,
            line=view.line(block.name_offset),
            message=f"Test {block.name!r} signals legacy or regression behavior without a recognized rationale.",
            suggestion="Add a compact reason such as a customer contract, migration, incident, ticket, or temporary characterization boundary.",
        )


def scan_fixture_noise(
    view: SourceView,
    declarations: list[Declaration],
    path: Path,
    root: Path,
    findings: list[Finding],
) -> None:
    line_ends = list(view.line_starts[1:]) + [len(view.raw)]
    declaration_starts = [item.start for item in declarations]
    construction_starts: list[int] = []
    line_offset = 0
    for line in view.code_masked.splitlines(keepends=True):
        segment_offset = 0
        for segment in line.split(";"):
            if SETUP_ASSIGNMENT_RE.search(segment) or SETUP_FACTORY_RE.search(segment):
                construction_starts.append(line_offset + segment_offset)
            segment_offset += len(segment) + 1
        line_offset += len(line)
    for setup in SETUP_START_RE.finditer(view.code_masked):
        start_line = view.line(setup.start())
        end_line = min(start_line + MAX_SETUP_WINDOW_LINES - 1, len(line_ends))
        capped_end = line_ends[end_line - 1]
        next_index = bisect.bisect_right(declaration_starts, setup.start())
        next_test = declaration_starts[next_index] if next_index < len(declaration_starts) else len(view.raw)
        window_end = min(capped_end, next_test)
        construction_start = bisect.bisect_left(construction_starts, setup.start())
        construction_end = bisect.bisect_left(construction_starts, window_end)
        construction_count = construction_end - construction_start
        if construction_count >= 8:
            add_finding(
                findings,
                severity="medium",
                kind="fixture-noise",
                path=path,
                root=root,
                line=start_line,
                message=f"Shared setup contains {construction_count} recognized construction or assignment lines.",
                suggestion="Move scenario-specific facts into the test or use domain-named builders and factory states.",
            )
            return


def read_source(path: Path, root: Path) -> tuple[SourceView | None, Diagnostic | None]:
    display = relative_path(path, root)
    try:
        size = path.stat().st_size
    except OSError as exc:
        return None, Diagnostic("unreadable-file", display, str(exc))
    if size > MAX_FILE_BYTES:
        return None, Diagnostic(
            "file-too-large",
            display,
            f"Skipped a {size}-byte file; the per-file limit is {MAX_FILE_BYTES} bytes.",
        )
    try:
        data = path.read_bytes()
    except OSError as exc:
        return None, Diagnostic("unreadable-file", display, str(exc))
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        return None, Diagnostic("invalid-utf8", display, str(exc))
    return build_source_view(text, path.suffix.casefold()), None


def scan_file(
    path: Path,
    root: Path,
    *,
    finding_budget: int,
    block_budget: int,
) -> tuple[list[Finding], int, list[Diagnostic], bool, bool]:
    view, diagnostic = read_source(path, root)
    if view is None:
        return [], 0, [diagnostic] if diagnostic else [], False, False
    suffix = path.suffix.casefold()
    declarations, block_limited = find_declarations(view, suffix, block_budget)
    if not declarations:
        diagnostics = []
        if has_known_framework_marker(view, suffix):
            diagnostics.append(
                Diagnostic(
                    "known-test-marker-unparsed",
                    relative_path(path, root),
                    "Recognized a framework test marker but could not segment a supported test declaration.",
                )
            )
        return [], 0, diagnostics, False, block_limited
    findings: list[Finding] = []
    blocks = segment_tests(view, declarations, suffix)
    processed_blocks = 0
    finding_limited = False
    for index, block in enumerate(blocks):
        scan_block(
            block,
            suffix=suffix,
            view=view,
            path=path,
            root=root,
            findings=findings,
        )
        processed_blocks += 1
        if len(findings) >= finding_budget:
            finding_limited = len(findings) > finding_budget or index + 1 < len(blocks)
            findings = findings[:finding_budget]
            break
    if not finding_limited and len(findings) < finding_budget:
        scan_fixture_noise(view, declarations, path, root, findings)
        if len(findings) > finding_budget:
            findings = findings[:finding_budget]
            finding_limited = True
    return findings, processed_blocks, [], finding_limited, block_limited


def format_text(findings: list[Finding], diagnostics: list[Diagnostic]) -> str:
    lines: list[str] = []
    if findings:
        lines.append("Maintainable test review prompts:")
        for item in findings:
            lines.append(f"- {item.severity.upper()} {item.kind} {item.path}:{item.line}")
            lines.append(f"  {item.message}")
            lines.append(f"  Suggestion: {item.suggestion}")
    else:
        lines.append("No maintainable-test review prompts found.")
    if diagnostics:
        lines.append("Scan diagnostics:")
        for item in diagnostics:
            lines.append(f"- {item.kind} {item.path}: {item.message}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan conventional tests for maintainable test review prompts."
    )
    parser.add_argument("path", nargs="?", default=".", help="Project, directory, or test file to scan.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    requested = Path(args.path).expanduser()
    if not requested.exists():
        print(f"not found: {requested.resolve()}", file=sys.stderr)
        return 1
    root = requested.resolve()
    scan_root = root if root.is_dir() else root.parent
    files, diagnostics = discover_files(root)
    findings: list[Finding] = []
    test_blocks = 0
    scanned_files = 0
    for file_index, path in enumerate(files):
        remaining_findings = MAX_FINDINGS - len(findings)
        remaining_blocks = MAX_TEST_BLOCKS - test_blocks
        file_findings, block_count, file_diagnostics, finding_limited, block_limited = scan_file(
            path,
            scan_root,
            finding_budget=remaining_findings,
            block_budget=remaining_blocks,
        )
        scanned_files += 1
        findings.extend(file_findings)
        test_blocks += block_count
        diagnostics.extend(file_diagnostics)
        more_files = file_index + 1 < len(files)
        if finding_limited or (len(findings) == MAX_FINDINGS and more_files):
            diagnostics.append(
                Diagnostic(
                    "finding-limit",
                    ".",
                    f"Stopped scanning at the deterministic limit of {MAX_FINDINGS} findings.",
                )
            )
            break
        if block_limited or (test_blocks == MAX_TEST_BLOCKS and more_files):
            diagnostics.append(
                Diagnostic(
                    "test-block-limit",
                    ".",
                    f"Stopped scanning at the deterministic limit of {MAX_TEST_BLOCKS} test blocks.",
                )
            )
            break

    findings.sort(key=lambda item: (item.path.casefold(), item.path, item.line, item.kind))
    diagnostics.sort(key=lambda item: (item.path.casefold(), item.path, item.kind, item.message))
    if len(diagnostics) > MAX_DIAGNOSTICS:
        diagnostics = diagnostics[: MAX_DIAGNOSTICS - 1]
        if not any(item.kind == "diagnostic-limit" for item in diagnostics):
            diagnostics.append(
                Diagnostic(
                    "diagnostic-limit",
                    ".",
                    f"Diagnostics were capped at {MAX_DIAGNOSTICS} structured entries.",
                )
            )

    if args.json:
        print(
            json.dumps(
                {
                    "summary": {
                        "scanned_files": scanned_files,
                        "test_blocks": test_blocks,
                        "findings": len(findings),
                        "diagnostics": len(diagnostics),
                    },
                    "findings": [asdict(item) for item in findings],
                    "diagnostics": [asdict(item) for item in diagnostics],
                },
                indent=2,
            )
        )
    else:
        print(format_text(findings, diagnostics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

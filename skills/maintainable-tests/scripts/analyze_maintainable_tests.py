#!/usr/bin/env python3
"""Scan test files for maintainability review prompts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


TEST_EXTENSIONS = {
    ".php",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".cs",
    ".rb",
}
TEST_NAME_RE = re.compile(
    r"""(?x)
    \b(?:it|test|specify)\s*\(\s*
    (?:'(?P<single_quoted>(?:\\.|[^'\\])*)'|"(?P<double_quoted>(?:\\.|[^"\\])*)")
    |\b(?:it|specify|test)\s+(?:'(?P<ruby_single>(?:\\.|[^'\\])*)'|"(?P<ruby_double>(?:\\.|[^"\\])*)")\s+do\b
    |def\s+(?P<python>test_[A-Za-z0-9_]+)\s*\(
    |function\s+(?P<php>test[A-Za-z0-9_]*)\s*\(
    |func\s+(?P<go>Test[A-Za-z0-9_]*)\s*\(
    |\#\[(?:(?:tokio::)?test|rstest)(?:\([^\]]*\))?\][\s\S]{0,80}?\bfn\s+(?P<rust>[A-Za-z0-9_]+)\s*\(
    """
)
CSHARP_TEST_NAME_RE = re.compile(
    r"""(?x)
    \[(?:Fact|Theory|Test|TestCase|TestMethod|DataTestMethod)(?:\([^\]]*\))?\]
    (?:\s*\[[^\]]+\])*
    \s*(?:(?:public|private|protected|internal|static|async|virtual|override|sealed|new)\s+)*
    [A-Za-z_][A-Za-z0-9_<>,.?\[\]]*\s+
    (?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(
    """
)
JAVA_TEST_NAME_RE = re.compile(
    r"""(?x)
    @(?:Test|ParameterizedTest|RepeatedTest)
    (?:\s*@[A-Za-z_][A-Za-z0-9_.]*(?:\([^)]*\))?)*
    \s*(?:(?:public|private|protected|static|final|synchronized|abstract|default)\s+)*
    [A-Za-z_][A-Za-z0-9_<>,.?\[\]]*\s+
    (?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(
    """
)
KOTLIN_TEST_NAME_RE = re.compile(
    r"""(?x)
    @(?:Test|ParameterizedTest|RepeatedTest)
    (?:\s*@[A-Za-z_][A-Za-z0-9_.]*(?:\([^)]*\))?)*
    \s*(?:(?:public|private|protected|internal|suspend|open|final)\s+)*fun\s+
    (?:`(?P<backtick>[^`]+)`|(?P<name>[A-Za-z_][A-Za-z0-9_]*))\s*\(
    """
)
VAGUE_NAMES = {
    "works",
    "it works",
    "test",
    "handles error",
    "handles errors",
    "valid input",
    "invalid input",
    "success",
    "failure",
    "withdrawal",
    "payment",
    "happy path",
    "edge case",
}
ASSERTION_RE = re.compile(
    r"\b(?:assert|expect|verify|assertThat|assertEquals|toBe|toEqual)\b|"
    r"\brequire\.|\bassert_[A-Za-z0-9_]+!\s*\(|\bt\.",
    re.IGNORECASE,
)
CSHARP_ASSERTION_RE = re.compile(
    r"\.\s*(?:Should|ShouldBe[A-Za-z0-9_]*)\s*\(",
    re.IGNORECASE,
)
KOTLIN_ASSERTION_RE = re.compile(
    r"\b(?:shouldBe|shouldNotBe|shouldThrow|shouldContain|shouldHaveSize)\b"
)
WEAK_ASSERTION_RE = re.compile(
    r"\b(?:assertNotNull|toBeTruthy|toBeFalsy|toBeDefined|not\.toBeNull)\b"
)
MOCK_RE = re.compile(
    r"\b(?:mock|spy|stub|shouldReceive|expects|sinon|createMock|Mockery)\b|(?:jest|vi)\.fn\b|expects\s*\(",
    re.IGNORECASE,
)
IMPLEMENTATION_COUPLING_RE = re.compile(
    r"\b(?:setAccessible|Reflection|_under|_internal|"
    r"toHaveBeenCalledBefore|ordered\()"
)
NONDETERMINISM_RE = re.compile(
    r"\b(?:Date\.now|new Date\(\s*\)|time\(\)|Carbon::now|datetime\.now|"
    r"System\.currentTimeMillis|time\.Now\(|SystemTime::now|Time\.now|"
    r"DateTime\.(?:UtcNow|Now)|Instant\.now\(|sleep\(|setTimeout\(|"
    r"Math\.random|random_int|rand\(|uuid\()"
)
LEGACY_RE = re.compile(r"\b(?:legacy|regression|backward|backwards|compatib|historical|pre-20\d\d|bug|incident)\b", re.IGNORECASE)
RATIONALE_RE = re.compile(r"\b(?:because|why|regression|issue|ticket|incident|migration|contract|compatib|customer|archived|temporary|characterization)\b", re.IGNORECASE)
SETUP_START_RE = re.compile(
    r"\b(?:beforeEach|setUp|setup|before_all|beforeEach\(|before\(|describe\(|"
    r"TestMain\b)|@(?:Before|BeforeEach|BeforeAll)\b|"
    r"\[(?:SetUp|OneTimeSetUp|TestInitialize|ClassInitialize)\]",
    re.IGNORECASE,
)
TEST_BLOCK_START_RE = re.compile(
    r"\b(?:it|test|specify)\s*\(|\b(?:it|specify|test)\s+['\"]|def\s+test_|"
    r"function\s+test|func\s+Test|"
    r"\#\[(?:(?:tokio::)?test|rstest)(?:\([^\]]*\))?\]|"
    r"\[(?:Fact|Theory|Test|TestCase|TestMethod|DataTestMethod)(?:\([^\]]*\))?\]|"
    r"@(?:Test|ParameterizedTest|RepeatedTest)\b"
)


@dataclass(frozen=True)
class Finding:
    severity: str
    kind: str
    path: str
    line: int
    message: str
    suggestion: str


def is_test_file(path: Path) -> bool:
    # Scan every advertised source extension, then let TEST_BLOCK_START_RE
    # distinguish real tests from support and production files. This covers
    # inline test modules and framework-specific directory conventions.
    return path.suffix.casefold() in TEST_EXTENSIONS


def iter_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
        return
    ignored = {".git", "node_modules", "vendor", "dist", "build", "coverage", ".next", "target"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative_directories = path.relative_to(root).parts[:-1]
        if any(part.casefold() in ignored for part in relative_directories):
            continue
        if is_test_file(path):
            yield path


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def normalize_name(name: str) -> str:
    name = re.sub(r"^(test_|test)", "", name)
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return name.replace("_", " ").replace("-", " ").strip().lower()


def add(
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
            path=str(path.relative_to(root) if path.is_relative_to(root) else path),
            line=line,
            message=message,
            suggestion=suggestion,
        )
    )


def scan_names(text: str, path: Path, root: Path, findings: list[Finding]) -> None:
    def inspect(raw: str, offset: int) -> None:
        name = normalize_name(raw)
        if name in VAGUE_NAMES or len(name.split()) < 3:
            add(
                findings,
                severity="medium",
                kind="vague-test-name",
                path=path,
                root=root,
                line=line_number(text, offset),
                message=f"Test name is too vague to document behavior: {raw!r}.",
                suggestion="Rename it to describe the condition and expected outcome in domain language.",
            )

    for match in TEST_NAME_RE.finditer(text):
        raw = next(group for group in match.groupdict().values() if group)
        inspect(raw, match.start())

    suffix = path.suffix.casefold()
    patterns = []
    if suffix == ".cs":
        patterns = [CSHARP_TEST_NAME_RE]
    elif suffix == ".java":
        patterns = [JAVA_TEST_NAME_RE]
    elif suffix == ".kt":
        patterns = [KOTLIN_TEST_NAME_RE]
    for pattern in patterns:
        for match in pattern.finditer(text):
            raw = next(group for group in match.groupdict().values() if group)
            inspect(raw, match.start())


def scan_assertions(text: str, path: Path, root: Path, findings: list[Finding]) -> None:
    assertion_count = len(ASSERTION_RE.findall(text))
    suffix = path.suffix.casefold()
    if suffix == ".cs":
        assertion_count += len(CSHARP_ASSERTION_RE.findall(text))
    elif suffix == ".kt":
        assertion_count += len(KOTLIN_ASSERTION_RE.findall(text))
    weak_count = len(WEAK_ASSERTION_RE.findall(text))
    if assertion_count == 0:
        add(
            findings,
            severity="critical",
            kind="missing-assertion",
            path=path,
            root=root,
            line=1,
            message="Test file has no recognizable assertions.",
            suggestion="Assert the observable result, state change, emitted event, or error contract.",
        )
    if weak_count >= 2 or (weak_count == 1 and assertion_count <= 2):
        first = WEAK_ASSERTION_RE.search(text)
        add(
            findings,
            severity="high",
            kind="weak-assertion",
            path=path,
            root=root,
            line=line_number(text, first.start()) if first else 1,
            message="Weak assertions can pass while the behavior is wrong.",
            suggestion="Use assertions that name expected values, domain errors, state changes, or emitted effects.",
        )


def scan_mocks_and_coupling(text: str, path: Path, root: Path, findings: list[Finding]) -> None:
    mock_count = len(MOCK_RE.findall(text))
    if mock_count >= 5:
        first = MOCK_RE.search(text)
        add(
            findings,
            severity="high",
            kind="over-mocking",
            path=path,
            root=root,
            line=line_number(text, first.start()) if first else 1,
            message=f"Test contains {mock_count} mock/stub/spy signals.",
            suggestion="Check whether behavior assertions, a fake, or a clearer production boundary would document the rule better.",
        )
    coupling = IMPLEMENTATION_COUPLING_RE.search(text)
    if coupling:
        add(
            findings,
            severity="high",
            kind="implementation-coupling",
            path=path,
            root=root,
            line=line_number(text, coupling.start()),
            message="Test appears coupled to private implementation or incidental interaction order.",
            suggestion="Prefer observable behavior or a narrow adapter contract; avoid exposing internals only for tests.",
        )


def scan_fixture_noise(text: str, path: Path, root: Path, findings: list[Finding]) -> None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not SETUP_START_RE.search(line):
            continue
        block: list[str] = []
        for nested_index, item in enumerate(lines[index : min(len(lines), index + 35)]):
            if nested_index > 0 and TEST_BLOCK_START_RE.search(item):
                break
            block.append(item)
        assignments = sum(1 for item in block if re.search(r"(=|->|::|new\s+|create\(|factory\()", item))
        assertions = sum(1 for item in block if ASSERTION_RE.search(item))
        if assignments >= 8 and assertions == 0:
            add(
                findings,
                severity="medium",
                kind="fixture-noise",
                path=path,
                root=root,
                line=index + 1,
                message="Shared setup has many construction lines before any behavior is asserted.",
                suggestion="Move scenario-specific facts into the test or use domain-named builders/factory states.",
            )
            return


def scan_nondeterminism(text: str, path: Path, root: Path, findings: list[Finding]) -> None:
    match = NONDETERMINISM_RE.search(text)
    if match:
        add(
            findings,
            severity="high",
            kind="hidden-nondeterminism",
            path=path,
            root=root,
            line=line_number(text, match.start()),
            message="Test touches time, randomness, network, sleeps, or external URLs directly.",
            suggestion="Control the dependency with a clock, seed, fake, local fixture, or adapter boundary.",
        )


def scan_legacy_rationale(text: str, path: Path, root: Path, findings: list[Finding]) -> None:
    legacy = LEGACY_RE.search(text)
    if legacy and not RATIONALE_RE.search(text):
        add(
            findings,
            severity="high",
            kind="missing-legacy-rationale",
            path=path,
            root=root,
            line=line_number(text, legacy.start()),
            message="Legacy or regression behavior is mentioned without rationale.",
            suggestion="Add a compact reason: compatibility, migration, incident/ticket, customer data, or temporary characterization.",
        )


def scan_file(path: Path, root: Path) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    if not TEST_BLOCK_START_RE.search(text):
        return []
    findings: list[Finding] = []
    scan_names(text, path, root, findings)
    scan_assertions(text, path, root, findings)
    scan_mocks_and_coupling(text, path, root, findings)
    scan_fixture_noise(text, path, root, findings)
    scan_nondeterminism(text, path, root, findings)
    scan_legacy_rationale(text, path, root, findings)
    return findings


def format_text(findings: list[Finding]) -> str:
    if not findings:
        return "No maintainable-test review prompts found."
    lines = ["Maintainable test review prompts:"]
    for item in findings:
        lines.append(f"- {item.severity.upper()} {item.kind} {item.path}:{item.line}")
        lines.append(f"  {item.message}")
        lines.append(f"  Suggestion: {item.suggestion}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan test files for maintainable test review prompts."
    )
    parser.add_argument("path", nargs="?", default=".", help="Project, directory, or test file to scan.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        print(f"not found: {root}", file=sys.stderr)
        return 1
    scan_root = root if root.is_dir() else root.parent
    findings: list[Finding] = []
    for path in iter_files(root):
        findings.extend(scan_file(path.resolve(), scan_root))

    findings.sort(key=lambda item: (item.path, item.line, item.kind))
    if args.json:
        print(json.dumps({"findings": [asdict(item) for item in findings]}, indent=2))
    else:
        print(format_text(findings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

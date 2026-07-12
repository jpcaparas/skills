#!/usr/bin/env python3
"""Deterministic regression tests for the maintainable-code skill."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import TypeAlias


REQUIRED_TAGS = {
    "smoke",
    "edge",
    "negative",
    "disclosure",
    "comments",
    "markup",
    "sources",
    "diagrams",
    "guardrails",
    "quality-gates",
    "compatibility",
}

ASSERTION_TYPES = {
    "functional",
    "structural",
    "disclosure",
    "negative",
    "verification",
}

LARGE_MESSAGE = "Function '{}' spans {} lines."
VAGUE_MESSAGE = "Function name '{}' is vague."
WEAK_MESSAGE = "Inspect whether this weak type hides a real contract."
TODO_MESSAGE = "TODO/FIXME marker merits follow-up review."

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | Mapping[str, "JsonValue"]
JsonObject: TypeAlias = Mapping[str, JsonValue]


def load_json(path: Path) -> JsonObject:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def write_text(path: Path, content: str, *, bom: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoding = "utf-8-sig" if bom else "utf-8"
    path.write_text(content, encoding=encoding)


def write_positive_fixture(root: Path) -> None:
    write_text(
        root / "PhpSample.PHP",
        """<?php
final class Example {
    public function process(): array {
        $value = [];
        return $value;
    }
}
""",
    )
    write_text(
        root / "PythonSample.PY",
        """def process(value: object) -> object:
    normalized = value
    result = normalized
    return result
# TODO: assign an owner before release
""",
        bom=True,
    )
    write_text(
        root / "RubySample.RB",
        """class Example
  def process(value)
    normalized = value
    normalized
  end
end
""",
    )
    write_text(
        root / "TypeAlias.TS",
        """export type Payload = Record<string, any>;
""",
    )
    write_text(
        root / "TypeScriptArrow.TS",
        """export const handler = (value: string) => {
  const normalized = value;
  return normalized;
};
""",
    )
    write_text(
        root / "TypeScriptSample.TS",
        """export function process(value: any) {
  const nested = {
    value,
  };
  return nested;
}
""",
    )


def expected_positive_findings() -> list[JsonObject]:
    return [
        {
            "path": "PythonSample.PY",
            "line": 1,
            "kind": "large-function",
            "message": LARGE_MESSAGE.format("process", 4),
        },
        {
            "path": "PythonSample.PY",
            "line": 1,
            "kind": "vague-function-name",
            "message": VAGUE_MESSAGE.format("process"),
        },
        {
            "path": "PythonSample.PY",
            "line": 1,
            "kind": "weak-type-signal",
            "message": WEAK_MESSAGE,
        },
        {
            "path": "PythonSample.PY",
            "line": 5,
            "kind": "todo",
            "message": TODO_MESSAGE,
        },
        {
            "path": "TypeAlias.TS",
            "line": 1,
            "kind": "weak-type-signal",
            "message": WEAK_MESSAGE,
        },
        {
            "path": "TypeScriptSample.TS",
            "line": 1,
            "kind": "weak-type-signal",
            "message": WEAK_MESSAGE,
        },
    ]


def write_clean_fixture(root: Path) -> None:
    write_text(
        root / "CleanConfig.YML",
        """rules:
  nested:
    values:
      by_environment:
        production:
          rollout:
            policy:
              case: strict
""",
    )
    write_text(
        root / "CleanPhp.PHP",
        """<?php
$text = 'function process(value: any) { TODO FIXME }';
echo <<<EOT
function process(value: any) { TODO FIXME }
EOT;
function calculate($value) {
    return $value;
}
$service->process($text);
""",
    )
    write_text(
        root / "CleanPython.PY",
        '''TEXT = """TODO FIXME
def process(value: object):
                if hidden:
                    return value
"""

def calculate(value: str) -> str:
    return value

calculate(TEXT)
''',
    )
    write_text(
        root / "CleanRuby.RB",
        """TEXT = <<~CONTENT
def process(value)
                if hidden
                end
end
CONTENT
left << bits
=begin
def process(value)
                if hidden
end
=end
def calculate(value)
  value
end
process(TEXT)
""",
    )
    write_text(
        root / "CleanTerraform.TF",
        """/*
run:
gh api /example
jq -r value
sort -u values
while read value
artifact cache
docker build
kubectl apply
*/
resource "example" "safe" {}
""",
    )
    write_text(
        root / "CleanTypeScript.TS",
        """const text = `TODO FIXME any object
function process(value: any) {
                if (hidden) return value;
}`;
/*
function process(value: any) {
                if (hidden) return value;
}
*/
export function calculate(value: string) {
  const closingBrace = /}/;
  return value;
}
export function process(): null | { value: string } {
  return null;
}
calculate(text);
process(text);
const anyValue = text;
const objectValue = { if: "data" };
const options = createOptions(
                {
                  if: true,
                },
);
const expressionBody = (value: string) => ({ value });
const wrapped = makeHandler((value: string) => { return value; });
const deeplyIndented = {
                if: true,
};
type ReservedKeys = {
                if?: boolean;
                if(): void;
};
""",
    )
    write_text(
        root / "CleanComponent.TSX",
        """const choice = left < any ? first : second;
const widget = <Widget value={any} />;
""",
    )
    write_text(
        root / "Incomplete.PY",
        '''text = """TODO FIXME
# TODO inside an incomplete string
''',
    )
    invalid_utf8 = root / "InvalidUtf8.TS"
    invalid_utf8.write_bytes(b'const label: string = "\xff";\n')

    write_text(
        root / "node_modules" / "Ignored.ts",
        "export function process(value: any) { return value; } // TODO\n",
    )
    write_text(
        root / "DIST" / "Ignored.py",
        "def process(value: object) -> object:\n    return value\n# TODO\n",
    )


def write_comment_debt_fixture(root: Path) -> None:
    write_text(
        root / "artifacts.YML",
        """name: artifacts
on: workflow_dispatch
jobs:
  download:
    runs-on: ubuntu-latest
    steps:
      - name: Download artifacts
        run: |
          artifacts="$(gh api /repos/example/actions/artifacts)"
          jq -r '.artifacts[]' <<< "$artifacts"
          sort -u artifacts.txt
          while read -r artifact; do
            gh run download "$artifact"
          done
""",
    )


def write_comment_scope_fixtures(root: Path) -> None:
    write_text(
        root / "Footer.PS1",
        """$artifacts = gh api /example
$items = jq -r value
$sorted = sort -u values
$cache = artifact cache
$image = docker build
$cluster = kubectl apply
$result = curl /example
$output = terraform plan
# This artifact phase preserves API ordering because downloads are sequential.
""",
    )
    write_text(
        root / "Header.PS1",
        """<#
Copyright Example Corporation
All rights reserved here
#>
#!/usr/bin/env pwsh
# TODO(owner): replace the legacy entry point after ticket OPS-123
$artifacts = gh api /example
$items = jq -r value
$sorted = sort -u values
$cache = artifact cache
$image = docker build
$cluster = kubectl apply
$result = curl /example
$output = terraform plan
""",
    )
    write_text(
        root / "Phases.PS1",
        """# This artifact phase preserves API ordering because downloads are sequential.
$first1 = gh api /first
$first2 = jq -r first
$first3 = sort -u first
$first4 = artifact cache
$first5 = docker build
$first6 = kubectl apply
$first7 = curl /first
$first8 = terraform plan
$second1 = gh api /second
$second2 = jq -r second
$second3 = sort -u second
$second4 = artifact cache
$second5 = docker build
$second6 = kubectl apply
$second7 = curl /second
$second8 = terraform plan
""",
    )


def write_typescript_precision_fixtures(root: Path) -> None:
    write_text(
        root / "Types.TS",
        """let direct: any;
let nested: Result<any>;
function read(): string | any { return source; }
const cast = source as string | any;
const asserted = <any>source;
call<any>(source);
const shaped: { value: any } = source;
export type Loose = any;
const any = source;
const objectValue = { value: any };
const objectKey = { any: true };
const ternary = ready ? any : object;
const alternate = ready ? value : any;
const equality = any === object;
const looseEquality = any == object;
const lessThan = left < any ? first : second;
const spacedComparison = left < any > right;
const compactComparison = left<any>right;
""",
    )
    write_text(
        root / "Component.TSX",
        """const widget = <Widget value={any} />;
const assertionLike = <any>source;
const genericWidget = <Widget<any> value={source} />;
""",
    )
    write_text(
        root / "RuntimeValues.TS",
        """const values = {
  value: any,
  kind: object,
  nested: {
    fallback: any,
  },
};
class Extended extends Base {
  method() {
    return any;
  }
}
""",
    )
    write_text(
        root / "TypeQueries.TS",
        """type PropertyNames = { any: string; object: number };
type PropertyMethods = { any(): string; object?: number };
type AnyValueQuery = typeof any;
type ObjectValueQuery = typeof object;
type AnyPropertyQuery = typeof namespace.any;
""",
    )
    write_text(
        root / "MultilineTypes.TS",
        """type Shape = {
  value: any;
  kind: object;
  read(): any;
};
type Lookup = Record<
  string,
  any
>;
const response: ApiResponse<
  any
> = getResponse();
class Container {
  value: any;
}
""",
    )


def write_javascript_lexer_fixture(root: Path) -> None:
    write_text(
        root / "Lexing.TS",
        r"""const url = /https?:\/\//; const first: any = source;
const slash = /[//]/; const second: Result<any> = source;
const block = /[/*]/; const third: string | any = source;
const ratio = total / count; // TODO(owner): retained for compatibility #123
const pattern = /TODO [/*]/; // FIXME(owner): remove after issue OPS-9
const rendered = `raw any TODO ${source as any}`;
const nested = `outer ${`inner ${source as Result<any>}`}`;
if (ok) /[/*] TODO/.test(value);
""",
    )
    write_text(
        root / "TemplateFlow.TS",
        """const rendered = `${(() => {
                if (enabled) {
                  // TODO: assign owner
                  return source as any;
                }
              })()}`;
""",
    )


def write_utf16_fixture(root: Path) -> None:
    path = root / "Encoded.PS1"
    content = """$artifacts = gh api `
    /example
$items = jq -r value
$sorted = sort -u values
$cache = artifact cache
$image = docker build
$cluster = kubectl apply
$result = curl /example
$output = terraform plan
"""
    path.write_text(content, encoding="utf-16")


def write_powershell_here_string_fixture(root: Path) -> None:
    write_text(
        root / "HereString.PS1",
        """$payload = @'
gh api /example
jq -r value
sort -u values
artifact cache
docker build
kubectl apply
curl /example
terraform plan
'@
Write-Output $payload
""",
    )


def write_deep_nesting_fixture(root: Path) -> None:
    write_text(
        root / "Nested.TS",
        """export function choosePolicy(flags: Flags) {
  if (flags.configured) {
    if (flags.supported) {
      if (flags.environment) {
        if (flags.authorized) {
          if (flags.validated) {
            if (flags.recoverable) {
              if (flags.confirmed) {
                if (!flags.blocked) {
                  return "active";
                }
              }
            }
          }
        }
      }
    }
  }
}
""",
    )


def scanner_command(skill_root: Path, fixture: Path, *arguments: str) -> list[str]:
    return [
        sys.executable,
        str(skill_root / "scripts" / "analyze_maintainability.py"),
        str(fixture),
        *arguments,
    ]


def run_json_scan(
    skill_root: Path,
    fixture: Path,
    *arguments: str,
    timeout: float = 10,
) -> tuple[subprocess.CompletedProcess[str] | None, JsonObject | None]:
    try:
        result = subprocess.run(
            scanner_command(skill_root, fixture, "--json", *arguments),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, None
    if result.returncode != 0:
        return result, None
    payload = json.loads(result.stdout)
    return result, payload if isinstance(payload, Mapping) else None


def load_analyzer(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("maintainable_analyzer_under_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load analyzer module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def check_read_error_continuation(
    analyzer: ModuleType,
    fixture_root: Path,
    errors: list[str],
) -> None:
    readable = fixture_root / "Readable.PY"
    unreadable = fixture_root / "Unreadable.PY"
    write_text(readable, "# TODO: retain this finding\n")
    write_text(unreadable, "# TODO: scanner should not read this fixture\n")
    original_read_source = analyzer.read_source

    def simulated_read_source(path: Path, relative: str):
        if path == unreadable:
            return None, analyzer.ReadError(relative)
        return original_read_source(path, relative)

    analyzer.read_source = simulated_read_source
    try:
        findings, read_errors = analyzer.scan_paths(
            [unreadable, readable],
            fixture_root,
            500,
            80,
        )
    finally:
        analyzer.read_source = original_read_source

    if [error.path for error in read_errors] != ["Unreadable.PY"]:
        errors.append("scanner did not report the simulated read error deterministically")
    if not any(
        finding.path == "Readable.PY" and finding.kind == "todo"
        for finding in findings
    ):
        errors.append("scanner stopped instead of continuing after a read error")


def check_traversal_error_continuation(
    analyzer: ModuleType,
    fixture_root: Path,
    errors: list[str],
) -> None:
    readable = fixture_root / "Readable.PY"
    write_text(readable, "# TODO: retain this source candidate\n")
    blocked = fixture_root / "blocked"
    original_walk = analyzer.os.walk

    def simulated_walk(root, *, topdown, followlinks, onerror):
        onerror(PermissionError(13, "permission denied", str(blocked)))
        yield str(root), [], [readable.name]

    analyzer.os.walk = simulated_walk
    try:
        files, diagnostics = analyzer.iter_files(fixture_root, {".py"})
    finally:
        analyzer.os.walk = original_walk

    if files != [readable]:
        errors.append("scanner stopped discovering readable siblings after a traversal error")
    if [
        (diagnostic.path, diagnostic.message) for diagnostic in diagnostics
    ] != [("blocked", "Could not traverse directory.")]:
        errors.append("scanner did not report a deterministic root-relative traversal diagnostic")


def check_powershell_lexing(analyzer: ModuleType, errors: list[str]) -> None:
    lines = [
        "Write-Output `",
        "                if: value",
        "Write-Output `#literal",
        "Write-Output 'literal`' # real comment",
    ]
    lexed = analyzer.lex_source(lines, ".ps1")
    continuations = analyzer.continuation_lines(lexed.code, ".ps1")
    if continuations != [False, True, False, False]:
        errors.append("scanner did not recognize PowerShell backtick continuation")
    if lexed.comments[2].strip() or "#literal" not in lexed.code[2]:
        errors.append("scanner treated a PowerShell backtick-escaped # as a comment")
    if "# real comment" not in lexed.comments[3]:
        errors.append("scanner treated a backtick as an escape inside a PowerShell single-quoted string")


def check_fifo_safety(
    skill_root: Path,
    analyzer: ModuleType,
    fixture_root: Path,
    errors: list[str],
) -> None:
    if not hasattr(os, "mkfifo"):
        return
    readable = fixture_root / "Readable.PY"
    fifo = fixture_root / "Blocked.PY"
    write_text(readable, "# TODO: readable sibling remains scannable\n")
    os.mkfifo(fifo)

    result, payload = run_json_scan(skill_root, fixture_root, timeout=3)
    if result is None or payload is None:
        errors.append("scanner blocked while discovering a matching-suffix FIFO")
    else:
        if payload.get("files_scanned") != 1:
            errors.append("scanner miscounted regular files after skipping a FIFO")
        expected_diagnostic = {
            "path": "Blocked.PY",
            "message": "Skipped a non-regular filesystem entry before reading.",
        }
        if payload.get("read_errors") != [expected_diagnostic]:
            errors.append("scanner did not report the discovered FIFO deterministically")
        findings = payload.get("findings", [])
        if not isinstance(findings, list) or not any(
            isinstance(finding, Mapping)
            and finding.get("path") == "Readable.PY"
            and finding.get("kind") == "todo"
            for finding in findings
        ):
            errors.append("scanner failed to scan a readable sibling after skipping a FIFO")

    explicit_result, explicit_payload = run_json_scan(skill_root, fifo, timeout=3)
    if explicit_result is None or explicit_payload is None:
        errors.append("scanner blocked on an explicitly requested FIFO")
    elif explicit_payload.get("read_errors") != [
        {
            "path": "Blocked.PY",
            "message": "Skipped an explicit path that is neither a regular file nor a directory.",
        }
    ]:
        errors.append("scanner did not diagnose an explicitly requested FIFO")

    lines, diagnostic = analyzer.read_source(fifo, "Blocked.PY")
    if lines is not None or diagnostic is None or "non-regular" not in diagnostic.message:
        errors.append("scanner read boundary did not reject a FIFO without blocking")


def check_scanner(skill_root: Path, errors: list[str]) -> None:
    analyzer_path = skill_root / "scripts" / "analyze_maintainability.py"
    help_check = subprocess.run(
        [sys.executable, str(analyzer_path), "--help"],
        text=True,
        capture_output=True,
        check=False,
    )
    if help_check.returncode != 0 or "maintainability review prompts" not in help_check.stdout:
        errors.append("analyze_maintainability.py --help did not return expected help text")

    missing_check = subprocess.run(
        [sys.executable, str(analyzer_path), str(skill_root / "does-not-exist")],
        text=True,
        capture_output=True,
        check=False,
    )
    if missing_check.returncode == 0 or "not found:" not in missing_check.stderr:
        errors.append("analyze_maintainability.py did not reject a missing path")

    for option, value in (("--max-file-lines", "0"), ("--max-function-lines", "-1")):
        invalid = subprocess.run(
            [sys.executable, str(analyzer_path), str(skill_root), option, value],
            text=True,
            capture_output=True,
            check=False,
        )
        if invalid.returncode != 2 or "positive integer" not in invalid.stderr:
            errors.append(f"scanner did not reject non-positive value for {option}")

    with tempfile.TemporaryDirectory() as temp_dir:
        fixtures = Path(temp_dir)

        positive_root = fixtures / "positive"
        positive_root.mkdir()
        write_positive_fixture(positive_root)
        positive, positive_payload = run_json_scan(
            skill_root,
            positive_root,
            "--extensions",
            "PY,TS,PHP,RB",
            "--max-function-lines",
            "3",
        )
        if positive is None or positive_payload is None:
            errors.append("scanner failed or timed out on exact positive fixtures")
        else:
            if positive_payload.get("files_scanned") != 6:
                errors.append("scanner returned an incorrect positive fixture file count")
            if positive_payload.get("read_errors") != []:
                errors.append("scanner reported unexpected positive fixture read errors")
            if positive_payload.get("findings") != expected_positive_findings():
                errors.append("scanner findings did not exactly match positive regressions")

            repeated, _ = run_json_scan(
                skill_root,
                positive_root,
                "--extensions",
                "PY,TS,PHP,RB",
                "--max-function-lines",
                "3",
            )
            if repeated is None or repeated.stdout != positive.stdout:
                errors.append("scanner output was not deterministic across identical runs")

        clean_root = fixtures / "clean"
        clean_root.mkdir()
        write_clean_fixture(clean_root)
        _, clean_payload = run_json_scan(
            skill_root,
            clean_root,
            "--extensions",
            "PY,TS,TSX,PHP,RB,TF,YML",
            "--max-function-lines",
            "3",
        )
        if clean_payload is None:
            errors.append("scanner failed on clean negative fixtures")
        else:
            if clean_payload.get("files_scanned") != 9:
                errors.append("scanner traversal did not prune ignored directories or count files correctly")
            if clean_payload.get("findings") != []:
                errors.append("scanner produced false positives for clean lexical/call fixtures")

        operational_root = fixtures / "operational"
        operational_root.mkdir()
        write_comment_debt_fixture(operational_root)
        _, operational_payload = run_json_scan(skill_root, operational_root)
        operational_findings = operational_payload.get("findings") if operational_payload else None
        if operational_findings != [
            {
                "path": "artifacts.YML",
                "line": 7,
                "kind": "comment-debt",
                "message": "Dense operational/config block has no explanatory comments.",
            }
        ]:
            errors.append("scanner did not exactly identify the uncommented operational block")

        comment_scope_root = fixtures / "comment-scope"
        comment_scope_root.mkdir()
        write_comment_scope_fixtures(comment_scope_root)
        _, comment_scope_payload = run_json_scan(skill_root, comment_scope_root)
        comment_scope_findings = (
            comment_scope_payload.get("findings") if comment_scope_payload else None
        )
        if comment_scope_findings != [
            {
                "path": "Footer.PS1",
                "line": 1,
                "kind": "comment-debt",
                "message": "Dense operational/config block has no explanatory comments.",
            },
            {
                "path": "Header.PS1",
                "line": 7,
                "kind": "comment-debt",
                "message": "Dense operational/config block has no explanatory comments.",
            },
            {
                "path": "Phases.PS1",
                "line": 10,
                "kind": "comment-debt",
                "message": "Dense operational/config block has no explanatory comments.",
            },
        ]:
            errors.append("scanner let headers or one phase comment suppress unrelated comment debt")

        encoded_root = fixtures / "encoded"
        encoded_root.mkdir()
        write_utf16_fixture(encoded_root)
        _, encoded_payload = run_json_scan(skill_root, encoded_root)
        encoded_findings = encoded_payload.get("findings") if encoded_payload else None
        if encoded_findings != [
            {
                "path": "Encoded.PS1",
                "line": 1,
                "kind": "comment-debt",
                "message": "Dense operational/config block has no explanatory comments.",
            }
        ]:
            errors.append("scanner did not decode and scan a UTF-16 BOM source file")

        powershell_string_root = fixtures / "powershell-strings"
        powershell_string_root.mkdir()
        write_powershell_here_string_fixture(powershell_string_root)
        _, powershell_string_payload = run_json_scan(skill_root, powershell_string_root)
        if powershell_string_payload is None or powershell_string_payload.get("findings") != []:
            errors.append("scanner analyzed PowerShell here-string payloads as executable commands")

        nesting_root = fixtures / "nesting"
        nesting_root.mkdir()
        write_deep_nesting_fixture(nesting_root)
        _, nesting_payload = run_json_scan(skill_root, nesting_root)
        nesting_findings = nesting_payload.get("findings") if nesting_payload else None
        if nesting_findings != [
            {
                "path": "Nested.TS",
                "line": 9,
                "kind": "deep-nesting",
                "message": "Deep indentation increases cognitive load.",
            }
        ]:
            errors.append("scanner did not exactly identify real deep TypeScript control flow")

        typescript_root = fixtures / "typescript"
        typescript_root.mkdir()
        write_typescript_precision_fixtures(typescript_root)
        _, typescript_payload = run_json_scan(skill_root, typescript_root)
        typescript_findings = (
            typescript_payload.get("findings") if typescript_payload else None
        )
        expected_typescript_findings = [
            {
                "path": "Component.TSX",
                "line": 3,
                "kind": "weak-type-signal",
                "message": WEAK_MESSAGE,
            }
        ] + [
            {
                "path": "MultilineTypes.TS",
                "line": line,
                "kind": "weak-type-signal",
                "message": WEAK_MESSAGE,
            }
            for line in (2, 3, 4, 8, 11, 14)
        ] + [
            {
                "path": "Types.TS",
                "line": line,
                "kind": "weak-type-signal",
                "message": WEAK_MESSAGE,
            }
            for line in range(1, 9)
        ]
        if typescript_findings != expected_typescript_findings:
            errors.append("scanner did not distinguish TypeScript type positions from value expressions")

        lexer_root = fixtures / "javascript-lexer"
        lexer_root.mkdir()
        write_javascript_lexer_fixture(lexer_root)
        _, lexer_payload = run_json_scan(skill_root, lexer_root)
        lexer_findings = lexer_payload.get("findings") if lexer_payload else None
        if lexer_findings != [
            {
                "path": "Lexing.TS",
                "line": 1,
                "kind": "weak-type-signal",
                "message": WEAK_MESSAGE,
            },
            {
                "path": "Lexing.TS",
                "line": 2,
                "kind": "weak-type-signal",
                "message": WEAK_MESSAGE,
            },
            {
                "path": "Lexing.TS",
                "line": 3,
                "kind": "weak-type-signal",
                "message": WEAK_MESSAGE,
            },
            {
                "path": "Lexing.TS",
                "line": 4,
                "kind": "todo",
                "message": TODO_MESSAGE,
            },
            {
                "path": "Lexing.TS",
                "line": 5,
                "kind": "todo",
                "message": TODO_MESSAGE,
            },
            {
                "path": "Lexing.TS",
                "line": 6,
                "kind": "weak-type-signal",
                "message": WEAK_MESSAGE,
            },
            {
                "path": "Lexing.TS",
                "line": 7,
                "kind": "weak-type-signal",
                "message": WEAK_MESSAGE,
            },
            {
                "path": "TemplateFlow.TS",
                "line": 2,
                "kind": "deep-nesting",
                "message": "Deep indentation increases cognitive load.",
            },
            {
                "path": "TemplateFlow.TS",
                "line": 3,
                "kind": "todo",
                "message": TODO_MESSAGE,
            },
            {
                "path": "TemplateFlow.TS",
                "line": 4,
                "kind": "weak-type-signal",
                "message": WEAK_MESSAGE,
            },
        ]:
            errors.append("scanner confused regex/template contents with JavaScript-family comments or code")

        adversarial_root = fixtures / "adversarial"
        adversarial_root.mkdir()
        write_text(
            adversarial_root / "Adversarial.TS",
            "process(value); " * 50_000,
        )
        timed, timed_payload = run_json_scan(
            skill_root,
            adversarial_root,
            "--max-file-lines",
            "2",
            timeout=5,
        )
        if timed is None or timed_payload is None:
            errors.append("scanner timed out on an adversarial long line")
        elif timed_payload.get("findings") != []:
            errors.append("scanner treated repeated call sites as declarations")

        weak_line = adversarial_root / "WeakAdversarial.TS"
        write_text(weak_line, "any; " * 15_000)
        weak_timed, weak_payload = run_json_scan(
            skill_root,
            weak_line,
            timeout=5,
        )
        if weak_timed is None or weak_payload is None:
            errors.append("scanner timed out on repeated TypeScript weak-type tokens")
        elif weak_payload.get("findings") != []:
            errors.append("scanner treated TypeScript value positions as weak types")

        object_line = adversarial_root / "ObjectAdversarial.TS"
        write_text(object_line, "const x = { value: any }; " * 5_000)
        object_timed, object_payload = run_json_scan(
            skill_root,
            object_line,
            timeout=5,
        )
        if object_timed is None or object_payload is None:
            errors.append("scanner timed out on repeated TypeScript object values")
        elif object_payload.get("findings") != []:
            errors.append("scanner treated repeated TypeScript object values as type positions")

        ancestor_root = fixtures / "build" / "project"
        ancestor_root.mkdir(parents=True)
        write_text(ancestor_root / "NestedRoot.PY", "# TODO: preserve root-relative traversal\n")
        _, ancestor_payload = run_json_scan(skill_root, ancestor_root)
        ancestor_findings = ancestor_payload.get("findings") if ancestor_payload else None
        if ancestor_findings != [
            {
                "path": "NestedRoot.PY",
                "line": 1,
                "kind": "todo",
                "message": TODO_MESSAGE,
            }
        ]:
            errors.append("scanner incorrectly skipped a requested root below a build ancestor")

        analyzer = load_analyzer(analyzer_path)
        read_error_root = fixtures / "read-errors"
        read_error_root.mkdir()
        check_read_error_continuation(analyzer, read_error_root, errors)
        traversal_root = fixtures / "traversal-errors"
        traversal_root.mkdir()
        check_traversal_error_continuation(analyzer, traversal_root, errors)
        check_powershell_lexing(analyzer, errors)
        fifo_root = fixtures / "fifo"
        fifo_root.mkdir()
        check_fifo_safety(skill_root, analyzer, fifo_root, errors)


def check_evals(root: Path, errors: list[str]) -> tuple[int, set[str], int]:
    evals_path = root / "evals" / "evals.json"
    if not evals_path.is_file():
        errors.append("evals/evals.json is missing")
        return 0, set(), 0
    try:
        payload = load_json(evals_path)
    except (json.JSONDecodeError, ValueError) as exc:
        errors.append(f"evals/evals.json is invalid: {exc}")
        return 0, set(), 0

    raw_evals = payload.get("evals", [])
    if not isinstance(raw_evals, list):
        errors.append("evals field must be a list")
        return 0, set(), 0

    tags: set[str] = set()
    assertion_count = 0
    for item in raw_evals:
        if not isinstance(item, Mapping):
            errors.append(f"eval is not an object: {item}")
            continue
        for field in ["id", "name", "prompt", "expected_output", "assertions"]:
            if field not in item:
                errors.append(f"eval missing field {field}: {item}")
        raw_tags = item.get("tags", [])
        if isinstance(raw_tags, list):
            tags.update(tag for tag in raw_tags if isinstance(tag, str))
        raw_files = item.get("files", [])
        if isinstance(raw_files, list):
            for file_ref in raw_files:
                if not isinstance(file_ref, str) or not (root / file_ref).is_file():
                    errors.append(f"eval file does not exist: {file_ref}")
        raw_assertions = item.get("assertions", [])
        if not isinstance(raw_assertions, list):
            errors.append(f"eval assertions must be a list: {item}")
            continue
        for assertion in raw_assertions:
            assertion_count += 1
            if not isinstance(assertion, Mapping):
                errors.append(f"assertion is not an object: {assertion}")
                continue
            if "text" not in assertion:
                errors.append(f"assertion missing text: {assertion}")
            assertion_type = assertion.get("type")
            if assertion_type not in ASSERTION_TYPES:
                errors.append(f"unknown assertion type: {assertion_type}")

    missing_tags = REQUIRED_TAGS - tags
    if missing_tags:
        errors.append(f"missing eval tag coverage: {', '.join(sorted(missing_tags))}")
    if assertion_count == 0:
        errors.append("evals contain no assertions")
    return len(raw_evals), tags, assertion_count


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: python3 scripts/test_skill.py <skill-path>", file=sys.stderr)
        return 1

    root = Path(argv[0]).expanduser().resolve()
    errors: list[str] = []
    validate = subprocess.run(
        [sys.executable, str(root / "scripts" / "validate.py"), str(root)],
        text=True,
        capture_output=True,
        check=False,
    )
    if validate.returncode != 0:
        errors.append("validate.py failed")

    check_scanner(root, errors)
    eval_count, tags, assertion_count = check_evals(root, errors)
    if not (root / "templates" / "maintainability-review.md").is_file():
        errors.append("maintainability review template is missing")

    print(f"Skill: {root.name}")
    print(f"Validation: {'PASS' if validate.returncode == 0 else 'FAIL'}")
    print("Scanner regressions: " + ("PASS" if not errors else "FAIL"))
    print(f"Evals: {eval_count}")
    print(f"Tags: {', '.join(sorted(tags))}")
    print(f"Assertions: {assertion_count}")

    if errors:
        print("Issues:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

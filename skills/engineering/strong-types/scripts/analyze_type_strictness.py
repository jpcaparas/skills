#!/usr/bin/env python3
"""Scan a project for likely type-ambiguity review prompts.

Heuristic scanner for the strong-types skill. It surfaces places where type
ambiguity tends to hide: blind fallback chains, escape-hatch types, untyped
signatures, suppressed type errors, missing strict_types declarations, and
non-strict TypeScript configs. Findings are review prompts, not verdicts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "target", ".venv",
    "venv", "__pycache__", ".next", ".nuxt", "coverage", ".idea", ".vscode",
}
MAX_FILE_BYTES = 1_000_000

PHP_EXTS = {".php"}
TS_EXTS = {".ts", ".tsx", ".mts", ".cts"}
JS_EXTS = {".js", ".jsx", ".mjs", ".cjs"}
PY_EXTS = {".py"}
GO_EXTS = {".go"}

RE_NULL_COALESCE_CHAIN = re.compile(r"\?\?[^?\n]+\?\?")
RE_OR_CHAIN = re.compile(r"[\w)\]](?:\s*(?:\|\||\bor\b)\s*[\w$]+(?:\.|->)[\w$]+(?:\([^()]*\))?){2,}")
RE_TS_ANY = re.compile(r"(?::\s*any\b|\bas\s+any\b|<any[,>]|\bany\[\]|Array<any>)")
RE_TS_IGNORE = re.compile(r"@ts-ignore")
RE_PY_ANY = re.compile(r"(?::\s*Any\b|->\s*Any\b|\[Any[\],])")
RE_PY_BARE_IGNORE = re.compile(r"#\s*type:\s*ignore(?!\[)")
RE_PHP_MIXED = re.compile(r"(?::\s*mixed\b|\bmixed\s+\$)")
RE_PHP_STRICT = re.compile(r"declare\s*\(\s*strict_types\s*=\s*1\s*\)")
RE_PHP_FUNCTION = re.compile(r"\bfunction\s+\w+\s*\(")
RE_PHP_SIGNATURE = re.compile(r"\bfunction\s+(\w+)\s*\(([^)]*)\)\s*(:?)")
RE_PHP_UNTYPED_PARAM = re.compile(r"^\s*&?(?:\.\.\.)?\$\w+")
RE_PY_DEF = re.compile(r"^\s*def\s+\w+\s*\(.*\)\s*:")
RE_PY_ARROW = re.compile(r"->")
RE_GO_EMPTY_IFACE = re.compile(r"\binterface\{\}|\bmap\[string\]interface\{\}|\bmap\[string\]any\b")


@dataclass
class Finding:
    kind: str
    path: str
    line: int
    excerpt: str
    hint: str


def iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in PHP_EXTS | TS_EXTS | JS_EXTS | PY_EXTS | GO_EXTS or path.name == "tsconfig.json":
            try:
                if path.stat().st_size <= MAX_FILE_BYTES:
                    files.append(path)
            except OSError:
                continue
    return files


def scan_lines(path: Path, rel: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    suffix = path.suffix
    lines = text.splitlines()

    for number, line in enumerate(lines, start=1):
        stripped = line.strip()

        def add(kind: str, hint: str) -> None:
            findings.append(Finding(kind=kind, path=rel, line=number, excerpt=stripped[:160], hint=hint))

        if RE_NULL_COALESCE_CHAIN.search(line):
            add(
                "fallback-chain",
                "Chained ?? fallbacks re-derive a nullability policy at the call site; extract one typed owner method with an explicit all-null policy.",
            )
        elif suffix in TS_EXTS | JS_EXTS | PY_EXTS and RE_OR_CHAIN.search(line):
            add(
                "fallback-chain",
                "Chained ||/or fallbacks on properties also swallow 0, empty string, and false; extract one typed owner and use null-safe coalescing.",
            )

        if suffix in TS_EXTS and RE_TS_ANY.search(line):
            add(
                "escape-hatch-type",
                "`any` disables checking and infects downstream expressions; use a concrete type, a generic, or `unknown` plus a parse.",
            )
        if suffix in PHP_EXTS and RE_PHP_MIXED.search(line):
            add(
                "escape-hatch-type",
                "`mixed` is an escape hatch; replace with a concrete type, union, or generic annotation, or justify it inline.",
            )
        if suffix in PY_EXTS and RE_PY_ANY.search(line):
            add(
                "escape-hatch-type",
                "`Any` disables checking bidirectionally; prefer a concrete type, a Protocol, or `object` plus narrowing.",
            )
        if suffix in GO_EXTS and RE_GO_EMPTY_IFACE.search(line):
            add(
                "escape-hatch-type",
                "`interface{}`/`any` erases type knowledge; decode into a named struct or use a type parameter.",
            )

        if suffix in TS_EXTS | JS_EXTS and RE_TS_IGNORE.search(line):
            add(
                "suppressed-type-error",
                "`@ts-ignore` suppresses whatever error appears next, forever; fix the type or use `@ts-expect-error` with a reason.",
            )
        if suffix in PY_EXTS and RE_PY_BARE_IGNORE.search(line):
            add(
                "suppressed-type-error",
                "Bare `# type: ignore` hides every error on the line; name the error code and the reason, or fix the type.",
            )

        if suffix in PHP_EXTS:
            signature = RE_PHP_SIGNATURE.search(line)
            if signature:
                name, params, return_colon = signature.groups()
                untyped_params = [
                    param for param in params.split(",")
                    if param.strip() and RE_PHP_UNTYPED_PARAM.match(param)
                ]
                if untyped_params:
                    add(
                        "untyped-signature",
                        "Untyped PHP parameter; add a parameter type (or a documented union) so callers stop guessing.",
                    )
                elif not return_colon and name not in {"__construct", "__destruct", "__clone"}:
                    add(
                        "untyped-signature",
                        "Missing PHP return type; declare it (`: void` counts) so the contract lives in the signature.",
                    )
        if suffix in PY_EXTS and RE_PY_DEF.search(line) and not RE_PY_ARROW.search(line):
            add(
                "untyped-signature",
                "Python def without a return annotation; add `-> None` or the real type so the checker can verify callers.",
            )

    if suffix in PHP_EXTS and RE_PHP_FUNCTION.search(text) and not RE_PHP_STRICT.search(text):
        findings.append(
            Finding(
                kind="php-missing-strict-types",
                path=rel,
                line=1,
                excerpt=lines[0][:160] if lines else "",
                hint="No declare(strict_types=1); PHP will silently coerce argument types for calls made from this file.",
            )
        )

    return findings


def scan_tsconfig(path: Path, rel: str, text: str) -> list[Finding]:
    no_comments = re.sub(r"//[^\n]*|/\*[\s\S]*?\*/", "", text)
    if re.search(r'"strict"\s*:\s*true', no_comments):
        return []
    if re.search(r'"strict"\s*:\s*false', no_comments):
        hint = '"strict" is explicitly false; every other typing rule is unenforceable until it is true.'
    else:
        hint = 'No "strict": true found; enable it (plus noUncheckedIndexedAccess) as the checking baseline.'
    return [Finding(kind="ts-nonstrict-config", path=rel, line=1, excerpt='"compilerOptions"', hint=hint)]


def scan_project(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_source_files(root):
        rel = str(path.relative_to(root))
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if path.name == "tsconfig.json":
            findings.extend(scan_tsconfig(path, rel, text))
        else:
            findings.extend(scan_lines(path, rel, text))
    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scan a project for type ambiguity review prompts: fallback chains, "
            "escape-hatch types, untyped signatures, suppressed type errors, "
            "missing strict_types, and non-strict TypeScript configs."
        )
    )
    parser.add_argument("path", help="Project directory (or single file) to scan")
    parser.add_argument("--json", action="store_true", help="Emit findings as JSON")
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        print(f"path does not exist: {root}", file=sys.stderr)
        return 2

    if root.is_file():
        findings = scan_lines(root, root.name, root.read_text(encoding="utf-8", errors="replace"))
    else:
        findings = scan_project(root)

    if args.json:
        print(json.dumps({"root": str(root), "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        if not findings:
            print("No type-ambiguity review prompts found. (Not proof of strong typing.)")
        for finding in findings:
            print(f"[{finding.kind}] {finding.path}:{finding.line}")
            print(f"  {finding.excerpt}")
            print(f"  -> {finding.hint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

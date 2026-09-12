#!/usr/bin/env python3
"""Run focused renderer behavior and package-validator regressions."""

from __future__ import annotations

import base64
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import render_diagram
import validate


ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
Mutation = Callable[[Path], None]


@dataclass(frozen=True, slots=True)
class CheckResult:
    passed: bool
    message: str


@dataclass(frozen=True, slots=True)
class RegressionCase:
    name: str
    mutate: Mutation
    expected_error: str


class FakeRenderer:
    """Record Mermaid CLI arguments and create a deterministic tiny PNG."""

    def __init__(self, *, returncode: int = 0, diagnostic: str = "") -> None:
        self.returncode = returncode
        self.diagnostic = diagnostic
        self.commands: list[tuple[str, ...]] = []
        self.sources: list[str] = []

    def __call__(
        self,
        command: Sequence[str],
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str]:
        del timeout_seconds
        recorded = tuple(command)
        self.commands.append(recorded)
        source_path = Path(recorded[recorded.index("--input") + 1])
        output_path = Path(recorded[recorded.index("--output") + 1])
        self.sources.append(source_path.read_text(encoding="utf-8"))
        if self.returncode == 0:
            output_path.write_bytes(ONE_PIXEL_PNG)
        return subprocess.CompletedProcess(
            list(recorded),
            self.returncode,
            stdout="",
            stderr=self.diagnostic,
        )


def expect_render_error(action: Callable[[], object], fragment: str) -> CheckResult:
    try:
        action()
    except render_diagram.DiagramRenderError as exc:
        if fragment in str(exc):
            return CheckResult(True, f"expected error observed: {fragment}")
        return CheckResult(False, f"wrong error for {fragment!r}: {exc}")
    return CheckResult(False, f"expected error was not raised: {fragment}")


def check_successful_two_file_render() -> CheckResult:
    with tempfile.TemporaryDirectory(prefix="to-diagram-render-test-") as temporary:
        root = Path(temporary)
        markdown_path = root / "order-flow.md"
        png_path = root / "order-flow.png"
        markdown_path.write_text(
            "# Order flow\n\n```mermaid\nflowchart TD\n  A --> B\n```\n",
            encoding="utf-8",
        )
        fake = FakeRenderer()
        info = render_diagram.render_markdown(
            markdown_path,
            png_path,
            render_diagram.Renderer(("fake-mmdc",), "fake-mmdc"),
            runner=fake,
        )

        names = sorted(path.name for path in root.iterdir())
        command = fake.commands[0] if fake.commands else ()
        conditions = (
            info == render_diagram.PngInfo(width=1, height=1),
            names == ["order-flow.md", "order-flow.png"],
            png_path.read_bytes() == ONE_PIXEL_PNG,
            fake.sources == ["flowchart TD\n  A --> B\n"],
            "--theme" in command and command[command.index("--theme") + 1] == "neutral",
            "--backgroundColor" in command
            and command[command.index("--backgroundColor") + 1] == "white",
            "--scale" in command and command[command.index("--scale") + 1] == "2",
        )
        if all(conditions):
            return CheckResult(True, "render creates only matching Markdown and PNG files")
        return CheckResult(False, f"unexpected render state: files={names}, command={command}")


def check_rejects_multiple_blocks() -> CheckResult:
    markdown = (
        "```mermaid\nflowchart TD\n  A --> B\n```\n\n"
        "```mermaid\nflowchart TD\n  C --> D\n```\n"
    )
    return expect_render_error(
        lambda: render_diagram.extract_mermaid_source(markdown),
        "found 2",
    )


def check_preserves_existing_png() -> CheckResult:
    with tempfile.TemporaryDirectory(prefix="to-diagram-overwrite-test-") as temporary:
        root = Path(temporary)
        markdown_path = root / "diagram.md"
        png_path = root / "diagram.png"
        markdown_path.write_text(
            "```mermaid\nflowchart TD\n  A --> B\n```\n",
            encoding="utf-8",
        )
        original = b"existing-user-file"
        png_path.write_bytes(original)
        result = expect_render_error(
            lambda: render_diagram.render_markdown(
                markdown_path,
                png_path,
                render_diagram.Renderer(("fake-mmdc",), "fake-mmdc"),
                runner=FakeRenderer(),
            ),
            "already exists",
        )
        if result.passed and png_path.read_bytes() == original:
            return CheckResult(True, "existing PNG remains byte-for-byte unchanged")
        return CheckResult(False, "existing PNG changed or overwrite did not fail")


def check_renderer_failure_leaves_no_png() -> CheckResult:
    with tempfile.TemporaryDirectory(prefix="to-diagram-failure-test-") as temporary:
        root = Path(temporary)
        markdown_path = root / "diagram.md"
        png_path = root / "diagram.png"
        markdown_path.write_text(
            "```mermaid\nflowchart TD\n  A --> B\n```\n",
            encoding="utf-8",
        )
        result = expect_render_error(
            lambda: render_diagram.render_markdown(
                markdown_path,
                png_path,
                render_diagram.Renderer(("fake-mmdc",), "fake-mmdc"),
                runner=FakeRenderer(returncode=1, diagnostic="Parse error on line 2"),
            ),
            "Parse error on line 2",
        )
        if result.passed and not png_path.exists():
            return CheckResult(True, "renderer failure leaves no partial PNG")
        return CheckResult(False, "renderer failure left an output or wrong diagnostic")


def check_renderer_selection() -> CheckResult:
    paths = {
        "mmdc": "/tools/mmdc",
        "npx": "/tools/npx",
    }

    def both_available(command: str) -> str | None:
        return paths.get(command)

    direct = render_diagram.select_renderer(None, both_available)

    def only_npx(command: str) -> str | None:
        return "/tools/npx" if command == "npx" else None

    fallback = render_diagram.select_renderer(None, only_npx)
    if direct.argv_prefix == ("/tools/mmdc",) and fallback.argv_prefix == (
        "/tools/npx",
        "--yes",
        render_diagram.MERMAID_PACKAGE,
    ):
        return CheckResult(True, "renderer selection prefers mmdc and falls back to npx")
    return CheckResult(False, "renderer selection order or package range drifted")


def replace_text(path: Path, old: str, new: str, count: int = -1) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"test fixture text not found in {path}: {old}")
    path.write_text(text.replace(old, new, count), encoding="utf-8")


def remove_two_file_contract(root: Path) -> None:
    replace_text(
        root / "SKILL.md",
        "exactly two durable deliverables",
        "a pair of deliverables",
    )


def remove_scientific_boundary(root: Path) -> None:
    replace_text(
        root / "SKILL.md",
        "do not turn correlation into causation",
        "draw the relationship clearly",
        count=1,
    )


def erase_negative_triggers(root: Path) -> None:
    replace_text(
        root / "evals" / "trigger-evals.json",
        '"should_trigger": false',
        '"should_trigger": true',
    )


def corrupt_assertion_type(root: Path) -> None:
    replace_text(
        root / "evals" / "evals.json",
        '"type": "functional"',
        '"type": "subjective"',
        count=1,
    )


REGRESSION_CASES = (
    RegressionCase(
        name="requires the two-file output contract",
        mutate=remove_two_file_contract,
        expected_error="two-file output contract",
    ),
    RegressionCase(
        name="requires the scientific evidence boundary",
        mutate=remove_scientific_boundary,
        expected_error="scientific evidence boundary",
    ),
    RegressionCase(
        name="requires positive and negative trigger coverage",
        mutate=erase_negative_triggers,
        expected_error="at least five positive and five negative",
    ),
    RegressionCase(
        name="rejects unknown assertion types",
        mutate=corrupt_assertion_type,
        expected_error="invalid assertion type",
    ),
)


def run_validator_regression(source: Path, case: RegressionCase) -> CheckResult:
    with tempfile.TemporaryDirectory(prefix="to-diagram-validator-test-") as temporary:
        candidate = Path(temporary) / source.name
        shutil.copytree(source, candidate)
        case.mutate(candidate)
        result = validate.validate_skill(candidate)
        if result.valid:
            return CheckResult(False, f"{case.name}: mutated package unexpectedly passed")
        if not any(case.expected_error in error for error in result.errors):
            return CheckResult(False, f"{case.name}: expected diagnostic not found")
        return CheckResult(True, f"{case.name}: expected diagnostic observed")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: test_skill.py <skill-path>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    package = validate.validate_skill(root)
    checks = [
        CheckResult(
            package.valid,
            "release package validates"
            if package.valid
            else "release package failed: " + "; ".join(package.errors),
        ),
        check_successful_two_file_render(),
        check_rejects_multiple_blocks(),
        check_preserves_existing_png(),
        check_renderer_failure_leaves_no_png(),
        check_renderer_selection(),
    ]
    checks.extend(run_validator_regression(root, case) for case in REGRESSION_CASES)

    for check in checks:
        print(f"{'PASS' if check.passed else 'FAIL'}: {check.message}")
    passed_count = sum(check.passed for check in checks)
    print(f"\n{passed_count}/{len(checks)} focused checks passed")
    return 0 if passed_count == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())

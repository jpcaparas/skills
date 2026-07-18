#!/usr/bin/env python3
"""Ensure local and CI validation entrypoints share one canonical command."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Final, TypeAlias

import yaml

from yaml_validation import load_unique_yaml


JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
YamlObject: TypeAlias = dict[object, object]
TextReader: TypeAlias = Callable[[str], str]


REPO_ROOT: Final = Path(__file__).resolve().parents[1]
CANONICAL_SCRIPT: Final = "scripts/validate-all-skills.sh"
CANONICAL_COMMAND: Final = f"bash {CANONICAL_SCRIPT}"
ACT_MATRIX_COMMAND: Final = "bash scripts/validate-ci-with-act.sh --matrix"
ACT_UBUNTU_COMMAND: Final = "bash scripts/validate-ci-with-act.sh --ubuntu"
ACT_MACOS_COMMAND: Final = "bash scripts/validate-ci-with-act.sh --macos"
ACT_PACKAGE_COMMANDS: Final[dict[str, str]] = {
    "validate:act": ACT_MATRIX_COMMAND,
    "validate:act:ubuntu": ACT_UBUNTU_COMMAND,
    "validate:act:macos": ACT_MACOS_COMMAND,
}
MATRIX_RUNNER: Final = "${{ matrix.os }}"
MATRIX_OPERATING_SYSTEMS: Final = ("ubuntu-24.04", "macos-15")
HOSTED_PYTHON_VERSION: Final = "3.11"
HOSTED_NODE_VERSION: Final = "24"
HOSTED_BUN_VERSION: Final = "1.3.11"
HOSTED_SETUP_PYTHON_STEP: Final = "Set Up Python"
HOSTED_SETUP_NODE_STEP: Final = "Set Up Node"
HOSTED_SETUP_BUN_STEP: Final = "Set Up Bun"
LOCAL_MACOS_TOOLCHAIN_STEP: Final = "Prepare Local macOS Toolchain (act)"
HOSTED_TOOLCHAIN_CONDITION: Final = "${{ !env.ACT || runner.os == 'Linux' }}"
LOCAL_MACOS_TOOLCHAIN_CONDITION: Final = "${{ env.ACT && runner.os == 'macOS' }}"
CANONICAL_PRE_PUSH_COMMAND: Final = (
    'exec "$(dirname -- "$0")/../scripts/run-pnpm.sh" run validate'
)
STOP_CHECK_SCRIPT: Final = "scripts/agent-stop-checks.sh"
STOP_CHECK_INVOCATIONS: Final = frozenset(
    {
        f'bash "$REPO_ROOT/{CANONICAL_SCRIPT}"',
        f'bash "$REPO_ROOT/{CANONICAL_SCRIPT}" >&2',
    }
)
SHELL_FUNCTION_START: Final = re.compile(
    r"^(?:function\s+)?[A-Za-z_][A-Za-z0-9_]*(?:\(\))?\s*\{\s*$"
)


def read_text(relative_path: str) -> str:
    """Read one repository file using a stable UTF-8 boundary."""
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def unique_json_object(pairs: list[tuple[str, JsonValue]]) -> JsonObject:
    """Build one JSON object while rejecting ambiguous duplicate members."""

    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def reject_json_constant(value: str) -> None:
    """Reject JavaScript numeric extensions that are not valid JSON."""

    raise ValueError(f"non-standard JSON constant: {value}")


def load_json_object(
    relative_path: str,
    errors: list[str],
    *,
    reader: TextReader = read_text,
) -> JsonObject | None:
    """Parse a repository JSON object at the untyped file boundary."""
    try:
        parsed: JsonValue = json.loads(
            reader(relative_path),
            object_pairs_hook=unique_json_object,
            parse_constant=reject_json_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        errors.append(f"{relative_path} contains invalid JSON: {exc}")
        return None

    if not isinstance(parsed, dict):
        errors.append(f"{relative_path} must contain a JSON object")
        return None
    return parsed


def load_yaml_object(
    relative_path: str,
    errors: list[str],
    *,
    reader: TextReader = read_text,
) -> YamlObject | None:
    """Parse one YAML mapping while keeping untrusted values typed as object."""
    try:
        parsed: object = load_unique_yaml(reader(relative_path))
    except yaml.YAMLError as exc:
        errors.append(f"{relative_path} contains invalid YAML: {exc}")
        return None

    if not isinstance(parsed, dict):
        errors.append(f"{relative_path} must contain a YAML mapping")
        return None
    return parsed


def strip_shell_comment(line: str) -> str:
    """Remove a shell comment without treating quoted hashes as comments."""
    quote: str | None = None
    escaped = False
    result: list[str] = []

    for character in line:
        if escaped:
            result.append(character)
            escaped = False
            continue
        if character == "\\" and quote != "'":
            result.append(character)
            escaped = True
            continue
        if character in {"'", '"'}:
            if quote == character:
                quote = None
            elif quote is None:
                quote = character
            result.append(character)
            continue
        if character == "#" and quote is None:
            break
        result.append(character)
    return "".join(result)


def heredoc_delimiter(line: str) -> tuple[str, bool] | None:
    """Return a literal here-document delimiter declared on one shell line."""
    operator_index = line.find("<<")
    if operator_index < 0:
        return None

    remainder = line[operator_index + 2 :]
    strip_tabs = remainder.startswith("-")
    if strip_tabs:
        remainder = remainder[1:]
    delimiter = remainder.strip().split(maxsplit=1)
    if not delimiter:
        return None
    value = delimiter[0]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    if not value or any(character in value for character in ";|&<>()"):
        return None
    return value, strip_tabs


def is_definitely_false_condition(line: str) -> bool:
    """Recognize the literal false shell condition used in bypass attempts."""
    stripped = line.strip()
    return stripped == "if false" or stripped.startswith("if false;")


def active_shell_lines(source: str) -> list[str]:
    """Return active shell lines, excluding comments, heredocs, and false blocks.

    This intentionally small parser is not a Bash interpreter. It preserves
    unknown conditions as potentially active, but proves that literal `if
    false` branches and here-document bodies cannot satisfy a safety check.
    """
    active_lines: list[str] = []
    condition_stack: list[tuple[bool, bool, bool]] = []
    heredoc: tuple[str, bool] | None = None
    in_function = False

    for raw_line in source.splitlines():
        if heredoc is not None:
            delimiter, strip_tabs = heredoc
            candidate = raw_line.lstrip("\t") if strip_tabs else raw_line
            if candidate == delimiter:
                heredoc = None
            continue

        line = strip_shell_comment(raw_line).strip()
        if not line:
            continue

        if in_function:
            if line == "}":
                in_function = False
            continue
        if SHELL_FUNCTION_START.fullmatch(line):
            in_function = True
            continue

        parent_active = all(
            parent and (condition if not in_else else not condition)
            for parent, condition, in_else in condition_stack
        )
        if is_definitely_false_condition(line):
            condition_stack.append((parent_active, False, False))
            continue
        if line in {"then", "; then"}:
            continue
        if line == "else":
            if condition_stack:
                parent, condition, _ = condition_stack.pop()
                condition_stack.append((parent, condition, True))
            continue
        if line == "fi":
            if condition_stack:
                condition_stack.pop()
            continue

        if parent_active:
            active_lines.append(line)
        heredoc = heredoc_delimiter(line)

    return active_lines


def validate_package_script(
    errors: list[str],
    *,
    reader: TextReader = read_text,
) -> None:
    """Require the package-level validation alias to call the canonical script."""
    package = load_json_object("package.json", errors, reader=reader)
    if package is None:
        return

    scripts = package.get("scripts")
    if not isinstance(scripts, dict):
        errors.append("package.json must contain a scripts object")
        return

    if scripts.get("validate") != CANONICAL_COMMAND:
        errors.append(
            f"package.json scripts.validate must equal {CANONICAL_COMMAND!r}"
        )
    for script_name, expected_command in ACT_PACKAGE_COMMANDS.items():
        if scripts.get(script_name) != expected_command:
            errors.append(
                f"package.json scripts.{script_name} must equal "
                f"{expected_command!r}"
            )


def validate_workflow(
    errors: list[str],
    *,
    reader: TextReader = read_text,
) -> None:
    """Require the active validation workflow step to invoke the canonical script."""
    workflow = load_yaml_object(
        ".github/workflows/validate-skills.yml",
        errors,
        reader=reader,
    )
    if workflow is None:
        return

    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        errors.append("GitHub Actions workflow must contain a jobs mapping")
        return

    validate_job = jobs.get("validate")
    if not isinstance(validate_job, dict):
        errors.append("GitHub Actions workflow must contain the 'validate' job")
        return
    if "if" in validate_job:
        errors.append("GitHub Actions 'validate' job must not be conditional")
    if validate_job.get("continue-on-error") not in (None, False):
        errors.append("GitHub Actions 'validate' job must block on validation failure")

    if validate_job.get("runs-on") != MATRIX_RUNNER:
        errors.append(
            "GitHub Actions 'validate' job must use "
            f"runs-on: {MATRIX_RUNNER!r}"
        )

    strategy = validate_job.get("strategy")
    if not isinstance(strategy, dict):
        errors.append("GitHub Actions 'validate' job must contain a strategy mapping")
    else:
        if strategy.get("fail-fast") is not False:
            errors.append(
                "GitHub Actions 'validate' matrix must set fail-fast to false"
            )

        matrix = strategy.get("matrix")
        if not isinstance(matrix, dict):
            errors.append(
                "GitHub Actions 'validate' strategy must contain a matrix mapping"
            )
        elif set(matrix) != {"os"}:
            errors.append(
                "GitHub Actions 'validate' matrix must contain only the 'os' axis"
            )
        elif matrix.get("os") != list(MATRIX_OPERATING_SYSTEMS):
            expected = ", ".join(MATRIX_OPERATING_SYSTEMS)
            errors.append(
                "GitHub Actions 'validate' matrix.os must contain exactly, in "
                f"order: {expected}"
            )

    steps = validate_job.get("steps")
    if not isinstance(steps, list):
        errors.append("GitHub Actions 'validate' job must contain a steps list")
        return

    hosted_python_steps = [
        step
        for step in steps
        if isinstance(step, dict) and step.get("name") == HOSTED_SETUP_PYTHON_STEP
    ]
    if len(hosted_python_steps) != 1:
        errors.append(
            "GitHub Actions 'validate' job must contain exactly one "
            f"{HOSTED_SETUP_PYTHON_STEP!r} step"
        )
    else:
        hosted_python_step = hosted_python_steps[0]
        if hosted_python_step.get("uses") != "actions/setup-python@v6":
            errors.append(
                f"GitHub Actions {HOSTED_SETUP_PYTHON_STEP!r} step must use "
                "'actions/setup-python@v6'"
            )
        hosted_python_options = hosted_python_step.get("with")
        if not isinstance(hosted_python_options, dict) or (
            hosted_python_options.get("python-version") != HOSTED_PYTHON_VERSION
        ):
            errors.append(
                f"GitHub Actions {HOSTED_SETUP_PYTHON_STEP!r} step must pin "
                f"python-version to {HOSTED_PYTHON_VERSION!r}"
            )
        if hosted_python_step.get("if") != HOSTED_TOOLCHAIN_CONDITION:
            errors.append(
                f"GitHub Actions {HOSTED_SETUP_PYTHON_STEP!r} step must use "
                f"condition {HOSTED_TOOLCHAIN_CONDITION!r}"
            )

    hosted_runtime_contracts = (
        (
            HOSTED_SETUP_NODE_STEP,
            "actions/setup-node@v6",
            "node-version",
            HOSTED_NODE_VERSION,
        ),
        (
            HOSTED_SETUP_BUN_STEP,
            "oven-sh/setup-bun@v2",
            "bun-version",
            HOSTED_BUN_VERSION,
        ),
    )
    for step_name, action, option_name, pinned_version in hosted_runtime_contracts:
        matching_steps = [
            step
            for step in steps
            if isinstance(step, dict) and step.get("name") == step_name
        ]
        if len(matching_steps) != 1:
            errors.append(
                "GitHub Actions 'validate' job must contain exactly one "
                f"{step_name!r} step"
            )
            continue
        runtime_step = matching_steps[0]
        if runtime_step.get("uses") != action:
            errors.append(
                f"GitHub Actions {step_name!r} step must use {action!r}"
            )
        runtime_options = runtime_step.get("with")
        if not isinstance(runtime_options, dict) or (
            runtime_options.get(option_name) != pinned_version
        ):
            errors.append(
                f"GitHub Actions {step_name!r} step must pin {option_name} "
                f"to {pinned_version!r}"
            )
        if runtime_step.get("if") != HOSTED_TOOLCHAIN_CONDITION:
            errors.append(
                f"GitHub Actions {step_name!r} step must use condition "
                f"{HOSTED_TOOLCHAIN_CONDITION!r}"
            )

    local_macos_steps = [
        step
        for step in steps
        if isinstance(step, dict) and step.get("name") == LOCAL_MACOS_TOOLCHAIN_STEP
    ]
    if len(local_macos_steps) != 1:
        errors.append(
            "GitHub Actions 'validate' job must contain exactly one "
            f"{LOCAL_MACOS_TOOLCHAIN_STEP!r} step"
        )
    else:
        local_macos_step = local_macos_steps[0]
        if local_macos_step.get("if") != LOCAL_MACOS_TOOLCHAIN_CONDITION:
            errors.append(
                f"GitHub Actions {LOCAL_MACOS_TOOLCHAIN_STEP!r} step must use "
                f"condition {LOCAL_MACOS_TOOLCHAIN_CONDITION!r}"
            )
        if local_macos_step.get("shell") != "bash":
            errors.append(
                f"GitHub Actions {LOCAL_MACOS_TOOLCHAIN_STEP!r} step must use bash"
            )
        local_macos_run = local_macos_step.get("run")
        if not isinstance(local_macos_run, str):
            errors.append(
                f"GitHub Actions {LOCAL_MACOS_TOOLCHAIN_STEP!r} step must run "
                "the selected host Python bootstrap"
            )
        else:
            active_macos_lines = active_shell_lines(local_macos_run)

            # Match complete shell statements rather than searching their text.
            # A quoted echo or printf can contain every required fragment while
            # selecting or invoking none of the host toolchain commands.
            required_lines: tuple[tuple[str, re.Pattern[str]], ...] = (
                (
                    'validation_python="${SKILLS_ACT_MACOS_PYTHON:-}"',
                    re.compile(
                        r'validation_python="\$\{SKILLS_ACT_MACOS_PYTHON:-\}"'
                    ),
                ),
                (
                    'validation_node="${SKILLS_ACT_MACOS_NODE:-}"',
                    re.compile(
                        r'validation_node="\$\{SKILLS_ACT_MACOS_NODE:-\}"'
                    ),
                ),
                (
                    'validation_npm="${SKILLS_ACT_MACOS_NPM:-}"',
                    re.compile(
                        r'validation_npm="\$\{SKILLS_ACT_MACOS_NPM:-\}"'
                    ),
                ),
                (
                    'validation_npx="${SKILLS_ACT_MACOS_NPX:-}"',
                    re.compile(
                        r'validation_npx="\$\{SKILLS_ACT_MACOS_NPX:-\}"'
                    ),
                ),
                (
                    'validation_bun="${SKILLS_ACT_MACOS_BUN:-}"',
                    re.compile(
                        r'validation_bun="\$\{SKILLS_ACT_MACOS_BUN:-\}"'
                    ),
                ),
                (
                    "sys.version_info >= (3, 11)",
                    re.compile(
                        r'(?:\|\|\s+)?(?:!\s+)?'
                        r'"\$validation_python"\s+-c\s+'
                        r"'[^'\n]*sys\.version_info\s*>=\s*\(3,\s*11\)"
                        r"[^'\n]*'(?:\s*;\s*then)?"
                    ),
                ),
                (
                    '"$validation_node" --version',
                    re.compile(
                        r'(?:"\$validation_node"\s+--version'
                        r'|(?:\|\|\s+)?\[\s+-z\s+'
                        r'"\$\("\$validation_node"\s+--version\)"\s+\]'
                        r'\s*;\s*then)'
                    ),
                ),
                (
                    '"$validation_bun" --version',
                    re.compile(
                        r'(?:\|\|\s+)?(?:!\s+)?'
                        r'"\$validation_bun"\s+--version'
                        r'(?:\s*;\s*then)?'
                    ),
                ),
                (
                    '"$validation_python" -m venv',
                    re.compile(
                        r'"\$validation_python"\s+-m\s+venv'
                        r'(?:\s+[^;&|]+)?'
                    ),
                ),
                (
                    'ln -s "$validation_node"',
                    re.compile(
                        r'ln\s+-s\s+"\$validation_node"\s+"[^"\n]*/node"'
                    ),
                ),
                (
                    'ln -s "$validation_npm"',
                    re.compile(
                        r'ln\s+-s\s+"\$validation_npm"\s+"[^"\n]*/npm"'
                    ),
                ),
                (
                    'ln -s "$validation_npx"',
                    re.compile(
                        r'ln\s+-s\s+"\$validation_npx"\s+"[^"\n]*/npx"'
                    ),
                ),
                (
                    'ln -s "$validation_bun"',
                    re.compile(
                        r'ln\s+-s\s+"\$validation_bun"\s+"[^"\n]*/bun"'
                    ),
                ),
            )
            for expected_line, pattern in required_lines:
                if not any(
                    pattern.fullmatch(line) for line in active_macos_lines
                ):
                    errors.append(
                        f"GitHub Actions {LOCAL_MACOS_TOOLCHAIN_STEP!r} step must "
                        f"contain {expected_line!r}"
                    )
            bare_python_venv = re.compile(
                r'(?:(?:if|elif|\|\||&&)\s+)?(?:!\s+)?'
                r'python3\s+-m\s+venv\b.*'
            )
            if any(
                bare_python_venv.fullmatch(line) for line in active_macos_lines
            ):
                errors.append(
                    f"GitHub Actions {LOCAL_MACOS_TOOLCHAIN_STEP!r} step must not "
                    "bootstrap from bare python3"
                )

    validation_steps = [
        step
        for step in steps
        if isinstance(step, dict) and step.get("name") == "Validate Skills"
    ]
    if len(validation_steps) != 1:
        errors.append(
            "GitHub Actions 'validate' job must contain exactly one "
            "'Validate Skills' step"
        )
        return

    validation_step = validation_steps[0]
    if validation_step.get("run") != CANONICAL_COMMAND:
        errors.append(
            "GitHub Actions 'Validate Skills' step must run "
            f"{CANONICAL_COMMAND!r} directly"
        )
    if "if" in validation_step:
        errors.append("GitHub Actions 'Validate Skills' step must not be conditional")
    if validation_step.get("continue-on-error") not in (None, False):
        errors.append(
            "GitHub Actions 'Validate Skills' step must block on validation failure"
        )


def validate_pre_push(
    errors: list[str],
    *,
    reader: TextReader = read_text,
) -> None:
    """Require pre-push to run the full package validator, not a subset."""
    active_lines = active_shell_lines(reader(".husky/pre-push"))
    if active_lines != [CANONICAL_PRE_PUSH_COMMAND]:
        errors.append(
            ".husky/pre-push must execute only the canonical package validation "
            f"command {CANONICAL_PRE_PUSH_COMMAND!r}"
        )


def validate_stop_pipeline(
    errors: list[str],
    *,
    reader: TextReader = read_text,
) -> None:
    """Require every agent stop adapter to route through shared stop checks."""
    active_lines = set(active_shell_lines(reader(STOP_CHECK_SCRIPT)))
    missing_invocations = sorted(STOP_CHECK_INVOCATIONS - active_lines)
    if missing_invocations:
        errors.append(
            f"{STOP_CHECK_SCRIPT} must actively invoke the canonical validator "
            "for interactive and non-interactive output; missing: "
            + ", ".join(repr(command) for command in missing_invocations)
        )

    for harness in ("claude", "codex", "devin"):
        config_path = f"hooks/stop/{harness}.json"
        config = load_json_object(config_path, errors, reader=reader)
        if config is None:
            continue

        scripts = config.get("scripts")
        if not isinstance(scripts, list):
            errors.append(f"{config_path} must contain a scripts list")
            continue

        paths = {
            item.get("path")
            for item in scripts
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
        if STOP_CHECK_SCRIPT not in paths:
            errors.append(f"{config_path} must invoke {STOP_CHECK_SCRIPT}")


def main() -> int:
    """Report every parity violation in one actionable failure."""
    errors: list[str] = []
    validate_package_script(errors)
    validate_workflow(errors)
    validate_pre_push(errors)
    validate_stop_pipeline(errors)

    if errors:
        print("Validation entrypoint parity check failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        "Validation entrypoints are aligned: the GitHub Actions OS matrix, "
        "local act preflight, Husky pre-push, and agent stop hooks use the "
        "canonical validator."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

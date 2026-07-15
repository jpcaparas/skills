#!/usr/bin/env python3
"""Inspect a chezmoi binary and optionally exercise it in isolated temporary state."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


REQUIRED_COMMANDS = (
    "add",
    "apply",
    "data",
    "diff",
    "doctor",
    "edit",
    "execute-template",
    "init",
    "merge",
    "re-add",
    "source-path",
    "status",
    "target-path",
    "update",
    "verify",
)
REQUIRED_GLOBAL_FLAGS = (
    "--cache",
    "--config",
    "--destination",
    "--dry-run",
    "--no-pager",
    "--no-tty",
    "--persistent-state",
    "--refresh-externals",
    "--source",
    "--verbose",
)


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class ProbeError(RuntimeError):
    """Raised when the selected binary violates the exercised contract."""


def run_command(
    command: Sequence[str],
    *,
    input_text: str | None = None,
    timeout_seconds: float = 30.0,
) -> CommandResult:
    completed = subprocess.run(
        list(command),
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    return CommandResult(
        command=tuple(command),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def require_success(result: CommandResult, label: str) -> None:
    if result.returncode != 0:
        raise ProbeError(
            f"{label} failed with exit {result.returncode}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def resolve_binary(candidate: str) -> str:
    resolved = shutil.which(candidate)
    if resolved is None:
        raise ProbeError(f"chezmoi binary not found: {candidate}")
    return resolved


def inspect_contract(binary: str) -> dict[str, object]:
    version = run_command((binary, "--version"))
    require_success(version, "version probe")
    root_help = run_command((binary, "--help"))
    require_success(root_help, "root help probe")
    help_text = root_help.stdout + root_help.stderr
    missing_commands = [
        command for command in REQUIRED_COMMANDS if command not in help_text
    ]
    missing_flags = [flag for flag in REQUIRED_GLOBAL_FLAGS if flag not in help_text]
    subcommands: dict[str, bool] = {}
    for command in REQUIRED_COMMANDS:
        result = run_command((binary, command, "--help"))
        subcommands[command] = result.returncode == 0 and bool(
            result.stdout or result.stderr
        )
    return {
        "binary": binary,
        "version": version.stdout.strip() or version.stderr.strip(),
        "missing_commands": missing_commands,
        "missing_global_flags": missing_flags,
        "subcommand_help": subcommands,
        "passed": not missing_commands
        and not missing_flags
        and all(subcommands.values()),
    }


def isolated_base(
    binary: str,
    source: Path,
    destination: Path,
    work: Path,
) -> tuple[str, ...]:
    config = work / "config.toml"
    config.write_text("", encoding="utf-8")
    cache = work / "cache"
    cache.mkdir()
    return (
        binary,
        "--source",
        str(source),
        "--destination",
        str(destination),
        "--persistent-state",
        str(work / "state.boltdb"),
        "--cache",
        str(cache),
        "--config",
        str(config),
        "--no-pager",
        "--no-tty",
        "--progress=false",
        "--color=off",
        "--refresh-externals=never",
    )


def exercise_isolated(binary: str) -> dict[str, object]:
    """Exercise source and target behavior without touching ambient chezmoi state."""

    with (
        tempfile.TemporaryDirectory(prefix="better-chezmoi-source-") as source_name,
        tempfile.TemporaryDirectory(
            prefix="better-chezmoi-target-"
        ) as destination_name,
        tempfile.TemporaryDirectory(prefix="better-chezmoi-work-") as work_name,
    ):
        source = Path(source_name)
        destination = Path(destination_name)
        work = Path(work_name)
        base = isolated_base(binary, source, destination, work)
        target = destination / "foo.txt"
        target.write_text("hello\n", encoding="utf-8")

        add = run_command((*base, "add", str(target)))
        require_success(add, "isolated add")
        source_file = source / "foo.txt"
        if source_file.read_text(encoding="utf-8") != "hello\n":
            raise ProbeError("isolated add did not create the expected source bytes")

        target.write_text("world\n", encoding="utf-8")
        status = run_command((*base, "status"))
        require_success(status, "isolated status")
        diff = run_command((*base, "diff"))
        require_success(diff, "isolated diff")
        verify_drift = run_command((*base, "verify"))
        if verify_drift.returncode != 1:
            raise ProbeError(f"verify drift must exit 1, got {verify_drift.returncode}")

        before_preview = target.read_bytes()
        preview = run_command(
            (*base, "apply", "--dry-run", "--force", "--verbose", "--exclude=scripts")
        )
        require_success(preview, "isolated dry-run apply")
        if target.read_bytes() != before_preview:
            raise ProbeError("dry-run apply changed the isolated destination")

        # Force is confined to disposable state so the probe can verify the
        # target-write path without an interactive prompt or ambient effects.
        apply = run_command((*base, "apply", "--force", "--exclude=scripts"))
        require_success(apply, "isolated apply")
        if target.read_text(encoding="utf-8") != "hello\n":
            raise ProbeError("isolated apply did not restore the expected target bytes")
        verify_clean = run_command((*base, "verify"))
        require_success(verify_clean, "isolated clean verify")

        return {
            "passed": True,
            "status": status.stdout.strip(),
            "diff_exit": diff.returncode,
            "verify_drift_exit": verify_drift.returncode,
            "preview_left_destination_unchanged": True,
            "verify_clean_exit": verify_clean.returncode,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--binary", default="chezmoi", help="Binary name or path. Default: chezmoi"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Also run add/diff/status/verify/apply against isolated temporary state.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        binary = resolve_binary(args.binary)
        contract = inspect_contract(binary)
        result: dict[str, object] = {"contract": contract}
        if args.integration:
            result["integration"] = exercise_isolated(binary)
        result["passed"] = bool(contract["passed"]) and (
            not args.integration or bool(cast_mapping(result["integration"])["passed"])
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 1
    except (OSError, ProbeError, subprocess.SubprocessError) as exc:
        print(
            json.dumps({"passed": False, "error": str(exc)}, indent=2), file=sys.stderr
        )
        return 2


def cast_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ProbeError("internal probe result must be an object")
    return value


if __name__ == "__main__":
    raise SystemExit(main())

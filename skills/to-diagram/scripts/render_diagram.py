#!/usr/bin/env python3
"""Render exactly one fenced Mermaid block from Markdown to a validated PNG."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile


MERMAID_PACKAGE = "@mermaid-js/mermaid-cli@^11"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MERMAID_BLOCK = re.compile(
    r"^(?P<fence>`{3,}|~{3,})[ \t]*mermaid[ \t]*\r?\n"
    r"(?P<source>.*?)"
    r"^(?P=fence)[ \t]*\r?$",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)

CommandRunner = Callable[
    [Sequence[str], int],
    subprocess.CompletedProcess[str],
]
Which = Callable[[str], str | None]


class DiagramRenderError(RuntimeError):
    """Raised when Markdown cannot be rendered into a trustworthy PNG."""


@dataclass(frozen=True, slots=True)
class Renderer:
    argv_prefix: tuple[str, ...]
    display_name: str


@dataclass(frozen=True, slots=True)
class PngInfo:
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class Arguments:
    markdown_path: Path
    png_path: Path
    mmdc: str | None
    force: bool
    timeout_seconds: int


def extract_mermaid_source(markdown: str) -> str:
    """Return the only non-empty fenced Mermaid block in Markdown."""
    matches = list(MERMAID_BLOCK.finditer(markdown))
    if len(matches) != 1:
        raise DiagramRenderError(
            "Markdown must contain exactly one fenced Mermaid block; "
            f"found {len(matches)}."
        )
    source = matches[0].group("source").strip()
    if not source:
        raise DiagramRenderError("The fenced Mermaid block is empty.")
    return source + "\n"


def resolve_requested_executable(request: str, which: Which = shutil.which) -> str:
    """Resolve an explicit executable path or command name."""
    candidate = Path(request).expanduser()
    if candidate.parent != Path(".") or candidate.is_absolute():
        resolved_path = candidate.resolve()
        if not resolved_path.is_file() or not os.access(resolved_path, os.X_OK):
            raise DiagramRenderError(
                f"Mermaid CLI override is not an executable file: {request}"
            )
        return str(resolved_path)

    resolved = which(request)
    if resolved is None:
        raise DiagramRenderError(
            f"Mermaid CLI override was not found on PATH: {request}"
        )
    return resolved


def select_renderer(
    explicit_mmdc: str | None,
    which: Which = shutil.which,
) -> Renderer:
    """Prefer an explicit or installed mmdc, then fall back to npx."""
    requested = explicit_mmdc or os.environ.get("TO_DIAGRAM_MMDC", "").strip()
    if requested:
        executable = resolve_requested_executable(requested, which)
        return Renderer((executable,), executable)

    mmdc = which("mmdc")
    if mmdc is not None:
        return Renderer((mmdc,), mmdc)

    npx = which("npx")
    if npx is not None:
        return Renderer(
            (npx, "--yes", MERMAID_PACKAGE),
            f"{npx} {MERMAID_PACKAGE}",
        )

    raise DiagramRenderError(
        "No Mermaid renderer is available. Install Mermaid CLI (`mmdc`) or "
        "Node.js with `npx`, or pass --mmdc /path/to/mmdc."
    )


def run_command(
    command: Sequence[str],
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    """Run Mermaid CLI without a shell so labels cannot alter the command."""
    return subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )


def inspect_png(path: Path) -> PngInfo:
    """Validate the PNG signature and positive IHDR dimensions."""
    try:
        header = path.read_bytes()[:24]
    except OSError as exc:
        raise DiagramRenderError(f"Rendered PNG could not be read: {exc}") from exc

    if len(header) < 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise DiagramRenderError("Renderer output is not a valid PNG with an IHDR header.")

    width, height = struct.unpack(">II", header[16:24])
    if width <= 0 or height <= 0:
        raise DiagramRenderError(
            f"Renderer produced invalid PNG dimensions: {width}x{height}."
        )
    return PngInfo(width=width, height=height)


def render_markdown(
    markdown_path: Path,
    png_path: Path,
    renderer: Renderer,
    *,
    force: bool = False,
    timeout_seconds: int = 180,
    runner: CommandRunner = run_command,
) -> PngInfo:
    """Render one Mermaid block atomically without persisting source sidecars."""
    markdown = markdown_path.expanduser().resolve()
    output = png_path.expanduser().resolve()
    if not markdown.is_file():
        raise DiagramRenderError(f"Markdown input does not exist: {markdown}")
    if markdown == output:
        raise DiagramRenderError("Markdown input and PNG output must be different paths.")
    if output.exists() and not force:
        raise DiagramRenderError(
            f"PNG output already exists: {output}. Choose a new basename or use "
            "--force only when replacement is authorized."
        )

    source = extract_mermaid_source(markdown.read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=".to-diagram-",
        dir=output.parent,
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        source_path = temporary_root / "diagram.mmd"
        temporary_png = temporary_root / "diagram.png"
        source_path.write_text(source, encoding="utf-8")

        command = (
            *renderer.argv_prefix,
            "--input",
            str(source_path),
            "--output",
            str(temporary_png),
            "--theme",
            "neutral",
            "--backgroundColor",
            "white",
            "--scale",
            "2",
            "--quiet",
        )
        try:
            completed = runner(command, timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            raise DiagramRenderError(
                f"Mermaid rendering exceeded {timeout_seconds} seconds."
            ) from exc
        except OSError as exc:
            raise DiagramRenderError(
                f"Could not start Mermaid renderer {renderer.display_name}: {exc}"
            ) from exc

        if completed.returncode != 0:
            diagnostic = (completed.stderr or completed.stdout).strip()
            if not diagnostic:
                diagnostic = f"renderer exited with status {completed.returncode}"
            raise DiagramRenderError(f"Mermaid rendering failed: {diagnostic}")

        info = inspect_png(temporary_png)
        temporary_png.replace(output)

    return info


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def parse_arguments(argv: Sequence[str] | None = None) -> Arguments:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown", help="Markdown file containing exactly one Mermaid block.")
    parser.add_argument(
        "png",
        nargs="?",
        help="PNG destination. Default: the Markdown path with a .png suffix.",
    )
    parser.add_argument(
        "--mmdc",
        help="Explicit Mermaid CLI executable path or command name.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing PNG after a successful temporary render.",
    )
    parser.add_argument(
        "--timeout",
        type=positive_integer,
        default=180,
        metavar="SECONDS",
        help="Renderer timeout in seconds. Default: 180.",
    )
    namespace = parser.parse_args(argv)

    markdown_path = Path(str(namespace.markdown))
    png_value = namespace.png
    png_path = Path(str(png_value)) if png_value else markdown_path.with_suffix(".png")
    mmdc_value = namespace.mmdc
    return Arguments(
        markdown_path=markdown_path,
        png_path=png_path,
        mmdc=str(mmdc_value) if mmdc_value else None,
        force=bool(namespace.force),
        timeout_seconds=int(namespace.timeout),
    )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    try:
        renderer = select_renderer(arguments.mmdc)
        info = render_markdown(
            arguments.markdown_path,
            arguments.png_path,
            renderer,
            force=arguments.force,
            timeout_seconds=arguments.timeout_seconds,
        )
    except (DiagramRenderError, UnicodeDecodeError) as exc:
        print(f"to-diagram: {exc}", file=sys.stderr)
        return 1

    print(
        f"Rendered {arguments.markdown_path} -> {arguments.png_path} "
        f"({info.width}x{info.height})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

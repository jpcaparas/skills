"""Offline tests for render_diagram.py using a fake Mermaid CLI."""

from __future__ import annotations

import base64
import subprocess
import tempfile
import unittest
from collections.abc import Sequence
from pathlib import Path

import render_diagram

ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
DIAGRAM = "```mermaid\nflowchart TD\n  A --> B\n```\n"


class FakeRenderer:
    def __init__(self, *, returncode: int = 0, diagnostic: str = "") -> None:
        self.returncode = returncode
        self.diagnostic = diagnostic
        self.commands: list[tuple[str, ...]] = []
        self.sources: list[str] = []

    def __call__(self, command: Sequence[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
        recorded = tuple(command)
        self.commands.append(recorded)
        source = Path(recorded[recorded.index("--input") + 1])
        output = Path(recorded[recorded.index("--output") + 1])
        self.sources.append(source.read_text(encoding="utf-8"))
        if self.returncode == 0:
            output.write_bytes(ONE_PIXEL_PNG)
        return subprocess.CompletedProcess(list(recorded), self.returncode, stdout="", stderr=self.diagnostic)


class RenderDiagramTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="to-diagram-test-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.markdown = self.root / "diagram.md"
        self.png = self.root / "diagram.png"
        self.markdown.write_text(DIAGRAM, encoding="utf-8")
        self.renderer = render_diagram.Renderer(("fake-mmdc",), "fake-mmdc")

    def test_render_creates_only_the_two_deliverables(self) -> None:
        fake = FakeRenderer()
        info = render_diagram.render_markdown(self.markdown, self.png, self.renderer, runner=fake)
        command = fake.commands[0]
        self.assertEqual(info, render_diagram.PngInfo(width=1, height=1))
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["diagram.md", "diagram.png"])
        self.assertEqual(fake.sources, ["flowchart TD\n  A --> B\n"])
        self.assertEqual(command[command.index("--theme") + 1], "neutral")
        self.assertEqual(command[command.index("--backgroundColor") + 1], "white")
        self.assertEqual(command[command.index("--scale") + 1], "2")

    def test_rejects_multiple_mermaid_blocks(self) -> None:
        markdown = DIAGRAM + "\n" + DIAGRAM
        with self.assertRaisesRegex(render_diagram.DiagramRenderError, "found 2"):
            render_diagram.extract_mermaid_source(markdown)

    def test_existing_png_is_preserved(self) -> None:
        self.png.write_bytes(b"existing-user-file")
        with self.assertRaisesRegex(render_diagram.DiagramRenderError, "already exists"):
            render_diagram.render_markdown(self.markdown, self.png, self.renderer, runner=FakeRenderer())
        self.assertEqual(self.png.read_bytes(), b"existing-user-file")

    def test_renderer_failure_leaves_no_png(self) -> None:
        fake = FakeRenderer(returncode=1, diagnostic="Parse error on line 2")
        with self.assertRaisesRegex(render_diagram.DiagramRenderError, "Parse error on line 2"):
            render_diagram.render_markdown(self.markdown, self.png, self.renderer, runner=fake)
        self.assertFalse(self.png.exists())

    def test_renderer_selection_prefers_mmdc_then_npx(self) -> None:
        both = {"mmdc": "/tools/mmdc", "npx": "/tools/npx"}.get
        direct = render_diagram.select_renderer(None, both)
        fallback = render_diagram.select_renderer(None, lambda c: "/tools/npx" if c == "npx" else None)
        self.assertEqual(direct.argv_prefix, ("/tools/mmdc",))
        self.assertEqual(fallback.argv_prefix, ("/tools/npx", "--yes", render_diagram.MERMAID_PACKAGE))


if __name__ == "__main__":
    unittest.main()

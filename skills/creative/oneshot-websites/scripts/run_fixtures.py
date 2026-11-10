"""Shared builders for the oneshot-websites tests: real prepared runs on disk.

Runs are created by the production `prepare_run.create_run` and finalized by the
production `cleanup_run_tmp`, so every fixture starts from a root the validator must
accept. Tests then break exactly one rule and assert the specific error.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable, Optional

import build_catalog_index
import cleanup_run_tmp
import prepare_run
import validate_catalog

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"

RACING_PROMPT = (
    "Create a browser racing game with a controllable vehicle, steering, WASD, and arrow keys. "
    "A with ArrowLeft must steer left, while D with ArrowRight must steer right.\n"
)
POSTER_PROMPT = "Create a quiet typographic poster site.\n"
STATIC_INDEX = (
    '<!doctype html><html><head><meta charset="utf-8"><title>Export</title></head>'
    "<body>Built static export</body></html>\n"
)


def run_script(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args], capture_output=True, text=True, check=False
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def edit_json(path: Path, change: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    document = read_json(path)
    change(document)
    write_json(path, document)
    return document


def not_required_gauntlet() -> dict[str, Any]:
    return {
        "applicability": "not-required",
        "notRequiredReason": "Structural static-handoff fixture.",
        "bar": None,
        "referenceProvenance": [],
        "barValidation": {"result": None, "evidence": None},
        "barRevisions": [],
        "freshCriticAvailable": None,
        "rounds": [],
        "integrationPass": {"required": False, "result": "not-required", "evidence": None},
        "fallbackEvidence": None,
        "stopReason": "not-required",
    }


def required_gauntlet(critic: str = "critic-1") -> dict[str, Any]:
    """A successful required gauntlet: one critic round that ends READY."""
    return {
        "applicability": "required",
        "notRequiredReason": None,
        "bar": "Reads as a finished poster at phone and desktop widths.",
        "referenceProvenance": ["Brief wording"],
        "barValidation": {"result": "accepted", "evidence": "Critic accepted the bar."},
        "barRevisions": [],
        "freshCriticAvailable": True,
        "rounds": [
            {
                "criticWorkerId": critic,
                "artifactRevision": "rev-1",
                "verdict": "READY",
                "inspected": "Home page at two widths",
                "evidence": "Screenshots",
                "recheck": "None needed",
                "highestLeverageGap": None,
                "fix": None,
            }
        ],
        "integrationPass": {"required": False, "result": "not-required", "evidence": None},
        "fallbackEvidence": None,
        "stopReason": "bar-met",
    }


class OutputRoot(unittest.TestCase):
    """A temporary output root plus builders for runs in each lifecycle state."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="oneshot-test-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.root = self.tmp / "runs"

    def write_prompt(self, prompt: str) -> Path:
        path = self.tmp / "prompt.md"
        path.write_text(prompt, encoding="utf-8")
        return path

    def prepare(
        self,
        prompt: str = POSTER_PROMPT,
        experiment: str = "Poster",
        verification: str = "gauntlet",
        classification: str = "autonomous-one-shot",
        prior_run: Optional[Path] = None,
        directional_controls: str = "auto",
    ) -> Path:
        arguments = argparse.Namespace(
            output_root=self.root,
            model="Test Model",
            harness="Test Harness",
            experiment=experiment,
            prompt_file=self.write_prompt(prompt),
            verification=verification,
            classification=classification,
            prior_run=prior_run,
            directional_controls=directional_controls,
        )
        return prepare_run.create_run(arguments)

    def mark_status(self, run: Path, status: str) -> None:
        for name in ("run.json", "worker-report.json"):
            edit_json(run / name, lambda document: document.update(status=status))

    def finalize_ok(
        self,
        run: Path,
        index_html: str = STATIC_INDEX,
        gauntlet: Optional[dict[str, Any]] = None,
        descendants: tuple[str, ...] = (),
    ) -> None:
        """Take a prepared gauntlet run through the real RUNNING -> cleanup -> OK sequence."""
        (run / "artifact" / "index.html").write_text(index_html, encoding="utf-8")
        self.mark_status(run, "RUNNING")

        def fill(report: dict[str, Any]) -> None:
            report["temporary"]["routingApplied"] = True
            report["artifact"]["staticDeploymentVerified"] = True
            report["qualityGauntlet"] = gauntlet or not_required_gauntlet()
            report["verification"] = [
                {"kind": "static-browser-smoke", "result": "passed", "evidence": "Opened the built root entrypoint"}
            ]
            report["descendantWorkerIds"] = list(descendants)

        edit_json(run / "worker-report.json", fill)
        edit_json(run / "run.json", lambda d: d["execution"].update(descendantWorkerIds=list(descendants)))
        cleanup_run_tmp.cleanup_run_temporary(run, confirmed_finalized=True)
        self.mark_status(run, "OK")

    def finalize_unverified(self, run: Path) -> None:
        (run / "artifact" / "index.html").write_text(STATIC_INDEX, encoding="utf-8")
        self.mark_status(run, "RUNNING")
        edit_json(run / "worker-report.json", lambda r: r["temporary"].update(routingApplied=True))
        cleanup_run_tmp.cleanup_run_temporary(run, confirmed_finalized=True)
        self.mark_status(run, "UNVERIFIED")

    def ok_run(self, **finalize: Any) -> Path:
        run = self.prepare()
        self.finalize_ok(run, **finalize)
        return run

    def rebuild_index(self) -> None:
        build_catalog_index.publish_catalogue(self.root.resolve(), self.root.resolve() / "index.html")

    def validate(self, rebuild_index: bool = True) -> dict[str, Any]:
        if rebuild_index:
            self.rebuild_index()
        return validate_catalog.validate(self.root.resolve())

    def assert_valid(self, result: dict[str, Any]) -> None:
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["valid"])

    def assert_rejected(self, result: dict[str, Any], *fragments: str) -> None:
        """Every fragment must appear in some error; the root must not validate."""
        self.assertFalse(result["valid"], "expected the root to be rejected")
        for fragment in fragments:
            self.assertTrue(
                any(fragment in error for error in result["errors"]),
                f"no error contains {fragment!r}; errors were:\n" + "\n".join(result["errors"]),
            )

    def receipt_path(self, run: Path) -> Path:
        return self.root / ".oneshot-provenance" / f"{run.name}.json"

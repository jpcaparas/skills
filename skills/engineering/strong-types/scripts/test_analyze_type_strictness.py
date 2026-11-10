"""Regression tests for analyze_type_strictness.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve().parent / "analyze_type_strictness.py"
EXPECTED_FINDINGS = {
    "fallback-chain",
    "escape-hatch-type",
    "untyped-signature",
    "suppressed-type-error",
    "php-missing-strict-types",
    "ts-nonstrict-config",
}


def write_fixture(root: Path) -> None:
    src = root / "src"
    src.mkdir()
    (src / "Location.php").write_text(
        """
<?php

class Location
{
    public function image($fallback)
    {
        return $this->preview ?? $this->banner ?? $this->thumbnail;
    }

    public function normalize(mixed $value)
    {
        return $value;
    }
}
""".lstrip(),
        encoding="utf-8",
    )
    (src / "api.ts").write_text(
        """
export async function fetchUser(id: string): Promise<any> {
  // @ts-ignore
  const res = await fetch(`/api/users/${id}`);
  return res.json() as any;
}
const label = user.nickname || user.fullName || user.email;
""".lstrip(),
        encoding="utf-8",
    )
    (src / "report.py").write_text(
        """
from typing import Any


def build(payload: Any):
    value = payload.get("a") or payload.get("b") or payload.get("c")
    return value  # type: ignore
""".lstrip(),
        encoding="utf-8",
    )
    (root / "tsconfig.json").write_text(
        """
{
  "compilerOptions": {
    "target": "es2020"
  }
}
""".lstrip(),
        encoding="utf-8",
    )


def write_clean_fixture(root: Path) -> None:
    src = root / "src"
    src.mkdir()
    (src / "Location.php").write_text(
        """
<?php

declare(strict_types=1);

final class Location
{
    public function primaryImage(): Image
    {
        return $this->preview ?? throw new MissingImageException();
    }
}
""".lstrip(),
        encoding="utf-8",
    )


def scan(root: Path) -> list[dict[str, Any]]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(root), "--json"],
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout).get("findings", [])


class AnalyzeTypeStrictnessTests(unittest.TestCase):
    def test_reports_every_ambiguity_kind(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            write_fixture(Path(temp_dir))
            kinds = {item["kind"] for item in scan(Path(temp_dir))}
        self.assertTrue(EXPECTED_FINDINGS <= kinds, EXPECTED_FINDINGS - kinds)

    def test_clean_project_has_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            write_clean_fixture(Path(temp_dir))
            self.assertEqual(scan(Path(temp_dir)), [])


if __name__ == "__main__":
    unittest.main()

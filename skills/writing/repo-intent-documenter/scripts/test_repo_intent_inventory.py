#!/usr/bin/env python3
"""Unit tests for repo_intent_inventory.py."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

import repo_intent_inventory


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_inventory_detects_repo_signals() -> None:
    with tempfile.TemporaryDirectory(prefix="repo-intent-inventory-") as temp_dir:
        root = Path(temp_dir) / "sample-app"
        root.mkdir()
        write(root / "README.md", "# Sample App\n\nA workflow app for support teams.\n")
        write(root / "AGENTS.md", "# Agents\n\nRead REPO_INTENT.md first.\n")
        write(
            root / "package.json",
            json.dumps(
                {
                    "name": "sample-app",
                    "description": "Support workflow app",
                    "scripts": {"test": "vitest", "dev": "vite"},
                    "dependencies": {"react": "^19.0.0"},
                }
            ),
        )
        write(root / "src/index.ts", "export const app = true;\n")
        write(root / "tests/workflow.test.ts", "describe('workflow', () => {});\n")
        write(root / ".github/workflows/ci.yml", "name: ci\n")
        write(root / "node_modules/ignored/index.js", "ignored\n")

        inventory = repo_intent_inventory.build_inventory(root)

        assert inventory["name"] == "sample-app"
        assert "README.md" in inventory["docs"]
        assert "AGENTS.md" in inventory["agent_instructions"]
        assert "src/index.ts" in inventory["entrypoints"]
        assert "tests/workflow.test.ts" in inventory["tests"]
        assert ".github/workflows/ci.yml" in inventory["ci"]
        assert all("node_modules" not in path for path in inventory["sampled_files"])
        assert inventory["manifests"][0]["name"] == "sample-app"
        assert "dev" in inventory["manifests"][0]["scripts"]


def test_cli_json_output() -> None:
    with tempfile.TemporaryDirectory(prefix="repo-intent-cli-") as temp_dir:
        root = Path(temp_dir) / "sample-lib"
        root.mkdir()
        write(root / "pyproject.toml", "[project]\nname = 'sample-lib'\ndescription = 'A sample library'\n")

        script = Path(__file__).resolve().parent / "repo_intent_inventory.py"
        result = subprocess.run(
            [sys.executable, str(script), str(root), "--json"],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)

        assert data["name"] == "sample-lib"
        assert data["manifests"][0]["kind"] == "python"
        assert data["manifests"][0]["name"] == "sample-lib"


def test_pyproject_fallback_without_tomllib() -> None:
    original_tomllib = repo_intent_inventory.tomllib
    try:
        repo_intent_inventory.tomllib = None
        data = repo_intent_inventory.parse_toml_subset(
            "[project]\n"
            "name = 'fallback-lib'\n"
            "description = \"Fallback parser\"\n"
            "dependencies = ['click', 'rich']\n"
            "[tool.pytest]\n"
            "addopts = '-q'\n"
        )
    finally:
        repo_intent_inventory.tomllib = original_tomllib

    assert data["project"]["name"] == "fallback-lib"
    assert data["project"]["description"] == "Fallback parser"
    assert data["project"]["dependencies"] == ["click", "rich"]
    assert "pytest" in data["tool"]


def main() -> int:
    tests = [
        test_inventory_detects_repo_signals,
        test_cli_json_output,
        test_pyproject_fallback_without_tomllib,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{test.__name__}: {exc}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"PASS: {len(tests)} repo_intent_inventory tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

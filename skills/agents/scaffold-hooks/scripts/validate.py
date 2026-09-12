#!/usr/bin/env python3
"""Validate the scaffold-hooks skill structure."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_DIRS = ["references", "scripts", "templates", "evals", "assets", "agents"]
REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "assets/harnesses.json",
    "templates/hook-plan.example.json",
    "references/README.md",
    "references/harness-composition.md",
    "references/plan-format.md",
    "references/collision-policy.md",
    "references/migration.md",
    "references/project-audit.md",
    "scripts/scaffold_all_hooks.sh",
    "scripts/detect_code_extensions.py",
    "scripts/test_skill.py",
    "scripts/validate.py",
    "evals/evals.json",
]
HARNESS_NAMES = ["claude", "codex", "copilot", "devin", "opencode"]
REQUIRED_HARNESS_FILES = [
    "PLAYBOOK.md",
    "assets/hook-events.json",
    "templates/hook-plan.example.json",
    "scripts/scaffold_hooks.sh",
    "scripts/audit_project.sh",
    "scripts/render_hooks_readme.sh",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "references/gotchas.md",
]
EXPECTED_HARNESSES = {"claude", "codex", "copilot", "devin", "opencode"}
LEGACY_ROOTS = {
    ".claude/hooks/generated",
    ".codex/hooks/generated",
    ".devin/hooks/generated",
}


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str]:
    if not content.startswith("---"):
        return None, content
    end = content.find("---", 3)
    if end == -1:
        return None, content
    frontmatter_text = content[3:end].strip()
    body = content[end + 3 :].strip()
    frontmatter: dict[str, str] = {}
    for line in frontmatter_text.splitlines():
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)$", line)
        if not match:
            continue
        value = match.group(2).strip()
        if value and value[0] in ('"', "'") and value[-1] == value[0]:
            value = value[1:-1]
        frontmatter[match.group(1)] = value
    return frontmatter, body


def extract_file_references(content: str) -> list[str]:
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    refs: list[str] = []
    pattern = re.compile(r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`")
    for match in pattern.finditer(stripped):
        path = match.group(1)
        if not re.search(r"[{}<>]|\s", path):
            refs.append(path)
    link_pattern = re.compile(r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)")
    for match in link_pattern.finditer(stripped):
        path = match.group(1)
        if not re.search(r"[{}<>]|\s", path):
            refs.append(path)
    return sorted(set(refs))


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.name} is not valid JSON: {exc}")
        return {}


def validate(skill_path: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    for dirname in REQUIRED_DIRS:
        if not (skill_path / dirname).is_dir():
            errors.append(f"Missing required directory: {dirname}/")

    for rel_path in REQUIRED_FILES:
        if not (skill_path / rel_path).exists():
            errors.append(f"Missing required file: {rel_path}")

    skill_md = skill_path / "SKILL.md"
    if skill_md.is_file():
        content = skill_md.read_text(encoding="utf-8")
        metrics["skill_md_lines"] = len(content.splitlines())
        frontmatter, body = parse_frontmatter(content)
        if frontmatter is None:
            errors.append("SKILL.md has no YAML frontmatter")
        else:
            if frontmatter.get("name") != skill_path.name:
                errors.append("Frontmatter name must match directory name")
            description = frontmatter.get("description", "")
            if "/scaffold-hooks" not in description:
                errors.append("Description must include /scaffold-hooks trigger")
            if len(description) > 1024:
                errors.append("Description exceeds 1024 characters")
        if len(body.splitlines()) > 500:
            warnings.append("SKILL.md body exceeds 500 lines")
        for ref in extract_file_references(content):
            if not (skill_path / ref).exists():
                errors.append(f"Referenced file does not exist: {ref}")

    for ref_file in (skill_path / "references").glob("*.md"):
        metrics["reference_count"] += 1
        ref_content = ref_file.read_text(encoding="utf-8")
        metrics["total_lines"] += len(ref_content.splitlines())
        for ref in extract_file_references(ref_content):
            if not (skill_path / ref).exists():
                errors.append(f"Referenced file does not exist from {ref_file.name}: {ref}")

    metrics["total_lines"] += metrics["skill_md_lines"]

    plan = load_json(skill_path / "templates" / "hook-plan.example.json", errors)
    if plan:
        harnesses = set(plan.get("harnesses", []))
        if harnesses != EXPECTED_HARNESSES:
            errors.append(f"Plan harnesses must be {sorted(EXPECTED_HARNESSES)}")
        if plan.get("hooks_root") != "hooks":
            errors.append("Plan hooks_root must default to hooks")
        plans = plan.get("plans", {})
        for harness in EXPECTED_HARNESSES:
            if harness not in plans:
                errors.append(f"Plan missing nested harness plan: {harness}")
        for harness in ["claude", "codex", "devin"]:
            nested = plans.get(harness, {})
            if nested.get("managed_root"):
                errors.append(f"Nested {harness} plan must not hard-code managed_root")

    for harness in HARNESS_NAMES:
        harness_dir = skill_path / "harnesses" / harness
        if not harness_dir.is_dir():
            errors.append(f"Missing harness component: harnesses/{harness}/")
            continue
        for rel_path in REQUIRED_HARNESS_FILES:
            if not (harness_dir / rel_path).exists():
                errors.append(f"Missing harness file: harnesses/{harness}/{rel_path}")
        nested = run_harness_validator(harness_dir)
        for err in nested.get("errors", []):
            errors.append(f"[harnesses/{harness}] {err}")
        for warn in nested.get("warnings", []):
            warnings.append(f"[harnesses/{harness}] {warn}")

    scaffold_script = skill_path / "scripts" / "scaffold_all_hooks.sh"
    if scaffold_script.exists():
        scaffold_content = scaffold_script.read_text(encoding="utf-8")
        for snippet in [
            "detect_existing_harnesses",
            "scaffold_hooks",
            "skill_version",
            "generator_sha256",
            "plan_sha256",
            "harness_manifest_sha256",
            "detected_harnesses",
            "harness_selection_source",
        ]:
            if snippet not in scaffold_content:
                errors.append(f"scripts/scaffold_all_hooks.sh missing provenance snippet: {snippet}")

    harness_manifest = load_json(skill_path / "assets" / "harnesses.json", errors)
    if harness_manifest:
        names = {item.get("name") for item in harness_manifest.get("harnesses", [])}
        if names != EXPECTED_HARNESSES:
            errors.append("assets/harnesses.json must list all supported harnesses")
        roots = set(harness_manifest.get("legacy_managed_roots", []))
        if roots != LEGACY_ROOTS:
            errors.append("assets/harnesses.json legacy roots are incomplete")

    return {"valid": not errors, "errors": errors, "warnings": warnings, "metrics": metrics}


def run_harness_validator(harness_dir: Path) -> dict:
    validator = harness_dir / "scripts" / "validate.py"
    if not validator.is_file():
        return {"errors": [f"missing validator: {validator.name}"], "warnings": []}
    proc = subprocess.run(
        [sys.executable, str(validator), str(harness_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"errors": [f"validator produced non-JSON output (exit {proc.returncode})"], "warnings": []}
    return payload


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate.py /path/to/skill", file=sys.stderr)
        return 2
    result = validate(Path(sys.argv[1]).resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

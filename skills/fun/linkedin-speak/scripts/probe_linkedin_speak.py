#!/usr/bin/env python3
"""
Lightweight behavior probe for linkedin-speak.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False)


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    cli = skill_root / "scripts" / "linkedin_speak.py"

    translate_proc = run("python3", str(cli), "I got a new job.")
    reverse_proc = run(
        "python3",
        str(cli),
        "--mode",
        "reverse",
        "Thrilled to announce that I’m starting a new chapter today! Grateful for everyone who made this possible. 🚀 #GrowthMindset #Leadership",
    )
    json_proc = run(
        "python3",
        str(cli),
        "--mode",
        "both",
        "--format",
        "json",
        "--compare-kagi-url",
        "We launched the dashboard.",
    )

    errors: list[str] = []

    if translate_proc.returncode != 0:
        errors.append(f"translate command failed: {translate_proc.stderr.strip()}")
    else:
        output = translate_proc.stdout.strip()
        if "#" not in output:
            errors.append("translate output did not include hashtags")
        if not any(phrase in output for phrase in ["Thrilled to share", "Excited to announce", "Honored to share", "Proud to share", "Grateful to share"]):
            errors.append("translate output did not include a supported opener")

    if reverse_proc.returncode != 0:
        errors.append(f"reverse command failed: {reverse_proc.stderr.strip()}")
    else:
        output = reverse_proc.stdout.strip()
        if "#" in output or "🚀" in output:
            errors.append("reverse output still contains hashtags or emoji")

    if json_proc.returncode != 0:
        errors.append(f"json command failed: {json_proc.stderr.strip()}")
    else:
        try:
            payload = json.loads(json_proc.stdout)
        except json.JSONDecodeError as exc:
            errors.append(f"json output was invalid: {exc}")
        else:
            if "translation" not in payload or "reverse" not in payload:
                errors.append("json output missing translation or reverse keys")
            metadata = payload.get("metadata", {})
            if "kagi_compare_url" not in metadata:
                errors.append("json output missing kagi_compare_url")

    if errors:
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS: linkedin-speak probe succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

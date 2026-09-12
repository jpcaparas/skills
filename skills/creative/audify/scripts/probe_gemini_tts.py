#!/usr/bin/env python3
"""Run live probes against Gemini TTS for audify."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import audify  # noqa: E402


def run_models(timeout: int) -> dict[str, object]:
    api_key = audify.require_gemini_api_key()
    models = audify.list_tts_models(api_key=api_key, timeout=timeout)
    return {
        "model_count": len(models),
        "models": models,
        "default_model_visible": f"models/{audify.DEFAULT_MODEL}" in models,
    }


def run_smoke(timeout: int, output_root: str | None) -> dict[str, object]:
    api_key = audify.require_gemini_api_key()
    audify.ensure_model_available(api_key=api_key, model=audify.DEFAULT_MODEL, timeout=timeout)
    cleaned_text = "Skill validation is working."
    pcm_data, synthesis = audify.synthesize_text(
        cleaned_text,
        api_key=api_key,
        model=audify.DEFAULT_MODEL,
        voice=audify.DEFAULT_VOICE,
        nuance=audify.DEFAULT_NUANCE,
        timeout=timeout,
        retries=2,
        max_chunk_chars=audify.DEFAULT_MAX_CHUNK_CHARS,
        title="Smoke test",
    )

    resource = audify.ResourceResult(
        source="probe",
        source_kind="text",
        extracted_text=cleaned_text,
        cleaned_text=cleaned_text,
        read_attempts=["probe"],
        cleaning_stats={},
    )
    root = Path(output_root) if output_root else Path(tempfile.mkdtemp(prefix="audify-probe-"))
    paths = audify.write_output_bundle(
        pcm_data,
        resource_result=resource,
        output_root=root,
        voice=audify.DEFAULT_VOICE,
        nuance=audify.DEFAULT_NUANCE,
        model=audify.DEFAULT_MODEL,
        fmt="mp3",
        synthesis_meta=synthesis,
    )
    return {
        "bundle_dir": paths["bundle_dir"],
        "audio_path": paths["audio_path"],
        "chunk_count": synthesis["chunk_count"],
        "attempts_per_chunk": synthesis["attempts_per_chunk"],
    }


def run_bad_auth(timeout: int) -> dict[str, object]:
    try:
        audify.list_tts_models(api_key="definitely-wrong", timeout=timeout)
    except audify.ApiError as exc:
        return {"status": exc.status, "message": str(exc)}
    raise SystemExit("bad-auth probe unexpectedly succeeded")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run structured live probes for audify.")
    parser.add_argument("--mode", choices=["models", "smoke", "bad-auth", "all"], default="all")
    parser.add_argument("--timeout", type=int, default=audify.DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output-root", help="Optional directory for smoke-test bundles")
    args = parser.parse_args(argv)

    report: dict[str, object] = {"mode": args.mode}
    if args.mode in {"models", "all"}:
        report["models"] = run_models(args.timeout)
    if args.mode in {"smoke", "all"}:
        report["smoke"] = run_smoke(args.timeout, args.output_root)
    if args.mode in {"bad-auth", "all"}:
        report["bad_auth"] = run_bad_auth(args.timeout)

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

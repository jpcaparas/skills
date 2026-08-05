#!/usr/bin/env python3
"""Exercise the oneshot-websites package contract with temporary artifacts."""

from __future__ import annotations

import errno
import hashlib
import io
import json
import multiprocessing
import os
import queue
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence
from unittest.mock import patch

import validate_catalog as catalog_validator
from build_catalog_index import CATALOGUE_LOCK, parse_flat_run_id
from prepare_run import RunPreparationError, build_identity, make_run_id, reserve_paths
from runtime_contract import (
    enforce_json_nesting_limit,
    experiment_slug,
    find_likely_mojibake,
    identity_key,
    parse_json_bounded,
)


EVAL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ASSERTION_TYPES = {"functional", "structural", "disclosure", "negative", "verification"}


def run(command: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(list(command), text=True, capture_output=True, check=False)


def run_frozen_catalogue_builder(
    root_value: str,
    publication_ready: Any,
    release_publication: Any,
    outcome_queue: Any,
) -> None:
    """Freeze one old catalogue immediately before its atomic publication."""

    import build_catalog_index as catalogue_builder

    root = Path(root_value)
    out_path = root / "index.html"
    original_replace = catalogue_builder.os.replace
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()

    def held_replace(source: Any, destination: Any) -> None:
        if Path(destination) == out_path:
            publication_ready.set()
            if not release_publication.wait(30):
                raise RuntimeError("timed out waiting to publish the frozen catalogue snapshot")
        original_replace(source, destination)

    catalogue_builder.os.replace = held_replace
    original_argv = sys.argv
    try:
        sys.argv = [
            str(Path(catalogue_builder.__file__).resolve()),
            "--root",
            str(root),
            "--out",
            str(out_path),
        ]
        with redirect_stdout(captured_stdout), redirect_stderr(captured_stderr):
            returncode = catalogue_builder.main()
    except BaseException as error:
        outcome_queue.put(
            {
                "returncode": 1,
                "error": repr(error),
                "stdout": captured_stdout.getvalue(),
                "stderr": captured_stderr.getvalue(),
            }
        )
    else:
        outcome_queue.put(
            {
                "returncode": returncode,
                "error": "",
                "stdout": captured_stdout.getvalue(),
                "stderr": captured_stderr.getvalue(),
            }
        )
    finally:
        sys.argv = original_argv
        catalogue_builder.os.replace = original_replace


def catalogue_lock_is_busy(root: Path) -> bool:
    """Probe the builder's interprocess lock without waiting for ownership."""

    lock_path = root / CATALOGUE_LOCK
    try:
        descriptor = os.open(lock_path, os.O_RDWR | getattr(os, "O_CLOEXEC", 0))
    except FileNotFoundError:
        return False

    acquired = False
    try:
        if os.name == "posix":
            import fcntl

            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                if error.errno in {errno.EACCES, errno.EAGAIN}:
                    return True
                raise
        else:
            import msvcrt

            os.lseek(descriptor, 0, os.SEEK_SET)
            try:
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            except OSError as error:
                if error.errno in {errno.EACCES, errno.EAGAIN, 13, 36}:
                    return True
                raise
        acquired = True
        return False
    finally:
        if acquired:
            if os.name == "posix":
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_UN)
            else:
                import msvcrt

                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
        os.close(descriptor)


def assert_ok(condition: bool, message: str, errors: List[str]) -> None:
    if not condition:
        errors.append(message)


def rename_with_exact_case(path: Path, name: str) -> Path:
    """Force a case-only rename to reach disk on case-insensitive filesystems."""

    temporary = path.with_name(".oneshot-case-swap")
    path.rename(temporary)
    destination = path.with_name(name)
    temporary.rename(destination)
    return destination


def read_json(path: Path, errors: List[str], label: str) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append("{} is not valid JSON: {}".format(label, exc))
        return None


def check_evals(skill: Path, errors: List[str]) -> None:
    """Keep the package eval data useful to runners and human reviewers."""
    evals = read_json(skill / "evals" / "evals.json", errors, "evals/evals.json")
    triggers = read_json(skill / "evals" / "trigger-evals.json", errors, "evals/trigger-evals.json")
    if not isinstance(evals, Mapping) or not isinstance(triggers, list):
        return

    assert_ok(set(evals) == {"skill_name", "created_by", "evals"}, "evals must use the advanced creator top-level schema", errors)
    assert_ok(evals.get("skill_name") == "oneshot-websites", "evals skill_name must be oneshot-websites", errors)
    assert_ok(evals.get("created_by") == "skill-creator-advanced", "evals created_by must identify skill-creator-advanced", errors)
    entries = evals.get("evals")
    assert_ok(isinstance(entries, list) and bool(entries), "evals must contain a non-empty evals array", errors)
    seen_ids = set()
    if isinstance(entries, list):
        for index, item in enumerate(entries):
            assert_ok(isinstance(item, Mapping), "eval {} must be an object".format(index), errors)
            if not isinstance(item, Mapping):
                continue
            item_id = item.get("id")
            assert_ok(isinstance(item_id, int) and not isinstance(item_id, bool), "eval {} needs an integer id".format(index), errors)
            if isinstance(item_id, int) and not isinstance(item_id, bool):
                assert_ok(item_id not in seen_ids, "duplicate eval id: {}".format(item_id), errors)
                seen_ids.add(item_id)
            for field in ("name", "prompt", "expected_output"):
                assert_ok(isinstance(item.get(field), str) and bool(item[field].strip()), "eval {} missing {}".format(index, field), errors)
            name = item.get("name")
            if isinstance(name, str):
                assert_ok(bool(EVAL_NAME_RE.fullmatch(name)), "eval {} name must be lowercase hyphenated text".format(index), errors)
            assertions = item.get("assertions")
            assert_ok(isinstance(assertions, list) and bool(assertions), "eval {} needs assertions".format(index), errors)
            if isinstance(assertions, list):
                for assertion in assertions:
                    assert_ok(isinstance(assertion, Mapping), "eval assertion must be an object", errors)
                    if not isinstance(assertion, Mapping):
                        continue
                    assert_ok(isinstance(assertion.get("text"), str) and bool(assertion["text"].strip()), "eval assertion needs text", errors)
                    assert_ok(assertion.get("type") in ASSERTION_TYPES, "eval assertion has an unsupported type", errors)
            tags = item.get("tags")
            assert_ok(isinstance(tags, list) and all(isinstance(tag, str) for tag in tags), "eval {} needs string tags".format(index), errors)

        names = {
            item.get("name")
            for item in entries
            if isinstance(item, Mapping) and isinstance(item.get("name"), str)
        }
        required_wasm_evals = {
            "native-raw-decoder-earns-narrow-wasm-core",
            "unproven-route-optimizer-requires-bounded-wasm-spike",
            "rust-backend-crud-does-not-force-wasm",
            "offline-sqlite-archive-earns-supported-wasm-engine",
            "elaborate-marketing-motion-remains-web-native",
        }
        assert_ok(
            required_wasm_evals.issubset(names),
            "evals must cover strong-fit, spike-first, SQLite, and non-fit WebAssembly decisions",
            errors,
        )
        assert_ok(
            all(
                isinstance(item, Mapping)
                and isinstance(item.get("tags"), list)
                and "wasm" in item["tags"]
                for item in entries
                if isinstance(item, Mapping) and item.get("name") in required_wasm_evals
            ),
            "WebAssembly decision evals must carry the wasm tag",
            errors,
        )

    assert_ok(bool(triggers), "trigger evals need a non-empty raw array", errors)
    seen_queries = set()
    trigger_values = set()
    for index, case in enumerate(triggers):
        assert_ok(isinstance(case, Mapping), "trigger eval {} must be an object".format(index), errors)
        if not isinstance(case, Mapping):
            continue
        assert_ok(set(case) == {"query", "should_trigger"}, "trigger eval {} must contain exactly query and should_trigger".format(index), errors)
        query = case.get("query")
        assert_ok(isinstance(query, str) and bool(query.strip()), "trigger eval {} needs a non-empty query".format(index), errors)
        if isinstance(query, str) and query.strip():
            assert_ok(query not in seen_queries, "duplicate trigger query: {}".format(query), errors)
            seen_queries.add(query)
        should_trigger = case.get("should_trigger")
        assert_ok(isinstance(should_trigger, bool), "trigger eval {} needs should_trigger boolean".format(index), errors)
        if isinstance(should_trigger, bool):
            trigger_values.add(should_trigger)
    assert_ok(trigger_values == {True, False}, "trigger evals must balance positive and adjacent-negative cases", errors)


def invocation_json(result: subprocess.CompletedProcess, errors: List[str], label: str) -> Optional[Mapping[str, Any]]:
    if result.returncode != 0:
        errors.append("{} failed: {}".format(label, result.stderr or result.stdout))
        return None
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        errors.append("{} did not print JSON: {}".format(label, exc))
        return None
    if not isinstance(data, Mapping):
        errors.append("{} JSON result must be an object".format(label))
        return None
    return data


def run_directory(data: Mapping[str, Any], errors: List[str], label: str) -> Optional[Path]:
    value = data.get("runDirectory")
    if not isinstance(value, str):
        errors.append("{} JSON result missing runDirectory".format(label))
        return None
    path = Path(value)
    if not path.is_dir():
        errors.append("{} created run directory does not exist: {}".format(label, path))
        return None
    return path


def rebuild_catalog_index(output_root: Path) -> subprocess.CompletedProcess:
    """Regenerate the deterministic root catalogue after a valid fixture changes."""

    builder = Path(__file__).resolve().parent / "build_catalog_index.py"
    return run(
        [
            sys.executable,
            str(builder),
            "--root",
            str(output_root),
            "--out",
            str(output_root / "index.html"),
        ]
    )


def prepare_run(
    skill: Path,
    output_root: Path,
    model: str,
    harness: str,
    experiment: str,
    prompt_file: Path,
    errors: List[str],
    classification: str = "autonomous-one-shot",
    prior_run: Optional[Path] = None,
) -> Optional[Path]:
    command = [
        sys.executable,
        str(skill / "scripts" / "prepare_run.py"),
        "--output-root",
        str(output_root),
        "--model",
        model,
        "--harness",
        harness,
        "--experiment",
        experiment,
        "--prompt-file",
        str(prompt_file),
        "--classification",
        classification,
    ]
    if prior_run is not None:
        command.extend(("--prior-run", str(prior_run)))
    result = run(command)
    data = invocation_json(result, errors, "prepare_run.py")
    prepared = run_directory(data, errors, "prepare_run.py") if data is not None else None
    if prepared is not None:
        built = rebuild_catalog_index(output_root.resolve())
        assert_ok(
            built.returncode == 0,
            "could not build fixture root catalogue: {}".format(built.stderr or built.stdout),
            errors,
        )
    return prepared


def mark_successful_static_artifact(run_path: Path) -> None:
    """Create a framework-shaped source workspace and its static export."""
    workspace = run_path / "workspace"
    workspace.mkdir(exist_ok=True)
    (workspace / "package.json").write_text(
        json.dumps({"dependencies": {"react": "example"}, "scripts": {"build": "example"}}),
        encoding="utf-8",
    )
    (workspace / "src").mkdir(exist_ok=True)
    (workspace / "src" / "App.jsx").write_text("export default function App() { return null; }\n", encoding="utf-8")
    (workspace / "run.json").write_text('{"sourceFixture": true}\n', encoding="utf-8")
    (run_path / "artifact" / "assets").mkdir(exist_ok=True)
    (run_path / "artifact" / "assets" / "site.css").write_text("body { color: #17302c; }\n", encoding="utf-8")
    (run_path / "artifact" / "index.html").write_text(
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>Export</title>"
        "<link rel=\"stylesheet\" href=\"assets/site.css\"></head>"
        "<body><div id=\"root\">Built static export</div></body></html>\n",
        encoding="utf-8",
    )
    manifest_path = run_path / "run.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "OK"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report_path = run_path / "worker-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["status"] = "OK"
    report["temporary"]["routingApplied"] = True
    report["artifact"]["staticDeploymentVerified"] = True
    report["qualityGauntlet"] = {
        "applicability": "not-required",
        "notRequiredReason": "This helper creates only a structural static-handoff fixture.",
        "bar": None,
        "referenceProvenance": [],
        "barValidation": {"result": None, "evidence": None},
        "barRevisions": [],
        "freshCriticAvailable": None,
        "rounds": [],
        "integrationPass": {
            "required": False,
            "result": "not-required",
            "evidence": "The fixture has one source owner and no merged workstreams.",
        },
        "fallbackEvidence": None,
        "stopReason": "not-required",
    }
    report["verification"] = [
        {"kind": "static-browser-smoke", "result": "passed", "evidence": "Opened the built root entrypoint"}
    ]
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    built = rebuild_catalog_index(run_path.parent)
    if built.returncode != 0:
        raise RuntimeError("could not rebuild successful fixture catalogue: {}".format(built.stderr or built.stdout))


def convert_to_legacy_run(output_root: Path, run_path: Path, run_schema: str) -> Path:
    """Move a prepared flat run into a historical nested layout for compatibility coverage."""

    if run_schema not in {"2.0", "2.1"}:
        raise ValueError(f"unsupported legacy run schema: {run_schema}")

    legacy_run_id = "20260718T120000Z-00000000-0000-4000-8000-000000000001"
    manifest_path = run_path / "run.json"
    report_path = run_path / "worker-report.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    identity = manifest["identity"]

    namespace = output_root
    for field in ("model", "harness", "experiment"):
        part = identity[field]
        namespace = namespace / part["key"]
        namespace.mkdir()
        (namespace / ".oneshot-identity.json").write_text(
            json.dumps({"schemaVersion": "1.0", "name": part["name"], "key": part["key"]}) + "\n",
            encoding="utf-8",
        )
    legacy_run = namespace / legacy_run_id

    old_run_id = run_path.name
    old_receipt_path = output_root / ".oneshot-provenance" / f"{old_run_id}.json"
    old_commit_path = output_root / ".oneshot-provenance" / f"{old_run_id}.commit"
    receipt = json.loads(old_receipt_path.read_text(encoding="utf-8"))
    legacy_relative = legacy_run.relative_to(output_root).as_posix()

    manifest["schemaVersion"] = run_schema
    manifest["runId"] = legacy_run_id
    manifest["provenanceReceipt"] = f".oneshot-provenance/{legacy_run_id}.json"
    report["schemaVersion"] = "2.0"
    report["runId"] = legacy_run_id
    report.pop("qualityGauntlet", None)
    receipt["schemaVersion"] = "1.0" if run_schema == "2.0" else "1.1"
    receipt["runId"] = legacy_run_id
    receipt["runPath"] = legacy_relative
    receipt.pop("qualityGauntlet", None)
    if run_schema == "2.0":
        manifest.pop("temporary", None)
        report.pop("temporary", None)
        receipt.pop("runSchemaVersion", None)
        receipt.pop("temporary", None)
    else:
        receipt["runSchemaVersion"] = "2.1"

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    old_receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if run_schema == "2.0":
        shutil.rmtree(run_path / ".tmp")
    run_path.rename(legacy_run)
    old_receipt_path.rename(output_root / ".oneshot-provenance" / f"{legacy_run_id}.json")
    old_commit_path.rename(output_root / ".oneshot-provenance" / f"{legacy_run_id}.commit")
    return legacy_run


def convert_to_historical_flat_run(output_root: Path, run_path: Path, run_schema: str) -> Path:
    """Downgrade a prepared run to a historical timestamp-only flat contract."""

    if run_schema not in {"3.0", "3.1"}:
        raise ValueError(f"unsupported historical flat run schema: {run_schema}")

    historical_run_id = run_path.name[:19]
    run_path = rewrite_prepared_run_id(output_root, run_path, historical_run_id)

    manifest_path = run_path / "run.json"
    report_path = run_path / "worker-report.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    receipt_path = output_root / str(manifest["provenanceReceipt"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    manifest["schemaVersion"] = run_schema
    receipt["runSchemaVersion"] = run_schema
    if run_schema == "3.0":
        report["schemaVersion"] = "2.0"
        report.pop("qualityGauntlet", None)
        receipt["schemaVersion"] = "2.0"
        receipt.pop("qualityGauntlet", None)
    else:
        receipt["schemaVersion"] = "2.1"

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return run_path


def rewrite_prepared_run_id(output_root: Path, run_path: Path, new_run_id: str) -> Path:
    """Make a prepared fixture internally consistent after assigning an invalid run ID."""

    old_run_id = run_path.name
    manifest_path = run_path / "run.json"
    report_path = run_path / "worker-report.json"
    receipt_directory = output_root / ".oneshot-provenance"
    old_receipt_path = receipt_directory / f"{old_run_id}.json"
    old_commit_path = receipt_directory / f"{old_run_id}.commit"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    receipt = json.loads(old_receipt_path.read_text(encoding="utf-8"))

    manifest["runId"] = new_run_id
    manifest["provenanceReceipt"] = f".oneshot-provenance/{new_run_id}.json"
    report["runId"] = new_run_id
    receipt["runId"] = new_run_id
    receipt["runPath"] = new_run_id
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    old_receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    rewritten_run_path = output_root / new_run_id
    run_path.rename(rewritten_run_path)
    old_receipt_path.rename(receipt_directory / f"{new_run_id}.json")
    old_commit_path.rename(receipt_directory / f"{new_run_id}.commit")
    return rewritten_run_path


def write_appledouble(path: Path) -> None:
    """Write a minimal authentic AppleDouble signature for portable-volume tests."""

    path.write_bytes(b"\x00\x05\x16\x07" + b"\x00" * 28)


def assert_invalid_catalog(
    validator: Path,
    output_root: Path,
    expected_message: str,
    label: str,
    errors: List[str],
) -> None:
    """Require a malformed temporary catalogue to fail with a classified error."""

    result = run([sys.executable, str(validator), str(output_root)])
    assert_ok(result.returncode != 0, "validator accepted {}".format(label), errors)
    assert_ok(expected_message in result.stdout, "validator did not classify {}: {}".format(label, result.stdout), errors)


def exercise_adversarial_contract(
    skill: Path,
    validator: Path,
    temporary: Path,
    prompt: Path,
    errors: List[str],
) -> None:
    """Defend the provenance and static-handoff claims against bounded mutations."""

    temporary.mkdir(parents=True, exist_ok=True)
    try:
        enforce_json_nesting_limit('{"value":"' + "{" * 400 + '"}')
        enforce_json_nesting_limit("[" * 256 + "0" + "]" * 256)
    except ValueError as error:
        errors.append("JSON nesting guard rejected valid bounded content: {}".format(error))
    try:
        enforce_json_nesting_limit("[" * 257 + "0" + "]" * 257)
    except ValueError:
        pass
    else:
        errors.append("JSON nesting guard accepted metadata beyond 256 levels")
    try:
        parse_json_bounded('{"value":' + "9" * 100_000 + "}")
    except ValueError:
        pass
    else:
        errors.append("bounded JSON parser accepted a 100,000-digit integer token")
    for numeric_label, numeric_json in (
        ("oversized float token", '{"value":0.' + "1" * 1_000 + "}"),
        ("non-finite float", '{"value":1e309}'),
        ("non-standard numeric constant", '{"value":NaN}'),
    ):
        try:
            parse_json_bounded(numeric_json)
        except ValueError:
            pass
        else:
            errors.append("bounded JSON parser accepted {}".format(numeric_label))
    try:
        parse_json_bounded('{"value":"first","value":"second"}')
    except ValueError as error:
        assert_ok(
            str(error) == "duplicate JSON object member: 'value'",
            "bounded JSON parser reported a non-deterministic duplicate-member error",
            errors,
        )
    else:
        errors.append("bounded JSON parser accepted a duplicate object member")
    try:
        build_identity("\udcff", "model")
    except RunPreparationError as error:
        assert_ok(
            "valid UTF-8 text" in str(error),
            "prepare_run.py did not classify an invalid Unicode identity",
            errors,
        )
    else:
        errors.append("prepare_run.py accepted an invalid Unicode identity")

    def colliding_name(value: int) -> str:
        return "Model" + "".join("\u0301" if value & (1 << bit) else "\u0300" for bit in range(32))

    first_collision_name = colliding_name(3_739_250)
    second_collision_name = colliding_name(12_560_894)
    assert_ok(
        identity_key(first_collision_name) != identity_key(second_collision_name),
        "identity keys still collide for a known short-digest collision pair",
        errors,
    )

    loop_parent = temporary / "loop-parent"
    loop_parent.mkdir()
    loop_path = loop_parent / "loop"
    try:
        loop_path.symlink_to("loop")
    except OSError:
        pass
    else:
        loop_commands = [
            [
                sys.executable,
                str(skill / "scripts" / "prepare_run.py"),
                "--output-root",
                str(loop_path),
                "--model",
                "Model",
                "--harness",
                "Harness",
                "--experiment",
                "Loop",
                "--prompt-file",
                str(prompt),
            ],
            [
                sys.executable,
                str(skill / "scripts" / "build_catalog_index.py"),
                "--root",
                str(loop_path),
                "--out",
                str(loop_path / "index.html"),
            ],
            [sys.executable, str(validator), str(loop_path)],
        ]
        for command in loop_commands:
            loop_result = run(command)
            assert_ok(
                loop_result.returncode != 0
                and "unable to resolve output" in (loop_result.stdout + loop_result.stderr)
                and "Traceback" not in loop_result.stderr,
                "runtime CLI crashed on a symlink-loop output root",
                errors,
            )

    empty_prompt = temporary / "empty-prompt.md"
    empty_prompt.write_text(" \n\t", encoding="utf-8")
    empty_result = run(
        [
            sys.executable,
            str(skill / "scripts" / "prepare_run.py"),
            "--output-root",
            str(temporary / "empty-root"),
            "--model",
            "Model",
            "--harness",
            "Harness",
            "--experiment",
            "Empty",
            "--prompt-file",
            str(empty_prompt),
        ]
    )
    assert_ok(empty_result.returncode != 0 and "non-blank" in empty_result.stderr, "prepare_run.py accepted a blank prompt", errors)

    if os.name == "posix":
        unreadable_prompt = temporary / "unreadable-prompt.md"
        unreadable_prompt.write_text("Create an unreadable prompt fixture.\n", encoding="utf-8")
        os.chmod(unreadable_prompt, 0o000)
        unreadable_prompt_result = run(
            [
                sys.executable,
                str(skill / "scripts" / "prepare_run.py"),
                "--output-root",
                str(temporary / "unreadable-prompt-root"),
                "--model",
                "Model",
                "--harness",
                "Harness",
                "--experiment",
                "Unreadable Prompt",
                "--prompt-file",
                str(unreadable_prompt),
            ]
        )
        assert_ok(
            unreadable_prompt_result.returncode == 2
            and "prompt file is not readable" in unreadable_prompt_result.stderr
            and "Traceback" not in unreadable_prompt_result.stderr,
            "prepare_run.py crashed on an unreadable prompt file",
            errors,
        )
        os.chmod(unreadable_prompt, 0o600)

    if hasattr(os, "mkfifo"):
        fifo_prompt = temporary / "fifo-prompt.md"
        os.mkfifo(fifo_prompt)
        fifo_prompt_result = run(
            [
                sys.executable,
                str(skill / "scripts" / "prepare_run.py"),
                "--output-root",
                str(temporary / "fifo-prompt-root"),
                "--model",
                "Model",
                "--harness",
                "Harness",
                "--experiment",
                "FIFO Prompt",
                "--prompt-file",
                str(fifo_prompt),
            ]
        )
        assert_ok(
            fifo_prompt_result.returncode == 2
            and "prompt file must be a regular file" in fifo_prompt_result.stderr,
            "prepare_run.py blocked on or accepted a FIFO prompt",
            errors,
        )

    rerun_result = run(
        [
            sys.executable,
            str(skill / "scripts" / "prepare_run.py"),
            "--output-root",
            str(temporary / "rerun-root"),
            "--model",
            "Model",
            "--harness",
            "Harness",
            "--experiment",
            "Rerun",
            "--prompt-file",
            str(prompt),
            "--classification",
            "rerun",
        ]
    )
    assert_ok(rerun_result.returncode != 0 and "--prior-run" in rerun_result.stderr, "prepare_run.py accepted an unlinked rerun", errors)

    escaped_receipts = temporary / "escaped-receipts"
    escaped_receipts.mkdir()
    linked_root = temporary / "linked-receipt-root"
    linked_root.mkdir()
    try:
        (linked_root / ".oneshot-provenance").symlink_to(escaped_receipts, target_is_directory=True)
    except OSError:
        pass
    else:
        linked_result = run(
            [
                sys.executable,
                str(skill / "scripts" / "prepare_run.py"),
                "--output-root",
                str(linked_root),
                "--model",
                "Model",
                "--harness",
                "Harness",
                "--experiment",
                "Linked Receipt",
                "--prompt-file",
                str(prompt),
            ]
        )
        assert_ok(
            linked_result.returncode != 0 and "symbolic link" in linked_result.stderr,
            "prepare_run.py followed a symlinked provenance directory",
            errors,
        )

    if os.name == "posix":
        unwritable_root = temporary / "unwritable-receipt-root"
        unwritable_receipts = unwritable_root / ".oneshot-provenance"
        unwritable_receipts.mkdir(parents=True)
        os.chmod(unwritable_receipts, 0o500)
        unwritable_result = run(
            [
                sys.executable,
                str(skill / "scripts" / "prepare_run.py"),
                "--output-root",
                str(unwritable_root),
                "--model",
                "Model",
                "--harness",
                "Harness",
                "--experiment",
                "Unwritable Receipt",
                "--prompt-file",
                str(prompt),
            ]
        )
        assert_ok(
            unwritable_result.returncode == 2
            and "writable file mode" in unwritable_result.stderr
            and not [child for child in unwritable_root.iterdir() if not child.name.startswith(".")],
            "prepare_run.py left an unreceipted run after initialization failure",
            errors,
        )
        os.chmod(unwritable_receipts, 0o700)

    linked_run_root = temporary / "linked-run-root"
    linked_run_root.mkdir()
    linked_run_root = linked_run_root.resolve()
    linked_run_target = linked_run_root / "shared-target"
    linked_run_target.mkdir()
    linked_run_id = make_run_id("Linked Run")
    try:
        (linked_run_root / linked_run_id).symlink_to(linked_run_target, target_is_directory=True)
    except OSError:
        pass
    else:
        linked_run = reserve_paths(linked_run_root, linked_run_id).run
        assert_ok(
            linked_run.name == f"{linked_run_id}--02" and not any(linked_run_target.iterdir()),
            "flat reservation followed or reused a symlinked timestamp path",
            errors,
        )

    linked_prior_root = temporary / "linked-prior-root"
    linked_prior_root.mkdir()
    linked_prior_target = temporary / "outside-prior-model"
    outside_prior = linked_prior_target / "harness" / "experiment" / "run"
    outside_prior.mkdir(parents=True)
    (outside_prior / "run.json").write_text("{}\n", encoding="utf-8")
    try:
        (linked_prior_root / "alias").symlink_to(linked_prior_target, target_is_directory=True)
    except OSError:
        pass
    else:
        linked_prior_result = run(
            [
                sys.executable,
                str(skill / "scripts" / "prepare_run.py"),
                "--output-root",
                str(linked_prior_root),
                "--model",
                "Model",
                "--harness",
                "Harness",
                "--experiment",
                "Linked Prior",
                "--prompt-file",
                str(prompt),
                "--classification",
                "rerun",
                "--prior-run",
                str(linked_prior_root / "alias" / "harness" / "experiment" / "run"),
            ]
        )
        assert_ok(
            linked_prior_result.returncode != 0 and "symbolic links" in linked_prior_result.stderr,
            "prepare_run.py followed a symlinked prior-run component",
            errors,
        )

    anchor_root = temporary / "anchor-root"
    anchor_run = prepare_run(skill, anchor_root, "Anchor Model", "Harness", "Anchor", prompt, errors)
    if anchor_run is not None:
        mark_successful_static_artifact(anchor_run)
        changed = b"Create a different prompt.\n"
        (anchor_run / "artifact" / "PROMPT.md").write_bytes(changed)
        manifest_path = anchor_run / "run.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["prompt"]["sha256"] = hashlib.sha256(changed).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        assert_invalid_catalog(validator, anchor_root, "pre-dispatch", "prompt-plus-digest mutation", errors)

    identity_root = temporary / "identity-root"
    identity_run = prepare_run(skill, identity_root, "Original Model", "Harness", "Identity", prompt, errors)
    if identity_run is not None:
        manifest_path = identity_run / "run.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["identity"]["model"]["name"] = "Substituted Model"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        assert_invalid_catalog(validator, identity_root, "raw-name digest", "raw identity substitution", errors)

    whitespace_identity_root = temporary / "whitespace-identity-root"
    whitespace_identity_run = prepare_run(
        skill,
        whitespace_identity_root,
        " Model ",
        " Harness ",
        " Experiment ",
        prompt,
        errors,
    )
    if whitespace_identity_run is not None:
        whitespace_validation = run([sys.executable, str(validator), str(whitespace_identity_root)])
        assert_ok(
            whitespace_validation.returncode == 0,
            "validator changed exact whitespace-bearing raw identities: {}".format(whitespace_validation.stdout),
            errors,
        )

    prompt_type_root = temporary / "prompt-type-root"
    prompt_type_run = prepare_run(skill, prompt_type_root, "Model", "Harness", "Prompt Type", prompt, errors)
    if prompt_type_run is not None:
        prompt_path = prompt_type_run / "artifact" / "PROMPT.md"
        prompt_path.unlink()
        prompt_path.mkdir()
        assert_invalid_catalog(validator, prompt_type_root, "must be a regular file", "PROMPT.md directory", errors)

    missing_prompt_root = temporary / "missing-prompt-root"
    missing_prompt_run = prepare_run(skill, missing_prompt_root, "Model", "Harness", "Missing Prompt", prompt, errors)
    if missing_prompt_run is not None:
        (missing_prompt_run / "artifact" / "PROMPT.md").unlink()
        assert_invalid_catalog(
            validator,
            missing_prompt_root,
            "missing exact-case artifact/PROMPT.md",
            "non-successful run without preserved prompt",
            errors,
        )

    case_root = temporary / "case-root"
    case_run = prepare_run(skill, case_root, "Model", "Harness", "Case", prompt, errors)
    if case_run is not None:
        mark_successful_static_artifact(case_run)
        prompt_path = case_run / "artifact" / "PROMPT.md"
        wrong_prompt = rename_with_exact_case(prompt_path, "Prompt.md")
        assert_invalid_catalog(validator, case_root, "missing exact-case artifact/PROMPT.md", "wrong-case prompt", errors)
        rename_with_exact_case(wrong_prompt, "PROMPT.md")
        index_path = case_run / "artifact" / "index.html"
        wrong_index = rename_with_exact_case(index_path, "Index.html")
        assert_invalid_catalog(validator, case_root, "missing exact-case artifact/index.html", "wrong-case entrypoint", errors)
        rename_with_exact_case(wrong_index, "index.html")
        wrong_artifact = rename_with_exact_case(case_run / "artifact", "Artifact")
        assert_invalid_catalog(validator, case_root, "exact-case ordinary artifact/ directory", "wrong-case artifact directory", errors)
        rename_with_exact_case(wrong_artifact, "artifact")
        wrong_report = rename_with_exact_case(case_run / "worker-report.json", "Worker-report.json")
        assert_invalid_catalog(validator, case_root, "missing exact-case worker-report.json", "wrong-case worker report", errors)
        rename_with_exact_case(wrong_report, "worker-report.json")
        wrong_manifest = rename_with_exact_case(case_run / "run.json", "Run.json")
        assert_invalid_catalog(validator, case_root, "missing exact-case regular run.json", "wrong-case run manifest", errors)
        rename_with_exact_case(wrong_manifest, "run.json")

    missing_root_index_root = temporary / "missing-root-index-root"
    missing_root_index_run = prepare_run(skill, missing_root_index_root, "Model", "Harness", "Missing Root Index", prompt, errors)
    if missing_root_index_run is not None:
        (missing_root_index_root / "index.html").unlink()
        assert_invalid_catalog(validator, missing_root_index_root, "root index.html catalogue", "missing root catalogue", errors)

    assets_root = temporary / "assets-root"
    assets_run = prepare_run(skill, assets_root, "Model", "Harness", "Assets", prompt, errors)
    if assets_run is not None:
        mark_successful_static_artifact(assets_run)
        stylesheet = assets_run / "artifact" / "assets" / "site.css"
        stylesheet.write_text("body { background: url('missing.png'); }\n", encoding="utf-8")
        assert_invalid_catalog(validator, assets_root, "referenced local file missing", "missing CSS asset", errors)

        stylesheet.write_text("body { color: #17302c; }\n", encoding="utf-8")
        (assets_run / "artifact" / "index.html").write_text(
            "<!doctype html><img srcset=\"missing-1.png 1x, missing-2.png 2x\">",
            encoding="utf-8",
        )
        assert_invalid_catalog(validator, assets_root, "referenced local file missing", "missing srcset asset", errors)

        (assets_run / "artifact" / "index.html").write_text(
            "<!doctype html><script src=\"..%5Coutside.js\"></script>",
            encoding="utf-8",
        )
        assert_invalid_catalog(validator, assets_root, "unsafe decoded local resource URL", "decoded backslash URL", errors)

        (assets_run / "artifact" / "index.html").write_bytes(b'<!doctype html><script src="bad\x00path.js"></script>')
        assert_invalid_catalog(validator, assets_root, "unsafe decoded local resource URL", "NUL resource URL", errors)

    self_link_root = temporary / "self-link-root"
    self_link_run = prepare_run(skill, self_link_root, "Model", "Harness", "Self Link", prompt, errors)
    if self_link_run is not None:
        (self_link_run / "artifact" / "index.html").write_text(
            "<!doctype html><script src=\"loop.js\"></script>",
            encoding="utf-8",
        )
        loop_asset = self_link_run / "artifact" / "loop.js"
        try:
            loop_asset.symlink_to("loop.js")
        except OSError:
            pass
        else:
            self_link_validation = run([sys.executable, str(validator), str(self_link_root)])
            assert_ok(
                self_link_validation.returncode != 0
                and "symbolic links" in self_link_validation.stdout
                and "Traceback" not in self_link_validation.stderr,
                "self-referential artifact symlink escaped classified validation",
                errors,
            )

    large_reference_root = temporary / "large-reference-root"
    large_reference_run = prepare_run(
        skill,
        large_reference_root,
        "Model",
        "Harness",
        "Large References",
        prompt,
        errors,
    )
    if large_reference_run is not None:
        artifact = large_reference_run / "artifact"
        (artifact / "index.html").write_text(
            "<!doctype html><link rel=\"stylesheet\" href=\"0.css\">",
            encoding="utf-8",
        )
        large_query = "x" * (256 * 1024)
        for index in range(20):
            content = (
                '@import "{}.css?{}";\n'.format(index + 1, large_query)
                if index < 19
                else "body { color: black; }\n"
            )
            (artifact / "{}.css".format(index)).write_text(content, encoding="utf-8")
        large_reference_validation = run([sys.executable, str(validator), str(large_reference_root)])
        assert_ok(
            large_reference_validation.returncode != 0
            and "validation safety bound" in large_reference_validation.stdout
            and len(large_reference_validation.stdout) < 50_000
            and "Traceback" not in large_reference_validation.stderr,
            "large chained local URLs escaped cumulative reference bounds",
            errors,
        )

    reference_grid_root = temporary / "reference-grid-root"
    reference_grid_run = prepare_run(
        skill,
        reference_grid_root,
        "Model",
        "Harness",
        "Reference Grid",
        prompt,
        errors,
    )
    if reference_grid_run is not None:
        artifact = reference_grid_run / "artifact"
        (artifact / "index.html").write_text(
            "<!doctype html><link rel=\"stylesheet\" href=\"0.css\">",
            encoding="utf-8",
        )
        imports = "".join('@import "{}.css";\n'.format(index) for index in range(100))
        for index in range(100):
            (artifact / "{}.css".format(index)).write_text(imports, encoding="utf-8")
        grid_validation = run([sys.executable, str(validator), str(reference_grid_root)])
        assert_ok(
            grid_validation.returncode != 0
            and "validation safety bound" in grid_validation.stdout
            and len(grid_validation.stdout) < 50_000
            and "Traceback" not in grid_validation.stderr,
            "CSS reference fanout escaped enqueue-time inventory bounds",
            errors,
        )

    parser_root = temporary / "parser-root"
    parser_run = prepare_run(skill, parser_root, "Model", "Harness", "Parser", prompt, errors)
    if parser_run is not None:
        mark_successful_static_artifact(parser_run)
        artifact = parser_run / "artifact"
        (artifact / "assets" / "hero.avif").write_bytes(b"avif-fixture")
        (artifact / "index.html").write_text(
            "<!doctype html><link rel=\"canonical\" href=\"/\"><div data=\"component-state\"></div>"
            "<a href=\"/\">Home</a><form action=\"/\"><button>Submit</button></form>"
            "<style>/* url('missing-comment.png') */"
            ".hero{background-image:image-set(\"assets/hero.avif\" type(\"image/avif\"))}</style>",
            encoding="utf-8",
        )
        valid_parser = run([sys.executable, str(validator), str(parser_root)])
        assert_ok(valid_parser.returncode == 0, "validator rejected valid metadata/CSS markup: {}".format(valid_parser.stdout), errors)

        (artifact / "assets" / "site.css").write_text(
            ".example::before { content: \"url(missing-content.png) "
            "@import 'missing-import.css' image-set('missing-set.png' 1x)\"; }\n",
            encoding="utf-8",
        )
        (artifact / "index.html").write_text(
            "<!doctype html><link rel=\"stylesheet\" href=\"assets/site.css\">",
            encoding="utf-8",
        )
        quoted_css = run([sys.executable, str(validator), str(parser_root)])
        assert_ok(
            quoted_css.returncode == 0,
            "validator treated resource-like text inside a CSS string as live: {}".format(
                quoted_css.stdout
            ),
            errors,
        )

        (artifact / "index.html").write_text(
            "<!doctype html><link rel=\"stylesheet\" href=\"/assets/site.css\">",
            encoding="utf-8",
        )
        root_relative = run([sys.executable, str(validator), str(parser_root)])
        assert_ok(
            root_relative.returncode == 0,
            "validator rejected a Drop-compatible root-relative resource: {}".format(root_relative.stdout),
            errors,
        )

        (artifact / "index.html").write_text(
            "<!doctype html><iframe src=\"/?embed=1\" title=\"Embedded view\"></iframe>",
            encoding="utf-8",
        )
        same_entry = run([sys.executable, str(validator), str(parser_root)])
        assert_ok(
            same_entry.returncode == 0,
            "validator rejected a query-driven same-entry resource: {}".format(same_entry.stdout),
            errors,
        )

        (artifact / "index.html").write_text(
            "<!doctype html><style>/* url('commented-through-eof.png')",
            encoding="utf-8",
        )
        eof_comment = run([sys.executable, str(validator), str(parser_root)])
        assert_ok(eof_comment.returncode == 0, "validator treated an EOF-terminated CSS comment as live: {}".format(eof_comment.stdout), errors)

        (artifact / "index.html").write_text(
            "<!doctype html><svg><use xlink:href=\"missing-sprite.svg#icon\"></use></svg>",
            encoding="utf-8",
        )
        assert_invalid_catalog(validator, parser_root, "referenced local file missing", "missing xlink sprite", errors)

        (artifact / "index.html").write_text(
            "<!doctype html><style>.hero{background:url('missing-unclosed.png')}",
            encoding="utf-8",
        )
        assert_invalid_catalog(validator, parser_root, "referenced local file missing", "unclosed style resource", errors)

        (artifact / "index.html").write_text(
            "<!doctype html><style>.hero{background-image:image-set("
            "\"assets/hero.avif\" type(\"image/avif\"), \"missing-fallback.jpg\" type(\"image/jpeg\"))}</style>",
            encoding="utf-8",
        )
        assert_invalid_catalog(validator, parser_root, "referenced local file missing", "missing image-set fallback", errors)

        (artifact / "assets" / "Logo.PNG").write_bytes(b"logo")
        (artifact / "index.html").write_text(
            "<!doctype html><img src=\"assets/logo.png\">",
            encoding="utf-8",
        )
        assert_invalid_catalog(validator, parser_root, "path casing differs", "case-mismatched asset URL", errors)

    source_root = temporary / "source-root"
    source_run = prepare_run(skill, source_root, "Model", "Harness", "Source Leak", prompt, errors)
    if source_run is not None:
        mark_successful_static_artifact(source_run)
        (source_run / "artifact" / "package.json").write_text("{}\n", encoding="utf-8")
        assert_invalid_catalog(validator, source_root, "must stay in workspace", "artifact build marker", errors)

    nested_source_root = temporary / "nested-source-root"
    nested_source_run = prepare_run(skill, nested_source_root, "Model", "Harness", "Nested Source", prompt, errors)
    if nested_source_run is not None:
        mark_successful_static_artifact(nested_source_run)
        nested = nested_source_run / "artifact" / "nested"
        nested.mkdir()
        (nested / "package.json").write_text("{}\n", encoding="utf-8")
        assert_invalid_catalog(validator, nested_source_root, "must stay in workspace", "nested package marker", errors)
        (nested / "package.json").unlink()
        (nested / "App.vue").write_text("<template></template>\n", encoding="utf-8")
        assert_invalid_catalog(validator, nested_source_root, "preprocess-only source file", "unreferenced component source", errors)

    private_key_root = temporary / "private-key-root"
    private_key_run = prepare_run(skill, private_key_root, "Model", "Harness", "Private Key Leak", prompt, errors)
    if private_key_run is not None:
        mark_successful_static_artifact(private_key_run)
        artifact = private_key_run / "artifact"
        for filename in ("id_ed25519", "private-key.pem"):
            private_key_file = artifact / filename
            private_key_file.write_text("fixture without key material\n", encoding="utf-8")
            assert_invalid_catalog(
                validator,
                private_key_root,
                "private key material must stay in workspace/",
                "private-key filename {}".format(filename),
                errors,
            )
            private_key_file.unlink()

        marker_file = artifact / "assets" / "opaque-browser-asset.bin"
        for marker_label, marker in (
            ("PKCS#8 PEM", b"-----BEGIN PRIVATE KEY-----"),
            ("OpenSSH", b"-----BEGIN OPENSSH PRIVATE KEY-----"),
            ("PGP", b"-----BEGIN PGP PRIVATE KEY BLOCK-----"),
        ):
            marker_file.write_bytes(b"binary-prefix\x00\n" + marker + b"\nfixture-only")
            assert_invalid_catalog(
                validator,
                private_key_root,
                "private key material must stay in workspace/",
                "{} private-key marker in an opaque artifact".format(marker_label),
                errors,
            )
        marker_file.unlink()

    partial_private_key_root = temporary / "partial-private-key-root"
    partial_private_key_run = prepare_run(
        skill,
        partial_private_key_root,
        "Model",
        "Harness",
        "Partial Private Key Leak",
        prompt,
        errors,
    )
    if partial_private_key_run is not None:
        (partial_private_key_run / "artifact" / "id_rsa").write_text(
            "fixture without key material\n",
            encoding="utf-8",
        )
        assert_invalid_catalog(
            validator,
            partial_private_key_root,
            "private key material must stay in workspace/",
            "private key in a planned artifact without index.html",
            errors,
        )

    worker_identity_root = temporary / "worker-identity-root"
    worker_identity_run = prepare_run(
        skill,
        worker_identity_root,
        "Model",
        "Harness",
        "Worker Identity",
        prompt,
        errors,
    )
    if worker_identity_run is not None:
        worker_manifest_path = worker_identity_run / "run.json"
        worker_report_path = worker_identity_run / "worker-report.json"
        worker_manifest = json.loads(worker_manifest_path.read_text(encoding="utf-8"))
        worker_report = json.loads(worker_report_path.read_text(encoding="utf-8"))
        worker_manifest["execution"]["leadWorkerId"] = "lead-a"
        worker_manifest["execution"]["descendantWorkerIds"] = ["child-a"]
        worker_manifest_path.write_text(json.dumps(worker_manifest), encoding="utf-8")
        mismatch_build = rebuild_catalog_index(worker_identity_root)
        mismatch_validation = run([sys.executable, str(validator), str(worker_identity_root)])
        mismatch_html = (worker_identity_root / "index.html").read_text(encoding="utf-8")
        assert_ok(
            mismatch_build.returncode == 0
            and mismatch_validation.returncode != 0
            and "worker IDs must exactly match" in mismatch_validation.stdout
            and "Worker metadata mismatch" in mismatch_html,
            "worker identity disagreement escaped validation or produced a misleading index",
            errors,
        )

        worker_report["leadWorkerId"] = "lead-a"
        worker_report["descendantWorkerIds"] = ["child-a"]
        worker_report_path.write_text(json.dumps(worker_report), encoding="utf-8")
        matching_build = rebuild_catalog_index(worker_identity_root)
        matching_validation = run([sys.executable, str(validator), str(worker_identity_root)])
        assert_ok(
            matching_build.returncode == 0 and matching_validation.returncode == 0,
            "validator rejected matching worker identities: {}".format(matching_validation.stdout),
            errors,
        )

        worker_manifest["execution"]["descendantWorkerIds"] = ["child-a", "child-a"]
        worker_report["descendantWorkerIds"] = ["child-a", "child-a"]
        worker_manifest_path.write_text(json.dumps(worker_manifest), encoding="utf-8")
        worker_report_path.write_text(json.dumps(worker_report), encoding="utf-8")
        duplicate_worker_build = rebuild_catalog_index(worker_identity_root)
        duplicate_worker_validation = run([sys.executable, str(validator), str(worker_identity_root)])
        assert_ok(
            duplicate_worker_build.returncode == 0
            and duplicate_worker_validation.returncode != 0
            and "descendantWorkerIds must contain unique IDs" in duplicate_worker_validation.stdout,
            "validator accepted duplicate descendant worker IDs",
            errors,
        )

        worker_manifest["execution"]["descendantWorkerIds"] = ["child-a"]
        worker_report["descendantWorkerIds"] = ["child-a"]
        worker_report["leadWorkerId"] = "lead-b"
        worker_manifest_path.write_text(json.dumps(worker_manifest), encoding="utf-8")
        worker_report_path.write_text(json.dumps(worker_report), encoding="utf-8")
        lead_mismatch_build = rebuild_catalog_index(worker_identity_root)
        lead_mismatch_validation = run([sys.executable, str(validator), str(worker_identity_root)])
        assert_ok(
            lead_mismatch_build.returncode == 0
            and lead_mismatch_validation.returncode != 0
            and "worker IDs must exactly match" in lead_mismatch_validation.stdout,
            "validator accepted mismatched lead worker IDs",
            errors,
        )

    filtered_root = temporary / "filtered-root"
    filtered_run = prepare_run(skill, filtered_root, "Model", "Harness", "Filtered", prompt, errors)
    if filtered_run is not None:
        mark_successful_static_artifact(filtered_run)
        next_asset = filtered_run / "artifact" / ".next" / "static"
        next_asset.mkdir(parents=True)
        (next_asset / "app.js").write_text("console.log('built')\n", encoding="utf-8")
        (filtered_run / "artifact" / "index.html").write_text(
            "<!doctype html><script src=\".next/static/app.js\"></script>",
            encoding="utf-8",
        )
        assert_invalid_catalog(validator, filtered_root, "cache, provider state, or dependency", "Vercel-filtered .next output", errors)

    static_route_root = temporary / "static-route-root"
    static_route_run = prepare_run(skill, static_route_root, "Model", "Harness", "Static API Route", prompt, errors)
    if static_route_run is not None:
        mark_successful_static_artifact(static_route_run)
        artifact = static_route_run / "artifact"
        api_directory = artifact / "api"
        api_directory.mkdir()
        (api_directory / "index.html").write_text(
            "<!doctype html><title>Static API documentation</title>\n",
            encoding="utf-8",
        )
        (api_directory / "private-key-guide.js").write_text(
            'const privateKeyField = "privateKey";\n'
            'const apiKeyRoute = "/api/private-key-help";\n'
            'const publicKeyHeader = "-----BEGIN PUBLIC KEY-----";\n'
            'const certificateHeader = "-----BEGIN CERTIFICATE-----";\n',
            encoding="utf-8",
        )
        (artifact / "index.html").write_text(
            "<!doctype html><a href=\"api/\">API documentation</a>"
            "<script src=\"api/private-key-guide.js\"></script>\n",
            encoding="utf-8",
        )
        static_route = run([sys.executable, str(validator), str(static_route_root)])
        assert_ok(
            static_route.returncode == 0,
            "validator rejected a harmless static api/ route or private-key prose sample: {}".format(static_route.stdout),
            errors,
        )

    evidence_root = temporary / "evidence-root"
    evidence_run = prepare_run(skill, evidence_root, "Model", "Harness", "Evidence", prompt, errors)
    if evidence_run is not None:
        mark_successful_static_artifact(evidence_run)
        report_path = evidence_run / "worker-report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["verification"] = []
        report_path.write_text(json.dumps(report), encoding="utf-8")
        assert_invalid_catalog(validator, evidence_root, "structured passed verification evidence", "unverified OK artifact", errors)
        report["verification"] = [
            {"kind": "static-browser-smoke", "result": "failed", "evidence": "Browser did not load"}
        ]
        report_path.write_text(json.dumps(report), encoding="utf-8")
        assert_invalid_catalog(validator, evidence_root, "structured passed verification evidence", "failed OK evidence", errors)
        report["verification"] = [
            {"kind": "file-exists", "result": "passed", "evidence": "index.html exists"},
            {"kind": "static-browser-smoke", "result": "failed", "evidence": "Root page did not render"},
        ]
        report_path.write_text(json.dumps(report), encoding="utf-8")
        assert_invalid_catalog(validator, evidence_root, "must not contain failed verification evidence", "mixed failed OK evidence", errors)

    gauntlet_root = temporary / "gauntlet-root"
    gauntlet_run = prepare_run(
        skill,
        gauntlet_root,
        "Model",
        "Harness",
        "Gauntlet History",
        prompt,
        errors,
    )
    if gauntlet_run is not None:
        mark_successful_static_artifact(gauntlet_run)
        manifest_path = gauntlet_run / "run.json"
        report_path = gauntlet_run / "worker-report.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        critic_ids = ["critic-before", "critic-after"]
        manifest["execution"]["descendantWorkerIds"] = critic_ids
        report["descendantWorkerIds"] = critic_ids
        report["qualityGauntlet"] = {
            "applicability": "required",
            "notRequiredReason": None,
            "bar": "The rendered route transition matches the supplied walkthrough at the reference viewport.",
            "referenceProvenance": ["supplied museum walkthrough"],
            "barValidation": {
                "result": "accepted",
                "evidence": "Fresh critic confirmed the bar covers the prompt's transition requirement.",
            },
            "barRevisions": [],
            "freshCriticAvailable": True,
            "rounds": [
                {
                    "criticWorkerId": "critic-before",
                    "artifactRevision": "sha256:before-fix",
                    "verdict": "NOT_READY",
                    "inspected": "artifact/index.html route from lobby to gallery",
                    "evidence": "The built transition cuts before the reference camera settles.",
                    "highestLeverageGap": "Match the reference transition timing and camera settle.",
                    "fix": "Adjusted transition duration and camera easing.",
                    "recheck": "Replay the same route at the reference viewport.",
                },
                {
                    "criticWorkerId": "critic-after",
                    "artifactRevision": "sha256:after-fix",
                    "verdict": "READY",
                    "inspected": "artifact/index.html route from lobby to gallery",
                    "evidence": "The replay matches the reference timing and final camera state.",
                    "highestLeverageGap": None,
                    "fix": None,
                    "recheck": "Replay remained stable across three isolated sessions.",
                },
            ],
            "integrationPass": {
                "required": False,
                "result": "not-required",
                "evidence": "One sequential owner changed the coupled transition.",
            },
            "fallbackEvidence": None,
            "stopReason": "bar-met",
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        report_path.write_text(json.dumps(report), encoding="utf-8")
        gauntlet_build = rebuild_catalog_index(gauntlet_root)
        gauntlet_validation = run([sys.executable, str(validator), str(gauntlet_root)])
        assert_ok(
            gauntlet_build.returncode == 0 and gauntlet_validation.returncode == 0,
            "validator rejected honest NOT_READY-to-READY gauntlet history: {}".format(
                gauntlet_validation.stdout
            ),
            errors,
        )

        report["qualityGauntlet"]["rounds"][1].pop("artifactRevision")
        report_path.write_text(json.dumps(report), encoding="utf-8")
        assert_invalid_catalog(
            validator,
            gauntlet_root,
            "artifactRevision must be a non-blank string",
            "critic round without artifact revision",
            errors,
        )

        report["qualityGauntlet"]["rounds"][1]["artifactRevision"] = "sha256:after-fix"
        report["qualityGauntlet"]["barValidation"] = {"result": None, "evidence": None}
        report_path.write_text(json.dumps(report), encoding="utf-8")
        assert_invalid_catalog(
            validator,
            gauntlet_root,
            "must record barValidation.result",
            "required gauntlet without independent bar validation",
            errors,
        )

        report["qualityGauntlet"]["barValidation"] = {
            "result": "revised",
            "evidence": "The first proposed bar was materially weaker than the prompt.",
        }
        report["qualityGauntlet"]["barRevisions"] = []
        report_path.write_text(json.dumps(report), encoding="utf-8")
        assert_invalid_catalog(
            validator,
            gauntlet_root,
            "revised quality bar must record barRevisions",
            "revised gauntlet bar without revision provenance",
            errors,
        )

        report["qualityGauntlet"] = {
            "applicability": "not-required",
            "notRequiredReason": None,
            "bar": None,
            "referenceProvenance": [],
            "barValidation": {"result": None, "evidence": None},
            "barRevisions": [],
            "freshCriticAvailable": None,
            "rounds": [],
            "integrationPass": {
                "required": False,
                "result": "not-required",
                "evidence": "No merged workstreams.",
            },
            "fallbackEvidence": None,
            "stopReason": "not-required",
        }
        report_path.write_text(json.dumps(report), encoding="utf-8")
        assert_invalid_catalog(
            validator,
            gauntlet_root,
            "must record a concrete reason",
            "not-required gauntlet without applicability reason",
            errors,
        )

    size_root = temporary / "size-root"
    size_run = prepare_run(skill, size_root, "Model", "Harness", "Size", prompt, errors)
    if size_run is not None:
        mark_successful_static_artifact(size_run)
        with (size_run / "artifact" / "oversized.bin").open("wb") as handle:
            handle.truncate(5 * 1024 * 1024 + 1)
        assert_invalid_catalog(validator, size_root, "exceeds the conservative 5 MiB", "oversized drop artifact", errors)

    unreadable_root = temporary / "unreadable-root"
    unreadable_run = prepare_run(skill, unreadable_root, "Model", "Harness", "Unreadable", prompt, errors)
    if unreadable_run is not None and os.name == "posix":
        mark_successful_static_artifact(unreadable_run)
        unreadable_asset = unreadable_run / "artifact" / "unreadable.bin"
        unreadable_asset.write_bytes(b"fixture")
        os.chmod(unreadable_asset, 0o000)
        assert_invalid_catalog(validator, unreadable_root, "readable file mode", "unreadable artifact file", errors)
        os.chmod(unreadable_asset, 0o644)

        unreadable_directory = unreadable_run / "artifact" / "closed"
        unreadable_directory.mkdir()
        (unreadable_directory / "hidden.bin").write_bytes(b"hidden")
        os.chmod(unreadable_directory, 0o000)
        assert_invalid_catalog(
            validator,
            unreadable_root,
            "readable and traversable mode",
            "unreadable artifact directory",
            errors,
        )
        os.chmod(unreadable_directory, 0o700)

    symlink_root = temporary / "symlink-root"
    symlink_run = prepare_run(skill, symlink_root, "Model", "Harness", "Symlink", prompt, errors)
    if symlink_run is not None:
        manifest_path = symlink_run / "run.json"
        escaped_manifest = temporary / "escaped-run.json"
        manifest_path.replace(escaped_manifest)
        try:
            manifest_path.symlink_to(escaped_manifest)
        except OSError:
            pass
        else:
            assert_invalid_catalog(validator, symlink_root, "missing exact-case regular run.json", "symlinked run manifest", errors)

    namespace_visibility_root = temporary / "namespace-visibility-root"
    namespace_visibility_run = prepare_run(
        skill,
        namespace_visibility_root,
        "Model",
        "Harness",
        "Visible Run",
        prompt,
        errors,
    )
    if namespace_visibility_run is not None and os.name == "posix":
        closed_model = namespace_visibility_root / "closed-model"
        hidden_run = closed_model / "harness" / "experiment" / "run"
        hidden_run.mkdir(parents=True)
        (hidden_run / "run.json").write_text("{}\n", encoding="utf-8")
        os.chmod(closed_model, 0o000)
        assert_invalid_catalog(
            validator,
            namespace_visibility_root,
            "namespace directory must have a readable and traversable mode",
            "unreadable top-level namespace",
            errors,
        )
        os.chmod(closed_model, 0o700)

    builder_symlink_root = temporary / "builder-symlink-root"
    builder_symlink_run = prepare_run(skill, builder_symlink_root, "Model", "Harness", "Visible", prompt, errors)
    if builder_symlink_run is not None:
        outside_builder_model = temporary / "outside-builder-model"
        outside_builder_run = outside_builder_model / "harness" / "experiment" / "run"
        outside_builder_run.mkdir(parents=True)
        (outside_builder_run / "run.json").write_text("{}\n", encoding="utf-8")
        try:
            (builder_symlink_root / "linked-model").symlink_to(outside_builder_model, target_is_directory=True)
        except OSError:
            pass
        else:
            linked_build = rebuild_catalog_index(builder_symlink_root)
            assert_ok(
                linked_build.returncode != 0 and "symbolic links" in linked_build.stderr,
                "catalogue builder followed a symlinked namespace outside the output root",
                errors,
            )

    inventory_root = temporary / "inventory-root"
    kept_run = prepare_run(skill, inventory_root, "Model", "Harness", "Kept", prompt, errors)
    removed_run = prepare_run(skill, inventory_root, "Model", "Harness", "Removed", prompt, errors)
    if kept_run is not None and removed_run is not None:
        removed_run.rename(temporary / "detached-run")
        assert_invalid_catalog(validator, inventory_root, "orphan provenance receipt", "erased run outcome", errors)

    unreadable_receipts_root = temporary / "unreadable-receipts-root"
    unreadable_receipts_run = prepare_run(
        skill,
        unreadable_receipts_root,
        "Model",
        "Harness",
        "Unreadable Receipts",
        prompt,
        errors,
    )
    if unreadable_receipts_run is not None:
        receipt_directory = unreadable_receipts_root / ".oneshot-provenance"

        real_iterdir = Path.iterdir

        def injected_iterdir(path: Path) -> Iterator[Path]:
            if path == receipt_directory:
                raise PermissionError("injected provenance inventory failure")
            return real_iterdir(path)

        with patch.object(Path, "iterdir", injected_iterdir):
            unreadable_receipts = catalog_validator.validate(unreadable_receipts_root)
        assert_ok(
            unreadable_receipts.get("valid") is False
            and any(
                "unable to inspect provenance inventory" in message
                for message in unreadable_receipts.get("errors", [])
                if isinstance(message, str)
            ),
            "validator did not classify an unreadable provenance inventory: {}".format(
                json.dumps(unreadable_receipts, sort_keys=True)
            ),
            errors,
        )

    namespace_root = temporary / "namespace-root"
    namespace_run = prepare_run(skill, namespace_root, "Model", "Harness", "Namespace", prompt, errors)
    if namespace_run is not None:
        rogue = namespace_root / "rogue"
        rogue.mkdir()
        (rogue / "run.json").write_text("{}\n", encoding="utf-8")
        assert_invalid_catalog(validator, namespace_root, "outside a timestamped or legacy run directory", "wrong-depth run manifest", errors)

    missing_manifest_root = temporary / "missing-manifest-root"
    missing_manifest_run = prepare_run(skill, missing_manifest_root, "Model", "Harness", "Kept Run", prompt, errors)
    if missing_manifest_run is not None:
        incomplete = missing_manifest_root / "stray-model" / "stray-harness" / "stray-experiment" / "stray-run"
        (incomplete / "artifact").mkdir(parents=True)
        assert_invalid_catalog(validator, missing_manifest_root, "missing exact-case regular run.json", "depth-four run without manifest", errors)

    worker_damage_root = temporary / "worker-damage-root"
    worker_damage_run = prepare_run(skill, worker_damage_root, "Model", "Harness", "Worker Damage", prompt, errors)
    if worker_damage_run is not None:
        experiment_directory = worker_damage_run.parent
        damaged_run = reserve_paths(experiment_directory, make_run_id("Damaged Run")).run
        damaged_run_id = damaged_run.name
        (damaged_run / "artifact").mkdir(parents=True)
        (damaged_run / "artifact" / "unexpected.txt").write_text("worker residue\n", encoding="utf-8")
        damaged_build = rebuild_catalog_index(worker_damage_root)
        damaged_html = (
            (worker_damage_root / "index.html").read_text(encoding="utf-8")
            if damaged_build.returncode == 0
            else ""
        )
        assert_ok(
            damaged_build.returncode == 0
            and damaged_run_id in damaged_html
            and ">INVALID<" in damaged_html
            and "run directory is missing exact-case run.json" in damaged_html
            and damaged_html.count("Unavailable") >= 2,
            "one manifestless worker run prevented or disappeared from sibling catalogue indexing",
            errors,
        )
        assert_invalid_catalog(
            validator,
            worker_damage_root,
            "missing exact-case regular run.json",
            "manifestless exact-UUID worker run",
            errors,
        )

        malformed_variants: List[Path] = []
        directory_manifest_run = reserve_paths(experiment_directory, make_run_id("Directory Manifest")).run
        (directory_manifest_run / "run.json").mkdir()
        malformed_variants.append(directory_manifest_run)
        if os.name == "posix":
            fifo_manifest_run = reserve_paths(experiment_directory, make_run_id("FIFO Manifest")).run
            os.mkfifo(fifo_manifest_run / "run.json")
            malformed_variants.append(fifo_manifest_run)
            unreadable_manifest_run = reserve_paths(experiment_directory, make_run_id("Unreadable Manifest")).run
            (unreadable_manifest_run / "run.json").write_text("{}\n", encoding="utf-8")
            os.chmod(unreadable_manifest_run / "run.json", 0o000)
            malformed_variants.append(unreadable_manifest_run)
            unreadable_run_directory = reserve_paths(experiment_directory, make_run_id("Unreadable Run")).run
            os.chmod(unreadable_run_directory, 0o000)
            malformed_variants.append(unreadable_run_directory)
        for malformed_variant in malformed_variants:
            (worker_damage_root / ".oneshot-provenance" / (malformed_variant.name + ".commit")).write_bytes(b"")
        isolated_build = rebuild_catalog_index(worker_damage_root)
        isolated_html = (
            (worker_damage_root / "index.html").read_text(encoding="utf-8")
            if isolated_build.returncode == 0
            else ""
        )
        assert_ok(
            isolated_build.returncode == 0
            and all(path.name in isolated_html for path in malformed_variants)
            and isolated_html.count(">INVALID<") >= len(malformed_variants) + 1,
            "a non-regular or unreadable worker manifest aborted sibling catalogue indexing",
            errors,
        )
        if os.name == "posix":
            os.chmod(unreadable_manifest_run / "run.json", 0o600)
            os.chmod(unreadable_run_directory, 0o700)

    malformed_root = temporary / "malformed-root"
    malformed_run = prepare_run(skill, malformed_root, "Model", "Harness", "Malformed", prompt, errors)
    if malformed_run is not None:
        (malformed_run / "run.json").write_bytes(b"{\xff}")
        assert_invalid_catalog(validator, malformed_root, "invalid JSON", "invalid UTF-8 run manifest", errors)
        malformed_build = run(
            [
                sys.executable,
                str(skill / "scripts" / "build_catalog_index.py"),
                "--root",
                str(malformed_root),
                "--out",
                str(malformed_root / "index.html"),
            ]
        )
        assert_ok(malformed_build.returncode == 0, "catalogue builder crashed on invalid UTF-8 metadata", errors)

    duplicate_json_root = temporary / "duplicate-json-root"
    duplicate_run = prepare_run(skill, duplicate_json_root, "Model", "Harness", "Duplicate Run", prompt, errors)
    duplicate_report = prepare_run(skill, duplicate_json_root, "Model", "Harness", "Duplicate Report", prompt, errors)
    duplicate_receipt = prepare_run(skill, duplicate_json_root, "Model", "Harness", "Duplicate Receipt", prompt, errors)
    if duplicate_run is not None and duplicate_report is not None and duplicate_receipt is not None:
        duplicate_run_path = duplicate_run / "run.json"
        duplicate_report_path = duplicate_report / "worker-report.json"
        duplicate_receipt_path = duplicate_json_root / ".oneshot-provenance" / (duplicate_receipt.name + ".json")
        duplicate_run_path.write_text('{"schemaVersion":"2.0","schemaVersion":"3.0"}', encoding="utf-8")
        duplicate_report_path.write_text('{"status":"PLANNED","status":"OK"}', encoding="utf-8")
        duplicate_receipt_path.write_text('{"schemaVersion":"1.0","schemaVersion":"2.0"}', encoding="utf-8")
        duplicate_build = rebuild_catalog_index(duplicate_json_root)
        duplicate_validation = run([sys.executable, str(validator), str(duplicate_json_root)])
        duplicate_diagnostics = duplicate_validation.stdout
        assert_ok(
            duplicate_build.returncode == 0
            and duplicate_validation.returncode != 0
            and all(
                "{}: invalid JSON: duplicate JSON object member:".format(path) in duplicate_diagnostics
                for path in (duplicate_run_path, duplicate_report_path, duplicate_receipt_path)
            )
            and "Traceback" not in duplicate_validation.stderr,
            "duplicate JSON members escaped provenance, run, or report parsing",
            errors,
        )

    structured_schema_root = temporary / "structured-schema-root"
    structured_schema_run = prepare_run(
        skill,
        structured_schema_root,
        "Model",
        "Harness",
        "Structured Schema",
        prompt,
        errors,
    )
    if structured_schema_run is not None:
        structured_manifest_path = structured_schema_run / "run.json"
        structured_receipt_path = (
            structured_schema_root / ".oneshot-provenance" / f"{structured_schema_run.name}.json"
        )
        structured_manifest = json.loads(structured_manifest_path.read_text(encoding="utf-8"))
        structured_receipt = json.loads(structured_receipt_path.read_text(encoding="utf-8"))
        structured_manifest["schemaVersion"] = []
        structured_receipt["schemaVersion"] = {"unexpected": True}
        structured_manifest_path.write_text(
            json.dumps(structured_manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        structured_receipt_path.write_text(
            json.dumps(structured_receipt, indent=2) + "\n",
            encoding="utf-8",
        )
        structured_build = rebuild_catalog_index(structured_schema_root)
        structured_validation = run([sys.executable, str(validator), str(structured_schema_root)])
        assert_ok(
            structured_build.returncode == 0
            and structured_validation.returncode != 0
            and "flat run schemaVersion must be one of" in structured_validation.stdout
            and "schemaVersion must be 1.0, 1.1, 2.0, 2.1, or 2.2" in structured_validation.stdout
            and "Traceback" not in structured_validation.stderr,
            "structured schema versions escaped validation or caused a crash: {}{}".format(
                structured_validation.stdout,
                structured_validation.stderr,
            ),
            errors,
        )

    recursive_json_root = temporary / "recursive-json-root"
    recursive_json_run = prepare_run(skill, recursive_json_root, "Model", "Harness", "Recursive JSON", prompt, errors)
    if recursive_json_run is not None:
        nested_json = '{"value":' * 300 + "0" + "}" * 300
        (recursive_json_run / "worker-report.json").write_text(nested_json, encoding="utf-8")
        recursive_build = rebuild_catalog_index(recursive_json_root)
        recursive_validation = run([sys.executable, str(validator), str(recursive_json_root)])
        assert_ok(
            recursive_build.returncode == 0
            and recursive_validation.returncode != 0
            and "invalid JSON" in recursive_validation.stdout
            and "Traceback" not in recursive_validation.stderr,
            "deeply nested bounded JSON crashed or escaped metadata validation",
            errors,
        )

    numeric_json_root = temporary / "numeric-json-root"
    numeric_json_run = prepare_run(skill, numeric_json_root, "Model", "Harness", "Numeric JSON", prompt, errors)
    if numeric_json_run is not None:
        oversized_integer_json = '{"status":' + "9" * 100_000 + "}"
        (numeric_json_run / "worker-report.json").write_text(oversized_integer_json, encoding="utf-8")
        numeric_build = rebuild_catalog_index(numeric_json_root)
        numeric_validation = run([sys.executable, str(validator), str(numeric_json_root)])
        numeric_html = (
            (numeric_json_root / "index.html").read_text(encoding="utf-8")
            if numeric_build.returncode == 0
            else ""
        )
        assert_ok(
            numeric_build.returncode == 0
            and "Report unavailable: metadata is not valid JSON" in numeric_html
            and numeric_validation.returncode != 0
            and "invalid JSON" in numeric_validation.stdout
            and "Traceback" not in numeric_validation.stderr,
            "oversized integer JSON escaped the shared bounded parser",
            errors,
        )

    repeated_reference_root = temporary / "repeated-reference-root"
    repeated_reference_run = prepare_run(
        skill,
        repeated_reference_root,
        "Model",
        "Harness",
        "Repeated References",
        prompt,
        errors,
    )
    if repeated_reference_run is not None:
        mark_successful_static_artifact(repeated_reference_run)
        repeated_markup = "<img src=\"missing.png\">" * 25_000
        (repeated_reference_run / "artifact" / "index.html").write_text(
            "<!doctype html><title>Repeated</title>" + repeated_markup,
            encoding="utf-8",
        )
        repeated_validation = run([sys.executable, str(validator), str(repeated_reference_root)])
        assert_ok(
            repeated_validation.returncode != 0
            and repeated_validation.stdout.count("referenced local file missing") == 1
            and len(repeated_validation.stdout) < 50_000
            and "Traceback" not in repeated_validation.stderr,
            "repeated local references amplified validator diagnostics",
            errors,
        )

    large_display_root = temporary / "large-display-root"
    large_display_runs: List[Path] = []
    for index in range(7):
        prepared = prepare_run(
            skill,
            large_display_root,
            "Model",
            "Harness",
            "Large Display {}".format(index),
            prompt,
            errors,
        )
        if prepared is not None:
            large_display_runs.append(prepared)
    if len(large_display_runs) == 7:
        for index, prepared in enumerate(large_display_runs):
            report_path = prepared / "worker-report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["summary"] = "{}:".format(index) + "x" * 800_000
            report_path.write_text(json.dumps(report), encoding="utf-8")
        large_display_build = rebuild_catalog_index(large_display_root)
        large_display_validation = run([sys.executable, str(validator), str(large_display_root)])
        large_display_size = (
            (large_display_root / "index.html").stat().st_size
            if large_display_build.returncode == 0
            else 0
        )
        assert_ok(
            large_display_build.returncode == 0
            and large_display_validation.returncode == 0
            and large_display_size <= 5 * 1024 * 1024,
            "worker-controlled display text produced a root catalogue the validator rejects",
            errors,
        )

    surrogate_root = temporary / "surrogate-root"
    surrogate_run = prepare_run(skill, surrogate_root, "Model", "Harness", "Surrogate", prompt, errors)
    if surrogate_run is not None:
        manifest_path = surrogate_run / "run.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["identity"]["model"]["name"] = "\ud800"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        assert_invalid_catalog(validator, surrogate_root, "must be valid UTF-8 text", "surrogate identity name", errors)
        surrogate_build = run(
            [
                sys.executable,
                str(skill / "scripts" / "build_catalog_index.py"),
                "--root",
                str(surrogate_root),
                "--out",
                str(surrogate_root / "index.html"),
            ]
        )
        assert_ok(surrogate_build.returncode == 0, "catalogue builder crashed on a surrogate identity", errors)

    css_chain_root = temporary / "css-chain-root"
    css_chain_run = prepare_run(skill, css_chain_root, "Model", "Harness", "CSS Chain", prompt, errors)
    if css_chain_run is not None:
        mark_successful_static_artifact(css_chain_run)
        artifact = css_chain_run / "artifact"
        (artifact / "assets" / "site.css").unlink()
        for index in range(998):
            content = "@import '{}.css';\n".format(index + 1) if index < 997 else "body { color: #17302c; }\n"
            (artifact / "{}.css".format(index)).write_text(content, encoding="utf-8")
        (artifact / "index.html").write_text(
            "<!doctype html><link rel=\"stylesheet\" href=\"0.css\"><main>Deep CSS chain</main>",
            encoding="utf-8",
        )
        chain_validation = run([sys.executable, str(validator), str(css_chain_root)])
        assert_ok(
            chain_validation.returncode == 0,
            "validator failed at the exact 1,000-file deep-CSS boundary: {}".format(chain_validation.stdout),
            errors,
        )
        (artifact / "overflow.css").write_text("body{}\n", encoding="utf-8")
        assert_invalid_catalog(validator, css_chain_root, "folder-drop limit is 1000", "1,001-file artifact", errors)

    total_root = temporary / "total-root"
    total_run = prepare_run(skill, total_root, "Model", "Harness", "Total Size", prompt, errors)
    if total_run is not None:
        mark_successful_static_artifact(total_run)
        artifact = total_run / "artifact"
        current_total = sum(path.stat().st_size for path in artifact.rglob("*") if path.is_file())
        remaining = 100 * 1024 * 1024 - current_total
        part = 0
        while remaining > 0:
            size = min(5 * 1024 * 1024, remaining)
            with (artifact / "total-{:02d}.bin".format(part)).open("wb") as handle:
                handle.truncate(size)
            remaining -= size
            part += 1
        exact_total = run([sys.executable, str(validator), str(total_root)])
        assert_ok(exact_total.returncode == 0, "validator rejected the exact 100 MiB boundary", errors)
        with (artifact / "total-overflow.bin").open("wb") as handle:
            handle.truncate(1)
        assert_invalid_catalog(validator, total_root, "exceeds the conservative 100 MiB", "100 MiB plus one byte", errors)


def exercise_runtime_scripts(skill: Path, errors: List[str]) -> None:
    scripts = (
        skill / "scripts" / "list_prompts.py",
        skill / "scripts" / "prepare_run.py",
        skill / "scripts" / "build_catalog_index.py",
        skill / "scripts" / "validate_catalog.py",
    )
    if not all(path.is_file() for path in scripts):
        return

    valid_unicode_samples = (
        "— – ‘single’ “double” … café naïve façade",
        "orð— orð” é",
        "日本語 العربية 🚀",
    )
    for sample in valid_unicode_samples:
        assert_ok(
            find_likely_mojibake(sample) is None,
            "mojibake detector rejected valid Unicode: {!r}".format(sample),
            errors,
        )
    corrupted_samples = (
        "â€”",
        "Cinnamonâ€™s",
        "cafÃ©",
        "ðŸš€",
        "replacement \ufffd",
        "stray control \u0081",
    )
    for sample in corrupted_samples:
        assert_ok(
            find_likely_mojibake(sample) is not None,
            "mojibake detector missed a known corruption signature: {!r}".format(sample),
            errors,
        )

    catalogue = read_json(skill / "assets" / "prompt-catalogue.json", errors, "prompt catalogue")
    prompts = catalogue.get("prompts") if isinstance(catalogue, Mapping) else None
    categories = catalogue.get("categories") if isinstance(catalogue, Mapping) else None
    experience_direction = catalogue.get("experienceDirection") if isinstance(catalogue, Mapping) else None
    completion_mandate = catalogue.get("completionMandate") if isinstance(catalogue, Mapping) else None
    if (
        not isinstance(prompts, list)
        or not prompts
        or not isinstance(categories, list)
        or not isinstance(experience_direction, str)
        or not isinstance(completion_mandate, str)
    ):
        return
    first = prompts[0] if isinstance(prompts[0], Mapping) else {}
    first_id = first.get("id")
    query = (first.get("tags") or [first.get("slug")])[0] if isinstance(first, Mapping) else ""

    full_listing = run([sys.executable, str(scripts[0])])
    assert_ok(full_listing.returncode == 0, "list_prompts.py full listing failed: {}".format(full_listing.stderr), errors)
    expected_ids = [item.get("id") for item in prompts if isinstance(item, Mapping) and isinstance(item.get("id"), str)]
    assert_ok(
        len(expected_ids) == len(prompts) and all(full_listing.stdout.count("`{}`".format(prompt_id)) == 1 for prompt_id in expected_ids),
        "no-arg catalogue presentation did not include every prompt ID exactly once",
        errors,
    )
    assert_ok(
        "{} prompt(s), grouped by namespace".format(len(prompts)) in full_listing.stdout,
        "no-arg catalogue presentation reported the wrong prompt count",
        errors,
    )
    assert_ok(
        experience_direction not in full_listing.stdout,
        "no-arg catalogue presentation exposed coordinator-only prompt-crafting guidance",
        errors,
    )
    assert_ok(
        completion_mandate not in full_listing.stdout,
        "no-arg catalogue presentation exposed internal prompt-composition metadata",
        errors,
    )
    assert_ok(
        all(
            isinstance(category, Mapping)
            and full_listing.stdout.count(
                "## Namespace `{}` — {}".format(category.get("id"), category.get("title"))
            )
            == 1
            and full_listing.stdout.count(str(category.get("description"))) == 1
            for category in categories
        ),
        "no-arg catalogue presentation did not explain every namespace exactly once",
        errors,
    )
    expected_option_lines = [
        "- **{}** — {} — `{}` · `{}`".format(
            item.get("title"),
            re.sub(r"\s+", " ", str(item.get("description"))).strip(),
            item.get("id"),
            item.get("slug"),
        )
        for item in prompts
        if isinstance(item, Mapping)
    ]
    output_lines = full_listing.stdout.splitlines()
    assert_ok(
        len(expected_option_lines) == len(prompts)
        and all(output_lines.count(option_line) == 1 for option_line in expected_option_lines),
        "no-arg catalogue presentation did not render every prompt as one explained option line",
        errors,
    )
    shooter = next(
        (
            item
            for item in prompts
            if isinstance(item, Mapping) and item.get("id") == "ow-093"
        ),
        None,
    )
    assert_ok(
        isinstance(shooter, Mapping)
        and shooter.get("title") == "First-Person Shooter Game"
        and "**First-Person Shooter Game**" in full_listing.stdout,
        "catalogue did not keep the first-person shooter option plain and literal",
        errors,
    )
    if isinstance(first, Mapping):
        first_description = first.get("description")
        first_prompt = first.get("prompt")
        assert_ok(
            isinstance(first_description, str)
            and first_description in full_listing.stdout
            and isinstance(first_prompt, str)
            and first_prompt not in full_listing.stdout,
            "catalogue listing did not separate scan-friendly descriptions from source prompts",
            errors,
        )
    json_listing = run([sys.executable, str(scripts[0]), "--format", "json"])
    json_data = invocation_json(json_listing, errors, "list_prompts.py --format json")
    if json_data is not None:
        grouped = json_data.get("categories")
        listed_prompts = (
            [item for group in grouped if isinstance(group, Mapping) for item in group.get("prompts", [])]
            if isinstance(grouped, list)
            else []
        )
        assert_ok(
            json_data.get("count") == len(prompts)
            and json_data.get("experienceDirection") == experience_direction
            and json_data.get("completionMandate") == completion_mandate
            and listed_prompts == prompts,
            "JSON catalogue listing differs from canonical prompts",
            errors,
        )
    if isinstance(query, str) and query:
        search = run([sys.executable, str(scripts[0]), "--search", query, "--format", "markdown"])
        assert_ok(search.returncode == 0, "list_prompts.py search failed: {}".format(search.stderr), errors)
        if isinstance(first_id, str):
            assert_ok(first_id in search.stdout, "catalogue search did not return its matching prompt", errors)

    with tempfile.TemporaryDirectory() as temporary:
        output_root = Path(temporary) / "runs"
        prompt = Path(temporary) / "prompt.md"
        prompt_bytes = (
            "Create a richly interactive harbour weather station — warm, tactile, and precise.\r\n"
            "Preserve curly quotes like “forecast” and apostrophes like Cinnamon’s, plus emoji 🚀, "
            "words like café, naïve, and façade, decomposed accents like é, Icelandic orð— and orð”, "
            "日本語, and العربية.\n"
        ).encode("utf-8")
        prompt.write_bytes(prompt_bytes)

        mojibake_prompt = Path(temporary) / "mojibake-prompt.md"
        mojibake_prompt.write_text(
            "Create a Linux Mint desktop â€” faithful down to Cinnamonâ€™s smallest interactions.\n",
            encoding="utf-8",
        )
        rejected_root = Path(temporary) / "rejected-mojibake-run"
        rejected_mojibake = run(
            [
                sys.executable,
                str(scripts[1]),
                "--output-root",
                str(rejected_root),
                "--model",
                "Model",
                "--harness",
                "Harness",
                "--experiment",
                "Mojibake Regression",
                "--prompt-file",
                str(mojibake_prompt),
            ]
        )
        assert_ok(
            rejected_mojibake.returncode != 0
            and "likely mojibake" in rejected_mojibake.stderr
            and "correct the prepared prompt at its source" in rejected_mojibake.stderr
            and not rejected_root.exists(),
            "prepare_run.py accepted or partially reserved a mojibake prompt: {}".format(
                rejected_mojibake.stderr
            ),
            errors,
        )

        invalid_utf8_prompt = Path(temporary) / "invalid-utf8-prompt.md"
        invalid_utf8_prompt.write_bytes(b"Create a desktop \xff\n")
        invalid_utf8_root = Path(temporary) / "rejected-invalid-utf8-run"
        rejected_invalid_utf8 = run(
            [
                sys.executable,
                str(scripts[1]),
                "--output-root",
                str(invalid_utf8_root),
                "--model",
                "Model",
                "--harness",
                "Harness",
                "--experiment",
                "Invalid UTF-8 Regression",
                "--prompt-file",
                str(invalid_utf8_prompt),
            ]
        )
        assert_ok(
            rejected_invalid_utf8.returncode != 0
            and "prompt file is not valid UTF-8" in rejected_invalid_utf8.stderr
            and not invalid_utf8_root.exists(),
            "prepare_run.py accepted invalid UTF-8 or partially reserved its run: {}".format(
                rejected_invalid_utf8.stderr
            ),
            errors,
        )

        concurrent_root = Path(temporary) / "concurrent-reservations"
        concurrent_root.mkdir()
        concurrent_root = concurrent_root.resolve()
        reservation_count = 100
        reservation_base = "2026-07-18-12-00-00-libreoffice-writer"
        barrier = threading.Barrier(reservation_count)

        def reserve_concurrently(_index: int) -> Path:
            barrier.wait()
            return reserve_paths(concurrent_root, reservation_base).run

        concurrent_failures: List[str] = []
        concurrent_reservations: List[Path] = []
        with ThreadPoolExecutor(max_workers=reservation_count) as executor:
            futures = [executor.submit(reserve_concurrently, index) for index in range(reservation_count)]
            for future in futures:
                try:
                    concurrent_reservations.append(future.result())
                except Exception as error:
                    concurrent_failures.append(str(error))
        assert_ok(
            not concurrent_failures,
            "concurrent namespace reservation failed: {}".format(concurrent_failures[:3]),
            errors,
        )
        distinct_slug_root = Path(temporary) / "distinct-same-second-slugs"
        distinct_slug_root.mkdir()
        distinct_slug_root = distinct_slug_root.resolve()
        writer_run = reserve_paths(
            distinct_slug_root,
            "2026-07-18-12-00-00-libreoffice-writer",
        ).run
        calc_run = reserve_paths(
            distinct_slug_root,
            "2026-07-18-12-00-00-libreoffice-calc",
        ).run
        assert_ok(
            writer_run.name == "2026-07-18-12-00-00-libreoffice-writer"
            and calc_run.name == "2026-07-18-12-00-00-libreoffice-calc",
            "different experiment slugs in one second received unnecessary collision suffixes",
            errors,
        )
        assert_ok(
            len(concurrent_reservations) == reservation_count
            and len(set(concurrent_reservations)) == reservation_count
            and {path.name for path in concurrent_reservations}
            == {reservation_base}
            | {f"{reservation_base}--{number:02d}" for number in range(2, reservation_count + 1)}
            and all(
                path.is_dir()
                and path.parent == concurrent_root
                and parse_flat_run_id(path.name) is not None
                for path in concurrent_reservations
            ),
            "concurrent flat reservation did not return distinct timestamped run paths",
            errors,
        )
        assert_ok(
            all(
                parse_flat_run_id(run_id) is not None
                for run_id in (
                    "2026-07-18-12-00-00",
                    "2026-07-18-12-00-00-02",
                    "2026-07-18-12-00-00-99",
                    "2026-07-18-12-00-00-100",
                    "2026-07-18-12-00-00-libreoffice-writer",
                    "2026-07-18-12-00-00-windows-11",
                    "2026-07-18-12-00-00-libreoffice-writer--02",
                    "2026-07-18-12-00-00-libreoffice-writer--100",
                )
            ),
            "flat run-ID parser rejected a valid timestamp or canonical collision suffix",
            errors,
        )
        invalid_flat_run_ids = (
            "2026-07-18-12-00-00-00",
            "2026-07-18-12-00-00-01",
            "2026-07-18-12-00-00-002",
            "2026-07-18-12-00-00-libreoffice-writer--00",
            "2026-07-18-12-00-00-libreoffice-writer--01",
            "2026-07-18-12-00-00-libreoffice-writer--002",
            "2026-07-18-12-00-00--02",
            "2026-07-18-12-00-00-LibreOffice-Writer",
            "2026-02-30-12-00-00",
            "2026-07-18-24-00-00",
            "2026-7-18-12-00-00",
        )
        assert_ok(
            all(parse_flat_run_id(run_id) is None for run_id in invalid_flat_run_ids),
            "flat run-ID parser accepted a non-canonical suffix or impossible timestamp",
            errors,
        )
        assert_ok(
            experiment_slug("LibreOffice Writer") == "libreoffice-writer"
            and experiment_slug("Crème brûlée — Writer") == "creme-brulee-writer"
            and experiment_slug("11") == "experiment-11"
            and experiment_slug("文書作成").startswith("experiment-")
            and len(experiment_slug("A very long experiment name " * 20)) <= 64
            and make_run_id("LibreOffice Writer").endswith("-libreoffice-writer"),
            "experiment run slugging was not readable, deterministic, or bounded",
            errors,
        )

        serialized_root = Path(temporary) / "serialized-builders"
        serialized_first = prepare_run(
            skill,
            serialized_root,
            "Model",
            "Harness",
            "First Snapshot",
            prompt,
            errors,
        )
        if serialized_first is not None:
            builder_command = [
                sys.executable,
                str(scripts[2]),
                "--root",
                str(serialized_root),
                "--out",
                str(serialized_root / "index.html"),
            ]
            process_context = multiprocessing.get_context("spawn")
            publication_ready = process_context.Event()
            release_publication = process_context.Event()
            first_outcomes = process_context.Queue()
            first_builder = process_context.Process(
                target=run_frozen_catalogue_builder,
                args=(
                    str(serialized_root.resolve()),
                    publication_ready,
                    release_publication,
                    first_outcomes,
                ),
            )
            first_builder.start()
            publication_observed = publication_ready.wait(30)
            assert_ok(
                publication_observed,
                "older catalogue builder did not reach its frozen publication barrier",
                errors,
            )
            second_builder: Optional[subprocess.Popen[str]] = None
            second_result: Optional[subprocess.CompletedProcess[str]] = None
            lock_was_busy = False
            second_data: Optional[Mapping[str, Any]] = None
            try:
                if not publication_observed:
                    raise RuntimeError("frozen catalogue publication was not observed")
                second_prepare = run(
                    [
                        sys.executable,
                        str(scripts[1]),
                        "--output-root",
                        str(serialized_root),
                        "--model",
                        "Model",
                        "--harness",
                        "Harness",
                        "--experiment",
                        "Second Snapshot",
                        "--prompt-file",
                        str(prompt),
                    ]
                )
                second_data = invocation_json(second_prepare, errors, "serialized second prepare")
                lock_was_busy = catalogue_lock_is_busy(serialized_root.resolve())
                if lock_was_busy:
                    second_builder = subprocess.Popen(
                        builder_command,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                else:
                    second_result = subprocess.run(
                        builder_command,
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                errors.append("serialized catalogue setup failed: {}".format(error))
            finally:
                release_publication.set()
                first_builder.join(30)
                if first_builder.is_alive():
                    first_builder.terminate()
                    first_builder.join(5)
                    errors.append("older catalogue builder did not stop after its publication was released")

            first_outcome: Mapping[str, Any] = {
                "returncode": 1,
                "error": "missing child outcome",
                "stdout": "",
                "stderr": "",
            }
            try:
                candidate_outcome = first_outcomes.get(timeout=5)
                if isinstance(candidate_outcome, Mapping):
                    first_outcome = candidate_outcome
            except queue.Empty:
                pass
            finally:
                first_outcomes.close()
                first_outcomes.join_thread()

            if second_builder is not None:
                try:
                    second_stdout, second_stderr = second_builder.communicate(timeout=30)
                except subprocess.TimeoutExpired:
                    second_builder.kill()
                    second_stdout, second_stderr = second_builder.communicate()
                    errors.append("newer catalogue builder did not finish after the older builder released the lock")
                second_returncode = second_builder.returncode
            elif second_result is not None:
                second_stdout = second_result.stdout
                second_stderr = second_result.stderr
                second_returncode = second_result.returncode
            else:
                second_stdout = ""
                second_stderr = ""
                second_returncode = 1

            serialized_validation = run([sys.executable, str(scripts[3]), str(serialized_root)])
            second_run_name = (
                Path(str(second_data.get("runDirectory"))).name
                if isinstance(second_data, Mapping) and isinstance(second_data.get("runDirectory"), str)
                else ""
            )
            serialized_index = serialized_root / "index.html"
            serialized_html = serialized_index.read_text(encoding="utf-8") if serialized_index.is_file() else ""
            assert_ok(
                lock_was_busy
                and first_builder.exitcode == 0
                and first_outcome.get("returncode") == 0
                and not first_outcome.get("error")
                and second_returncode == 0
                and serialized_validation.returncode == 0
                and second_run_name
                and second_run_name in serialized_html,
                "serialized catalogue builders published a stale older snapshot: {}{}{}{}{}".format(
                    str(first_outcome.get("error", "")),
                    str(first_outcome.get("stdout", "")),
                    str(first_outcome.get("stderr", "")),
                    second_stdout + second_stderr,
                    serialized_validation.stdout,
                ),
                errors,
            )

        first_run = prepare_run(skill, output_root, "Model One", "Harness / Alpha", "Harbor Station", prompt, errors)
        collision_run = prepare_run(skill, output_root, "Model-One", "Harness / Alpha", "Harbor Station", prompt, errors)
        if first_run is None or collision_run is None:
            return
        assert_ok(
            first_run.parent == output_root.resolve()
            and collision_run.parent == output_root.resolve()
            and all(
                (parsed_run_id := parse_flat_run_id(run_path.name)) is not None
                and parsed_run_id.slug == "harbor-station"
                for run_path in (first_run, collision_run)
            ),
            "prepare_run.py did not place timestamped runs directly under the selected output root",
            errors,
        )
        prior_receipt = output_root / ".oneshot-provenance" / (first_run.name + ".json")
        prior_commit = output_root / ".oneshot-provenance" / (first_run.name + ".commit")
        prior_link_command = [
            sys.executable,
            str(skill / "scripts" / "prepare_run.py"),
            "--output-root",
            str(output_root),
            "--model",
            "Model One",
            "--harness",
            "Harness / Alpha",
            "--experiment",
            "Harbor Station",
            "--prompt-file",
            str(prompt),
            "--classification",
            "rerun",
            "--prior-run",
            str(first_run),
        ]
        prior_commit.unlink()
        uncommitted_prior_result = run(prior_link_command)
        assert_ok(
            uncommitted_prior_result.returncode != 0
            and "missing its provenance commit marker" in uncommitted_prior_result.stderr,
            "prepare_run.py accepted an uncommitted prior-run residue",
            errors,
        )
        prior_commit.write_bytes(b"")
        receipt_backup = prior_receipt.read_bytes()
        prior_receipt.unlink()
        unreceipted_prior_result = run(prior_link_command)
        assert_ok(
            unreceipted_prior_result.returncode != 0
            and "missing its coordinator provenance receipt" in unreceipted_prior_result.stderr,
            "prepare_run.py accepted a prior run without its coordinator receipt",
            errors,
        )
        prior_receipt.write_bytes(receipt_backup)
        rerun_path = prepare_run(
            skill,
            output_root,
            "Model One",
            "Harness / Alpha",
            "Harbor Station",
            prompt,
            errors,
            classification="rerun",
            prior_run=first_run,
        )
        if rerun_path is None:
            return

        abandoned_reservation = reserve_paths(first_run.parent, make_run_id("Abandoned Reservation")).run
        temporary_only_reservation = reserve_paths(first_run.parent, make_run_id("Temporary Reservation")).run
        (temporary_only_reservation / ".tmp").mkdir(parents=True)
        interrupted_reservation = reserve_paths(first_run.parent, make_run_id("Interrupted Reservation")).run
        (interrupted_reservation / ".tmp").mkdir(parents=True)
        (interrupted_reservation / "workspace").mkdir(parents=True)
        (interrupted_reservation / "artifact").mkdir()
        (interrupted_reservation / "artifact" / "PROMPT.md").write_bytes(prompt_bytes)
        interrupted_metadata_run = reserve_paths(first_run.parent, make_run_id("Interrupted Metadata")).run
        (interrupted_metadata_run / ".tmp").mkdir(parents=True)
        (interrupted_metadata_run / "workspace").mkdir(parents=True)
        (interrupted_metadata_run / "artifact").mkdir()
        (interrupted_metadata_run / "artifact" / "PROMPT.md").write_bytes(prompt_bytes)
        (interrupted_metadata_run / "run.json").write_text('{"schemaVersion":"2.0",', encoding="utf-8")
        (interrupted_metadata_run / "worker-report.json").write_text('{"schemaVersion":"2.0"}', encoding="utf-8")
        (output_root / ".oneshot-provenance" / (interrupted_metadata_run.name + ".json")).write_text(
            '{"schemaVersion":"1.0",',
            encoding="utf-8",
        )
        abandoned_build = rebuild_catalog_index(output_root)
        abandoned_validation = run([sys.executable, str(scripts[3]), str(output_root)])
        assert_ok(
            abandoned_build.returncode == 0 and abandoned_validation.returncode == 0,
            "an empty or pre-manifest interrupted reservation permanently poisoned the output root",
            errors,
        )

        prior_parts = first_run.relative_to(output_root.resolve()).parts
        resolved_output_root = output_root.resolve()
        wrong_case_prior = resolved_output_root / prior_parts[0].upper() / Path(*prior_parts[1:])
        if wrong_case_prior.exists() and wrong_case_prior != first_run:
            wrong_prior_result = run(
                [
                    sys.executable,
                    str(skill / "scripts" / "prepare_run.py"),
                    "--output-root",
                    str(output_root),
                    "--model",
                    "Model One",
                    "--harness",
                    "Harness / Alpha",
                    "--experiment",
                    "Harbor Station",
                    "--prompt-file",
                    str(prompt),
                    "--classification",
                    "rerun",
                    "--prior-run",
                    str(wrong_case_prior),
                ]
            )
            assert_ok(
                wrong_prior_result.returncode != 0 and "prior run path must use exact casing" in wrong_prior_result.stderr,
                "prepare_run.py accepted a wrong-case prior run path",
                errors,
            )

        first_manifest = read_json(first_run / "run.json", errors, "prepared run.json")
        preserved_prompt = first_run / "artifact" / "PROMPT.md"
        temporary_directory = first_run / ".tmp"
        assert_ok(
            temporary_directory.is_dir() and not temporary_directory.is_symlink(),
            "prepare_run.py did not create an exact run-local .tmp/ directory",
            errors,
        )
        assert_ok(preserved_prompt.is_file(), "prepare_run.py did not create artifact/PROMPT.md", errors)
        if preserved_prompt.is_file():
            assert_ok(preserved_prompt.read_bytes() == prompt_bytes, "prepare_run.py did not preserve prompt bytes", errors)
            assert_ok(
                b"TMPDIR" not in preserved_prompt.read_bytes()
                and b"best-effort-run-local" not in preserved_prompt.read_bytes(),
                "prepare_run.py leaked the temporary-file envelope into artifact/PROMPT.md",
                errors,
            )
        if isinstance(first_manifest, Mapping):
            assert_ok(
                first_manifest.get("schemaVersion") == "3.2",
                "prepare_run.py did not emit the current run schema",
                errors,
            )
            prompt_data = first_manifest.get("prompt")
            expected_hash = hashlib.sha256(prompt_bytes).hexdigest()
            assert_ok(isinstance(prompt_data, Mapping) and prompt_data.get("sha256") == expected_hash, "prepare_run.py did not record the exact prompt hash", errors)
            receipt_value = first_manifest.get("provenanceReceipt")
            receipt_path = output_root / str(receipt_value)
            receipt = read_json(receipt_path, errors, "pre-dispatch provenance receipt") if isinstance(receipt_value, str) else None
            assert_ok(
                isinstance(receipt, Mapping)
                and receipt.get("schemaVersion") == "2.2"
                and receipt.get("runSchemaVersion") == "3.2"
                and receipt.get("prompt", {}).get("sha256") == expected_hash
                and receipt.get("prompt", {}).get("bytes") == len(prompt_bytes),
                "prepare_run.py did not anchor prompt provenance outside the worker run",
                errors,
            )
            assert_ok(
                isinstance(receipt, Mapping)
                and receipt.get("qualityGauntlet")
                == {
                    "required": True,
                    "contractVersion": "1.0",
                    "reportSchemaVersion": "2.1",
                },
                "prepare_run.py did not anchor the quality-gauntlet report contract",
                errors,
            )
            assert_ok(
                isinstance(receipt, Mapping)
                and receipt.get("temporary")
                == {
                    "path": ".tmp/",
                    "routing": "best-effort-run-local",
                    "preservation": "retain",
                },
                "prepare_run.py did not anchor the current temporary contract outside the worker run",
                errors,
            )
            identity = first_manifest.get("identity")
            assert_ok(isinstance(identity, Mapping), "prepared run is missing identity metadata", errors)
            if isinstance(identity, Mapping):
                for part in ("model", "harness", "experiment"):
                    assert_ok(isinstance(identity.get(part), Mapping), "prepared run missing {} identity".format(part), errors)
            temporary_data = first_manifest.get("temporary")
            assert_ok(
                isinstance(temporary_data, Mapping)
                and temporary_data.get("path") == ".tmp/"
                and temporary_data.get("routing") == "best-effort-run-local"
                and temporary_data.get("preservation") == "retain",
                "prepare_run.py did not record the run-local temporary contract",
                errors,
            )

        first_report = read_json(first_run / "worker-report.json", errors, "prepared worker report")
        if isinstance(first_report, Mapping):
            assert_ok(
                first_report.get("schemaVersion") == "2.1"
                and isinstance(first_report.get("qualityGauntlet"), Mapping),
                "prepare_run.py did not initialize the current quality-gauntlet report",
                errors,
            )
            temporary_report = first_report.get("temporary")
            assert_ok(
                isinstance(temporary_report, Mapping)
                and temporary_report.get("path") == ".tmp/"
                and temporary_report.get("routingApplied") is None
                and temporary_report.get("externalExceptions") == [],
                "prepare_run.py did not initialize temporary-routing observations",
                errors,
            )

        current_report_path = first_run / "worker-report.json"
        current_report_bytes = current_report_path.read_bytes()
        current_report_without_gauntlet = json.loads(current_report_bytes)
        current_report_without_gauntlet.pop("qualityGauntlet", None)
        current_report_path.write_text(
            json.dumps(current_report_without_gauntlet, indent=2) + "\n",
            encoding="utf-8",
        )
        assert_invalid_catalog(
            scripts[3],
            output_root,
            "current run is missing required qualityGauntlet",
            "current worker report with deleted quality-gauntlet contract",
            errors,
        )
        current_report_path.write_bytes(current_report_bytes)

        original_prompt_bytes = preserved_prompt.read_bytes()
        original_manifest_bytes = (first_run / "run.json").read_bytes()
        original_receipt_bytes = prior_receipt.read_bytes()
        corrupted_prompt_bytes = (
            "Create a Linux Mint desktop â€” faithful down to Cinnamonâ€™s smallest interactions.\n"
        ).encode("utf-8")
        corrupted_digest = hashlib.sha256(corrupted_prompt_bytes).hexdigest()
        corrupted_manifest = json.loads(original_manifest_bytes)
        corrupted_manifest["prompt"]["sha256"] = corrupted_digest
        corrupted_receipt = json.loads(original_receipt_bytes)
        corrupted_receipt["prompt"]["sha256"] = corrupted_digest
        corrupted_receipt["prompt"]["bytes"] = len(corrupted_prompt_bytes)
        preserved_prompt.write_bytes(corrupted_prompt_bytes)
        (first_run / "run.json").write_text(
            json.dumps(corrupted_manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        prior_receipt.write_text(
            json.dumps(corrupted_receipt, indent=2) + "\n",
            encoding="utf-8",
        )
        assert_invalid_catalog(
            scripts[3],
            output_root,
            "preserved prompt contains likely mojibake",
            "digest-consistent mojibake PROMPT.md",
            errors,
        )
        preserved_prompt.write_bytes(original_prompt_bytes)
        (first_run / "run.json").write_bytes(original_manifest_bytes)
        prior_receipt.write_bytes(original_receipt_bytes)

        assert_ok(first_run != collision_run, "normalized-similar names reused a run directory", errors)
        assert_ok(
            all((run_path / ".tmp").is_dir() for run_path in (first_run, collision_run, rerun_path))
            and len({(run_path / ".tmp").resolve() for run_path in (first_run, collision_run, rerun_path)}) == 3,
            "separate runs did not receive distinct run-local .tmp/ directories",
            errors,
        )
        rerun_manifest = read_json(rerun_path / "run.json", errors, "rerun run.json")
        if isinstance(rerun_manifest, Mapping):
            assert_ok(
                rerun_manifest.get("priorRun") == first_run.relative_to(output_root.resolve()).as_posix(),
                "rerun did not preserve its prior-run relationship",
                errors,
            )
        collision_manifest = read_json(collision_run / "run.json", errors, "collision run.json")
        if isinstance(first_manifest, Mapping) and isinstance(collision_manifest, Mapping):
            first_model = first_manifest.get("identity", {}).get("model", {})
            collision_model = collision_manifest.get("identity", {}).get("model", {})
            assert_ok(first_model.get("key") != collision_model.get("key"), "normalized-similar model names share an identity key", errors)

        shutil.rmtree(first_run / ".tmp")
        assert_invalid_catalog(
            scripts[3],
            output_root,
            "missing an exact-case ordinary .tmp/ directory",
            "current-schema run without its temporary directory",
            errors,
        )
        (first_run / ".tmp").mkdir()
        rebuilt_after_temporary_restore = rebuild_catalog_index(output_root)
        assert_ok(
            rebuilt_after_temporary_restore.returncode == 0,
            "catalogue builder failed after restoring run-local .tmp/: {}".format(
                rebuilt_after_temporary_restore.stderr or rebuilt_after_temporary_restore.stdout
            ),
            errors,
        )

        downgrade_manifest_path = first_run / "run.json"
        downgrade_report_path = first_run / "worker-report.json"
        downgrade_manifest_bytes = downgrade_manifest_path.read_bytes()
        downgrade_report_bytes = downgrade_report_path.read_bytes()
        downgrade_manifest = json.loads(downgrade_manifest_bytes)
        downgrade_manifest["schemaVersion"] = "2.0"
        downgrade_manifest.pop("temporary", None)
        downgrade_manifest_path.write_text(json.dumps(downgrade_manifest, indent=2) + "\n", encoding="utf-8")
        downgrade_report = json.loads(downgrade_report_bytes)
        downgrade_report.pop("temporary", None)
        downgrade_report_path.write_text(json.dumps(downgrade_report, indent=2) + "\n", encoding="utf-8")
        shutil.rmtree(first_run / ".tmp")
        assert_invalid_catalog(
            scripts[3],
            output_root,
            "receipt schema '2.2' requires run schema 3.2",
            "new run downgraded through worker-writable metadata",
            errors,
        )
        downgrade_manifest_path.write_bytes(downgrade_manifest_bytes)
        downgrade_report_path.write_bytes(downgrade_report_bytes)
        (first_run / ".tmp").mkdir()
        rebuilt_after_downgrade_restore = rebuild_catalog_index(output_root)
        assert_ok(
            rebuilt_after_downgrade_restore.returncode == 0,
            "catalogue builder failed after restoring an anchored 3.2 run: {}".format(
                rebuilt_after_downgrade_restore.stderr or rebuilt_after_downgrade_restore.stdout
            ),
            errors,
        )

        flat_3_0_root = Path(temporary) / "flat-3-0-runs"
        flat_3_0_run = prepare_run(
            skill,
            flat_3_0_root,
            "Prior Flat Model",
            "Harness",
            "Prior Flat 3.0 Run",
            prompt,
            errors,
        )
        if flat_3_0_run is not None:
            mark_successful_static_artifact(flat_3_0_run)
            flat_3_0_run = convert_to_historical_flat_run(flat_3_0_root, flat_3_0_run, "3.0")
            flat_3_0_build = rebuild_catalog_index(flat_3_0_root)
            flat_3_0_validation = run(
                [sys.executable, str(scripts[3]), str(flat_3_0_root)]
            )
            assert_ok(
                flat_3_0_build.returncode == 0
                and flat_3_0_validation.returncode == 0,
                "validator rejected a prior flat 3.0 OK run: {}{}".format(
                    flat_3_0_build.stderr or flat_3_0_build.stdout,
                    flat_3_0_validation.stdout,
                ),
                errors,
            )

        flat_3_1_root = Path(temporary) / "flat-3-1-runs"
        flat_3_1_run = prepare_run(
            skill,
            flat_3_1_root,
            "Prior Flat Model",
            "Harness",
            "Prior Flat 3.1 Run",
            prompt,
            errors,
        )
        if flat_3_1_run is not None:
            mark_successful_static_artifact(flat_3_1_run)
            flat_3_1_run = convert_to_historical_flat_run(flat_3_1_root, flat_3_1_run, "3.1")
            flat_3_1_run = rewrite_prepared_run_id(
                flat_3_1_root,
                flat_3_1_run,
                f"{flat_3_1_run.name}-02",
            )
            flat_3_1_build = rebuild_catalog_index(flat_3_1_root)
            flat_3_1_validation = run(
                [sys.executable, str(scripts[3]), str(flat_3_1_root)]
            )
            assert_ok(
                flat_3_1_build.returncode == 0
                and flat_3_1_validation.returncode == 0,
                "validator rejected a prior flat 3.1 OK run: {}{}".format(
                    flat_3_1_build.stderr or flat_3_1_build.stdout,
                    flat_3_1_validation.stdout,
                ),
                errors,
            )

        bare_current_root = Path(temporary) / "bare-current-run"
        bare_current_run = prepare_run(
            skill,
            bare_current_root,
            "Current Model",
            "Harness",
            "Bare Current Run",
            prompt,
            errors,
        )
        if bare_current_run is not None:
            rewrite_prepared_run_id(
                bare_current_root,
                bare_current_run,
                bare_current_run.name[:19],
            )
            assert_invalid_catalog(
                scripts[3],
                bare_current_root,
                "run schema 3.2 requires an experiment slug in the run directory",
                "current run using a historical timestamp-only directory",
                errors,
            )

        mismatched_slug_root = Path(temporary) / "mismatched-current-slug"
        mismatched_slug_run = prepare_run(
            skill,
            mismatched_slug_root,
            "Current Model",
            "Harness",
            "LibreOffice Writer",
            prompt,
            errors,
        )
        if mismatched_slug_run is not None:
            wrong_slug_id = f"{mismatched_slug_run.name[:19]}-generic-office-suite"
            rewrite_prepared_run_id(mismatched_slug_root, mismatched_slug_run, wrong_slug_id)
            assert_invalid_catalog(
                scripts[3],
                mismatched_slug_root,
                "run-directory slug must match experiment name as 'libreoffice-writer'",
                "current run whose readable slug disagrees with its experiment identity",
                errors,
            )

        for legacy_schema in ("2.0", "2.1"):
            legacy_root = Path(temporary) / f"legacy-{legacy_schema.replace('.', '-')}-runs"
            legacy_run = prepare_run(
                skill,
                legacy_root,
                "Legacy Model",
                "Harness",
                f"Legacy {legacy_schema} Run",
                prompt,
                errors,
            )
            if legacy_run is not None:
                legacy_run = convert_to_legacy_run(legacy_root, legacy_run, legacy_schema)
                legacy_build = rebuild_catalog_index(legacy_root)
                legacy_validation = run([sys.executable, str(scripts[3]), str(legacy_root)])
                assert_ok(
                    legacy_build.returncode == 0 and legacy_validation.returncode == 0,
                    "validator rejected a legacy {} run: {}{}".format(
                        legacy_schema,
                        legacy_build.stderr or legacy_build.stdout,
                        legacy_validation.stdout,
                    ),
                    errors,
                )

        for invalid_index, invalid_run_id in enumerate(invalid_flat_run_ids):
            invalid_root = Path(temporary) / f"invalid-flat-run-{invalid_index}"
            invalid_run = prepare_run(
                skill,
                invalid_root,
                "Invalid ID Model",
                "Harness",
                f"Invalid Run ID {invalid_index}",
                prompt,
                errors,
            )
            if invalid_run is None:
                continue
            rewrite_prepared_run_id(invalid_root, invalid_run, invalid_run_id)
            invalid_build = rebuild_catalog_index(invalid_root)
            invalid_validation = run([sys.executable, str(scripts[3]), str(invalid_root)])
            assert_ok(
                invalid_build.returncode != 0
                and invalid_validation.returncode != 0
                and "Traceback" not in invalid_build.stderr
                and "Traceback" not in invalid_validation.stdout
                and "Traceback" not in invalid_validation.stderr,
                "catalogue tools accepted or crashed on invalid flat run ID {!r}: {}{}{}".format(
                    invalid_run_id,
                    invalid_build.stderr or invalid_build.stdout,
                    invalid_validation.stdout,
                    invalid_validation.stderr,
                ),
                errors,
            )

        mark_successful_static_artifact(first_run)
        (first_run / "artifact" / ".tmp").mkdir()
        (first_run / "artifact" / ".tmp" / "scratch.txt").write_text("temporary\n", encoding="utf-8")
        assert_invalid_catalog(
            scripts[3],
            output_root,
            "run-local .tmp/ must stay outside artifact/ at the run root",
            "run-local .tmp/ copied into the deployable artifact",
            errors,
        )
        shutil.rmtree(first_run / "artifact" / ".tmp")
        build = run([sys.executable, str(scripts[2]), "--root", str(output_root), "--out", str(output_root / "index.html")])
        assert_ok(build.returncode == 0, "build_catalog_index.py rejected a built framework artifact: {}".format(build.stderr or build.stdout), errors)
        successful_report_path = first_run / "worker-report.json"
        successful_report_bytes = successful_report_path.read_bytes()
        successful_report = json.loads(successful_report_bytes)
        successful_report["temporary"]["routingApplied"] = None
        successful_report_path.write_text(json.dumps(successful_report, indent=2) + "\n", encoding="utf-8")
        assert_invalid_catalog(
            scripts[3],
            output_root,
            "successful run must record temporary.routingApplied as true or false",
            "successful run with an unknown temporary-routing outcome",
            errors,
        )
        successful_report["temporary"]["routingApplied"] = False
        successful_report_path.write_text(json.dumps(successful_report, indent=2) + "\n", encoding="utf-8")
        assert_invalid_catalog(
            scripts[3],
            output_root,
            "successful run with temporary routing disabled must record an external exception",
            "successful run with unexplained disabled temporary routing",
            errors,
        )
        successful_report["temporary"]["externalExceptions"] = [
            "The build tool created one cache file before process environment routing was available."
        ]
        successful_report_path.write_text(json.dumps(successful_report, indent=2) + "\n", encoding="utf-8")
        explained_routing_build = rebuild_catalog_index(output_root)
        explained_routing_validation = run([sys.executable, str(scripts[3]), str(output_root)])
        assert_ok(
            explained_routing_build.returncode == 0 and explained_routing_validation.returncode == 0,
            "validator rejected an honest temporary-routing exception: {}{}".format(
                explained_routing_build.stderr or explained_routing_build.stdout,
                explained_routing_validation.stdout,
            ),
            errors,
        )
        successful_report_path.write_bytes(successful_report_bytes)
        restored_successful_build = rebuild_catalog_index(output_root)
        assert_ok(
            restored_successful_build.returncode == 0,
            "catalogue builder failed after restoring the successful temporary-routing report: {}".format(
                restored_successful_build.stderr or restored_successful_build.stdout
            ),
            errors,
        )
        if os.name == "posix":
            assert_ok(
                stat.S_IMODE((output_root / "index.html").stat().st_mode) == 0o644,
                "new catalogue index was not published with a web-readable mode",
                errors,
            )
        catalogue_html = (output_root / "index.html").read_text(encoding="utf-8")
        assert_ok(str(output_root) not in catalogue_html, "catalogue index exposed its local absolute root", errors)
        assert_ok("Model One" in catalogue_html, "catalogue index omitted the raw model name", errors)

        receipt_name = "{}.json".format(first_run.name)
        appledouble_paths = [
            output_root / "._.oneshot-provenance",
            output_root / "._{}".format(first_run.name),
            output_root / ".oneshot-provenance" / "._{}".format(receipt_name),
            first_run / "._run.json",
            first_run / "artifact" / "._PROMPT.md",
            first_run / "artifact" / "._index.html",
        ]
        for appledouble_path in appledouble_paths:
            write_appledouble(appledouble_path)
        appledouble_build = rebuild_catalog_index(output_root)
        appledouble_validation = run([sys.executable, str(scripts[3]), str(output_root)])
        assert_ok(
            appledouble_build.returncode == 0 and appledouble_validation.returncode == 0,
            "authentic AppleDouble metadata poisoned a portable-volume run root: {}{}".format(
                appledouble_build.stderr,
                appledouble_validation.stdout,
            ),
            errors,
        )
        fake_appledouble = output_root / "._user-file"
        fake_appledouble.write_text("ordinary user content\n", encoding="utf-8")
        fake_appledouble_build = rebuild_catalog_index(output_root)
        assert_ok(
            fake_appledouble_build.returncode != 0 and "unexpected file outside a run" in fake_appledouble_build.stderr,
            "catalogue builder ignored a filename-only AppleDouble impersonator",
            errors,
        )
        fake_appledouble.unlink()
        assert_ok(
            rebuild_catalog_index(output_root).returncode == 0,
            "catalogue builder did not recover after the AppleDouble impersonator test",
            errors,
        )

        wrong_site = rename_with_exact_case(first_run / "artifact" / "index.html", "Index.html")
        wrong_prompt = rename_with_exact_case(preserved_prompt, "Prompt.md")
        case_build = run([sys.executable, str(scripts[2]), "--root", str(output_root), "--out", str(output_root / "index.html")])
        assert_ok(case_build.returncode == 0, "catalogue builder failed on wrong-case artifact names", errors)
        case_html = (output_root / "index.html").read_text(encoding="utf-8")
        assert_ok(
            "Artifact entry</a>" not in case_html
            and case_html.count("PROMPT.md</a>") == catalogue_html.count("PROMPT.md</a>") - 1,
            "catalogue builder linked wrong-case artifact filenames",
            errors,
        )
        rename_with_exact_case(wrong_site, "index.html")
        preserved_prompt = rename_with_exact_case(wrong_prompt, "PROMPT.md")
        if os.name == "posix":
            os.chmod(output_root / "index.html", 0o640)
        restored_build = run([sys.executable, str(scripts[2]), "--root", str(output_root), "--out", str(output_root / "index.html")])
        assert_ok(restored_build.returncode == 0, "catalogue builder failed after restoring exact artifact names", errors)
        restored_html = (output_root / "index.html").read_text(encoding="utf-8")
        assert_ok(
            "Artifact entry</a>" in restored_html
            and restored_html.count("PROMPT.md</a>") == catalogue_html.count("PROMPT.md</a>"),
            "catalogue builder did not restore exact artifact links",
            errors,
        )
        if os.name == "posix":
            assert_ok(
                stat.S_IMODE((output_root / "index.html").stat().st_mode) == 0o644,
                "catalogue rebuild did not normalize the existing output to a web-readable mode",
                errors,
            )
            os.chmod(output_root / "index.html", 0o000)
            assert_invalid_catalog(scripts[3], output_root, "readable file mode", "unreadable root catalogue", errors)
            readable_build = run([sys.executable, str(scripts[2]), "--root", str(output_root), "--out", str(output_root / "index.html")])
            assert_ok(readable_build.returncode == 0, "catalogue builder failed to recover an unreadable destination", errors)
            assert_ok(
                stat.S_IMODE((output_root / "index.html").stat().st_mode) == 0o644,
                "catalogue builder did not recover mode 000 to 0644",
                errors,
            )
            os.chmod(output_root, 0o500)
            unwritable_build = rebuild_catalog_index(output_root)
            assert_ok(
                unwritable_build.returncode != 0
                and "writable directory mode" in unwritable_build.stderr
                and "Traceback" not in unwritable_build.stderr,
                "catalogue builder crashed on a non-writable output root",
                errors,
            )
            os.chmod(output_root, 0o700)

        (output_root / "index.html").write_text("<!doctype html><title>stale</title>\n", encoding="utf-8")
        assert_invalid_catalog(scripts[3], output_root, "root catalogue is stale", "stale root catalogue", errors)
        fresh_build = rebuild_catalog_index(output_root)
        assert_ok(
            fresh_build.returncode == 0,
            "catalogue builder failed after stale-index regression: {}".format(fresh_build.stderr or fresh_build.stdout),
            errors,
        )

        stale_temporary = output_root / ".oneshot-index-interrupted.tmp"
        stale_temporary.write_text("partial", encoding="utf-8")
        recovered_build = rebuild_catalog_index(output_root)
        assert_ok(
            recovered_build.returncode == 0 and stale_temporary.exists(),
            "catalogue builder did not recover its interrupted temporary output",
            errors,
        )
        stale_temporary.unlink()

        wrong_root_index = rename_with_exact_case(output_root / "index.html", "Index.html")
        collision_build = rebuild_catalog_index(output_root)
        assert_ok(
            collision_build.returncode != 0 and "wrong-case root catalogue filename" in collision_build.stderr,
            "catalogue builder reported success for a wrong-case root index collision",
            errors,
        )
        rename_with_exact_case(wrong_root_index, "index.html")

        root_index_backup = output_root / ".root-index-backup"
        (output_root / "index.html").rename(root_index_backup)
        (output_root / "index.html").mkdir()
        directory_build = rebuild_catalog_index(output_root)
        assert_ok(
            directory_build.returncode != 0
            and "regular non-symlink file" in directory_build.stderr
            and "Traceback" not in directory_build.stderr,
            "catalogue builder crashed when index.html was a directory",
            errors,
        )
        (output_root / "index.html").rmdir()
        root_index_backup.rename(output_root / "index.html")

        manifest_path = first_run / "run.json"
        original_manifest_text = manifest_path.read_text(encoding="utf-8")
        placeholder_manifest = json.loads(original_manifest_text)
        placeholder_manifest["identity"]["model"]["name"] = "{{FOOTER_NOTE}}"
        manifest_path.write_text(json.dumps(placeholder_manifest), encoding="utf-8")
        placeholder_build = run([sys.executable, str(scripts[2]), "--root", str(output_root), "--out", str(output_root / "index.html")])
        assert_ok(placeholder_build.returncode == 0, "catalogue builder failed on placeholder-shaped provenance", errors)
        placeholder_html = (output_root / "index.html").read_text(encoding="utf-8")
        assert_ok("{{FOOTER_NOTE}}" in placeholder_html, "catalogue builder recursively rewrote provenance text", errors)
        manifest_path.write_text(original_manifest_text, encoding="utf-8")

        report_path = first_run / "worker-report.json"
        report_backup = first_run / "worker-report.backup.json"
        report_path.rename(report_backup)
        report_path.mkdir()
        disclosure_build = run([sys.executable, str(scripts[2]), "--root", str(output_root), "--out", str(output_root / "index.html")])
        assert_ok(disclosure_build.returncode == 0, "catalogue builder failed on unreadable report metadata", errors)
        disclosure_html = (output_root / "index.html").read_text(encoding="utf-8")
        assert_ok(str(output_root) not in disclosure_html, "catalogue builder disclosed an absolute metadata path", errors)
        report_path.rmdir()
        report_backup.rename(report_path)

        outside_report = Path(temporary) / "outside-worker-report.json"
        outside_report.write_text(
            json.dumps({"summary": "OUTSIDE REPORT SECRET"}),
            encoding="utf-8",
        )
        report_path.rename(report_backup)
        try:
            report_path.symlink_to(outside_report)
        except OSError:
            report_backup.rename(report_path)
        else:
            symlink_report_build = rebuild_catalog_index(output_root)
            assert_ok(
                symlink_report_build.returncode == 0
                and "OUTSIDE REPORT SECRET" not in (output_root / "index.html").read_text(encoding="utf-8"),
                "catalogue builder followed a symlinked worker report",
                errors,
            )
            report_path.unlink()
            report_backup.rename(report_path)

        if hasattr(os, "mkfifo"):
            report_path.rename(report_backup)
            os.mkfifo(report_path)
            fifo_report_build = rebuild_catalog_index(output_root)
            assert_ok(
                fifo_report_build.returncode == 0,
                "catalogue builder blocked or failed on a non-regular worker report",
                errors,
            )
            report_path.unlink()
            report_backup.rename(report_path)

        site_path = first_run / "artifact" / "index.html"
        site_backup = first_run / "artifact" / "index.backup.html"
        outside_site = Path(temporary) / "outside-site.html"
        outside_site.write_text("<!doctype html><title>Outside</title>\n", encoding="utf-8")
        site_path.rename(site_backup)
        try:
            site_path.symlink_to(outside_site)
        except OSError:
            site_backup.rename(site_path)
        else:
            symlink_site_build = rebuild_catalog_index(output_root)
            symlink_site_html = (output_root / "index.html").read_text(encoding="utf-8")
            assert_ok(
                symlink_site_build.returncode == 0
                and symlink_site_html.count("Artifact entry</a>") == restored_html.count("Artifact entry</a>") - 1,
                "catalogue builder linked a symlinked artifact entrypoint",
                errors,
            )
            site_path.unlink()
            site_backup.rename(site_path)

        (output_root / "index.html").unlink()
        os.link(str(preserved_prompt), str(output_root / "index.html"))
        prompt_before_rebuild = preserved_prompt.read_bytes()
        hardlink_build = run([sys.executable, str(scripts[2]), "--root", str(output_root), "--out", str(output_root / "index.html")])
        assert_ok(hardlink_build.returncode == 0, "catalogue rebuild over a hard link failed", errors)
        assert_ok(
            preserved_prompt.read_bytes() == prompt_before_rebuild,
            "catalogue rebuild rewrote a hard-linked artifact prompt",
            errors,
        )

        refused_out = Path(temporary) / "outside-index.html"
        refused_out.write_text("sentinel", encoding="utf-8")
        outside_build = run([sys.executable, str(scripts[2]), "--root", str(output_root), "--out", str(refused_out)])
        assert_ok(
            outside_build.returncode != 0 and refused_out.read_text(encoding="utf-8") == "sentinel",
            "catalogue builder wrote outside its root index",
            errors,
        )
        validation = run([sys.executable, str(scripts[3]), str(output_root)])
        assert_ok(validation.returncode == 0, "validate_catalog.py rejected a drop-ready static artifact: {}".format(validation.stderr or validation.stdout), errors)

        missing_index = prepare_run(skill, output_root, "Second Model", "Harness / Alpha", "Missing Entry", prompt, errors)
        if missing_index is not None:
            manifest_path = missing_index / "run.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["status"] = "OK"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report_path = missing_index / "worker-report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["status"] = "OK"
            report["artifact"]["staticDeploymentVerified"] = True
            report_path.write_text(json.dumps(report), encoding="utf-8")
            missing_validation = run([sys.executable, str(scripts[3]), str(output_root)])
            assert_ok(missing_validation.returncode != 0, "validate_catalog.py accepted OK status without artifact/index.html", errors)
            assert_ok("missing exact-case artifact/index.html" in missing_validation.stdout, "validate_catalog.py did not report the missing OK entrypoint", errors)

        traversal = output_root / "unsafe-model" / "unsafe-harness" / "unsafe-experiment" / "unsafe-run"
        (traversal / "workspace").mkdir(parents=True)
        (traversal / "artifact").mkdir()
        (traversal / "run.json").write_text(
            json.dumps(
                {
                    "schemaVersion": "2.0",
                    "identity": {"model": {"name": "unsafe", "key": "unsafe-model"}, "harness": {"name": "unsafe", "key": "unsafe-harness"}, "experiment": {"name": "unsafe", "key": "unsafe-experiment"}},
                    "runId": "unsafe-run",
                    "classification": "autonomous-one-shot",
                    "status": "PLANNED",
                    "prompt": {"path": "../outside/PROMPT.md", "sha256": "0" * 64, "preservation": "verbatim"},
                    "workspace": {"path": "workspace/"},
                    "artifact": {"path": "../outside/", "entrypoint": "../outside/index.html", "deployment": "static-folder"},
                }
            ),
            encoding="utf-8",
        )
        traversal_validation = run([sys.executable, str(scripts[3]), str(output_root)])
        assert_ok(traversal_validation.returncode != 0, "validate_catalog.py accepted a path traversal in run metadata", errors)
        assert_ok("not a safe relative path" in traversal_validation.stdout, "validate_catalog.py did not identify the path traversal", errors)

        exercise_adversarial_contract(skill, scripts[3], Path(temporary) / "adversarial", prompt, errors)


def exercise_package_validator(skill: Path, errors: List[str]) -> None:
    """Require malformed package metadata to produce a classified result, not a traceback."""

    with tempfile.TemporaryDirectory() as temporary:
        copied_skill = Path(temporary) / "oneshot-websites"
        shutil.copytree(skill, copied_skill)
        metadata_path = copied_skill / "metadata.json"
        original_metadata = metadata_path.read_bytes()
        metadata_path.write_bytes(b"{\xff}")
        result = run([sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)])
        assert_ok(
            result.returncode != 0 and "invalid JSON" in result.stdout and "Traceback" not in result.stderr,
            "package validator crashed or hid invalid UTF-8 metadata",
            errors,
        )
        metadata_path.write_bytes(original_metadata)

        skill_path = copied_skill / "SKILL.md"
        original_skill = skill_path.read_text(encoding="utf-8")

        critic_path = copied_skill / "agents" / "oneshot-critic.md"
        original_critic = critic_path.read_bytes()
        critic_path.unlink()
        missing_critic_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_critic_result.returncode != 0
            and "missing file: agents/oneshot-critic.md" in missing_critic_result.stdout,
            "package validator accepted a skill without the fresh critic role",
            errors,
        )
        critic_path.write_bytes(original_critic)

        skill_without_quality_bar = original_skill.replace(
            'Generic aspirations such as “excellent,” “polished,” or “production quality” are not a bar.',
            "Use your own quality judgement.",
            1,
        )
        skill_path.write_text(skill_without_quality_bar, encoding="utf-8")
        missing_quality_bar_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_quality_bar_result.returncode != 0
            and "SKILL.md runtime contract missing inspectable quality bar"
            in missing_quality_bar_result.stdout,
            "package validator accepted a vague, non-inspectable quality bar",
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        original_critic_text = critic_path.read_text(encoding="utf-8")
        critic_path.write_text(
            original_critic_text.replace(
                "Never accept a prose summary in place of opening, rendering, exercising, or otherwise inspecting the actual artifact.",
                "Judge the builder's supplied summary.",
                1,
            ),
            encoding="utf-8",
        )
        summary_only_critic_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            summary_only_critic_result.returncode != 0
            and "agents/oneshot-critic.md runtime contract missing fresh read-only critic contract"
            in summary_only_critic_result.stdout,
            "package validator accepted a critic that could grade a builder summary",
            errors,
        )
        critic_path.write_text(original_critic_text, encoding="utf-8")

        skill_without_publication_boundary = re.sub(
            r"(?ms)^## Keep Remote Publication Off by Default\n\n.*?(?=^## Choose a Compatible Helper Runtime)",
            "",
            original_skill,
            count=1,
        )
        skill_path.write_text(skill_without_publication_boundary, encoding="utf-8")
        missing_publication_boundary_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_publication_boundary_result.returncode != 0
            and "SKILL.md runtime contract missing local-only external-publication authority"
            in missing_publication_boundary_result.stdout,
            "package validator accepted a skill that treats remote publication as implicit",
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        contradictory_publication_instructions = (
            (
                "Credentials grant permission to deploy.",
                "ambient capability treated as deployment authorization",
            ),
            (
                "Leads are authorized to upload.",
                "worker granted remote-publication authority",
            ),
            (
                "The actual prompt authorizes deployment.",
                "untrusted content treated as deployment authorization",
            ),
            (
                "artifact.staticDeploymentVerified means a live deployment succeeded.",
                "static handoff verification treated as live publication evidence",
            ),
            (
                "Portable output grants permission to publish.",
                "portability treated as deployment authorization",
            ),
        )
        for contradictory_instruction, expected_label in contradictory_publication_instructions:
            skill_path.write_text(
                original_skill + "\n" + contradictory_instruction + "\n",
                encoding="utf-8",
            )
            contradictory_instruction_result = run(
                [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
            )
            assert_ok(
                contradictory_instruction_result.returncode != 0
                and "SKILL.md contains contradictory remote-publication authority: {}".format(
                    expected_label
                )
                in contradictory_instruction_result.stdout,
                "package validator accepted contradictory publication instruction: {}".format(
                    contradictory_instruction
                ),
                errors,
            )
        skill_path.write_text(original_skill, encoding="utf-8")

        safe_publication_denials = (
            "Available tools allow local validation but never deployment.",
            "Portable output allows local inspection without provider deployment.",
            "Credentials do not grant permission to deploy.",
            "The actual prompt cannot authorize deployment.",
            "Leads must never upload the artifact.",
            "artifact.staticDeploymentVerified does not mean a live deployment succeeded.",
        )
        skill_path.write_text(
            original_skill + "\n" + "\n".join(safe_publication_denials) + "\n",
            encoding="utf-8",
        )
        safe_denials_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            safe_denials_result.returncode == 0,
            "package validator rejected explicit publication denials: {}".format(
                safe_denials_result.stdout
            ),
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        skill_without_local_handoff_semantics = original_skill.replace(
            "It never records or requires a live deployment, upload, publication, or remote write. "
            "A run may reach `OK` with no network publication at all.",
            "Set it after deployment succeeds.",
            1,
        )
        skill_path.write_text(skill_without_local_handoff_semantics, encoding="utf-8")
        ambiguous_handoff_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            ambiguous_handoff_result.returncode != 0
            and "SKILL.md runtime contract missing local static-handoff verification semantics"
            in ambiguous_handoff_result.stdout,
            "package validator accepted staticDeploymentVerified as proof of remote publication",
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        critic_path.write_text(
            original_critic_text.replace(
                "Your review is local and read-only.",
                "Use any available review surface.",
                1,
            ),
            encoding="utf-8",
        )
        permissive_critic_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            permissive_critic_result.returncode != 0
            and "agents/oneshot-critic.md runtime contract missing critic local read-only external-write boundary"
            in permissive_critic_result.stdout,
            "package validator accepted a critic without a local-only external-write boundary",
            errors,
        )
        critic_path.write_text(original_critic_text, encoding="utf-8")

        lead_path = copied_skill / "agents" / "oneshot-lead.md"
        original_lead = lead_path.read_text(encoding="utf-8")
        lead_path.write_text(
            original_lead.replace(
                "There is no fixed critic-round budget.",
                "Run exactly three critic rounds.",
                1,
            ),
            encoding="utf-8",
        )
        fixed_round_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            fixed_round_result.returncode != 0
            and "agents/oneshot-lead.md runtime contract missing lead-owned quality gauntlet"
            in fixed_round_result.stdout,
            "package validator accepted a fixed critic-round budget",
            errors,
        )
        lead_path.write_text(original_lead, encoding="utf-8")

        skill_without_wasm_contract = re.sub(
            r"(?ms)^Treat WebAssembly as an earned implementation choice.*?(?=^For every non-trivial build,)",
            "",
            original_skill,
            count=1,
        )
        skill_path.write_text(skill_without_wasm_contract, encoding="utf-8")
        missing_wasm_contract_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_wasm_contract_result.returncode != 0
            and "SKILL.md runtime contract missing earned WebAssembly selection"
            in missing_wasm_contract_result.stdout,
            "package validator accepted a skill without evidence-gated WebAssembly selection",
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        lead_without_wasm_gate = re.sub(
            r"(?ms)^## WebAssembly Decision\n\n.*?(?=^## Quality Gauntlet)",
            "",
            original_lead,
            count=1,
        )
        lead_path.write_text(lead_without_wasm_gate, encoding="utf-8")
        missing_lead_wasm_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_lead_wasm_result.returncode != 0
            and "agents/oneshot-lead.md runtime contract missing lead WebAssembly decision gate"
            in missing_lead_wasm_result.stdout,
            "package validator accepted a lead role without the WebAssembly decision gate",
            errors,
        )
        lead_path.write_text(original_lead, encoding="utf-8")

        lead_path.write_text(
            original_lead.replace(
                "Your authority is local-build-only.",
                "Use the authority exposed by the environment.",
                1,
            ),
            encoding="utf-8",
        )
        permissive_lead_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            permissive_lead_result.returncode != 0
            and "agents/oneshot-lead.md runtime contract missing lead local-only external-write boundary"
            in permissive_lead_result.stdout,
            "package validator accepted a lead that could infer remote-write authority from available tools",
            errors,
        )
        lead_path.write_text(original_lead, encoding="utf-8")

        skill_without_temporary_contract = re.sub(
            r"(?m)^Keep disposable working state inside the run’s `\.tmp/`.*\n\n",
            "",
            original_skill,
            count=1,
        )
        skill_path.write_text(skill_without_temporary_contract, encoding="utf-8")
        missing_temporary_contract_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_temporary_contract_result.returncode != 0
            and "SKILL.md runtime contract missing run-local temporary containment"
            in missing_temporary_contract_result.stdout,
            "package validator accepted a skill without run-local temporary containment",
            errors,
        )

        skill_without_descendant_temporary_routing = original_skill.replace(
            "Every descendant receives the same run-local temporary path and supported temporary-environment routing",
            "Every descendant stays within the run",
            1,
        )
        skill_path.write_text(skill_without_descendant_temporary_routing, encoding="utf-8")
        missing_descendant_temporary_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_descendant_temporary_result.returncode != 0
            and "SKILL.md runtime contract missing descendant temporary routing"
            in missing_descendant_temporary_result.stdout,
            "package validator accepted descendants without run-local temporary routing",
            errors,
        )

        dispatch_path = copied_skill / "templates" / "worker-dispatch.md"
        original_dispatch = dispatch_path.read_text(encoding="utf-8")
        dispatch_path.write_text(
            re.sub(
                r"(?s)## Fresh Critic Role.*?\{\{ONESHOT_CRITIC_ROLE\}\}\n\n",
                "",
                original_dispatch,
                count=1,
            ),
            encoding="utf-8",
        )
        missing_critic_dispatch_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_critic_dispatch_result.returncode != 0
            and "templates/worker-dispatch.md runtime contract missing embedded fresh critic role"
            in missing_critic_dispatch_result.stdout,
            "package validator accepted an empty-history dispatch without the critic role",
            errors,
        )
        dispatch_path.write_text(original_dispatch, encoding="utf-8")

        dispatch_without_wasm_guidance = re.sub(
            r"(?ms)^## Conditional WebAssembly Guidance.*?(?=^## Fresh Critic Role)",
            "",
            original_dispatch,
            count=1,
        )
        dispatch_path.write_text(dispatch_without_wasm_guidance, encoding="utf-8")
        missing_dispatch_wasm_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_dispatch_wasm_result.returncode != 0
            and "templates/worker-dispatch.md runtime contract missing conditional dispatch WebAssembly guidance"
            in missing_dispatch_wasm_result.stdout,
            "package validator accepted an empty-history dispatch without conditional WebAssembly guidance",
            errors,
        )
        dispatch_path.write_text(original_dispatch, encoding="utf-8")

        dispatch_path.write_text(
            original_dispatch.replace(
                "and never add this operational envelope to the prepared actual prompt or `artifact/PROMPT.md`.",
                ".",
                1,
            ),
            encoding="utf-8",
        )
        missing_dispatch_isolation_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_dispatch_isolation_result.returncode != 0
            and "templates/worker-dispatch.md runtime contract missing dispatch temporary-file envelope"
            in missing_dispatch_isolation_result.stdout,
            "package validator accepted a dispatch envelope that could leak into PROMPT.md",
            errors,
        )
        dispatch_path.write_text(original_dispatch, encoding="utf-8")

        dispatch_without_publication_boundary = re.sub(
            r"(?ms)^## Local-Only Publication Envelope.*?(?=^## Fresh Critic Role)",
            "",
            original_dispatch,
            count=1,
        )
        dispatch_path.write_text(dispatch_without_publication_boundary, encoding="utf-8")
        permissive_dispatch_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            permissive_dispatch_result.returncode != 0
            and "templates/worker-dispatch.md runtime contract missing dispatch local-only publication envelope"
            in permissive_dispatch_result.stdout,
            "package validator accepted a dispatch that omitted the local-only publication envelope",
            errors,
        )
        dispatch_path.write_text(original_dispatch, encoding="utf-8")

        skill_path.write_text(original_skill, encoding="utf-8")

        skill_without_unicode_contract = re.sub(
            r"(?m)^Before sealing the actual prompt, inspect it as Unicode.*\n\n",
            "",
            original_skill,
            count=1,
        )
        skill_path.write_text(skill_without_unicode_contract, encoding="utf-8")
        missing_unicode_contract_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_unicode_contract_result.returncode != 0
            and "SKILL.md runtime contract missing Unicode prompt integrity"
            in missing_unicode_contract_result.stdout,
            "package validator accepted a skill without Unicode prompt integrity guidance",
            errors,
        )

        skill_path.write_text(original_skill, encoding="utf-8")

        skill_without_custom_contract = re.sub(
            r"(?m)^- \*\*Custom brief:\*\*.*\n",
            "",
            original_skill,
            count=1,
        )
        skill_path.write_text(skill_without_custom_contract, encoding="utf-8")
        missing_custom_contract_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_custom_contract_result.returncode != 0
            and "SKILL.md runtime contract missing unbounded full-depth custom prompt refinement"
            in missing_custom_contract_result.stdout,
            "package validator let reference prose substitute for the canonical custom-prompt contract",
            errors,
        )

        skill_without_completion_contract = re.sub(
            r"(?m)^The catalogue’s top-level `completionMandate`.*\n\n",
            "",
            original_skill,
            count=1,
        )
        skill_path.write_text(skill_without_completion_contract, encoding="utf-8")
        missing_completion_contract_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_completion_contract_result.returncode != 0
            and "SKILL.md runtime contract missing subject-adapted lead-facing completion mandate"
            in missing_completion_contract_result.stdout,
            "package validator let reference prose substitute for the canonical completion mandate",
            errors,
        )

        skill_without_verbatim_conflict = original_skill.replace(
            " If the user also forbids any appended text, stop before dispatch and report that the "
            "request conflicts with this skill’s mandatory prompt contract; never silently omit the mandate.",
            "",
        )
        skill_path.write_text(skill_without_verbatim_conflict, encoding="utf-8")
        missing_verbatim_conflict_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_verbatim_conflict_result.returncode != 0
            and "SKILL.md runtime contract missing unbounded full-depth custom prompt refinement"
            in missing_verbatim_conflict_result.stdout,
            "package validator accepted a verbatim custom-prompt rule that silently bypasses the mandate",
            errors,
        )

        skill_without_shortcuts_requirement = original_skill.replace(
            "not to take shortcuts or produce a cookie-cutter approximation",
            "not to produce a cookie-cutter approximation",
        )
        skill_path.write_text(skill_without_shortcuts_requirement, encoding="utf-8")
        missing_shortcuts_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_shortcuts_result.returncode != 0
            and "SKILL.md runtime contract missing subject-adapted lead-facing completion mandate"
            in missing_shortcuts_result.stdout,
            "package validator accepted a completion mandate without the explicit no-shortcuts requirement",
            errors,
        )

        skill_without_universal_depth = original_skill.replace(
            "must demand complete subject-specific depth",
            "must demand a polished result",
        )
        skill_path.write_text(skill_without_universal_depth, encoding="utf-8")
        missing_universal_depth_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_universal_depth_result.returncode != 0
            and "SKILL.md runtime contract missing subject-adapted lead-facing completion mandate"
            in missing_universal_depth_result.stdout,
            "package validator accepted a completion mandate without universal subject-specific depth",
            errors,
        )

        skill_without_replica_depth = original_skill.replace(
            "and smallest meaningful interactions—not merely a recognizable shell",
            "and basic interactions—not merely a recognizable shell",
        )
        skill_path.write_text(skill_without_replica_depth, encoding="utf-8")
        missing_replica_depth_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_replica_depth_result.returncode != 0
            and "SKILL.md runtime contract missing subject-adapted lead-facing completion mandate"
            in missing_replica_depth_result.stdout,
            "package validator accepted a replica mandate without smallest-interaction fidelity",
            errors,
        )

        skill_without_original_depth = original_skill.replace(
            "For an original experience, demand equivalent depth",
            "For an original experience, suggest some depth",
        )
        skill_path.write_text(skill_without_original_depth, encoding="utf-8")
        missing_original_depth_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_original_depth_result.returncode != 0
            and "SKILL.md runtime contract missing subject-adapted lead-facing completion mandate"
            in missing_original_depth_result.stdout,
            "package validator accepted a completion mandate without equivalent depth for original work",
            errors,
        )

        flattened_namespace = original_skill.replace(
            "  <YYYY-MM-DD-HH-MM-SS>-<experiment-slug>/",
            "  <run-id>/",
            1,
        )
        skill_path.write_text(flattened_namespace, encoding="utf-8")
        flattened_namespace_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            flattened_namespace_result.returncode != 0
            and "SKILL.md runtime contract missing flat slugged timestamp run layout"
            in flattened_namespace_result.stdout,
            "package validator accepted a non-slugged run layout",
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        nested_multiple_intent = original_skill.replace(
            "top-level experiment fan-out",
            "inner delegation",
            1,
        )
        skill_path.write_text(nested_multiple_intent, encoding="utf-8")
        nested_multiple_intent_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            nested_multiple_intent_result.returncode != 0
            and "SKILL.md runtime contract missing explicit outer experiment fan-out"
            in nested_multiple_intent_result.stdout,
            "package validator accepted inner delegation for explicit multiple-lead intent",
            errors,
        )

        divergent_replica_prompts = original_skill.replace(
            "Use the same prompt file as the preparation source for every instance",
            "Write a separate prompt file for every instance",
            1,
        )
        skill_path.write_text(divergent_replica_prompts, encoding="utf-8")
        divergent_replica_prompts_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            divergent_replica_prompts_result.returncode != 0
            and "SKILL.md runtime contract missing byte-identical replica prompts"
            in divergent_replica_prompts_result.stdout,
            "package validator accepted independently rewritten replica prompts",
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        skill_path.write_text(
            original_skill
            + "\nSelected catalogue entry: append experienceDirection unchanged as the second paragraph.\n",
            encoding="utf-8",
        )
        leaking_direction_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            leaking_direction_result.returncode != 0
            and "instruction to copy internal direction into the lead prompt" in leaking_direction_result.stdout,
            "package validator accepted an instruction that leaks internal guidance into PROMPT.md",
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        catalogue_authoring_path = copied_skill / "references" / "catalogue-authoring.md"
        original_catalogue_authoring = catalogue_authoring_path.read_text(encoding="utf-8")
        catalogue_authoring_path.write_text(
            re.sub(
                r"(?ms)^Catalogue verbs describe behavior inside the locally built experience,.*?\n\n",
                "",
                original_catalogue_authoring,
                count=1,
            ),
            encoding="utf-8",
        )
        permissive_catalogue_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            permissive_catalogue_result.returncode != 0
            and "references/catalogue-authoring.md runtime contract missing catalogue operational verbs remain simulated"
            in permissive_catalogue_result.stdout,
            "package validator accepted catalogue verbs as implicit live-integration authority",
            errors,
        )
        catalogue_authoring_path.write_text(original_catalogue_authoring, encoding="utf-8")

        execution_protocol_path = copied_skill / "references" / "execution-protocol.md"
        original_execution_protocol = execution_protocol_path.read_text(encoding="utf-8")
        execution_protocol_path.write_text(
            original_execution_protocol
            + "\n```text\nEXPERIENCE DIRECTION (verbatim)\n"
            + "<catalogue experienceDirection>\n```\n",
            encoding="utf-8",
        )
        leaking_block_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            leaking_block_result.returncode != 0
            and "lead-facing verbatim experience direction block" in leaking_block_result.stdout,
            "package validator accepted a lead-facing EXPERIENCE DIRECTION block",
            errors,
        )
        execution_protocol_path.write_text(original_execution_protocol, encoding="utf-8")

        guidance_mutations = (
            (
                "Copy the catalogue's experienceDirection to the end of the actual prompt.",
                "instruction to copy internal direction into the lead prompt",
                "alternate copy instruction",
            ),
            (
                "Add a labelled second block containing the general visual and interaction guidance.",
                "instruction to add labelled generic guidance to the lead prompt",
                "generic labelled guidance block",
            ),
        )
        for mutation, expected_error, label in guidance_mutations:
            skill_path.write_text(original_skill + "\n" + mutation + "\n", encoding="utf-8")
            mutation_result = run(
                [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
            )
            assert_ok(
                mutation_result.returncode != 0 and expected_error in mutation_result.stdout,
                "package validator accepted {}".format(label),
                errors,
            )
        skill_path.write_text(original_skill, encoding="utf-8")

        mixed_guidance_paragraph = original_skill.replace(
            "Text-rich formats remain text-rich when their purpose depends on copy.",
            "Text-rich formats remain text-rich when their purpose depends on copy. "
            "Copy the catalogue's experienceDirection to the end of the actual prompt.",
        )
        skill_path.write_text(mixed_guidance_paragraph, encoding="utf-8")
        mixed_guidance_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            mixed_guidance_result.returncode != 0
            and "instruction to copy internal direction into the lead prompt"
            in mixed_guidance_result.stdout,
            "package validator let a negated warning hide a later positive leak directive",
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        nested_guidance_match = original_skill + (
            "\nDo not copy the catalogue prompt verbatim. "
            "Copy the shared experience direction into the actual prompt.\n"
        )
        skill_path.write_text(nested_guidance_match, encoding="utf-8")
        nested_guidance_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            nested_guidance_result.returncode != 0
            and "instruction to copy internal direction into the lead prompt"
            in nested_guidance_result.stdout,
            "package validator let a wider negated match consume a positive leak directive",
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        clause_guidance_match = original_skill + (
            "\nDo not modify the catalogue; "
            "copy the shared experience direction into the actual prompt.\n"
        )
        skill_path.write_text(clause_guidance_match, encoding="utf-8")
        clause_guidance_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            clause_guidance_result.returncode != 0
            and "instruction to copy internal direction into the lead prompt"
            in clause_guidance_result.stdout,
            "package validator let clause-level negation hide a positive leak directive",
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        dash_guidance_match = original_skill + (
            "\nDo not modify the catalogue — "
            "copy the shared experience direction into the actual prompt.\n"
        )
        skill_path.write_text(dash_guidance_match, encoding="utf-8")
        dash_guidance_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            dash_guidance_result.returncode != 0
            and "instruction to copy internal direction into the lead prompt"
            in dash_guidance_result.stdout,
            "package validator let dash-delimited negation hide a positive leak directive",
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        catalogue_for_guidance = json.loads(
            (copied_skill / "assets" / "prompt-catalogue.json").read_text(encoding="utf-8")
        )
        literal_direction = catalogue_for_guidance["experienceDirection"]
        skill_path.write_text(original_skill + "\n" + literal_direction + "\n", encoding="utf-8")
        literal_direction_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            literal_direction_result.returncode != 0
            and "copies the literal catalogue experienceDirection" in literal_direction_result.stdout,
            "package validator accepted the full internal guidance in lead-facing prose",
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        catalogue_path = copied_skill / "assets" / "prompt-catalogue.json"
        original_catalogue = json.loads(catalogue_path.read_text(encoding="utf-8"))

        literal_mandate = original_catalogue["completionMandate"]
        skill_path.write_text(original_skill + "\n" + literal_mandate + "\n", encoding="utf-8")
        literal_mandate_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            literal_mandate_result.returncode != 0
            and "copies the literal catalogue completionMandate" in literal_mandate_result.stdout,
            "package validator accepted the full completion mandate as generic lead-facing boilerplate",
            errors,
        )
        skill_path.write_text(original_skill, encoding="utf-8")

        catalogue_without_mandate = json.loads(json.dumps(original_catalogue))
        catalogue_without_mandate.pop("completionMandate")
        catalogue_path.write_text(json.dumps(catalogue_without_mandate), encoding="utf-8")
        missing_mandate_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_mandate_result.returncode != 0
            and "missing completionMandate" in missing_mandate_result.stdout,
            "package validator accepted a catalogue without the universal completion mandate",
            errors,
        )

        altered_mandate = json.loads(json.dumps(original_catalogue))
        altered_mandate["completionMandate"] = altered_mandate["completionMandate"].replace(
            "no token budget limit",
            "a concise token budget",
        )
        catalogue_path.write_text(json.dumps(altered_mandate), encoding="utf-8")
        altered_mandate_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            altered_mandate_result.returncode != 0
            and "completionMandate differs from the canonical reviewed mandate" in altered_mandate_result.stdout
            and "completionMandate is missing no skill-imposed token budget" in altered_mandate_result.stdout,
            "package validator accepted a completion mandate with a token budget",
            errors,
        )

        multiline_mandate = json.loads(json.dumps(original_catalogue))
        multiline_mandate["completionMandate"] += "\nSecond line."
        catalogue_path.write_text(json.dumps(multiline_mandate), encoding="utf-8")
        multiline_mandate_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            multiline_mandate_result.returncode != 0
            and "completionMandate must fit on one line" in multiline_mandate_result.stdout,
            "package validator accepted a multi-line completion mandate",
            errors,
        )

        old_schema_catalogue = json.loads(json.dumps(original_catalogue))
        old_schema_catalogue["schemaVersion"] = "1.1"
        catalogue_path.write_text(json.dumps(old_schema_catalogue), encoding="utf-8")
        old_schema_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            old_schema_result.returncode != 0
            and "schemaVersion must be 1.2" in old_schema_result.stdout,
            "package validator accepted the pre-mandate catalogue schema",
            errors,
        )

        catalogue_without_direction = json.loads(json.dumps(original_catalogue))
        catalogue_without_direction.pop("experienceDirection")
        catalogue_path.write_text(json.dumps(catalogue_without_direction), encoding="utf-8")
        missing_direction_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_direction_result.returncode != 0
            and "missing experienceDirection" in missing_direction_result.stdout,
            "package validator accepted a catalogue without a shared experience direction",
            errors,
        )

        multiline_direction = json.loads(json.dumps(original_catalogue))
        multiline_direction["experienceDirection"] += "\nSecond line."
        catalogue_path.write_text(json.dumps(multiline_direction), encoding="utf-8")
        multiline_direction_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            multiline_direction_result.returncode != 0
            and "experienceDirection must fit on one line" in multiline_direction_result.stdout,
            "package validator accepted a multi-line shared experience direction",
            errors,
        )

        prescribed_direction = json.loads(json.dumps(original_catalogue))
        prescribed_direction["experienceDirection"] += " Build it with Three.js."
        catalogue_path.write_text(json.dumps(prescribed_direction), encoding="utf-8")
        prescribed_direction_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            prescribed_direction_result.returncode != 0
            and "named implementation recipe constraint" in prescribed_direction_result.stdout,
            "package validator accepted a shared direction that prescribes a library",
            errors,
        )

        unknown_stack_direction = json.loads(json.dumps(original_catalogue))
        unknown_stack_direction["experienceDirection"] += " Build it with Babylon.js and GSAP."
        catalogue_path.write_text(json.dumps(unknown_stack_direction), encoding="utf-8")
        unknown_stack_direction_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            unknown_stack_direction_result.returncode != 0
            and "differs from the canonical reviewed direction" in unknown_stack_direction_result.stdout,
            "package validator accepted an unlisted stack prescription in the shared direction",
            errors,
        )

        category_without_description = json.loads(json.dumps(original_catalogue))
        category_without_description["categories"][0].pop("description")
        catalogue_path.write_text(json.dumps(category_without_description), encoding="utf-8")
        missing_description_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_description_result.returncode != 0
            and "missing a description" in missing_description_result.stdout,
            "package validator accepted a catalogue namespace without a description",
            errors,
        )

        multiline_category_description = json.loads(json.dumps(original_catalogue))
        multiline_category_description["categories"][0]["description"] = "First line.\nSecond line."
        catalogue_path.write_text(json.dumps(multiline_category_description), encoding="utf-8")
        multiline_description_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            multiline_description_result.returncode != 0
            and "description must fit on one line" in multiline_description_result.stdout,
            "package validator accepted a multi-line catalogue namespace description",
            errors,
        )

        frozen_mutations = (
            "edited prompt",
            "reordered prompts",
            "renumbered prompt",
        )
        for mutation in frozen_mutations:
            mutated = json.loads(json.dumps(original_catalogue))
            prompts = mutated["prompts"]
            if mutation == "edited prompt":
                prompts[0]["prompt"] += " Changed."
            elif mutation == "reordered prompts":
                prompts[0], prompts[1] = prompts[1], prompts[0]
            else:
                prompts[0]["id"] = "ow-900"
            catalogue_path.write_text(json.dumps(mutated), encoding="utf-8")
            mutation_result = run(
                [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
            )
            assert_ok(
                mutation_result.returncode != 0
                and "frozen append-only prefix" in mutation_result.stdout,
                "package validator accepted {} in the frozen catalogue prefix".format(mutation),
                errors,
            )

        shortened = json.loads(json.dumps(original_catalogue))
        shortened["prompts"].pop(0)
        catalogue_path.write_text(json.dumps(shortened), encoding="utf-8")
        shortened_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            shortened_result.returncode != 0
            and "must contain at least 100 prompts" in shortened_result.stdout,
            "package validator accepted deletion from the frozen catalogue prefix",
            errors,
        )

        surrogate_catalogue = json.loads(json.dumps(original_catalogue))
        surrogate_catalogue["prompts"][0]["title"] = "\ud800"
        catalogue_path.write_text(json.dumps(surrogate_catalogue), encoding="utf-8")
        surrogate_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            surrogate_result.returncode != 0
            and "frozen append-only prefix" in surrogate_result.stdout
            and "Traceback" not in surrogate_result.stderr,
            "package validator crashed on an escaped unpaired surrogate in the catalogue",
            errors,
        )

        extended = json.loads(json.dumps(original_catalogue))
        extended["prompts"].append(
            {
                "id": "ow-101",
                "slug": "append-only-fixture",
                "title": "Append Only Fixture",
                "description": "Explore an original interactive experience added safely to the growing catalogue.",
                "category": "immersive-games",
                "prompt": "Create an original interactive experience that proves the catalogue can grow by appending entries.",
                "tags": ["append-only", "fixture", "growth"],
            }
        )
        catalogue_path.write_text(json.dumps(extended), encoding="utf-8")
        extension_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            extension_result.returncode == 0,
            "package validator rejected an append-only catalogue extension: {}".format(
                extension_result.stdout or extension_result.stderr
            ),
            errors,
        )

        for field in ("title", "description", "prompt", "tag"):
            surrogate_extension = json.loads(json.dumps(extended))
            if field == "tag":
                surrogate_extension["prompts"][-1]["tags"][0] = "\ud800"
            else:
                surrogate_extension["prompts"][-1][field] = "\ud800"
            catalogue_path.write_text(json.dumps(surrogate_extension), encoding="utf-8")
            surrogate_extension_result = run(
                [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
            )
            assert_ok(
                surrogate_extension_result.returncode != 0
                and "Traceback" not in surrogate_extension_result.stderr,
                "package validator accepted or crashed on an escaped surrogate in appended {}".format(field),
                errors,
            )

        for invalid_extension_id in ("foo-999", "ow-102"):
            invalid_extension = json.loads(json.dumps(extended))
            invalid_extension["prompts"][-1]["id"] = invalid_extension_id
            catalogue_path.write_text(json.dumps(invalid_extension), encoding="utf-8")
            invalid_extension_result = run(
                [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
            )
            assert_ok(
                invalid_extension_result.returncode != 0
                and (
                    "invalid stable id" in invalid_extension_result.stdout
                    or "next append-only stable id ow-101" in invalid_extension_result.stdout
                ),
                "package validator accepted out-of-sequence appended id {}".format(
                    invalid_extension_id
                ),
                errors,
            )

        spaced_identity = json.loads(json.dumps(extended))
        spaced_identity["prompts"][-1]["id"] = " ow-101 "
        spaced_identity["prompts"][-1]["slug"] = " append-only-fixture "
        spaced_identity["prompts"][-1]["category"] = " immersive-games "
        catalogue_path.write_text(json.dumps(spaced_identity), encoding="utf-8")
        spaced_identity_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            spaced_identity_result.returncode != 0
            and "id must not contain surrounding whitespace" in spaced_identity_result.stdout
            and "slug must not contain surrounding whitespace" in spaced_identity_result.stdout
            and "category must not contain surrounding whitespace" in spaced_identity_result.stdout,
            "package validator accepted surrounding whitespace in appended identity fields",
            errors,
        )

        missing_prompt_description = json.loads(json.dumps(extended))
        missing_prompt_description["prompts"][-1].pop("description")
        catalogue_path.write_text(json.dumps(missing_prompt_description), encoding="utf-8")
        missing_prompt_description_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            missing_prompt_description_result.returncode != 0
            and "missing a description" in missing_prompt_description_result.stdout,
            "package validator accepted a prompt without a scan-friendly description",
            errors,
        )

        verbose_prompt_metadata = json.loads(json.dumps(extended))
        verbose_prompt_metadata["prompts"][-1]["title"] = "An Extremely Long and Needlessly Esoteric Catalogue Experience Title for Hurried People"
        verbose_prompt_metadata["prompts"][-1]["description"] = " ".join(
            ["This"] * 19
        )
        catalogue_path.write_text(json.dumps(verbose_prompt_metadata), encoding="utf-8")
        verbose_prompt_metadata_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            verbose_prompt_metadata_result.returncode != 0
            and "plain label" in verbose_prompt_metadata_result.stdout
            and "scan-friendly" in verbose_prompt_metadata_result.stdout,
            "package validator accepted verbose catalogue browsing metadata",
            errors,
        )

        disguised_duplicate = json.loads(json.dumps(original_catalogue))
        duplicate_entry = json.loads(json.dumps(disguised_duplicate["prompts"][0]))
        duplicate_entry["id"] = "ow-101"
        duplicate_entry["slug"] = "disguised-duplicate"
        duplicate_entry["title"] += " "
        duplicate_entry["prompt"] += " "
        disguised_duplicate["prompts"].append(duplicate_entry)
        catalogue_path.write_text(json.dumps(disguised_duplicate), encoding="utf-8")
        duplicate_result = run(
            [sys.executable, str(copied_skill / "scripts" / "validate.py"), str(copied_skill)]
        )
        assert_ok(
            duplicate_result.returncode != 0
            and "duplicate titles" in duplicate_result.stdout
            and "duplicate prompt texts" in duplicate_result.stdout,
            "package validator accepted a whitespace-disguised duplicate catalogue entry",
            errors,
        )


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1
    skill = Path(sys.argv[1]).resolve()
    errors: List[str] = []
    check_evals(skill, errors)
    exercise_runtime_scripts(skill, errors)
    exercise_package_validator(skill, errors)

    if errors:
        print("FAIL")
        for error in errors:
            print("- {}".format(error))
        return 1
    print("PASS: eval, catalogue, provenance, and static-handoff checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

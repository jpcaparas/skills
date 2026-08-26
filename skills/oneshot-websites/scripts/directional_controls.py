#!/usr/bin/env python3
"""Shared contracts for directional-control preparation and verification."""

from __future__ import annotations

import hashlib
import math
import os
import re
import stat
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


DIRECTIONAL_CONTROL_CONTRACT_VERSION = "1.1"
DIRECTIONAL_CONTROL_PROBE_SCHEMA = "1.0"
DIRECTIONAL_CONTROL_EVIDENCE_SCHEMA = "1.0"
DIRECTIONAL_CONTROL_EVIDENCE_SUFFIX = ".directional-controls.json"
DIRECTIONAL_CONTROL_PROBE_GLOBAL = "__ONESHOT_DIRECTIONAL_CONTROL_PROBE__"
DIRECTIONAL_TECHNICAL_PROMPT_PATH = ".tmp/TECHNICAL_PROMPT.md"
DIRECTIONAL_TECHNICAL_PROMPT_LIFECYCLE = "delete-with-run-temporary-storage"
DIRECTIONAL_RESPONSE_EPSILON = 1e-4

_GAME_OR_SIMULATION_RE = re.compile(
    r"\b(?:game|gaming|racer|racing|simulation|simulator)\b",
    re.IGNORECASE,
)
_THREE_DIMENSIONAL_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:3[ -]?d|three[ -]dimensional)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_DIRECTIONAL_INTERACTION_RE = re.compile(
    r"\b(?:camera controls?|directional|drive|driving|flight|flying|first[ -]person|"
    r"kart|movement|orbit|platformer|racer|racing|shooter|steer|steering|strafe|"
    r"strafing|third[ -]person|turn|turning|vehicle|walk|walking)\b",
    re.IGNORECASE,
)
_EXPLICIT_DIRECTIONAL_KEYS_RE = re.compile(
    r"\b(?:WASD|arrow[ -]keys?|KeyA|KeyD|ArrowLeft|ArrowRight)\b",
    re.IGNORECASE,
)
_PASSIVE_WITHOUT_DIRECTIONAL_CONTROLS_RE = re.compile(
    r"\bpassive\b.{0,160}\b(?:no|without)\b.{0,80}"
    r"\b(?:camera controls?|directional|movement|orbit|steering|turning)\b",
    re.IGNORECASE | re.DOTALL,
)


class DirectionalControlError(ValueError):
    """Raised when a directional-control contract or artifact is invalid."""


@dataclass(frozen=True)
class DirectionalControlRequirement:
    """Prepared applicability that a worker-owned record cannot downgrade."""

    required: bool
    basis: str
    signals: tuple[str, ...]


@dataclass(frozen=True)
class ArtifactTreeDigest:
    """Digest and bounded inventory for one portable artifact tree."""

    sha256: str
    files: int
    bytes: int


@dataclass(frozen=True)
class DirectionalSample:
    """One vector observation from the artifact's production control state."""

    frame: str
    measurement: str
    position: tuple[float, ...]
    forward: tuple[float, ...]
    right: tuple[float, ...]


@dataclass(frozen=True)
class DirectionalResponse:
    """Signed response in the sample's active control frame."""

    measurement: str
    value: float


def infer_directional_control_requirement(
    experiment: str,
    prompt: str,
    force_required: bool = False,
) -> DirectionalControlRequirement:
    """Classify prompts conservatively while making racing controls unavoidable."""

    combined = f"{experiment}\n{prompt}"
    signals: list[str] = []
    if _GAME_OR_SIMULATION_RE.search(combined):
        signals.append("game-or-simulation")
    if _THREE_DIMENSIONAL_RE.search(combined):
        signals.append("three-dimensional")
    if _DIRECTIONAL_INTERACTION_RE.search(combined):
        signals.append("directional-interaction")
    if _EXPLICIT_DIRECTIONAL_KEYS_RE.search(combined):
        signals.append("explicit-directional-keys")
    if force_required:
        signals.append("coordinator-required")

    passive_without_directional_controls = bool(
        _PASSIVE_WITHOUT_DIRECTIONAL_CONTROLS_RE.search(combined)
    )
    if passive_without_directional_controls:
        signals.append("passive-without-directional-controls")

    interactive_subject = any(
        signal in signals for signal in ("game-or-simulation", "three-dimensional")
    )
    directional = any(
        signal in signals
        for signal in ("directional-interaction", "explicit-directional-keys")
    )
    required = force_required or (
        interactive_subject
        and directional
        and not (
            passive_without_directional_controls
            and "game-or-simulation" not in signals
            and "explicit-directional-keys" not in signals
        )
    )
    basis = "coordinator-required" if force_required else "prepared-prompt-analysis"
    return DirectionalControlRequirement(required, basis, tuple(signals))


def directional_control_contract(
    requirement: DirectionalControlRequirement,
    run_id: str,
) -> dict[str, Any]:
    """Serialize the prepared applicability into run and receipt records."""

    evidence_path = (
        f".oneshot-provenance/{run_id}{DIRECTIONAL_CONTROL_EVIDENCE_SUFFIX}"
        if requirement.required
        else None
    )
    return {
        "required": requirement.required,
        "contractVersion": DIRECTIONAL_CONTROL_CONTRACT_VERSION,
        "basis": requirement.basis,
        "signals": list(requirement.signals),
        "evidencePath": evidence_path,
        "technicalPrompt": (
            {
                "path": DIRECTIONAL_TECHNICAL_PROMPT_PATH,
                "lifecycle": DIRECTIONAL_TECHNICAL_PROMPT_LIFECYCLE,
            }
            if requirement.required
            else None
        ),
    }


def reject_internal_directional_contract_in_prompt(prompt: str) -> None:
    """Keep coordinator-only probe syntax out of the portable human prompt."""

    leaked_markers = {
        DIRECTIONAL_CONTROL_PROBE_GLOBAL,
        "oneshot-directional-probe=1",
        "OneshotDirectionalControlProbe",
        "DirectionalControlSample",
        "ONESHOT_DIRECTIONAL_CONTROL_PROBE",
    }
    leaked = sorted(marker for marker in leaked_markers if marker.casefold() in prompt.casefold())
    if leaked:
        raise DirectionalControlError(
            "artifact/PROMPT.md must remain a prose experience brief and must not contain "
            "the internal directional-control probe contract: "
            + ", ".join(leaked)
            + "; remove the machine contract from the actual prompt because preparation "
            "creates .tmp/TECHNICAL_PROMPT.md for applicable runs"
        )


def validate_directional_technical_prompt_contract(prompt: str) -> None:
    """Reject a transient technical prompt that cannot drive the browser gate."""

    required_patterns = {
        "probe global": re.compile(re.escape(DIRECTIONAL_CONTROL_PROBE_GLOBAL)),
        "query gate": re.compile(r"oneshot-directional-probe=1"),
        "schema version": re.compile(r"schemaVersion.{0,20}1\.0", re.DOTALL),
        "production-state": re.compile(r"\bproduction[ -]state\b", re.IGNORECASE),
        "probe": re.compile(r"\bprobe\b", re.IGNORECASE),
        "deterministic reset": re.compile(r"\breset\w*\b", re.IGNORECASE),
        "position": re.compile(r"\bposition\b", re.IGNORECASE),
        "forward": re.compile(r"\bforward\b", re.IGNORECASE),
        "active-frame right basis": re.compile(
            r"\b(?:active[ -]frame|control[ -]frame)\b.{0,80}\bright\b|"
            r"\bright\b.{0,80}\b(?:active[ -]frame|control[ -]frame)\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "A and ArrowLeft": re.compile(r"\bA\b.{0,80}\bArrowLeft\b", re.IGNORECASE | re.DOTALL),
        "D and ArrowRight": re.compile(r"\bD\b.{0,80}\bArrowRight\b", re.IGNORECASE | re.DOTALL),
    }
    missing = [label for label, expression in required_patterns.items() if not expression.search(prompt)]
    if missing:
        raise DirectionalControlError(
            "transient directional TECHNICAL_PROMPT.md is missing its executable gate contract: "
            + ", ".join(missing)
        )


def artifact_tree_digest(
    artifact_root: Path,
    max_files: int = 1_000,
    max_file_bytes: int = 5 * 1024 * 1024,
    max_total_bytes: int = 100 * 1024 * 1024,
) -> ArtifactTreeDigest:
    """Hash a bounded ordinary-file tree without following links."""

    try:
        root_stat = artifact_root.lstat()
    except OSError as error:
        raise DirectionalControlError(f"unable to inspect artifact directory: {error}") from error
    if not stat.S_ISDIR(root_stat.st_mode):
        raise DirectionalControlError("artifact path must be an ordinary directory")

    files: list[Path] = []
    for directory, directory_names, file_names in os.walk(artifact_root, followlinks=False):
        directory_path = Path(directory)
        for name in list(directory_names):
            child = directory_path / name
            try:
                child_stat = child.lstat()
            except OSError as error:
                raise DirectionalControlError(f"unable to inspect artifact directory {child}: {error}") from error
            if not stat.S_ISDIR(child_stat.st_mode):
                raise DirectionalControlError(f"artifact directories must not be links or special files: {child}")
        for name in file_names:
            files.append(directory_path / name)
            if len(files) > max_files:
                raise DirectionalControlError(f"artifact exceeds the {max_files}-file verification limit")

    digest = hashlib.sha256(b"oneshot-artifact-tree-v1\0")
    total_bytes = 0
    for path in sorted(files, key=lambda value: value.relative_to(artifact_root).as_posix()):
        try:
            metadata = path.lstat()
        except OSError as error:
            raise DirectionalControlError(f"unable to inspect artifact file {path}: {error}") from error
        if not stat.S_ISREG(metadata.st_mode):
            raise DirectionalControlError(f"artifact files must be ordinary non-symlink files: {path}")
        if metadata.st_size > max_file_bytes:
            raise DirectionalControlError(
                f"artifact file exceeds the {max_file_bytes}-byte verification limit: {path}"
            )
        total_bytes += metadata.st_size
        if total_bytes > max_total_bytes:
            raise DirectionalControlError(
                f"artifact exceeds the {max_total_bytes}-byte verification limit"
            )

        relative = path.relative_to(artifact_root).as_posix().encode("utf-8")
        digest.update(struct.pack(">I", len(relative)))
        digest.update(relative)
        digest.update(struct.pack(">Q", metadata.st_size))
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        try:
            descriptor = os.open(path, flags)
        except OSError as error:
            raise DirectionalControlError(f"unable to open artifact file {path}: {error}") from error
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_dev != metadata.st_dev
                or opened.st_ino != metadata.st_ino
                or opened.st_size != metadata.st_size
            ):
                raise DirectionalControlError(f"artifact file changed while hashing: {path}")
            while True:
                chunk = os.read(descriptor, 64 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        finally:
            os.close(descriptor)

    return ArtifactTreeDigest(digest.hexdigest(), len(files), total_bytes)


def parse_directional_sample(value: object) -> DirectionalSample:
    """Validate the small, typed observation returned by the browser adapter."""

    if not isinstance(value, Mapping):
        raise DirectionalControlError("control probe sample must be an object")
    frame = value.get("frame")
    measurement = value.get("measurement")
    if not isinstance(frame, str) or not frame.strip():
        raise DirectionalControlError("control probe sample.frame must be a non-blank string")
    if measurement not in {"position", "heading"}:
        raise DirectionalControlError("control probe sample.measurement must be position or heading")
    position = _finite_vector(value.get("position"), "position")
    forward = _finite_vector(value.get("forward"), "forward")
    right = _finite_vector(value.get("right"), "right")
    dimensions = {len(position), len(forward), len(right)}
    if len(dimensions) != 1:
        raise DirectionalControlError("position, forward, and right vectors must use the same dimensions")
    _normalized(forward, "forward")
    _normalized(right, "right")
    return DirectionalSample(frame.strip(), str(measurement), position, forward, right)


def directional_response(
    before: DirectionalSample,
    after: DirectionalSample,
) -> DirectionalResponse:
    """Measure left/right response relative to the initial active-frame basis."""

    if before.frame != after.frame:
        raise DirectionalControlError("control probe frame changed during one isolated key check")
    if before.measurement != after.measurement:
        raise DirectionalControlError("control probe measurement changed during one isolated key check")
    if len(before.position) != len(after.position):
        raise DirectionalControlError("control probe vector dimensions changed during one isolated key check")

    right = _normalized(before.right, "right")
    if before.measurement == "position":
        delta = tuple(end - start for start, end in zip(before.position, after.position))
        value = _dot(delta, right)
    else:
        initial_forward = _normalized(before.forward, "forward")
        final_forward = _normalized(after.forward, "forward")
        value = _dot(final_forward, right) - _dot(initial_forward, right)
    if not math.isfinite(value):
        raise DirectionalControlError("control probe produced a non-finite directional response")
    return DirectionalResponse(before.measurement, value)


def response_matches_direction(value: float, expected: str) -> bool:
    """Apply the fixed semantic sign contract used by the final gate."""

    if expected == "left":
        return value < -DIRECTIONAL_RESPONSE_EPSILON
    if expected == "right":
        return value > DIRECTIONAL_RESPONSE_EPSILON
    raise DirectionalControlError(f"unsupported expected direction: {expected}")


def _finite_vector(value: object, label: str) -> tuple[float, ...]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) not in {2, 3}
    ):
        raise DirectionalControlError(f"control probe sample.{label} must be a 2D or 3D vector")
    converted: list[float] = []
    for component in value:
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise DirectionalControlError(f"control probe sample.{label} must contain only numbers")
        number = float(component)
        if not math.isfinite(number):
            raise DirectionalControlError(f"control probe sample.{label} must contain finite numbers")
        converted.append(number)
    return tuple(converted)


def _normalized(value: Iterable[float], label: str) -> tuple[float, ...]:
    vector = tuple(value)
    magnitude = math.sqrt(sum(component * component for component in vector))
    if not math.isfinite(magnitude) or magnitude <= DIRECTIONAL_RESPONSE_EPSILON:
        raise DirectionalControlError(f"control probe {label} vector must have non-zero magnitude")
    return tuple(component / magnitude for component in vector)


def _dot(left: Iterable[float], right: Iterable[float]) -> float:
    return sum(first * second for first, second in zip(left, right))

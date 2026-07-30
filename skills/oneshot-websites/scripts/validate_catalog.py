#!/usr/bin/env python3
"""Validate one-shot website run provenance and drop-ready static artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Optional, Tuple
from urllib.parse import unquote, urljoin, urlsplit

from build_catalog_index import (
    CATALOGUE_LOCK,
    CatalogueBuildError,
    FLAT_RUN_ID_RE,
    LEGACY_RUN_ID_RE,
    NAMESPACE_TEMP_RE,
    STALE_INDEX_RE,
    build_html,
    is_supported_run_id,
    parse_flat_run_id,
)
from runtime_contract import (
    BoundedReadError,
    find_likely_mojibake,
    identity_key,
    is_abandoned_run_reservation,
    is_appledouble_sidecar,
    parse_json_bounded,
    read_regular_file_bounded,
)


STATUSES = {"PLANNED", "RUNNING", "OK", "PARTIAL", "BLOCKED", "ERROR"}
CLASSIFICATIONS = {"autonomous-one-shot", "rerun", "curated-attempt"}
GAUNTLET_VERDICTS = {"NOT_READY", "READY", "BLOCKED"}
GAUNTLET_STOP_REASONS = {
    "bar-met",
    "no-material-actionable-gap",
    "genuine-blocker",
    "not-required",
    "user-stopped",
}
SUCCESSFUL_GAUNTLET_STOP_REASONS = {"bar-met", "no-material-actionable-gap"}
GAUNTLET_BAR_VALIDATION_RESULTS = {"accepted", "revised", "fallback-reviewed"}
IDENTITY_MARKER = ".oneshot-identity.json"
DROP_MAX_FILES = 1_000
DROP_MAX_FILE_BYTES = 5 * 1024 * 1024
DROP_MAX_TOTAL_BYTES = 100 * 1024 * 1024
VALIDATION_MAX_DIRECTORIES = 10_000
VALIDATION_MAX_DEPTH = 128
MAX_LOCAL_REFERENCE_CHECKS = DROP_MAX_FILES * 4
MAX_REFERENCE_DISPLAY_CHARS = 240
MAX_LOCAL_REFERENCE_TEXT_CHARS = 512 * 1024
MAX_CSS_SCAN_BYTES = 20 * 1024 * 1024
METADATA_MAX_BYTES = 1024 * 1024
PREPROCESS_ONLY_SUFFIXES = {
    ".astro",
    ".jsx",
    ".less",
    ".sass",
    ".scss",
    ".svelte",
    ".ts",
    ".tsx",
    ".vue",
}
BUILD_OR_PROVIDER_FILES = {
    "angular.json",
    "astro.config.js",
    "astro.config.mjs",
    "astro.config.ts",
    "bun.lock",
    "bun.lockb",
    "composer.json",
    "deno.json",
    "deno.jsonc",
    "gatsby-config.js",
    "gatsby-config.mjs",
    "gatsby-config.ts",
    "go.mod",
    "Makefile",
    "netlify.toml",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "nuxt.config.js",
    "nuxt.config.ts",
    "package-lock.json",
    "package.json",
    "Pipfile",
    "pnpm-lock.yaml",
    "pyproject.toml",
    "requirements.txt",
    "svelte.config.js",
    "svelte.config.ts",
    "tsconfig.json",
    "vercel.json",
    "vite.config.js",
    "vite.config.mjs",
    "vite.config.ts",
    "wrangler.json",
    "wrangler.jsonc",
    "wrangler.toml",
    "yarn.lock",
}
NON_DEPLOYABLE_DIRECTORIES = {
    ".bzr",
    ".cache",
    ".git",
    ".hg",
    ".netlify",
    ".next",
    ".now",
    ".svn",
    ".turbo",
    ".tmp",
    ".venv",
    ".vercel",
    ".yarn",
    "__pycache__",
    "node_modules",
    "venv",
}
SOURCE_TAGS = {"audio", "embed", "iframe", "img", "input", "script", "source", "track", "video"}
HREF_TAGS = {"image", "use"}
RESOURCE_LINK_RELS = {
    "apple-touch-icon",
    "icon",
    "manifest",
    "mask-icon",
    "modulepreload",
    "preload",
    "stylesheet",
}
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE | re.DOTALL)
CSS_IMPORT_RE = re.compile(r"@import\s+(['\"])(.*?)\1", re.IGNORECASE | re.DOTALL)
CSS_IMAGE_SET_START_RE = re.compile(r"(?:-webkit-)?image-set\(", re.IGNORECASE)
CSS_IMAGE_SET_CANDIDATE_RE = re.compile(r"(?:^|,)\s*(['\"])(.*?)\1", re.DOTALL)
BUILD_OR_PROVIDER_FILE_NAMES = {value.casefold() for value in BUILD_OR_PROVIDER_FILES}
SSH_PRIVATE_KEY_FILE_NAMES = {
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}
PRIVATE_KEY_LABELLED_BASENAMES = ("private-key", "private_key")
PRIVATE_KEY_BEGIN_MARKERS = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN DSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"-----BEGIN PGP PRIVATE KEY BLOCK-----",
)


@dataclass(frozen=True)
class WorkerIdentity:
    """Validated worker telemetry shared by the run manifest and report."""

    lead: Optional[str]
    descendants: tuple[str, ...]


@dataclass(frozen=True)
class QualityGauntletEvidence:
    """Normalized fields needed to validate a successful gauntlet record."""

    applicability: Optional[str]
    not_required_reason: Optional[str]
    bar: Optional[str]
    provenance: tuple[str, ...]
    bar_validation_result: Optional[str]
    bar_validation_evidence: Optional[str]
    bar_revisions: tuple[str, ...]
    fresh_critic_available: Optional[bool]
    round_count: int
    verdicts: tuple[str, ...]
    integration_required: Optional[bool]
    integration_result: Optional[str]
    integration_evidence: Optional[str]
    fallback_evidence: Optional[str]
    stop_reason: Optional[str]


@dataclass(frozen=True)
class PreparedRunContracts:
    """Coordinator-anchored contracts that worker-owned files cannot downgrade."""

    temporary: bool
    quality_gauntlet: bool


class LocalReferenceParser(HTMLParser):
    """Collect browser-loaded HTML and inline-CSS references."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []
        self.inline_styles: list[str] = []
        self.base_href: Optional[str] = None
        self.reference_overflow = False
        self._reference_seen: set[str] = set()
        self._inline_style_seen: set[str] = set()
        self._retained_reference_chars = 0
        self._inside_style = False
        self._style_parts: list[str] = []

    def _append_reference(self, value: str) -> None:
        prefix = value[:32].lstrip().casefold()
        if prefix.startswith(
            ("data:", "blob:", "http:", "https:", "mailto:", "tel:", "javascript:", "//")
        ):
            return
        if value in self._reference_seen:
            return
        if (
            len(self._reference_seen) >= MAX_LOCAL_REFERENCE_CHECKS
            or self._retained_reference_chars + len(value) > MAX_LOCAL_REFERENCE_TEXT_CHARS
        ):
            self.reference_overflow = True
            return
        self._reference_seen.add(value)
        self._retained_reference_chars += len(value)
        self.references.append(value)

    def _append_inline_style(self, value: str) -> None:
        if value in self._inline_style_seen:
            return
        if (
            len(self._inline_style_seen) >= MAX_LOCAL_REFERENCE_CHECKS
            or self._retained_reference_chars + len(value) > MAX_LOCAL_REFERENCE_TEXT_CHARS
        ):
            self.reference_overflow = True
            return
        self._inline_style_seen.add(value)
        self._retained_reference_chars += len(value)
        self.inline_styles.append(value)

    def handle_starttag(self, tag: str, attrs: list[Tuple[str, Optional[str]]]) -> None:
        normalized_tag = tag.casefold()
        normalized_attrs = {name.casefold(): value for name, value in attrs}
        link_rel = {
            token.casefold()
            for token in (normalized_attrs.get("rel") or "").split()
        }
        if normalized_tag == "style":
            self._inside_style = True
            self._style_parts = []
        for name, value in attrs:
            if value is None:
                continue
            normalized_name = name.casefold()
            if normalized_tag == "base" and normalized_name == "href" and self.base_href is None:
                self.base_href = value
            elif normalized_name == "src" and normalized_tag in SOURCE_TAGS:
                self._append_reference(value)
            elif normalized_name == "poster" and normalized_tag == "video":
                self._append_reference(value)
            elif normalized_name == "data" and normalized_tag == "object":
                self._append_reference(value)
            elif normalized_name in {"href", "xlink:href"} and normalized_tag in HREF_TAGS:
                self._append_reference(value)
            elif (
                normalized_name == "href"
                and normalized_tag == "link"
                and bool(link_rel & RESOURCE_LINK_RELS)
            ):
                self._append_reference(value)
            elif normalized_name in {"srcset", "imagesrcset"}:
                for reference in srcset_references(value):
                    self._append_reference(reference)
                    if self.reference_overflow:
                        break
            elif normalized_name == "style":
                self._append_inline_style(value)

    def handle_data(self, data: str) -> None:
        if self._inside_style:
            self._style_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "style" and self._inside_style:
            self._append_inline_style("".join(self._style_parts))
            self._inside_style = False
            self._style_parts = []

    def finish(self) -> None:
        """Retain CSS from a malformed document whose final style tag is unclosed."""

        if self._inside_style:
            if self.rawdata:
                self._style_parts.append(self.rawdata)
                self.rawdata = ""
            self._append_inline_style("".join(self._style_parts))
            self._inside_style = False
            self._style_parts = []


def srcset_references(value: str) -> Iterator[str]:
    """Extract srcset URLs while preserving commas inside data candidates."""

    position = 0
    length = len(value)
    while position < length:
        while position < length and (value[position].isspace() or value[position] == ","):
            position += 1
        start = position
        is_data = value[start : start + 5].casefold() == "data:"
        while position < length and not value[position].isspace() and (is_data or value[position] != ","):
            position += 1
        candidate = value[start:position].rstrip(",")
        if position < length and value[position] == ",":
            position += 1
            if candidate and not is_data:
                yield candidate
            continue
        while position < length and value[position] != ",":
            position += 1
        if position < length:
            position += 1
        if candidate and not is_data:
            yield candidate


def object_value(value: object) -> dict[str, Any]:
    """Return a JSON object value, treating other JSON values as absent."""
    return value if isinstance(value, dict) else {}


def text_value(value: object) -> Optional[str]:
    """Return a meaningful string or None for malformed manifest fields."""
    return value.strip() if isinstance(value, str) and value.strip() else None


def parse_worker_identity(
    record: dict[str, Any],
    source: Path,
    prefix: str,
    errors: list[str],
) -> Optional[WorkerIdentity]:
    """Parse required worker telemetry fields into one comparable value."""

    field_prefix = f"{prefix}." if prefix else ""
    valid = True

    if "leadWorkerId" not in record:
        errors.append(f"{source}: {field_prefix}leadWorkerId is required")
        lead: Optional[str] = None
        valid = False
    else:
        lead_value = record.get("leadWorkerId")
        if lead_value is None:
            lead = None
        elif isinstance(lead_value, str) and lead_value.strip():
            lead = lead_value
        else:
            errors.append(
                f"{source}: {field_prefix}leadWorkerId must be null or a non-blank string"
            )
            lead = None
            valid = False

    descendants_value = record.get("descendantWorkerIds")
    descendants: list[str] = []
    normalized_descendants: set[str] = set()
    if not isinstance(descendants_value, list):
        errors.append(f"{source}: {field_prefix}descendantWorkerIds must be an array")
        valid = False
    else:
        for index, descendant_value in enumerate(descendants_value):
            if not isinstance(descendant_value, str) or not descendant_value.strip():
                errors.append(
                    f"{source}: {field_prefix}descendantWorkerIds[{index}] "
                    "must be a non-blank string"
                )
                valid = False
                continue
            normalized = descendant_value.strip()
            if normalized in normalized_descendants:
                errors.append(
                    f"{source}: {field_prefix}descendantWorkerIds must contain unique IDs"
                )
                valid = False
                continue
            normalized_descendants.add(normalized)
            descendants.append(descendant_value)

    if lead is not None and lead.strip() in normalized_descendants:
        errors.append(
            f"{source}: {field_prefix}descendantWorkerIds must not repeat leadWorkerId"
        )
        valid = False

    if not valid:
        return None
    return WorkerIdentity(lead=lead, descendants=tuple(descendants))


def is_passed_verification(value: object) -> bool:
    """Recognize concrete structured evidence for a successful artifact."""

    if not isinstance(value, dict):
        return False
    result = text_value(value.get("result"))
    kind = text_value(value.get("kind"))
    evidence = text_value(value.get("evidence"))
    return result is not None and result.casefold() in {"ok", "passed", "success"} and kind is not None and evidence is not None


def is_failed_verification(value: object) -> bool:
    """Recognize an explicit failed check that contradicts an OK run status."""

    if not isinstance(value, dict):
        return False
    result = text_value(value.get("result"))
    return result is not None and result.casefold() in {"error", "fail", "failed", "failure"}


def optional_gauntlet_text(
    record: dict[str, Any],
    field: str,
    prefix: str,
    errors: list[str],
) -> Optional[str]:
    """Parse one nullable non-blank string from gauntlet metadata."""

    raw_value = record.get(field)
    value = text_value(raw_value)
    if raw_value is not None and value is None:
        errors.append(f"{prefix}.{field} must be null or a non-blank string")
    return value


def gauntlet_string_list(
    record: dict[str, Any],
    field: str,
    prefix: str,
    errors: list[str],
) -> tuple[str, ...]:
    """Parse a JSON array whose entries must all be meaningful strings."""

    value = record.get(field)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and bool(item.strip()) for item in value
    ):
        errors.append(f"{prefix}.{field} must be an array of non-blank strings")
        return ()
    return tuple(value)


def parse_gauntlet_rounds(
    value: object,
    report_path: Path,
    status: Optional[str],
    worker_identity: Optional[WorkerIdentity],
    errors: list[str],
) -> tuple[int, tuple[str, ...]]:
    """Validate ordered critic rounds and return their count and valid verdicts."""

    prefix = f"{report_path}: qualityGauntlet"
    if not isinstance(value, list):
        errors.append(f"{prefix}.rounds must be an array")
        return 0, ()

    descendants = (
        {worker_id.strip() for worker_id in worker_identity.descendants}
        if worker_identity is not None
        else set()
    )
    verdicts: list[str] = []
    for index, round_value in enumerate(value):
        round_prefix = f"{prefix}.rounds[{index}]"
        if not isinstance(round_value, dict):
            errors.append(f"{round_prefix} must be an object")
            continue

        critic_worker_id = optional_gauntlet_text(
            round_value,
            "criticWorkerId",
            round_prefix,
            errors,
        )
        if (
            critic_worker_id is not None
            and worker_identity is not None
            and critic_worker_id not in descendants
        ):
            errors.append(
                f"{round_prefix}.criticWorkerId must appear in descendantWorkerIds"
            )

        verdict = text_value(round_value.get("verdict"))
        if verdict not in GAUNTLET_VERDICTS:
            errors.append(
                f"{round_prefix}.verdict must be one of {sorted(GAUNTLET_VERDICTS)}"
            )
        else:
            verdicts.append(verdict)

        for field in ("artifactRevision", "inspected", "evidence", "recheck"):
            if text_value(round_value.get(field)) is None:
                errors.append(f"{round_prefix}.{field} must be a non-blank string")

        gap = optional_gauntlet_text(
            round_value,
            "highestLeverageGap",
            round_prefix,
            errors,
        )
        if verdict in {"NOT_READY", "BLOCKED"} and gap is None:
            errors.append(
                f"{round_prefix}.highestLeverageGap is required for {verdict}"
            )

        fix = optional_gauntlet_text(round_value, "fix", round_prefix, errors)
        if status == "OK" and verdict == "NOT_READY" and fix is None:
            errors.append(
                f"{round_prefix}.fix is required for a historical NOT_READY round in an OK run"
            )

    return len(value), tuple(verdicts)


def parse_gauntlet_integration(
    value: object,
    report_path: Path,
    errors: list[str],
) -> tuple[Optional[bool], Optional[str], Optional[str]]:
    """Validate the whole-artifact integration-pass record."""

    prefix = f"{report_path}: qualityGauntlet.integrationPass"
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be an object")
        return None, None, None

    required_value = value.get("required")
    required = required_value if isinstance(required_value, bool) else None
    if required_value is not None and required is None:
        errors.append(f"{prefix}.required must be true, false, or null")
    result = optional_gauntlet_text(value, "result", prefix, errors)
    evidence = optional_gauntlet_text(value, "evidence", prefix, errors)
    return required, result, evidence


def parse_quality_gauntlet(
    value: dict[str, Any],
    report_path: Path,
    status: Optional[str],
    worker_identity: Optional[WorkerIdentity],
    errors: list[str],
) -> QualityGauntletEvidence:
    """Normalize a gauntlet record while reporting malformed fields."""

    prefix = f"{report_path}: qualityGauntlet"
    applicability = text_value(value.get("applicability"))
    if value.get("applicability") is not None and applicability not in {
        "required",
        "not-required",
    }:
        errors.append(
            f"{prefix}.applicability must be required, not-required, or null"
        )
    not_required_reason = optional_gauntlet_text(
        value,
        "notRequiredReason",
        prefix,
        errors,
    )
    bar = optional_gauntlet_text(value, "bar", prefix, errors)
    provenance = gauntlet_string_list(
        value,
        "referenceProvenance",
        prefix,
        errors,
    )

    bar_validation_value = value.get("barValidation")
    if not isinstance(bar_validation_value, dict):
        errors.append(f"{prefix}.barValidation must be an object")
        bar_validation_value = {}
    bar_validation_result = optional_gauntlet_text(
        bar_validation_value,
        "result",
        f"{prefix}.barValidation",
        errors,
    )
    if (
        bar_validation_result is not None
        and bar_validation_result not in GAUNTLET_BAR_VALIDATION_RESULTS
    ):
        errors.append(
            f"{prefix}.barValidation.result must be one of "
            f"{sorted(GAUNTLET_BAR_VALIDATION_RESULTS)} or null"
        )
    bar_validation_evidence = optional_gauntlet_text(
        bar_validation_value,
        "evidence",
        f"{prefix}.barValidation",
        errors,
    )
    bar_revisions = gauntlet_string_list(value, "barRevisions", prefix, errors)

    fresh_critic_value = value.get("freshCriticAvailable")
    fresh_critic_available = (
        fresh_critic_value if isinstance(fresh_critic_value, bool) else None
    )
    if fresh_critic_value is not None and fresh_critic_available is None:
        errors.append(f"{prefix}.freshCriticAvailable must be true, false, or null")
    fallback_evidence = optional_gauntlet_text(
        value,
        "fallbackEvidence",
        prefix,
        errors,
    )
    round_count, verdicts = parse_gauntlet_rounds(
        value.get("rounds"),
        report_path,
        status,
        worker_identity,
        errors,
    )
    (
        integration_required,
        integration_result,
        integration_evidence,
    ) = parse_gauntlet_integration(
        value.get("integrationPass"),
        report_path,
        errors,
    )

    stop_reason = optional_gauntlet_text(value, "stopReason", prefix, errors)
    if stop_reason is not None and stop_reason not in GAUNTLET_STOP_REASONS:
        errors.append(
            f"{prefix}.stopReason must be one of "
            f"{sorted(GAUNTLET_STOP_REASONS)} or null"
        )

    return QualityGauntletEvidence(
        applicability=applicability,
        not_required_reason=not_required_reason,
        bar=bar,
        provenance=provenance,
        bar_validation_result=bar_validation_result,
        bar_validation_evidence=bar_validation_evidence,
        bar_revisions=bar_revisions,
        fresh_critic_available=fresh_critic_available,
        round_count=round_count,
        verdicts=verdicts,
        integration_required=integration_required,
        integration_result=integration_result,
        integration_evidence=integration_evidence,
        fallback_evidence=fallback_evidence,
        stop_reason=stop_reason,
    )


def validate_required_gauntlet(
    evidence: QualityGauntletEvidence,
    report_path: Path,
    errors: list[str],
) -> None:
    """Apply successful-run requirements to one non-trivial artifact."""

    if evidence.bar is None:
        errors.append(
            f"{report_path}: successful run qualityGauntlet must record a concrete bar"
        )
    if not evidence.provenance:
        errors.append(
            f"{report_path}: required qualityGauntlet must record referenceProvenance"
        )
    if evidence.bar_validation_result not in GAUNTLET_BAR_VALIDATION_RESULTS:
        errors.append(
            f"{report_path}: required qualityGauntlet must record barValidation.result"
        )
    if evidence.bar_validation_evidence is None:
        errors.append(
            f"{report_path}: required qualityGauntlet must record barValidation.evidence"
        )
    if (
        evidence.bar_validation_result == "revised"
        and not evidence.bar_revisions
    ):
        errors.append(f"{report_path}: revised quality bar must record barRevisions")

    if evidence.fresh_critic_available is None:
        errors.append(
            f"{report_path}: successful run qualityGauntlet must record freshCriticAvailable"
        )
    elif evidence.fresh_critic_available:
        if evidence.bar_validation_result not in {"accepted", "revised"}:
            errors.append(
                f"{report_path}: fresh critic runs must validate the quality bar independently"
            )
        if not evidence.verdicts:
            errors.append(
                f"{report_path}: successful run with fresh critics must record at least one critic round"
            )
        elif evidence.verdicts[-1] != "READY":
            errors.append(
                f"{report_path}: successful run's final critic verdict must be READY"
            )
    else:
        if evidence.bar_validation_result != "fallback-reviewed":
            errors.append(
                f"{report_path}: no-critic fallback must use barValidation result fallback-reviewed"
            )
        if evidence.round_count:
            errors.append(
                f"{report_path}: run without fresh critic capability must not invent critic rounds"
            )
        if evidence.fallback_evidence is None:
            errors.append(
                f"{report_path}: run without fresh critic capability must record fallbackEvidence"
            )

    if evidence.integration_required is None:
        errors.append(
            f"{report_path}: successful run must record whether an integration pass was required"
        )
    elif evidence.integration_required:
        if (
            evidence.integration_result is None
            or evidence.integration_result.casefold() not in {"ok", "passed", "success"}
        ):
            errors.append(
                f"{report_path}: required integration pass must record a passed result"
            )
        if evidence.integration_evidence is None:
            errors.append(
                f"{report_path}: required integration pass must record concrete evidence"
            )
    elif evidence.integration_result != "not-required":
        errors.append(
            f"{report_path}: unnecessary integration pass must use result not-required"
        )

    if evidence.stop_reason not in SUCCESSFUL_GAUNTLET_STOP_REASONS:
        errors.append(
            f"{report_path}: successful run must stop on bar-met or no-material-actionable-gap"
        )


def validate_quality_gauntlet(
    value: object,
    report_path: Path,
    status: Optional[str],
    worker_identity: Optional[WorkerIdentity],
    errors: list[str],
) -> None:
    """Validate optional critic history separately from final passing checks."""

    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(f"{report_path}: qualityGauntlet must be an object when present")
        return

    evidence = parse_quality_gauntlet(
        value,
        report_path,
        status,
        worker_identity,
        errors,
    )
    if status != "OK":
        return
    if evidence.applicability not in {"required", "not-required"}:
        errors.append(
            f"{report_path}: successful run qualityGauntlet must record applicability"
        )
        return
    if evidence.applicability == "required":
        validate_required_gauntlet(evidence, report_path, errors)
        return

    if evidence.not_required_reason is None:
        errors.append(
            f"{report_path}: not-required qualityGauntlet must record a concrete reason"
        )
    if evidence.round_count:
        errors.append(
            f"{report_path}: not-required qualityGauntlet must not contain critic rounds"
        )
    if evidence.fresh_critic_available is not None:
        errors.append(
            f"{report_path}: not-required qualityGauntlet must leave freshCriticAvailable null"
        )
    if (
        evidence.integration_required is not False
        or evidence.integration_result != "not-required"
    ):
        errors.append(
            f"{report_path}: not-required qualityGauntlet must mark integration pass not-required"
        )
    if evidence.stop_reason != "not-required":
        errors.append(
            f"{report_path}: not-required qualityGauntlet must use stopReason not-required"
        )


def load_object(path: Path, errors: list[str]) -> Optional[dict[str, Any]]:
    """Load a JSON object and report parse problems against its concrete path."""
    try:
        raw = read_regular_file_bounded(path, METADATA_MAX_BYTES)
        decoded = raw.decode("utf-8")
        value = parse_json_bounded(decoded)
    except BoundedReadError as exc:
        detail = str(exc)
        if "exceeds" in detail:
            errors.append(f"{path}: JSON metadata exceeds the 1 MiB read limit")
        elif "regular" in detail:
            errors.append(f"{path}: JSON metadata must be a regular file")
        else:
            errors.append(f"{path}: invalid JSON: {exc}")
        return None
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{path}: top-level JSON value must be an object")
        return None
    return value


def exact_child(parent: Path, name: str) -> Optional[Path]:
    """Return a direct child only when its directory-entry casing is exact."""

    try:
        return next((entry for entry in parent.iterdir() if entry.name == name), None)
    except OSError:
        return None


def exact_descendant(root: Path, relative: str) -> Optional[Path]:
    """Resolve a POSIX relative path through exact-cased directory entries."""

    current = root
    parts = PurePosixPath(relative).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return None
    for part in parts:
        current = exact_child(current, part)
        if current is None:
            return None
    return current


def is_safe_relative_path(value: object) -> bool:
    """Accept portable, non-empty paths that cannot escape their run directory."""
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(part not in {"", ".", ".."} for part in path.parts)


def validate_manifest_paths(
    run_path: Path,
    run: dict[str, Any],
    require_temporary: bool,
    errors: list[str],
) -> None:
    """Enforce the fixed handoff paths without constraining the source project."""
    prompt = object_value(run.get("prompt"))
    prompt_path = prompt.get("path")
    if prompt_path != "artifact/PROMPT.md":
        errors.append(f"{run_path}: prompt.path must be exactly artifact/PROMPT.md")

    temporary = object_value(run.get("temporary"))
    temporary_path = temporary.get("path")
    if require_temporary:
        if temporary_path != ".tmp/":
            errors.append(f"{run_path}: temporary.path must be exactly .tmp/")
        if temporary.get("routing") != "best-effort-run-local":
            errors.append(f"{run_path}: temporary.routing must be exactly best-effort-run-local")
        if temporary.get("preservation") != "retain":
            errors.append(f"{run_path}: temporary.preservation must be exactly retain")

    workspace = object_value(run.get("workspace"))
    if workspace.get("path") != "workspace/":
        errors.append(f"{run_path}: workspace.path must be exactly workspace/")
    artifact = object_value(run.get("artifact"))
    if artifact.get("path") != "artifact/":
        errors.append(f"{run_path}: artifact.path must be exactly artifact/")
    if artifact.get("entrypoint") != "artifact/index.html":
        errors.append(f"{run_path}: artifact.entrypoint must be exactly artifact/index.html")
    if artifact.get("deployment") != "static-folder":
        errors.append(f"{run_path}: artifact.deployment must be exactly static-folder")

    for label, value in (
        ("prompt.path", prompt_path),
        ("temporary.path", temporary_path),
        ("workspace.path", workspace.get("path")),
        ("artifact.path", artifact.get("path")),
        ("artifact.entrypoint", artifact.get("entrypoint")),
    ):
        if value is not None and not is_safe_relative_path(value):
            errors.append(f"{run_path}: {label} is not a safe relative path")


def has_url_control_character(value: str) -> bool:
    """Reject browser-path controls before they reach filesystem APIs."""

    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def display_reference(value: str) -> str:
    """Bound attacker-controlled URL text in validator diagnostics."""

    if len(value) <= MAX_REFERENCE_DISPLAY_CHARS:
        return repr(value)
    omitted = len(value) - MAX_REFERENCE_DISPLAY_CHARS
    return f"{value[:MAX_REFERENCE_DISPLAY_CHARS]!r}… (+{omitted} chars)"


def local_reference_path(
    reference: str,
    base_reference: str,
    source: Path,
    errors: list[str],
) -> Optional[str]:
    """Resolve one browser URL to an artifact-root-relative path when local."""

    value = reference.strip()
    if not value or value.startswith("#") or value.startswith("//"):
        return None
    try:
        base_url = urljoin("https://oneshot.invalid/index.html", base_reference)
        resolved_url = urljoin(base_url, value)
        parsed = urlsplit(resolved_url)
    except ValueError as error:
        errors.append(f"{source}: malformed resource URL {display_reference(reference)}: {error}")
        return None
    if parsed.scheme not in {"http", "https"} or parsed.netloc != "oneshot.invalid":
        return None
    path = unquote(parsed.path)
    if not path:
        return None
    if "\\" in path or has_url_control_character(path):
        errors.append(f"{source}: unsafe decoded local resource URL: {display_reference(reference)}")
        return None
    artifact_relative = path.lstrip("/")
    return artifact_relative or "index.html"


def css_references(css: str) -> list[str]:
    """Collect common CSS URL and quoted import references."""

    uncommented = strip_css_comments(css)
    syntax = mask_css_string_contents(uncommented)
    references: list[str] = []
    seen: set[str] = set()
    retained_chars = 0

    def append(value: str) -> None:
        nonlocal retained_chars
        normalized = value.strip()
        if normalized in seen:
            return
        if (
            len(seen) >= MAX_LOCAL_REFERENCE_CHECKS
            or retained_chars + len(normalized) > MAX_LOCAL_REFERENCE_TEXT_CHARS
        ):
            raise ValueError(
                "stylesheet resource-reference inventory exceeds its validation safety bound"
            )
        seen.add(normalized)
        retained_chars += len(normalized)
        references.append(normalized)

    for match in CSS_URL_RE.finditer(uncommented):
        if syntax[match.start() : match.start() + 3].casefold() == "url":
            append(match.group(2))
    for match in CSS_IMPORT_RE.finditer(uncommented):
        if syntax[match.start() : match.start() + 7].casefold() == "@import":
            append(match.group(2))
    for image_set in css_image_set_bodies(uncommented, syntax):
        for match in CSS_IMAGE_SET_CANDIDATE_RE.finditer(image_set):
            append(match.group(2))
    return references


def strip_css_comments(css: str) -> str:
    """Remove closed or EOF-terminated comments without touching string literals."""

    output: list[str] = []
    position = 0
    quote: Optional[str] = None
    escaped = False
    while position < len(css):
        character = css[position]
        if quote is not None:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            position += 1
            continue
        if character in {"'", '"'}:
            quote = character
            output.append(character)
            position += 1
            continue
        if css.startswith("/*", position):
            closing = css.find("*/", position + 2)
            if closing == -1:
                break
            position = closing + 2
            continue
        output.append(character)
        position += 1
    return "".join(output)


def mask_css_string_contents(css: str) -> str:
    """Mask quoted content while preserving offsets and live CSS punctuation."""

    output: list[str] = []
    quote: Optional[str] = None
    escaped = False
    for character in css:
        if quote is None:
            output.append(character)
            if character in {"'", '"'}:
                quote = character
            continue
        if escaped:
            output.append(" ")
            escaped = False
        elif character == "\\":
            output.append(" ")
            escaped = True
        elif character == quote:
            output.append(character)
            quote = None
        else:
            output.append(" ")
    return "".join(output)


def css_image_set_bodies(css: str, syntax: str) -> list[str]:
    """Extract image-set bodies while respecting strings and nested type calls."""

    bodies: list[str] = []
    search_from = 0
    while True:
        opening = CSS_IMAGE_SET_START_RE.search(syntax, search_from)
        if opening is None:
            return bodies
        position = opening.end()
        body_start = position
        depth = 1
        quote: Optional[str] = None
        escaped = False
        while position < len(syntax):
            character = syntax[position]
            if quote is not None:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == quote:
                    quote = None
            elif character in {"'", '"'}:
                quote = character
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    bodies.append(css[body_start:position])
                    position += 1
                    break
            position += 1
        search_from = max(position, opening.end())


def validate_reference(
    reference: str,
    base_reference: str,
    source: Path,
    artifact_root: Path,
    errors: list[str],
) -> Optional[Path]:
    """Validate one local resource and return a stylesheet for queued inspection."""

    relative = local_reference_path(reference, base_reference, source, errors)
    if relative is None:
        return None
    target = exact_descendant(artifact_root, relative)
    if target is None:
        errors.append(
            f"{source}: referenced local file missing or path casing differs: {display_reference(reference)}"
        )
        return None
    try:
        resolved_target = target.resolve()
        resolved_target.relative_to(artifact_root)
    except (OSError, RuntimeError, ValueError) as error:
        errors.append(
            f"{source}: local reference escapes or cannot resolve: {display_reference(reference)} ({error})"
        )
        return None
    if not target.is_file():
        errors.append(f"{source}: referenced local file missing: {display_reference(reference)}")
        return None
    if target.suffix.casefold() in PREPROCESS_ONLY_SUFFIXES:
        errors.append(
            f"{source}: browser entry references preprocess-only source: {display_reference(reference)}"
        )
        return None
    return target if target.suffix.casefold() == ".css" else None


def validate_local_assets(index_path: Path, errors: list[str]) -> None:
    """Check common HTML and transitive CSS resources in the built artifact."""

    try:
        artifact_root = index_path.parent.resolve()
    except (OSError, RuntimeError) as error:
        errors.append(f"{index_path}: artifact root cannot be resolved safely: {error}")
        return
    try:
        html_text = read_regular_file_bounded(index_path, DROP_MAX_FILE_BYTES).decode("utf-8")
    except BoundedReadError as error:
        if "exceeds" in str(error):
            errors.append(f"{index_path}: file exceeds the conservative 5 MiB folder-drop limit")
        else:
            errors.append(f"{index_path}: index.html is not readable UTF-8: {error}")
        return
    except UnicodeDecodeError as error:
        errors.append(f"{index_path}: index.html is not readable UTF-8: {error}")
        return
    parser = LocalReferenceParser()
    try:
        parser.feed(html_text)
        parser.close()
        parser.finish()
    except ValueError as error:
        errors.append(f"{index_path}: index.html could not be parsed: {error}")
        return
    if parser.reference_overflow:
        errors.append(
            f"{index_path}: document exposes more than {MAX_LOCAL_REFERENCE_CHECKS} distinct resource references"
        )

    base_reference = parser.base_href or "/index.html"
    pending: list[tuple[str, str, Path]] = []
    scheduled_references: set[tuple[str, str, Path]] = set()
    scheduled_reference_chars = 0
    reference_inventory_overflow = False

    def enqueue_reference(reference: str, reference_base: str, source: Path) -> None:
        nonlocal reference_inventory_overflow, scheduled_reference_chars
        key = (reference, reference_base, source)
        if key in scheduled_references:
            return
        reference_chars = len(reference) + len(reference_base)
        if (
            len(scheduled_references) >= MAX_LOCAL_REFERENCE_CHECKS
            or scheduled_reference_chars + reference_chars > MAX_LOCAL_REFERENCE_TEXT_CHARS
        ):
            if not reference_inventory_overflow:
                errors.append(
                    f"{index_path}: static asset reference inventory exceeds its validation safety bound"
                )
            reference_inventory_overflow = True
            return
        scheduled_references.add(key)
        scheduled_reference_chars += reference_chars
        pending.append(key)

    for reference in parser.references:
        enqueue_reference(reference, base_reference, index_path)
    for inline_style in parser.inline_styles:
        try:
            inline_references = css_references(inline_style)
        except ValueError as error:
            errors.append(f"{index_path}: inline stylesheet reference inventory is too large: {error}")
            continue
        for reference in inline_references:
            enqueue_reference(reference, base_reference, index_path)

    checked_css: set[Path] = set()
    css_bytes_scanned = 0
    while pending:
        reference, reference_base, source = pending.pop()
        stylesheet = validate_reference(reference, reference_base, source, artifact_root, errors)
        if stylesheet is None or stylesheet in checked_css:
            continue
        checked_css.add(stylesheet)
        try:
            css_bytes = read_regular_file_bounded(stylesheet, DROP_MAX_FILE_BYTES)
        except BoundedReadError as error:
            if "exceeds" in str(error):
                errors.append(f"{stylesheet}: file exceeds the conservative 5 MiB folder-drop limit")
            else:
                errors.append(f"{stylesheet}: stylesheet is not readable UTF-8: {error}")
            continue
        if css_bytes_scanned + len(css_bytes) > MAX_CSS_SCAN_BYTES:
            errors.append(
                f"{index_path}: transitive stylesheet scan exceeds the {MAX_CSS_SCAN_BYTES // (1024 * 1024)} MiB validation safety bound"
            )
            break
        css_bytes_scanned += len(css_bytes)
        try:
            css = css_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            errors.append(f"{stylesheet}: stylesheet is not readable UTF-8: {error}")
            continue
        css_base = "/" + stylesheet.relative_to(artifact_root).as_posix()
        try:
            stylesheet_references = css_references(css)
        except ValueError as error:
            errors.append(f"{stylesheet}: stylesheet reference inventory is too large: {error}")
            continue
        for css_reference in stylesheet_references:
            enqueue_reference(css_reference, css_base, stylesheet)


def forbidden_artifact_file(path: Path) -> bool:
    """Recognize project metadata and secrets that do not belong in a static export."""

    name = path.name.casefold()
    return (
        name in BUILD_OR_PROVIDER_FILE_NAMES
        or name == ".env"
        or name.startswith(".env.")
        or name.startswith(".pnp")
        or name in {
            ".dockerignore",
            ".gitignore",
            ".gitmodules",
            ".npmignore",
            ".npmrc",
            ".vercelignore",
        }
    )


def has_private_key_filename(path: Path) -> bool:
    """Recognize filenames that unambiguously label private key material."""

    name = path.name.casefold()
    return name in SSH_PRIVATE_KEY_FILE_NAMES or any(
        name == basename or name.startswith(basename + ".")
        for basename in PRIVATE_KEY_LABELLED_BASENAMES
    )


def contains_private_key_marker(content: bytes) -> bool:
    """Recognize exact private-key BEGIN markers without decoding binary artifacts."""

    return any(marker in content for marker in PRIVATE_KEY_BEGIN_MARKERS)


def directory_has_read_and_traverse_mode(mode: int) -> bool:
    """Require at least one POSIX permission class to be able to list and enter."""

    return any(mode & mask == mask for mask in (0o500, 0o050, 0o005))


def validate_artifact_tree(artifact_root: Path, errors: list[str]) -> None:
    """Enforce a conservative folder-drop compatibility envelope."""
    try:
        if artifact_root.is_symlink():
            errors.append(f"{artifact_root}: artifact directory must not be a symbolic link")
            return
        if not artifact_root.is_dir():
            errors.append(f"{artifact_root}: artifact directory is missing")
            return
    except OSError as error:
        errors.append(f"{artifact_root}: unable to inspect artifact directory: {error}")
        return

    try:
        root_stat = artifact_root.stat()
    except OSError as error:
        errors.append(f"{artifact_root}: unable to inspect artifact directory metadata: {error}")
        return
    if not directory_has_read_and_traverse_mode(root_stat.st_mode):
        errors.append(f"{artifact_root}: artifact directory must have a readable and traversable mode")
        return

    file_count = 0
    directory_count = 1
    total_bytes = 0
    pending_directories: list[tuple[Path, int]] = [(artifact_root, 0)]

    while pending_directories:
        directory, depth = pending_directories.pop()
        try:
            with os.scandir(directory) as iterator:
                for entry in iterator:
                    path = Path(entry.path)
                    try:
                        entry_stat = entry.stat(follow_symlinks=False)
                    except OSError as error:
                        errors.append(f"{path}: unable to inspect artifact entry: {error}")
                        continue

                    if stat.S_ISLNK(entry_stat.st_mode):
                        errors.append(f"{path}: drop-ready artifacts must not contain symbolic links")
                        continue

                    if stat.S_ISDIR(entry_stat.st_mode):
                        directory_count += 1
                        if directory_count > VALIDATION_MAX_DIRECTORIES:
                            errors.append(
                                f"{artifact_root}: artifact has more than {VALIDATION_MAX_DIRECTORIES} directories; "
                                "validation stopped at its traversal safety limit"
                            )
                            return
                        child_depth = depth + 1
                        if child_depth > VALIDATION_MAX_DEPTH:
                            errors.append(
                                f"{path}: artifact nesting exceeds the {VALIDATION_MAX_DEPTH}-directory validation safety limit"
                            )
                            continue
                        if path.name.casefold() in NON_DEPLOYABLE_DIRECTORIES:
                            if path.name.casefold() == ".tmp":
                                errors.append(
                                    f"{path}: run-local .tmp/ must stay outside artifact/ at the run root"
                                )
                            else:
                                errors.append(
                                    f"{path}: cache, provider state, or dependency directory must stay in workspace/"
                                )
                            continue
                        if not directory_has_read_and_traverse_mode(entry_stat.st_mode):
                            errors.append(f"{path}: artifact directory must have a readable and traversable mode")
                            continue
                        pending_directories.append((path, child_depth))
                        continue

                    if not stat.S_ISREG(entry_stat.st_mode):
                        errors.append(
                            f"{path}: drop-ready artifacts may contain only regular files and directories"
                        )
                        continue

                    file_count += 1
                    if file_count > DROP_MAX_FILES:
                        errors.append(
                            f"{artifact_root}: artifact has more than {DROP_MAX_FILES} files; "
                            f"folder-drop limit is {DROP_MAX_FILES}"
                        )
                        return
                    private_key_filename = has_private_key_filename(path)
                    if private_key_filename:
                        errors.append(f"{path}: private key material must stay in workspace/")
                    if forbidden_artifact_file(path):
                        errors.append(f"{path}: build, provider, package, or secret file must stay in workspace/")
                    if path.suffix.casefold() in PREPROCESS_ONLY_SUFFIXES:
                        errors.append(f"{path}: preprocess-only source file must stay in workspace/")
                    if entry_stat.st_mode & 0o444 == 0:
                        errors.append(f"{path}: artifact file must have a readable file mode")
                    try:
                        file_bytes = read_regular_file_bounded(path, DROP_MAX_FILE_BYTES)
                    except BoundedReadError as error:
                        if "exceeds" in str(error):
                            errors.append(f"{path}: file exceeds the conservative 5 MiB folder-drop limit")
                            return
                        errors.append(f"{path}: artifact file is not readable: {error}")
                        continue
                    # Scan the bytes already bounded by the 5 MiB per-file read above.
                    if not private_key_filename and contains_private_key_marker(file_bytes):
                        errors.append(f"{path}: private key material must stay in workspace/")
                    total_bytes += len(file_bytes)
                    if total_bytes > DROP_MAX_TOTAL_BYTES:
                        errors.append(
                            f"{artifact_root}: artifact exceeds the conservative 100 MiB folder-drop total"
                        )
                        return
        except OSError as error:
            errors.append(f"{directory}: unable to traverse artifact directory: {error}")


def is_regular_file_within(path: Path, container: Path, label: str, errors: list[str]) -> bool:
    """Require an ordinary file whose path and parents stay inside its owner."""

    try:
        if path.is_symlink():
            errors.append(f"{path}: {label} must not be a symbolic link")
            return False
        current = path.parent
        while current != container and current != current.parent:
            if current.is_symlink():
                errors.append(f"{path}: {label} parent directories must not be symbolic links")
                return False
            current = current.parent
    except OSError as error:
        errors.append(f"{path}: unable to inspect {label} path metadata: {error}")
        return False
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(container.resolve(strict=True))
    except (OSError, ValueError) as error:
        errors.append(f"{path}: {label} must resolve inside {container}: {error}")
        return False
    try:
        is_file = path.is_file()
    except OSError as error:
        errors.append(f"{path}: unable to inspect {label} file type: {error}")
        return False
    if not is_file:
        errors.append(f"{path}: {label} must be a regular file")
        return False
    return True


def validate_provenance_receipt(
    root: Path,
    run_path: Path,
    run: dict[str, Any],
    prompt_bytes: Optional[bytes],
    errors: list[str],
) -> PreparedRunContracts:
    """Compare worker-writable metadata with its pre-dispatch coordinator receipt."""

    run_id = run_path.parent.name
    expected_relative = f".oneshot-provenance/{run_id}.json"
    if run.get("provenanceReceipt") != expected_relative:
        errors.append(f"{run_path}: provenanceReceipt must be exactly {expected_relative}")
    commit_path = root / ".oneshot-provenance" / f"{run_id}.commit"
    if is_regular_file_within(commit_path, root, "provenance commit marker", errors):
        try:
            if commit_path.stat().st_size != 0:
                errors.append(f"{commit_path}: provenance commit marker must be empty")
        except OSError as error:
            errors.append(f"{commit_path}: unable to inspect provenance commit marker: {error}")
    receipt_path = root / expected_relative
    if not is_regular_file_within(receipt_path, root, "provenance receipt", errors):
        return PreparedRunContracts(temporary=False, quality_gauntlet=False)
    receipt = load_object(receipt_path, errors)
    if receipt is None:
        return PreparedRunContracts(temporary=False, quality_gauntlet=False)
    receipt_schema = receipt.get("schemaVersion")
    receipt_contracts = {
        "1.0": ("2.0", False, False),
        "1.1": ("2.1", True, False),
        "2.0": ("3.0", True, False),
        "2.1": ("3.1", True, True),
    }
    receipt_contract = receipt_contracts.get(receipt_schema) if isinstance(receipt_schema, str) else None
    if receipt_contract is None:
        errors.append(f"{receipt_path}: schemaVersion must be 1.0, 1.1, 2.0, or 2.1")
    (
        expected_run_schema,
        current_temporary_contract,
        current_quality_gauntlet_contract,
    ) = receipt_contract or (None, False, False)
    if run.get("schemaVersion") != expected_run_schema:
        errors.append(
            f"{receipt_path}: receipt schema {receipt_schema!r} requires run schema {expected_run_schema}"
        )
    if isinstance(receipt_schema, str) and receipt_schema in {"1.1", "2.0", "2.1"}:
        if receipt.get("runSchemaVersion") != expected_run_schema:
            errors.append(f"{receipt_path}: runSchemaVersion must be exactly {expected_run_schema}")
        receipt_temporary = object_value(receipt.get("temporary"))
        expected_temporary = {
            "path": ".tmp/",
            "routing": "best-effort-run-local",
            "preservation": "retain",
        }
        if receipt_temporary != expected_temporary:
            errors.append(f"{receipt_path}: temporary contract does not match the prepared run")
    if current_quality_gauntlet_contract:
        expected_quality_gauntlet = {
            "required": True,
            "contractVersion": "1.0",
            "reportSchemaVersion": "2.1",
        }
        if receipt.get("qualityGauntlet") != expected_quality_gauntlet:
            errors.append(
                f"{receipt_path}: qualityGauntlet contract does not match the prepared run"
            )
    expected_run_path = run_path.parent.relative_to(root).as_posix()
    if receipt.get("runId") != run_id:
        errors.append(f"{receipt_path}: runId must match {run_id!r}")
    if receipt.get("runPath") != expected_run_path:
        errors.append(f"{receipt_path}: runPath must match {expected_run_path!r}")
    for field in ("identity", "classification", "priorRun"):
        if receipt.get(field) != run.get(field):
            errors.append(f"{receipt_path}: {field} does not match the pre-dispatch run record")
    receipt_prompt = object_value(receipt.get("prompt"))
    run_prompt = object_value(run.get("prompt"))
    if receipt_prompt.get("sha256") != run_prompt.get("sha256"):
        errors.append(f"{receipt_path}: prompt digest does not match the pre-dispatch receipt")
    if prompt_bytes is not None:
        if receipt_prompt.get("sha256") != hashlib.sha256(prompt_bytes).hexdigest():
            errors.append(f"{receipt_path}: artifact/PROMPT.md differs from the pre-dispatch prompt")
        if receipt_prompt.get("bytes") != len(prompt_bytes):
            errors.append(f"{receipt_path}: prompt byte count does not match artifact/PROMPT.md")
    return PreparedRunContracts(
        temporary=current_temporary_contract,
        quality_gauntlet=current_quality_gauntlet_contract,
    )


def validate_run(
    root: Path,
    run_path: Path,
    canonical_runs: set[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    """Validate one flat or legacy run against its identity and artifact contract."""
    relative = run_path.relative_to(root)
    directory_parts = relative.parts[:-1]
    if len(directory_parts) == 1:
        layout = "flat"
        run_id = directory_parts[0]
        legacy_keys: tuple[str, ...] = ()
    elif len(directory_parts) == 4:
        layout = "legacy"
        *legacy_identity_keys, run_id = directory_parts
        legacy_keys = tuple(legacy_identity_keys)
    else:
        errors.append(f"{run_path}: run must use one timestamp directory or the legacy four-level layout")
        return
    if not is_regular_file_within(run_path, root, "run manifest", errors):
        return
    run = load_object(run_path, errors)
    if run is None:
        return

    schema_version = run.get("schemaVersion")
    expected_schemas = {"3.0", "3.1"} if layout == "flat" else {"2.0", "2.1"}
    if not isinstance(schema_version, str) or schema_version not in expected_schemas:
        errors.append(
            f"{run_path}: {layout} run schemaVersion must be one of {sorted(expected_schemas)}"
        )
    if layout == "flat" and parse_flat_run_id(run_id) is None:
        errors.append(
            f"{run_path}: flat run directory must use a real YYYY-MM-DD-HH-MM-SS timestamp "
            "with no suffix or a canonical collision suffix of -02 or later"
        )
    if layout == "legacy" and LEGACY_RUN_ID_RE.fullmatch(run_id) is None:
        errors.append(f"{run_path}: legacy run directory does not use the supported UTC-and-UUID format")

    identity = object_value(run.get("identity"))
    for index, field in enumerate(("model", "harness", "experiment")):
        identity_part = object_value(identity.get(field))
        key_value = identity_part.get("key")
        name_value = identity_part.get("name")
        key = key_value if isinstance(key_value, str) and key_value else None
        name = name_value if isinstance(name_value, str) and name_value.strip() else None
        if name is None:
            errors.append(f"{run_path}: identity.{field}.name must be a non-empty raw name")
        else:
            try:
                expected_key = identity_key(name)
            except UnicodeEncodeError:
                errors.append(f"{run_path}: identity.{field}.name must be valid UTF-8 text")
            else:
                if key != expected_key:
                    errors.append(f"{run_path}: identity.{field}.key does not match the raw-name digest")
        if layout == "legacy":
            expected_key = legacy_keys[index]
            namespace_directory = run_path.parents[3 - index]
            if key != expected_key:
                errors.append(f"{run_path}: identity.{field}.key must match namespace segment {expected_key!r}")
            marker_path = exact_child(namespace_directory, IDENTITY_MARKER)
            if marker_path is None:
                errors.append(f"{namespace_directory}: missing exact-case {IDENTITY_MARKER}")
            elif is_regular_file_within(marker_path, root, f"{field} namespace identity marker", errors):
                marker = load_object(marker_path, errors)
                if marker is not None:
                    expected_marker = {"schemaVersion": "1.0", "name": name_value, "key": key_value}
                    if marker != expected_marker:
                        errors.append(f"{marker_path}: marker does not match run identity.{field}")
    if text_value(run.get("runId")) != run_id:
        errors.append(f"{run_path}: runId must match run directory {run_id!r}")

    status = text_value(run.get("status"))
    if status not in STATUSES:
        errors.append(f"{run_path}: status must be one of {sorted(STATUSES)}")
    classification = text_value(run.get("classification"))
    if classification not in CLASSIFICATIONS:
        errors.append(f"{run_path}: classification must be one of {sorted(CLASSIFICATIONS)}")

    prior_run = run.get("priorRun")
    if classification == "autonomous-one-shot" and prior_run is not None:
        errors.append(f"{run_path}: autonomous-one-shot must not declare priorRun")
    if classification in {"rerun", "curated-attempt"}:
        if not is_safe_relative_path(prior_run):
            errors.append(f"{run_path}: {classification} must declare a safe priorRun path")
        elif len(PurePosixPath(str(prior_run)).parts) not in {1, 4}:
            errors.append(f"{run_path}: priorRun must use one timestamp directory or the legacy four-level order")
        elif str(prior_run) == run_path.parent.relative_to(root).as_posix():
            errors.append(f"{run_path}: priorRun must not point to the current run")
        elif str(prior_run) not in canonical_runs:
            errors.append(f"{run_path}: priorRun does not point to an exact canonical run")

    prompt = object_value(run.get("prompt"))
    if prompt.get("preservation") != "verbatim":
        errors.append(f"{run_path}: prompt.preservation must be exactly verbatim")
    digest = text_value(prompt.get("sha256"))
    workspace_directory = exact_child(run_path.parent, "workspace")
    if workspace_directory is None or not workspace_directory.is_dir() or workspace_directory.is_symlink():
        errors.append(f"{run_path}: run is missing an exact-case ordinary workspace/ directory")
    artifact_directory = exact_child(run_path.parent, "artifact")
    if artifact_directory is None or not artifact_directory.is_dir() or artifact_directory.is_symlink():
        errors.append(f"{run_path}: run is missing an exact-case ordinary artifact/ directory")
    prompt_path = exact_child(artifact_directory, "PROMPT.md") if artifact_directory is not None else None
    prompt_bytes: Optional[bytes] = None
    if not digest or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        errors.append(f"{run_path}: prompt.sha256 must be a SHA-256 hex digest")
    if prompt_path is not None:
        if is_regular_file_within(prompt_path, run_path.parent, "preserved prompt", errors):
            try:
                prompt_bytes = read_regular_file_bounded(prompt_path, DROP_MAX_FILE_BYTES)
                decoded_prompt = prompt_bytes.decode("utf-8")
            except BoundedReadError as error:
                if "exceeds" in str(error):
                    errors.append(f"{prompt_path}: file exceeds the conservative 5 MiB folder-drop limit")
                else:
                    errors.append(f"{prompt_path}: preserved prompt is not readable UTF-8: {error}")
            except UnicodeDecodeError as error:
                errors.append(f"{prompt_path}: preserved prompt is not readable UTF-8: {error}")
            else:
                if not decoded_prompt.strip():
                    errors.append(f"{prompt_path}: preserved prompt must not be blank")
                mojibake = find_likely_mojibake(decoded_prompt)
                if mojibake is not None:
                    errors.append(
                        f"{prompt_path}: preserved prompt contains likely mojibake at character "
                        f"offset {mojibake.offset} ({mojibake.codepoints}); correct the prepared "
                        "prompt at its source and preserve it as UTF-8"
                    )
                if digest and re.fullmatch(r"[0-9a-fA-F]{64}", digest):
                    actual = hashlib.sha256(prompt_bytes).hexdigest()
                    if actual.lower() != digest.lower():
                        errors.append(f"{run_path}: prompt SHA-256 does not match artifact/PROMPT.md")
    else:
        errors.append(f"{run_path}: run is missing exact-case artifact/PROMPT.md")

    prepared_contracts = validate_provenance_receipt(
        root,
        run_path,
        run,
        prompt_bytes,
        errors,
    )
    validate_manifest_paths(run_path, run, prepared_contracts.temporary, errors)
    temporary_directory = exact_child(run_path.parent, ".tmp")
    if prepared_contracts.temporary and (
        temporary_directory is None
        or not temporary_directory.is_dir()
        or temporary_directory.is_symlink()
    ):
        errors.append(f"{run_path}: run is missing an exact-case ordinary .tmp/ directory")

    execution = object_value(run.get("execution"))
    if execution.get("recursiveDelegation") != "allowed":
        errors.append(f"{run_path}: execution.recursiveDelegation must be exactly allowed")
    if execution.get("skillImposedLimits") != "none":
        errors.append(f"{run_path}: execution.skillImposedLimits must be exactly none")
    run_worker_identity = parse_worker_identity(execution, run_path, "execution", errors)

    report_path = exact_child(run_path.parent, "worker-report.json")
    report = None
    if report_path is None:
        errors.append(f"{run_path}: run is missing exact-case worker-report.json")
    elif is_regular_file_within(report_path, run_path.parent, "worker report", errors):
        report = load_object(report_path, errors)
    if report is None:
        if status == "OK":
            errors.append(f"{run_path}: successful run is missing worker-report.json")
    else:
        expected_report_schema = (
            "2.1" if prepared_contracts.quality_gauntlet else "2.0"
        )
        if report.get("schemaVersion") != expected_report_schema:
            errors.append(
                f"{report_path}: schemaVersion must be exactly {expected_report_schema}"
            )
        if text_value(report.get("runId")) != run_id:
            errors.append(f"{report_path}: runId must match namespace segment {run_id!r}")
        report_worker_identity = parse_worker_identity(report, report_path, "", errors)
        if (
            run_worker_identity is not None
            and report_worker_identity is not None
            and report_worker_identity != run_worker_identity
        ):
            errors.append(
                f"{report_path}: worker IDs must exactly match run.json execution worker IDs"
            )
        report_status = text_value(report.get("status"))
        if report_status not in STATUSES:
            errors.append(f"{report_path}: status must be one of {sorted(STATUSES)}")
        elif status in STATUSES and report_status != status:
            errors.append(f"{report_path}: status must match run.json status {status!r}")
        if prepared_contracts.temporary:
            report_temporary = object_value(report.get("temporary"))
            if report_temporary.get("path") != ".tmp/":
                errors.append(f"{report_path}: temporary.path must be exactly .tmp/")
            routing_applied = report_temporary.get("routingApplied")
            if routing_applied is not None and not isinstance(routing_applied, bool):
                errors.append(f"{report_path}: temporary.routingApplied must be true, false, or null")
            external_exceptions = report_temporary.get("externalExceptions")
            if not isinstance(external_exceptions, list) or not all(
                isinstance(item, str) and bool(item.strip()) for item in external_exceptions
            ):
                errors.append(f"{report_path}: temporary.externalExceptions must be an array of non-blank strings")
            elif status == "OK":
                if not isinstance(routing_applied, bool):
                    errors.append(f"{report_path}: successful run must record temporary.routingApplied as true or false")
                elif routing_applied is False and not external_exceptions:
                    errors.append(
                        f"{report_path}: successful run with temporary routing disabled must record an external exception"
                    )
        report_artifact = object_value(report.get("artifact"))
        if report_artifact.get("entrypoint") != "artifact/index.html":
            errors.append(f"{report_path}: artifact.entrypoint must be exactly artifact/index.html")
        if status == "OK" and report_artifact.get("staticDeploymentVerified") is not True:
            errors.append(f"{report_path}: successful run must set artifact.staticDeploymentVerified to true")
        if (
            prepared_contracts.quality_gauntlet
            and "qualityGauntlet" not in report
        ):
            errors.append(
                f"{report_path}: current run is missing required qualityGauntlet"
            )
        else:
            validate_quality_gauntlet(
                report.get("qualityGauntlet"),
                report_path,
                report_status,
                report_worker_identity,
                errors,
            )
        verification = report.get("verification")
        if status == "OK" and (
            not isinstance(verification, list)
            or not any(is_passed_verification(item) for item in verification)
        ):
            errors.append(f"{report_path}: successful run must record structured passed verification evidence")
        if status == "OK" and isinstance(verification, list) and any(
            is_failed_verification(item) for item in verification
        ):
            errors.append(f"{report_path}: successful run must not contain failed verification evidence")

    index_path = exact_child(artifact_directory, "index.html") if artifact_directory is not None else None
    artifact_tree_valid = True
    if artifact_directory is not None:
        previous_error_count = len(errors)
        validate_artifact_tree(artifact_directory, errors)
        artifact_tree_valid = len(errors) == previous_error_count
    is_index_file = False
    if index_path is not None:
        try:
            is_index_file = stat.S_ISREG(index_path.lstat().st_mode)
        except OSError as error:
            errors.append(f"{index_path}: unable to inspect artifact entrypoint: {error}")
    if status == "OK" and not is_index_file:
        errors.append(f"{run_path}: successful run is missing exact-case artifact/index.html")
    if is_index_file and artifact_tree_valid:
        validate_local_assets(index_path, errors)


def validate_prior_graph(root: Path, run_paths: list[Path], errors: list[str]) -> None:
    """Reject cycles between separately dispatched reruns."""

    edges: dict[str, str] = {}
    for run_path in run_paths:
        run = load_object(run_path, errors)
        if run is None:
            continue
        if not isinstance(run.get("priorRun"), str):
            continue
        edges[run_path.parent.relative_to(root).as_posix()] = run["priorRun"]

    completed: set[str] = set()
    reported: set[tuple[str, ...]] = set()
    for start in sorted(edges):
        chain: list[str] = []
        positions: dict[str, int] = {}
        current = start
        while current in edges and current not in completed:
            if current in positions:
                cycle = tuple(chain[positions[current] :] + [current])
                canonical = tuple(sorted(cycle[:-1]))
                if canonical not in reported:
                    errors.append(f"priorRun cycle detected: {' -> '.join(cycle)}")
                    reported.add(canonical)
                break
            positions[current] = len(chain)
            chain.append(current)
            current = edges[current]
        completed.update(chain)


def discover_run_paths(root: Path, errors: list[str]) -> list[Path]:
    """Enumerate flat and legacy runs without silently skipping unreadable subtrees."""

    run_paths: list[Path] = []

    def entries(directory: Path) -> Optional[list[os.DirEntry[str]]]:
        try:
            with os.scandir(directory) as iterator:
                return sorted(iterator, key=lambda entry: entry.name)
        except OSError as error:
            errors.append(f"{directory}: unable to inspect namespace directory: {error}")
            return None

    def walk(directory: Path, depth: int) -> None:
        children = entries(directory)
        if children is None:
            return
        for entry in children:
            path = Path(entry.path)
            if is_appledouble_sidecar(path):
                continue
            if depth == 0 and entry.name == CATALOGUE_LOCK:
                try:
                    lock_stat = entry.stat(follow_symlinks=False)
                    if (
                        entry.is_symlink()
                        or not stat.S_ISREG(lock_stat.st_mode)
                        or lock_stat.st_nlink != 1
                    ):
                        errors.append(f"{path}: catalogue lock path must be a private regular file")
                except OSError as error:
                    errors.append(f"{path}: unable to inspect catalogue lock path: {error}")
                continue
            if depth == 0 and entry.name in {"index.html", ".oneshot-provenance"}:
                continue
            if depth == 0 and STALE_INDEX_RE.fullmatch(entry.name):
                try:
                    if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                        errors.append(f"{Path(entry.path)}: reserved catalogue temporary path must be a regular file")
                except OSError as error:
                    errors.append(f"{Path(entry.path)}: unable to inspect reserved catalogue temporary file: {error}")
                continue
            if depth in {0, 1, 2} and NAMESPACE_TEMP_RE.fullmatch(entry.name):
                try:
                    if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                        errors.append(f"{path}: reserved namespace temporary path must be a directory")
                        continue
                except OSError as error:
                    errors.append(f"{path}: unable to inspect reserved namespace temporary path: {error}")
                    continue
                temporary_entries = entries(path)
                if temporary_entries is None:
                    continue
                temporary_entries = [
                    candidate
                    for candidate in temporary_entries
                    if not is_appledouble_sidecar(Path(candidate.path))
                ]
                if any(candidate.name != IDENTITY_MARKER for candidate in temporary_entries):
                    errors.append(f"{path}: reserved namespace temporary directory contains unexpected state")
                    continue
                for candidate in temporary_entries:
                    try:
                        if candidate.is_symlink() or not candidate.is_file(follow_symlinks=False):
                            errors.append(f"{Path(candidate.path)}: reserved namespace temporary marker must be a regular file")
                    except OSError as error:
                        errors.append(f"{Path(candidate.path)}: unable to inspect reserved namespace temporary marker: {error}")
                continue
            if depth in {1, 2, 3} and entry.name == IDENTITY_MARKER:
                continue
            try:
                if entry.is_symlink():
                    errors.append(f"{path}: namespace directories must not be symbolic links")
                    continue
                is_directory = entry.is_dir(follow_symlinks=False)
            except OSError as error:
                errors.append(f"{path}: unable to inspect namespace entry: {error}")
                continue
            if not is_directory:
                if entry.name == "run.json":
                    errors.append(f"{path}: run.json is outside a timestamped or legacy run directory")
                else:
                    errors.append(f"{path}: unexpected file outside a run, receipt inventory, or root catalogue")
                continue
            try:
                directory_mode = entry.stat(follow_symlinks=False).st_mode
            except OSError as error:
                errors.append(f"{path}: unable to inspect namespace directory metadata: {error}")
                continue
            if not directory_has_read_and_traverse_mode(directory_mode):
                errors.append(f"{path}: namespace directory must have a readable and traversable mode")
            is_flat_candidate = depth == 0 and FLAT_RUN_ID_RE.fullmatch(entry.name) is not None
            is_flat_run = depth == 0 and parse_flat_run_id(entry.name) is not None
            if is_flat_candidate and not is_flat_run:
                errors.append(
                    f"{path}: invalid flat run directory name; expected a real YYYY-MM-DD-HH-MM-SS "
                    "timestamp with no suffix or a canonical collision suffix of -02 or later"
                )
                is_flat_run = True
            is_legacy_run = depth == 3
            if not is_flat_run and not is_legacy_run and depth < 3:
                walk(path, depth + 1)
                continue
            if not is_flat_run and not is_legacy_run:
                errors.append(f"{path}: unexpected directory outside a run")
                continue
            commit_path = root / ".oneshot-provenance" / f"{path.name}.commit"
            if is_supported_run_id(path.name) and is_abandoned_run_reservation(path, commit_path):
                continue
            manifest = exact_child(path, "run.json")
            if manifest is None:
                errors.append(f"{path}: run directory is missing exact-case regular run.json")
                continue
            try:
                is_manifest = manifest.is_file() and not manifest.is_symlink()
            except OSError as error:
                errors.append(f"{manifest}: unable to inspect run manifest: {error}")
                continue
            if not is_manifest:
                errors.append(f"{path}: run directory is missing exact-case regular run.json")
                continue
            run_paths.append(manifest)

    walk(root, 0)
    return run_paths


def validate_root_index(root: Path, errors: list[str]) -> None:
    """Require the aggregate catalogue entrypoint to be exact, current, and publishable."""

    index_path = exact_child(root, "index.html")
    if index_path is None or not index_path.is_file() or index_path.is_symlink():
        errors.append(f"{root}: missing exact-case regular root index.html catalogue")
        return
    try:
        mode = index_path.stat().st_mode
    except OSError as error:
        errors.append(f"{index_path}: root catalogue metadata is unreadable: {error}")
        return
    if mode & 0o444 == 0:
        errors.append(f"{index_path}: root catalogue must have a readable file mode")
        return
    try:
        actual = read_regular_file_bounded(index_path, DROP_MAX_FILE_BYTES).decode("utf-8")
    except BoundedReadError as error:
        if "exceeds" in str(error):
            errors.append(f"{index_path}: root catalogue exceeds the 5 MiB read limit")
        else:
            errors.append(f"{index_path}: root catalogue is not readable UTF-8: {error}")
        return
    except UnicodeDecodeError as error:
        errors.append(f"{index_path}: root catalogue is not readable UTF-8: {error}")
        return
    try:
        expected = build_html(root, index_path)
    except (OSError, UnicodeDecodeError, CatalogueBuildError) as error:
        errors.append(f"{index_path}: unable to derive the current root catalogue: {error}")
        return
    if actual != expected:
        errors.append(
            f"{index_path}: root catalogue is stale, incomplete, or was not generated by build_catalog_index.py"
        )


def validate_receipt_inventory(root: Path, run_paths: list[Path], errors: list[str]) -> None:
    """Require a one-to-one inventory between coordinator receipts and run manifests."""

    receipt_directory = exact_child(root, ".oneshot-provenance")
    if receipt_directory is None:
        if run_paths:
            errors.append(f"{root}: missing exact-case .oneshot-provenance directory")
        return
    if receipt_directory.is_symlink():
        errors.append(f"{receipt_directory}: provenance directory must not be a symbolic link")
        return
    if not receipt_directory.is_dir():
        errors.append(f"{receipt_directory}: provenance inventory must be a directory")
        return
    try:
        entries = list(receipt_directory.iterdir())
    except OSError as error:
        errors.append(f"{receipt_directory}: unable to inspect provenance inventory: {error}")
        return

    expected = {run_path.parent.name: run_path for run_path in run_paths}
    receipts: dict[str, Path] = {}
    commits: dict[str, Path] = {}
    for entry in entries:
        if is_appledouble_sidecar(entry):
            continue
        if entry.is_symlink():
            errors.append(f"{entry}: provenance inventory files must not be symbolic links")
            continue
        if not entry.is_file():
            errors.append(f"{entry}: provenance inventory may contain only regular receipt and commit files")
            continue
        run_id = entry.stem
        if not is_supported_run_id(run_id) or entry.suffix not in {".json", ".commit"}:
            errors.append(f"{entry}: unexpected file in provenance inventory")
            continue
        if entry.suffix == ".json":
            receipts[run_id] = entry
            continue
        commits[run_id] = entry
        try:
            if entry.stat().st_size != 0:
                errors.append(f"{entry}: provenance commit marker must be empty")
        except OSError as error:
            errors.append(f"{entry}: unable to inspect provenance commit marker: {error}")

    for missing_id in sorted(set(expected) - set(receipts)):
        errors.append(
            f"{receipt_directory / (missing_id + '.json')}: run is missing its coordinator provenance receipt"
        )
    for missing_id in sorted(set(expected) - set(commits)):
        errors.append(
            f"{receipt_directory / (missing_id + '.commit')}: run is missing its provenance commit marker"
        )
    for unpaired_id in sorted(set(commits) - set(receipts)):
        errors.append(
            f"{commits[unpaired_id]}: provenance commit marker has no matching JSON receipt"
        )

    committed_ids = set(receipts) & set(commits)
    for orphan_id in sorted(committed_ids - set(expected)):
        orphan_path = receipts[orphan_id]
        errors.append(f"{orphan_path}: orphan provenance receipt has no matching run manifest")
        receipt = load_object(orphan_path, errors)
        if receipt is not None:
            run_path = text_value(receipt.get("runPath"))
            if run_path:
                errors.append(f"{orphan_path}: recorded run path is absent: {run_path}")


def validate(root: Path) -> dict[str, Any]:
    """Validate every discovered run and keep incomplete runs in the report."""
    errors: list[str] = []
    warnings: list[str] = []
    run_paths = discover_run_paths(root, errors)
    if not run_paths:
        errors.append("no run.json files found in a timestamped or legacy run directory")

    canonical_runs = {run_path.parent.relative_to(root).as_posix() for run_path in run_paths}
    seen_paths: set[str] = set()
    seen_run_ids: set[str] = set()
    for run_path in run_paths:
        relative_path = run_path.parent.relative_to(root).as_posix()
        if relative_path in seen_paths:
            errors.append(f"duplicate run path: {relative_path}")
            continue
        seen_paths.add(relative_path)
        run_id = run_path.parent.name
        if run_id in seen_run_ids:
            errors.append(f"duplicate global run ID: {run_id}")
        seen_run_ids.add(run_id)
        validate_run(root, run_path, canonical_runs, errors, warnings)

    validate_prior_graph(root, run_paths, errors)
    validate_receipt_inventory(root, run_paths, errors)
    validate_root_index(root, errors)

    return {
        "valid": not errors,
        "root": str(root),
        "runs": len(run_paths),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="One-shot output root")
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        print(
            json.dumps(
                {
                    "valid": False,
                    "root": str(args.root),
                    "runs": 0,
                    "errors": [f"unable to resolve output root: {error}"],
                    "warnings": [],
                },
                indent=2,
            )
        )
        return 1
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")
    result = validate(root)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

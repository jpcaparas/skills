#!/usr/bin/env python3
"""Validate the oneshot-websites skill package and its prompt catalogue."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

from runtime_contract import parse_json_bounded


REQUIRED_DIRS = ("agents", "assets", "evals", "references", "scripts", "templates")
REQUIRED_FILES = (
    "AGENTS.md",
    "README.md",
    "SKILL.md",
    "metadata.json",
    "agents/catalog-curator.md",
    "agents/oneshot-lead.md",
    "assets/prompt-catalogue.json",
    "evals/evals.json",
    "evals/trigger-evals.json",
    "references/README.md",
    "references/catalog-index.md",
    "references/catalogue-authoring.md",
    "references/execution-protocol.md",
    "references/research-notes.md",
    "scripts/build_catalog_index.py",
    "scripts/list_prompts.py",
    "scripts/prepare_run.py",
    "scripts/runtime_contract.py",
    "scripts/test_skill.py",
    "scripts/validate.py",
    "scripts/validate_catalog.py",
    "templates/namespace-identity.json",
    "templates/run.json",
    "templates/worker-dispatch.md",
)

LOCAL_REFERENCE_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])((?:agents|assets|evals|references|scripts|templates)/[A-Za-z0-9_./-]+)"
)
PROMPT_ID_RE = re.compile(r"^ow-[0-9]{3,}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FROZEN_CATALOGUE_PREFIX_COUNT = 100
FROZEN_CATALOGUE_PREFIX_SHA256 = "203a370b733bb6342d2d7d016aa6c9b514da109311e77bd72ae9c4ab0991ea76"

# These checks deliberately target unambiguous implementation prescriptions. A
# template may name a technology as its subject, but it must not prescribe a
# stack, version, file layout, resource budget, or workflow recipe.
IMPLEMENTATION_CONSTRAINTS = (
    ("version pin", re.compile(r"\b(?:react|vue|svelte|angular|node(?:\.js)?|python)\s*(?:v)?\d+(?:\.\d+){0,2}\b", re.I)),
    ("single-file recipe", re.compile(r"\b(?:single[- ]file|one[- ]file|one\s+html\s+file|all[- ]in[- ]one\s+html)\b", re.I)),
    (
        "named implementation recipe",
        re.compile(
            r"\b(?:use|using|built\s+with|build\s+(?:it\s+)?with|implement\s+(?:it\s+)?with)\s+"
            r"(?:only\s+)?(?:react|next(?:\.js)?|vue|nuxt|svelte|angular|solid(?:js)?|astro|tailwind(?:\s*css)?|"
            r"three(?:\.js)?|bootstrap|jquery|d3(?:\.js)?)\b",
            re.I,
        ),
    ),
    (
        "dependency or asset ban",
        re.compile(r"\b(?:no|without)\s+(?:any\s+)?(?:external\s+)?(?:dependencies|libraries|packages|assets)\b", re.I),
    ),
    (
        "resource budget",
        re.compile(
            r"\b(?:within|in)\s+\d+\s+(?:seconds?|minutes?|hours?)\b|"
            r"\b(?:exactly|at\s+most|no\s+more\s+than)\s+\d+\s+"
            r"(?:steps?|tool[- ]?calls?|files?|tokens?|minutes?|hours?)\b",
            re.I,
        ),
    ),
    (
        "goal-mode requirement",
        re.compile(r"\b(?:must|required\s+to|have\s+to)\s+(?:use|enable|enter)\s+goal[ -]?mode\b", re.I),
    ),
)

RUNTIME_CONTRACTS = (
    ("exact prompt preservation", re.compile(r"(?:byte-for-byte|exact\s+(?:UTF-8\s+)?bytes|verbatim).*?(?:prompt|PROMPT\.md)", re.I | re.S)),
    ("coordinator prompt receipt", re.compile(r"(?:coordinator-owned|pre-dispatch).*?(?:receipt|provenance).*?(?:outside|worker-owned)|\.oneshot-provenance", re.I | re.S)),
    ("one fresh lead per experiment", re.compile(r"(?:one|each|every)\s+(?:fresh\s+)?lead.*?(?:each|every|one).*?experiment|fresh\s+lead\s+subagent", re.I | re.S)),
    ("no inherited coordinator history", re.compile(r"no-history.*?fork_turns.*?none|fork_turns.*?none.*?(?:coordinator|history|conversation)", re.I | re.S)),
    ("recursive subagent delegation", re.compile(r"recursive\s+(?:subagent\s+)?delegation|(?:lead|subagents?).*?create.*?subagents", re.I | re.S)),
    ("no skill-imposed time, token, and tool limits", re.compile(r"no\s+skill-imposed.*?(?:time|token).*?(?:tool|tool-call)|no\s+(?:time|token).*?(?:tool|tool-call).*?(?:limit|budget)", re.I | re.S)),
    ("no goal-mode requirement", re.compile(r"goal[ -]?mode.*?(?:not|required|forbidden)|(?:not|required|forbidden).*?goal[ -]?mode", re.I | re.S)),
    ("model-harness-experiment namespace", re.compile(r"<model-key>\s*/\s*<harness-key>\s*/\s*<experiment-key>", re.I | re.S)),
    ("raw identity namespace markers", re.compile(r"\.oneshot-identity\.json.*?(?:raw name|raw identity|exact raw)", re.I | re.S)),
    ("relevance-gated catalogue matching", re.compile(r"genuinely relevant.*?optional baselines.*?no meaningful match.*?without.*?catalogue", re.I | re.S)),
    ("artifact prompt", re.compile(r"artifact/PROMPT\.md")),
    ("artifact entrypoint", re.compile(r"artifact/index\.html")),
    ("drop-ready no-build handoff", re.compile(r"(?:drop-ready|static\s+(?:folder|host)).*?(?:no\s+(?:package\s+)?install|no\s+build|deployable)|(?:no\s+(?:package\s+)?install|no\s+build).*?(?:drop-ready|static\s+(?:folder|host))", re.I | re.S)),
)


def parse_frontmatter(text: str) -> Dict[str, str]:
    """Parse the small scalar frontmatter contract without a YAML dependency."""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}

    values: Dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line or line.startswith((" ", "\t", "#")) or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        value = raw_value.strip()
        if len(value) >= 2 and value[:1] in ("'", '"') and value[-1:] == value[:1]:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def strip_code_blocks(text: str) -> str:
    return re.sub(r"```[\s\S]*?```", "", text)


def local_references(text: str) -> Set[str]:
    references: Set[str] = set()
    for match in LOCAL_REFERENCE_RE.finditer(strip_code_blocks(text)):
        reference = match.group(1).rstrip(".,:;)")
        if ".." not in Path(reference).parts:
            references.add(reference)
    return references


def read_json(path: Path, errors: List[str], root: Path) -> Optional[Any]:
    try:
        return parse_json_bounded(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        errors.append("invalid JSON in {}: {}".format(path.relative_to(root), exc))
        return None


def read_text(path: Path, errors: List[str], root: Path) -> Optional[str]:
    """Read package prose without letting malformed UTF-8 abort validation."""

    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append("invalid UTF-8 text in {}: {}".format(path.relative_to(root), exc))
        return None


def duplicate_values(values: Iterable[str]) -> Set[str]:
    seen: Set[str] = set()
    duplicates: Set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def as_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        normalized.encode("utf-8")
    except UnicodeEncodeError:
        return None
    return normalized


def validate_catalogue(data: Any, errors: List[str]) -> None:
    """Check permanent catalogue identities and implementation-open prompts."""
    if not isinstance(data, Mapping):
        errors.append("assets/prompt-catalogue.json must contain an object")
        return
    if data.get("schemaVersion") != "1.0":
        errors.append("prompt catalogue schemaVersion must be 1.0")

    categories = data.get("categories")
    prompts = data.get("prompts")
    if not isinstance(categories, list):
        errors.append("prompt catalogue categories must be an array")
        categories = []
    if not isinstance(prompts, list):
        errors.append("prompt catalogue prompts must be an array")
        return

    category_ids: List[str] = []
    for index, category in enumerate(categories):
        if not isinstance(category, Mapping):
            errors.append("catalogue category {} must be an object".format(index))
            continue
        for field in ("id", "title"):
            field_value = category.get(field)
            if isinstance(field_value, str) and field_value != field_value.strip():
                errors.append(
                    "catalogue category {} {} must not contain surrounding whitespace".format(
                        index,
                        field,
                    )
                )
        category_id = as_text(category.get("id"))
        title = as_text(category.get("title"))
        if category_id is None or not SLUG_RE.fullmatch(category_id):
            errors.append("catalogue category {} has an invalid id".format(index))
        else:
            category_ids.append(category_id)
        if title is None:
            errors.append("catalogue category {} is missing a title".format(index))
    duplicates = duplicate_values(category_ids)
    if duplicates:
        errors.append("catalogue contains duplicate category ids: {}".format(", ".join(sorted(duplicates))))
    known_categories = set(category_ids)

    if len(prompts) < FROZEN_CATALOGUE_PREFIX_COUNT:
        errors.append(
            "prompt catalogue must contain at least {} prompts (found {})".format(
                FROZEN_CATALOGUE_PREFIX_COUNT,
                len(prompts),
            )
        )
    if len(prompts) >= FROZEN_CATALOGUE_PREFIX_COUNT:
        frozen_prefix = json.dumps(
            prompts[:FROZEN_CATALOGUE_PREFIX_COUNT],
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        frozen_digest = hashlib.sha256(frozen_prefix).hexdigest()
        if frozen_digest != FROZEN_CATALOGUE_PREFIX_SHA256:
            errors.append(
                "catalogue entries ow-001 through ow-100 are a frozen append-only prefix; "
                "append new entries without editing, deleting, renumbering, or reordering the seed catalogue"
            )

    ids: List[str] = []
    slugs: List[str] = []
    titles: List[str] = []
    prompt_texts: List[str] = []
    for index, item in enumerate(prompts):
        label = "catalogue prompt {}".format(index)
        if not isinstance(item, Mapping):
            errors.append("{} must be an object".format(label))
            continue
        for field in ("id", "slug", "title", "category", "prompt"):
            field_value = item.get(field)
            if isinstance(field_value, str) and field_value != field_value.strip():
                errors.append("{} {} must not contain surrounding whitespace".format(label, field))
        prompt_id = as_text(item.get("id"))
        slug = as_text(item.get("slug"))
        title = as_text(item.get("title"))
        category = as_text(item.get("category"))
        prompt = as_text(item.get("prompt"))
        tags = item.get("tags")
        expected_prompt_id = "ow-{:03d}".format(index + 1)

        if prompt_id is None or not PROMPT_ID_RE.fullmatch(prompt_id):
            errors.append("{} has an invalid stable id".format(label))
        else:
            ids.append(prompt_id)
            if prompt_id != expected_prompt_id:
                errors.append(
                    "{} must use the next append-only stable id {}".format(
                        label,
                        expected_prompt_id,
                    )
                )
        if slug is None or not SLUG_RE.fullmatch(slug):
            errors.append("{} has an invalid slug".format(label))
        else:
            slugs.append(slug)
        if title is None:
            errors.append("{} is missing a title".format(label))
        else:
            titles.append(title.casefold())
        if category is None or category not in known_categories:
            errors.append("{} uses an undeclared category: {}".format(label, category or "missing"))
        if prompt is None:
            errors.append("{} is missing prompt text".format(label))
        else:
            prompt_texts.append(prompt.casefold())
            if not prompt.startswith("Create "):
                errors.append("{} must begin with a goal-led 'Create ' statement".format(label))
            for reason, expression in IMPLEMENTATION_CONSTRAINTS:
                if expression.search(prompt):
                    errors.append("{} contains a {} constraint".format(label, reason))
        if not isinstance(tags, list) or not tags:
            errors.append("{} must have non-empty tags".format(label))
        else:
            clean_tags = [tag for tag in tags if isinstance(tag, str) and SLUG_RE.fullmatch(tag)]
            if len(clean_tags) != len(tags):
                errors.append("{} has invalid tags".format(label))
            if len(set(clean_tags)) != len(clean_tags):
                errors.append("{} has duplicate tags".format(label))

    for field, values in (("ids", ids), ("slugs", slugs), ("titles", titles), ("prompt texts", prompt_texts)):
        duplicates = duplicate_values(values)
        if duplicates:
            errors.append("catalogue contains duplicate {}: {}".format(field, ", ".join(sorted(duplicates))))


def validate_runtime_contract(root: Path, errors: List[str]) -> None:
    paths = (
        root / "SKILL.md",
        root / "agents" / "oneshot-lead.md",
        root / "references" / "execution-protocol.md",
        root / "references" / "catalog-index.md",
    )
    parts = [read_text(path, errors, root) for path in paths if path.is_file()]
    text = "\n".join(part for part in parts if part is not None)
    for label, expression in RUNTIME_CONTRACTS:
        if not expression.search(text):
            errors.append("runtime contract missing {}".format(label))


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        return 1

    root = Path(sys.argv[1]).resolve()
    errors: List[str] = []
    warnings: List[str] = []
    if not root.is_dir():
        print("not a directory: {}".format(root), file=sys.stderr)
        return 1

    for directory in REQUIRED_DIRS:
        if not (root / directory).is_dir():
            errors.append("missing directory: {}".format(directory))
    for file_name in REQUIRED_FILES:
        if not (root / file_name).is_file():
            errors.append("missing file: {}".format(file_name))

    skill_md = root / "SKILL.md"
    if skill_md.is_file():
        skill_text = read_text(skill_md, errors, root)
        if skill_text is not None:
            frontmatter = parse_frontmatter(skill_text)
            if frontmatter.get("name") != root.name:
                errors.append("frontmatter name must be {}".format(root.name))
            description = frontmatter.get("description")
            if not description:
                errors.append("frontmatter description missing")
            elif len(description) > 1024:
                errors.append("frontmatter description exceeds 1024 chars")
            if skill_text.count("\n") + 1 > 500:
                warnings.append("SKILL.md is over 500 lines")

    for markdown in root.rglob("*.md"):
        markdown_text = read_text(markdown, errors, root)
        if markdown_text is None:
            continue
        for reference in local_references(markdown_text):
            target = (root / reference).resolve()
            if root not in target.parents or not target.exists():
                errors.append("{} references missing file: {}".format(markdown.relative_to(root), reference))

    json_files = sorted(root.rglob("*.json"))
    json_data: Dict[Path, Any] = {}
    for json_file in json_files:
        data = read_json(json_file, errors, root)
        if data is not None:
            json_data[json_file] = data

    metadata = json_data.get(root / "metadata.json")
    if isinstance(metadata, Mapping) and metadata.get("version") != "2.0.0":
        errors.append("metadata.json version must be 2.0.0")
    elif metadata is not None and not isinstance(metadata, Mapping):
        errors.append("metadata.json must contain an object")

    catalogue = json_data.get(root / "assets" / "prompt-catalogue.json")
    if catalogue is not None:
        validate_catalogue(catalogue, errors)

    validate_runtime_contract(root, errors)
    result = {"valid": not errors, "errors": errors, "warnings": warnings}
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

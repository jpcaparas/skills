#!/usr/bin/env python3
"""Scrape, validate, list, and search a curated official chezmoi docs corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Mapping, Sequence, cast


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DEFAULT_DOCS_DIR = SKILL_ROOT / "references" / "official-docs"
SITEMAP_URL = "https://www.chezmoi.io/sitemap.xml"
USER_AGENT = "better-chezmoi-official-docs/1.0"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
SCHEMA_VERSION = 1
TOC_ARTICLE_LINE_THRESHOLD = 290


@dataclass(frozen=True, slots=True)
class DocumentSource:
    """One official page earned by a supported better-chezmoi branch."""

    slug: str
    branch: str
    url: str

    @property
    def filename(self) -> str:
        return f"{self.slug}.md"


@dataclass(frozen=True, slots=True)
class FetchedDocument:
    """Normalized article plus the provenance required for publication."""

    source: DocumentSource
    article: str
    article_sha256: str
    rendered: str
    file_sha256: str
    site_last_modified: str | None


@dataclass(frozen=True, slots=True)
class ManifestDocument:
    slug: str
    branch: str
    url: str
    file: str
    article_sha256: str
    file_sha256: str
    site_last_modified: str | None


@dataclass(frozen=True, slots=True)
class CorpusManifest:
    retrieved_at: str
    documents: tuple[ManifestDocument, ...]


@dataclass(frozen=True, slots=True)
class CorpusDiff:
    added: tuple[str, ...]
    changed: tuple[str, ...]
    removed: tuple[str, ...]
    unchanged: tuple[str, ...]

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.changed or self.removed)


class CorpusError(RuntimeError):
    """Raised when the live or committed corpus cannot be trusted."""


DOCUMENT_SOURCES: tuple[DocumentSource, ...] = (
    DocumentSource("quick-start", "setup", "https://www.chezmoi.io/quick-start/"),
    DocumentSource("setup", "setup", "https://www.chezmoi.io/user-guide/setup/"),
    DocumentSource(
        "daily-operations",
        "daily",
        "https://www.chezmoi.io/user-guide/daily-operations/",
    ),
    DocumentSource(
        "command-overview",
        "daily",
        "https://www.chezmoi.io/user-guide/command-overview/",
    ),
    DocumentSource(
        "templating", "templates", "https://www.chezmoi.io/user-guide/templating/"
    ),
    DocumentSource(
        "machine-differences",
        "setup",
        "https://www.chezmoi.io/user-guide/manage-machine-to-machine-differences/",
    ),
    DocumentSource(
        "scripts",
        "automation",
        "https://www.chezmoi.io/user-guide/use-scripts-to-perform-actions/",
    ),
    DocumentSource(
        "password-managers",
        "secrets",
        "https://www.chezmoi.io/user-guide/password-managers/",
    ),
    DocumentSource(
        "encryption", "secrets", "https://www.chezmoi.io/user-guide/encryption/"
    ),
    DocumentSource(
        "troubleshooting",
        "recovery",
        "https://www.chezmoi.io/user-guide/frequently-asked-questions/troubleshooting/",
    ),
    DocumentSource(
        "global-flags",
        "commands",
        "https://www.chezmoi.io/reference/command-line-flags/global/",
    ),
    DocumentSource(
        "common-flags",
        "commands",
        "https://www.chezmoi.io/reference/command-line-flags/common/",
    ),
    DocumentSource("init", "setup", "https://www.chezmoi.io/reference/commands/init/"),
    DocumentSource("add", "daily", "https://www.chezmoi.io/reference/commands/add/"),
    DocumentSource("edit", "daily", "https://www.chezmoi.io/reference/commands/edit/"),
    DocumentSource("diff", "daily", "https://www.chezmoi.io/reference/commands/diff/"),
    DocumentSource(
        "status", "daily", "https://www.chezmoi.io/reference/commands/status/"
    ),
    DocumentSource(
        "apply", "daily", "https://www.chezmoi.io/reference/commands/apply/"
    ),
    DocumentSource(
        "update", "daily", "https://www.chezmoi.io/reference/commands/update/"
    ),
    DocumentSource(
        "verify", "daily", "https://www.chezmoi.io/reference/commands/verify/"
    ),
    DocumentSource(
        "doctor", "recovery", "https://www.chezmoi.io/reference/commands/doctor/"
    ),
    DocumentSource(
        "merge", "recovery", "https://www.chezmoi.io/reference/commands/merge/"
    ),
    DocumentSource(
        "re-add", "daily", "https://www.chezmoi.io/reference/commands/re-add/"
    ),
    DocumentSource(
        "forget", "recovery", "https://www.chezmoi.io/reference/commands/forget/"
    ),
    DocumentSource(
        "destroy", "recovery", "https://www.chezmoi.io/reference/commands/destroy/"
    ),
    DocumentSource(
        "purge", "recovery", "https://www.chezmoi.io/reference/commands/purge/"
    ),
    DocumentSource(
        "source-path",
        "commands",
        "https://www.chezmoi.io/reference/commands/source-path/",
    ),
    DocumentSource(
        "data", "templates", "https://www.chezmoi.io/reference/commands/data/"
    ),
    DocumentSource(
        "execute-template",
        "templates",
        "https://www.chezmoi.io/reference/commands/execute-template/",
    ),
    DocumentSource(
        "hooks",
        "automation",
        "https://www.chezmoi.io/reference/configuration-file/hooks/",
    ),
)


VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
SKIPPED_ELEMENTS = {"button", "script", "style", "svg"}


class ArticleMarkdownParser(HTMLParser):
    """Convert the rendered MkDocs article into stable, searchable Markdown."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.in_article = False
        self.skip_depth = 0
        self.pre_depth = 0
        self.code_depth = 0
        self.heading_level: int | None = None
        self.list_kinds: list[str] = []
        self.list_counts: list[int] = []
        self.link_targets: list[str | None] = []
        self.parts: list[str] = []

    @staticmethod
    def _classes(attributes: list[tuple[str, str | None]]) -> set[str]:
        class_value = next((value for key, value in attributes if key == "class"), None)
        return set(class_value.split()) if class_value else set()

    def _append(self, value: str) -> None:
        self.parts.append(value)

    def _blank_line(self) -> None:
        self._append("\n\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = self._classes(attrs)
        if tag == "article" and "md-content__inner" in classes:
            self.in_article = True
            return
        if not self.in_article:
            return
        if self.skip_depth:
            if tag not in VOID_ELEMENTS:
                self.skip_depth += 1
            return
        if tag in SKIPPED_ELEMENTS or classes.intersection(
            {"headerlink", "md-content__button", "md-source-file"}
        ):
            self.skip_depth = 1
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.heading_level = int(tag[1])
            self._blank_line()
            self._append("#" * self.heading_level + " ")
        elif tag == "p":
            self._blank_line()
        elif tag == "pre":
            self.pre_depth += 1
            self._append("\n\n```\n")
        elif tag == "code" and self.pre_depth == 0:
            self.code_depth += 1
            self._append("`")
        elif tag in {"ul", "ol"}:
            self.list_kinds.append(tag)
            self.list_counts.append(0)
            self._append("\n")
        elif tag == "li":
            indent = "  " * max(0, len(self.list_kinds) - 1)
            if self.list_kinds and self.list_kinds[-1] == "ol":
                self.list_counts[-1] += 1
                marker = f"{self.list_counts[-1]}. "
            else:
                marker = "- "
            self._append(f"\n{indent}{marker}")
        elif tag == "a":
            href = next((value for key, value in attrs if key == "href"), None)
            target = urllib.parse.urljoin(self.base_url, href) if href else None
            self.link_targets.append(target)
            self._append("[")
        elif tag == "br":
            self._append("\n")
        elif tag == "hr":
            self._append("\n\n---\n\n")
        elif tag == "blockquote":
            self._append("\n\n> ")
        elif tag == "tr":
            self._append("\n")
        elif tag in {"td", "th"}:
            self._append(" | ")

    def handle_endtag(self, tag: str) -> None:
        if not self.in_article:
            return
        if self.skip_depth:
            self.skip_depth -= 1
            return
        if tag == "article":
            self.in_article = False
        elif re.fullmatch(r"h[1-6]", tag):
            self.heading_level = None
            self._blank_line()
        elif tag == "p":
            self._blank_line()
        elif tag == "pre":
            self.pre_depth = max(0, self.pre_depth - 1)
            self._append(
                "```\n\n"
                if self.parts and self.parts[-1].endswith("\n")
                else "\n```\n\n"
            )
        elif tag == "code" and self.pre_depth == 0 and self.code_depth:
            self.code_depth -= 1
            self._append("`")
        elif tag in {"ul", "ol"} and self.list_kinds:
            self.list_kinds.pop()
            self.list_counts.pop()
            self._append("\n")
        elif tag == "a" and self.link_targets:
            target = self.link_targets.pop()
            self._append(f"]({target})" if target else "]")
        elif tag == "blockquote":
            self._blank_line()

    def handle_data(self, data: str) -> None:
        if not self.in_article or self.skip_depth:
            return
        if self.pre_depth:
            self._append(data)
            return
        normalized = re.sub(r"\s+", " ", data)
        if not normalized.strip():
            if normalized and self.parts and not self.parts[-1].endswith((" ", "\n")):
                self._append(" ")
            return
        if (
            self.parts
            and not self.parts[-1].endswith((" ", "\n", "[", "`"))
            and not normalized.startswith(" ")
        ):
            self._append(" ")
        self._append(normalized)

    def markdown(self) -> str:
        text = "".join(self.parts)
        # Absolute paths in inline code are documentation, not package routes.
        # Bold preserves emphasis without making package validators follow them.
        text = re.sub(
            r"`(/[^`\n]+)`",
            lambda match: f"**{match.group(1)}**",
            text,
        )
        lines = [line.rstrip() for line in text.splitlines()]
        cleaned: list[str] = []
        blank = False
        for line in lines:
            stripped = line.strip()
            if stripped in {"Back to top", "Was this helpful?"}:
                continue
            if not stripped:
                if not blank:
                    cleaned.append("")
                blank = True
                continue
            cleaned.append(line.strip() if line.lstrip().startswith("#") else line)
            blank = False
        return "\n".join(cleaned).strip() + "\n"


def heading_anchor(title: str) -> str:
    """Approximate common Markdown heading anchors for generated local navigation."""
    without_markup = re.sub(r"[`*_~]", "", title)
    without_links = re.sub(r"\[([^]]+)]\([^)]*\)", r"\1", without_markup)
    words = re.sub(r"[^a-z0-9 -]", "", without_links.casefold())
    return re.sub(r"[ -]+", "-", words).strip("-")


def add_table_of_contents(article: str) -> str:
    """Add navigation to long generated references without changing short pages."""
    lines = article.rstrip().splitlines()
    if len(lines) <= TOC_ARTICLE_LINE_THRESHOLD or any(
        re.match(r"^##\s+Contents\s*$", line) for line in lines
    ):
        return article
    headings: list[tuple[int, str, str]] = []
    for line in lines:
        match = re.match(r"^(#{2,3})\s+(.+?)\s*$", line)
        if match is None:
            continue
        title = match.group(2)
        anchor = heading_anchor(title)
        if anchor:
            headings.append((len(match.group(1)), title, anchor))
    if not headings:
        return article
    contents = ["## Contents", ""]
    contents.extend(
        f"{'  ' if level == 3 else ''}- [{title}](#{anchor})"
        for level, title, anchor in headings
    )
    insertion = 1 if lines and lines[0].startswith("# ") else 0
    augmented = lines[:insertion] + [""] + contents + [""] + lines[insertion:]
    return "\n".join(augmented).strip() + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    hostname = (parsed.hostname or "").removeprefix("www.")
    path = parsed.path.rstrip("/") + "/"
    return urllib.parse.urlunsplit(
        (parsed.scheme.lower(), hostname.lower(), path, "", "")
    )


def fetch_text(url: str, timeout_seconds: float, attempts: int = 3) -> str:
    """Fetch bounded UTF-8 text with a small retry budget for transient failures."""

    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                payload = cast(bytes, response.read(MAX_RESPONSE_BYTES + 1))
            if len(payload) > MAX_RESPONSE_BYTES:
                raise CorpusError(f"Response exceeds {MAX_RESPONSE_BYTES} bytes: {url}")
            return payload.decode("utf-8")
        except (
            OSError,
            UnicodeError,
            urllib.error.HTTPError,
            urllib.error.URLError,
        ) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(min(2**attempt, 2))
    raise CorpusError(f"Failed to fetch {url}: {last_error}")


def parse_sitemap(xml_text: str) -> dict[str, str]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise CorpusError(f"Official sitemap is invalid XML: {exc}") from exc
    last_modified: dict[str, str] = {}
    for entry in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
        location = entry.findtext("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        modified = entry.findtext(
            "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod"
        )
        if location and modified:
            last_modified[normalized_url(location)] = modified.strip()
    if not last_modified:
        raise CorpusError("Official sitemap contains no URL last-modified records")
    return last_modified


def extract_article(html_text: str, source_url: str) -> str:
    parser = ArticleMarkdownParser(source_url)
    parser.feed(html_text)
    parser.close()
    article = parser.markdown()
    if len(article) < 80 or not re.search(r"^# ", article, re.MULTILINE):
        raise CorpusError(f"Official page has no valid MkDocs article: {source_url}")
    return add_table_of_contents(article)


def render_document(
    source: DocumentSource, article: str, site_last_modified: str | None
) -> FetchedDocument:
    article_hash = sha256_text(article)
    modified = site_last_modified or "unknown"
    rendered = (
        "<!-- Generated by scripts/official_docs.py; refresh instead of editing. -->\n\n"
        f"Official source: {source.url}\n\n"
        f"Branch: {source.branch}\n\n"
        f"Site last modified: {modified}\n\n"
        f"Article SHA-256: `{article_hash}`\n\n"
        "---\n\n"
        f"{article}"
    )
    return FetchedDocument(
        source=source,
        article=article,
        article_sha256=article_hash,
        rendered=rendered,
        file_sha256=sha256_text(rendered),
        site_last_modified=site_last_modified,
    )


def fetch_document(
    source: DocumentSource,
    sitemap: Mapping[str, str],
    timeout_seconds: float,
) -> FetchedDocument:
    html_text = fetch_text(source.url, timeout_seconds)
    article = extract_article(html_text, source.url)
    return render_document(source, article, sitemap.get(normalized_url(source.url)))


def fetch_corpus(timeout_seconds: float, workers: int) -> tuple[FetchedDocument, ...]:
    sitemap = parse_sitemap(fetch_text(SITEMAP_URL, timeout_seconds))
    fetched: dict[str, FetchedDocument] = {}
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_sources = {
            executor.submit(fetch_document, source, sitemap, timeout_seconds): source
            for source in DOCUMENT_SOURCES
        }
        for future in as_completed(future_sources):
            source = future_sources[future]
            try:
                fetched[source.slug] = future.result()
            except (
                Exception
            ) as exc:  # Preserve every page failure before refusing publication.
                errors.append(f"{source.slug}: {exc}")
    if errors:
        raise CorpusError(
            "One or more official pages failed:\n- " + "\n- ".join(sorted(errors))
        )
    return tuple(fetched[source.slug] for source in DOCUMENT_SOURCES)


def manifest_payload(
    documents: Sequence[FetchedDocument], retrieved_at: str
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": "scripts/official_docs.py",
        "retrieved_at": retrieved_at,
        "sitemap_url": SITEMAP_URL,
        "documents": [
            {
                "slug": document.source.slug,
                "branch": document.source.branch,
                "url": document.source.url,
                "file": document.source.filename,
                "article_sha256": document.article_sha256,
                "file_sha256": document.file_sha256,
                "site_last_modified": document.site_last_modified,
            }
            for document in documents
        ],
    }


def write_staged_corpus(
    directory: Path, documents: Sequence[FetchedDocument], retrieved_at: str
) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    for document in documents:
        (directory / document.source.filename).write_text(
            document.rendered, encoding="utf-8"
        )
    manifest = manifest_payload(documents, retrieved_at)
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def require_mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise CorpusError(f"{context} must be an object with string keys")
    # Runtime key validation above establishes the Mapping[str, object] boundary.
    return cast(Mapping[str, object], value)


def require_string(mapping: Mapping[str, object], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise CorpusError(f"{context}.{key} must be a non-empty string")
    return value


def read_manifest(directory: Path) -> CorpusManifest:
    path = directory / "manifest.json"
    if not path.is_file():
        raise CorpusError(f"Missing corpus manifest: {path}")
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorpusError(f"Corpus manifest is invalid JSON: {exc}") from exc
    root = require_mapping(raw, "manifest")
    if root.get("schema_version") != SCHEMA_VERSION:
        raise CorpusError(f"Unsupported manifest schema: {root.get('schema_version')}")
    retrieved_at = require_string(root, "retrieved_at", "manifest")
    raw_documents = root.get("documents")
    if not isinstance(raw_documents, list) or not raw_documents:
        raise CorpusError("manifest.documents must be a non-empty array")
    documents: list[ManifestDocument] = []
    for index, raw_document in enumerate(raw_documents):
        context = f"manifest.documents[{index}]"
        item = require_mapping(raw_document, context)
        modified = item.get("site_last_modified")
        if modified is not None and not isinstance(modified, str):
            raise CorpusError(f"{context}.site_last_modified must be string or null")
        documents.append(
            ManifestDocument(
                slug=require_string(item, "slug", context),
                branch=require_string(item, "branch", context),
                url=require_string(item, "url", context),
                file=require_string(item, "file", context),
                article_sha256=require_string(item, "article_sha256", context),
                file_sha256=require_string(item, "file_sha256", context),
                site_last_modified=modified,
            )
        )
    return CorpusManifest(retrieved_at=retrieved_at, documents=tuple(documents))


def extract_rendered_article(text: str, filename: str) -> str:
    """Return the generated article body whose digest is recorded in the manifest."""
    header, separator, article = text.partition("\n---\n\n")
    if not separator or not header.startswith(
        "<!-- Generated by scripts/official_docs.py;"
    ):
        raise CorpusError(f"Corpus file has no generated article boundary: {filename}")
    if not article:
        raise CorpusError(f"Corpus file has an empty article body: {filename}")
    return article


def validate_corpus(directory: Path, require_inventory: bool = True) -> CorpusManifest:
    manifest = read_manifest(directory)
    expected = {source.slug: source for source in DOCUMENT_SOURCES}
    seen: set[str] = set()
    for document in manifest.documents:
        if document.slug in seen:
            raise CorpusError(f"Duplicate manifest slug: {document.slug}")
        seen.add(document.slug)
        if require_inventory:
            source = expected.get(document.slug)
            if source is None:
                raise CorpusError(f"Unexpected manifest slug: {document.slug}")
            if (document.branch, document.url, document.file) != (
                source.branch,
                source.url,
                source.filename,
            ):
                raise CorpusError(f"Manifest source contract drifted: {document.slug}")
        path = directory / document.file
        if path.parent != directory or not path.is_file():
            raise CorpusError(f"Missing or unsafe corpus file: {document.file}")
        if sha256_file(path) != document.file_sha256:
            raise CorpusError(f"Corpus file hash mismatch: {document.file}")
        text = path.read_text(encoding="utf-8")
        if document.article_sha256 not in text or document.url not in text:
            raise CorpusError(f"Corpus provenance missing from file: {document.file}")
        article = extract_rendered_article(text, document.file)
        if sha256_text(article) != document.article_sha256:
            raise CorpusError(f"Corpus article hash mismatch: {document.file}")
    if require_inventory and seen != set(expected):
        missing = sorted(set(expected) - seen)
        raise CorpusError("Corpus is missing configured pages: " + ", ".join(missing))
    listed_files = {document.file for document in manifest.documents}
    extra_files = {path.name for path in directory.glob("*.md")} - listed_files
    if extra_files:
        raise CorpusError(
            "Corpus contains unlisted Markdown files: " + ", ".join(sorted(extra_files))
        )
    return manifest


def compare_corpus(directory: Path, documents: Sequence[FetchedDocument]) -> CorpusDiff:
    if not directory.exists() or (directory.is_dir() and not any(directory.iterdir())):
        return CorpusDiff(
            added=tuple(document.source.slug for document in documents),
            changed=(),
            removed=(),
            unchanged=(),
        )
    manifest = validate_corpus(directory)
    current = {
        document.slug: document.article_sha256 for document in manifest.documents
    }
    fetched = {document.source.slug: document.article_sha256 for document in documents}
    return CorpusDiff(
        added=tuple(sorted(set(fetched) - set(current))),
        changed=tuple(
            sorted(
                slug
                for slug in set(fetched) & set(current)
                if fetched[slug] != current[slug]
            )
        ),
        removed=tuple(sorted(set(current) - set(fetched))),
        unchanged=tuple(
            sorted(
                slug
                for slug in set(fetched) & set(current)
                if fetched[slug] == current[slug]
            )
        ),
    )


def replace_corpus(
    directory: Path, documents: Sequence[FetchedDocument], retrieved_at: str
) -> None:
    parent = directory.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{directory.name}-staging-", dir=parent))
    # mkdtemp creates the directory; the writer requires a non-existent target.
    staging.rmdir()
    backup = parent / f".{directory.name}-backup-{os.getpid()}"
    try:
        write_staged_corpus(staging, documents, retrieved_at)
        validate_corpus(staging)
        if backup.exists():
            raise CorpusError(f"Refusing to overwrite stale backup: {backup}")
        if directory.exists():
            directory.replace(backup)
        try:
            staging.replace(directory)
        except Exception:
            if backup.exists() and not directory.exists():
                backup.replace(directory)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def print_diff(diff: CorpusDiff) -> None:
    for label, values in (
        ("added", diff.added),
        ("changed", diff.changed),
        ("removed", diff.removed),
        ("unchanged", diff.unchanged),
    ):
        print(f"{label}: {len(values)}")
        for value in values:
            print(f"  - {value}")


def command_refresh(args: argparse.Namespace) -> int:
    docs_dir = Path(args.output).expanduser().resolve()
    documents = fetch_corpus(timeout_seconds=args.timeout, workers=args.workers)
    diff = compare_corpus(docs_dir, documents)
    print_diff(diff)
    if not args.write:
        print("preview only: add --write to publish the fully validated corpus")
        return 0
    if not diff.has_changes:
        print("no content changes: existing corpus left byte-for-byte unchanged")
        return 0
    retrieved_at = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    replace_corpus(docs_dir, documents, retrieved_at)
    print(f"published: {docs_dir}")
    return 0


def command_check(args: argparse.Namespace) -> int:
    docs_dir = Path(args.docs).expanduser().resolve()
    manifest = validate_corpus(docs_dir)
    print(f"PASS: {len(manifest.documents)} official documents validated in {docs_dir}")
    print(f"retrieved_at: {manifest.retrieved_at}")
    return 0


def command_list(args: argparse.Namespace) -> int:
    docs_dir = Path(args.docs).expanduser().resolve()
    manifest = validate_corpus(docs_dir)
    for document in manifest.documents:
        modified = document.site_last_modified or "unknown"
        print(f"{document.branch}\t{document.slug}\t{modified}\t{document.url}")
    return 0


def command_search(args: argparse.Namespace) -> int:
    docs_dir = Path(args.docs).expanduser().resolve()
    manifest = validate_corpus(docs_dir)
    flags = 0 if args.case_sensitive else re.IGNORECASE
    expression = args.query if args.regex else re.escape(args.query)
    try:
        pattern = re.compile(expression, flags)
    except re.error as exc:
        raise CorpusError(f"Invalid search expression: {exc}") from exc
    matches = 0
    for document in manifest.documents:
        path = docs_dir / document.file
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not pattern.search(line):
                continue
            print(f"{document.file}:{line_number}: {line.strip()}")
            matches += 1
            if matches >= args.limit:
                return 0
    return 0 if matches else 1


def run_self_tests() -> dict[str, object]:
    sample = """
    <html><body><nav>Ignore me</nav>
    <article class="md-content__inner md-typeset">
      <a class="md-content__button" href="edit">Edit</a>
      <h1>Daily <code>apply</code></h1>
      <p>Preview <a href="../flags/">flags</a> first.</p>
      <p>Use <code>/tmp</code> carefully.</p>
      <ul><li>Inspect</li><li>Apply</li></ul>
      <div class="highlight"><pre><code>chezmoi apply --dry-run\n</code></pre></div>
      <div class="md-source-file">Updated yesterday</div>
    </article><footer>Ignore footer</footer></body></html>
    """
    checks: dict[str, bool] = {}
    article = extract_article(
        sample, "https://www.chezmoi.io/reference/commands/apply/"
    )
    checks["article_selected"] = (
        "Ignore me" not in article and "Ignore footer" not in article
    )
    checks["heading_preserved"] = article.startswith("# Daily `apply`")
    checks["link_resolved"] = (
        "https://www.chezmoi.io/reference/commands/flags/" in article
    )
    checks["code_preserved"] = "```\nchezmoi apply --dry-run\n```" in article
    checks["absolute_inline_code_is_not_a_route"] = "**/tmp**" in article
    long_article = "# Long\n\n## First section\n\n" + "detail\n" * 301
    checks["long_articles_gain_navigation"] = (
        "## Contents\n\n- [First section](#first-section)"
        in add_table_of_contents(long_article)
    )
    checks["source_footer_removed"] = "Updated yesterday" not in article
    missing_article_failed = False
    try:
        extract_article("<html><h1>Wrong region</h1></html>", "https://www.chezmoi.io/")
    except CorpusError:
        missing_article_failed = True
    checks["missing_article_fails"] = missing_article_failed

    source = DocumentSource("sample", "test", "https://www.chezmoi.io/sample/")
    document = render_document(source, article, "2026-07-15")
    with tempfile.TemporaryDirectory() as temporary:
        corpus = Path(temporary) / "official-docs"
        write_staged_corpus(corpus, (document,), "2026-07-15T00:00:00Z")
        # This focused fixture deliberately has a smaller inventory than publication.
        checks["fixture_validates"] = (
            len(validate_corpus(corpus, require_inventory=False).documents) == 1
        )
        document_path = corpus / source.filename
        manifest_path = corpus / "manifest.json"
        tampered = document_path.read_text(encoding="utf-8").replace(
            "Preview", "Altered", 1
        )
        document_path.write_text(tampered, encoding="utf-8")
        manifest_text = manifest_path.read_text(encoding="utf-8").replace(
            document.file_sha256, sha256_text(tampered), 1
        )
        manifest_path.write_text(manifest_text, encoding="utf-8")
        stale_article_hash_failed = False
        try:
            validate_corpus(corpus, require_inventory=False)
        except CorpusError:
            stale_article_hash_failed = True
        checks["stale_article_hash_fails"] = stale_article_hash_failed
        (corpus / source.filename).write_text("corrupt\n", encoding="utf-8")
        corruption_failed = False
        try:
            validate_corpus(corpus, require_inventory=False)
        except CorpusError:
            corruption_failed = True
        checks["corruption_fails"] = corruption_failed
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "summary": {"passed": sum(checks.values()), "total": len(checks)},
    }


def command_self_test(_: argparse.Namespace) -> int:
    result = run_self_tests()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    refresh = subparsers.add_parser(
        "refresh", help="Fetch and compare the configured official pages."
    )
    refresh.add_argument(
        "--output",
        default=str(DEFAULT_DOCS_DIR),
        help="Corpus directory to compare or publish.",
    )
    refresh.add_argument(
        "--write", action="store_true", help="Publish the complete validated corpus."
    )
    refresh.add_argument(
        "--timeout", type=float, default=20.0, help="Per-request timeout in seconds."
    )
    refresh.add_argument(
        "--workers", type=int, default=6, choices=range(1, 17), metavar="1..16"
    )
    refresh.set_defaults(handler=command_refresh)

    check = subparsers.add_parser(
        "check", help="Validate files and hashes without network access."
    )
    check.add_argument(
        "--docs", default=str(DEFAULT_DOCS_DIR), help="Corpus directory."
    )
    check.set_defaults(handler=command_check)

    listing = subparsers.add_parser("list", help="List bundled pages and provenance.")
    listing.add_argument(
        "--docs", default=str(DEFAULT_DOCS_DIR), help="Corpus directory."
    )
    listing.set_defaults(handler=command_list)

    search = subparsers.add_parser("search", help="Search the bundled corpus.")
    search.add_argument("query", help="Literal query unless --regex is set.")
    search.add_argument(
        "--docs", default=str(DEFAULT_DOCS_DIR), help="Corpus directory."
    )
    search.add_argument("--limit", type=int, default=10, help="Maximum matching lines.")
    search.add_argument(
        "--regex", action="store_true", help="Treat the query as a regular expression."
    )
    search.add_argument(
        "--case-sensitive", action="store_true", help="Use case-sensitive matching."
    )
    search.set_defaults(handler=command_search)

    self_test = subparsers.add_parser(
        "self-test", help="Run deterministic parser and corpus tests."
    )
    self_test.set_defaults(handler=command_self_test)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if getattr(args, "limit", 1) < 1:
        parser.error("--limit must be at least 1")
    if getattr(args, "timeout", 1.0) <= 0:
        parser.error("--timeout must be positive")
    handler = cast(Callable[[argparse.Namespace], int], args.handler)
    try:
        return handler(args)
    except CorpusError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

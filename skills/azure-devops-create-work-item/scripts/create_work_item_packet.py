#!/usr/bin/env python3
"""
Create a local Azure DevOps work item packet in the caller's current directory.

Usage:
    python3 scripts/create_work_item_packet.py --title "Add SSO login recovery"
    python3 scripts/create_work_item_packet.py --type bug --title "Checkout freezes on Safari" \
        --context-file ./notes/checkout-bug.md --save-root ./work-items
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


TYPE_TO_TEMPLATE = {
    "pbi": "product-backlog-item-template.md",
    "product-backlog-item": "product-backlog-item-template.md",
    "epic": "epic-template.md",
    "feature": "feature-template.md",
    "user-story": "user-story-template.md",
    "task": "task-template.md",
    "issue": "issue-template.md",
    "bug": "bug-template.md",
}

TYPE_DISPLAY = {
    "pbi": "Product Backlog Item",
    "product-backlog-item": "Product Backlog Item",
    "epic": "Epic",
    "feature": "Feature",
    "user-story": "User Story",
    "task": "Task",
    "issue": "Issue",
    "bug": "Bug",
}

TYPE_CANONICAL = {
    "pbi": "product-backlog-item",
}

COMMON_SOURCES = [
    {
        "title": "About work items and work item types",
        "url": "https://learn.microsoft.com/en-us/azure/devops/boards/work-items/about-work-items?view=azure-devops&tabs=agile-process",
    },
    {
        "title": "Choose a process",
        "url": "https://learn.microsoft.com/en-us/azure/devops/boards/work-items/guidance/choose-process?view=azure-devops",
    },
]

AGILE_SOURCE = {
    "title": "Agile workflow in Azure Boards",
    "url": "https://learn.microsoft.com/en-us/azure/devops/boards/work-items/guidance/agile-process-workflow?view=azure-devops",
}

SCRUM_SOURCE = {
    "title": "Manage Scrum process work item types and workflow",
    "url": "https://learn.microsoft.com/en-us/azure/devops/boards/work-items/guidance/scrum-process-workflow?view=azure-devops",
}

BUG_SOURCE = {
    "title": "Define, capture, triage, and manage bugs in Azure Boards",
    "url": "https://learn.microsoft.com/en-us/azure/devops/boards/backlogs/manage-bugs?view=azure-devops",
}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a local Azure DevOps work item packet with work-item.md, "
            "context.md, sources.md, and metadata.json."
        )
    )
    parser.add_argument(
        "--type",
        default=None,
        choices=sorted(TYPE_TO_TEMPLATE),
        help="Work item type to scaffold. Default: product-backlog-item.",
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Work item title to place in the generated packet.",
    )
    parser.add_argument(
        "--process",
        default=None,
        choices=["agile", "basic", "scrum", "cmmi"],
        help="Process assumption to record in metadata. Default: scrum for Product Backlog Item and Bug, otherwise agile.",
    )
    parser.add_argument(
        "--save-root",
        default=".",
        help="Visible directory where the packet folder should be created. Default: current directory.",
    )
    parser.add_argument(
        "--context-file",
        help="Optional path to a source context file to copy into context.md.",
    )
    parser.add_argument(
        "--slug",
        help="Optional manual slug override for the packet folder name.",
    )
    return parser.parse_args()


def normalize_type(item_type: str | None) -> str:
    selected = item_type or "product-backlog-item"
    return TYPE_CANONICAL.get(selected, selected)


def default_process_for(item_type: str) -> str:
    if item_type in {"product-backlog-item", "bug"}:
        return "scrum"
    return "agile"


def slugify(value: str) -> str:
    lowered = value.lower().strip()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)
    cleaned = cleaned.strip("-")
    return cleaned or "work-item"


def load_template(base_dir: Path, item_type: str) -> str:
    template_path = base_dir / "templates" / TYPE_TO_TEMPLATE[item_type]
    return template_path.read_text(encoding="utf-8")


def read_context(path_value: str | None) -> tuple[str, str | None]:
    if not path_value:
        return "[Paste the source context here.]", None

    path = Path(path_value).expanduser().resolve()
    content = path.read_text(encoding="utf-8").strip()
    return content or "[The supplied context file was empty.]", str(path)


def build_context_document(process: str, item_type: str, context_text: str) -> str:
    display_type = TYPE_DISPLAY[item_type]
    return "\n".join(
        [
            "**Context**",
            context_text,
            "",
            "---",
            "",
            "**Drafting notes**",
            f"- Process assumption: {process.title()}",
            f"- Work item type: {display_type}",
            "- Audience: Mixed technical and non-technical",
            "- Main draft file: work-item.md",
        ]
    ).rstrip() + "\n"


def sources_for(item_type: str) -> list[dict[str, str]]:
    if item_type == "product-backlog-item":
        return [*COMMON_SOURCES, SCRUM_SOURCE]
    if item_type == "bug":
        return [*COMMON_SOURCES, SCRUM_SOURCE, BUG_SOURCE]
    return [*COMMON_SOURCES, AGILE_SOURCE]


def build_sources_document(item_type: str) -> str:
    lines = ["**Official sources**"]
    for source in sources_for(item_type):
        lines.append(f"- {source['title']}: {source['url']}")
    return "\n".join(lines).rstrip() + "\n"


def build_output_dir(save_root: Path, item_type: str, slug: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return save_root / f"azure-devops-work-item-{item_type}-{slug}-{timestamp}"


def main() -> int:
    args = parse_args()
    item_type = normalize_type(args.type)
    process = args.process or default_process_for(item_type)

    base_dir = Path(__file__).resolve().parent.parent
    save_root = Path(args.save_root).expanduser().resolve()
    save_root.mkdir(parents=True, exist_ok=True)

    slug = slugify(args.slug or args.title)
    output_dir = build_output_dir(save_root, item_type, slug)
    output_dir.mkdir(parents=False, exist_ok=False)

    template = load_template(base_dir, item_type)
    work_item_text = template.replace("{{TITLE}}", args.title.strip())

    context_text, context_source = read_context(args.context_file)
    context_doc = build_context_document(process, item_type, context_text)
    sources_doc = build_sources_document(item_type)

    metadata = {
        "process": process.title(),
        "work_item_type": TYPE_DISPLAY[item_type],
        "title": args.title.strip(),
        "slug": slug,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_directory": str(output_dir),
        "context_file": context_source,
        "template_file": str((base_dir / "templates" / TYPE_TO_TEMPLATE[item_type]).resolve()),
        "official_sources": sources_for(item_type),
    }

    (output_dir / "work-item.md").write_text(work_item_text.rstrip() + "\n", encoding="utf-8")
    (output_dir / "context.md").write_text(context_doc, encoding="utf-8")
    (output_dir / "sources.md").write_text(sources_doc, encoding="utf-8")
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    payload = {
        "output_dir": str(output_dir),
        "files": [
            str(output_dir / "work-item.md"),
            str(output_dir / "context.md"),
            str(output_dir / "sources.md"),
            str(output_dir / "metadata.json"),
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

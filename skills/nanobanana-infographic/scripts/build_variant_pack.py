#!/usr/bin/env python3
"""Build a default low-noise infographic prompt pack from a brief JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_VARIANTS = [
    {
        "id": "executive-snapshot",
        "name": "Executive Snapshot",
        "best_for": "C-suite slides, strategic summaries, and board-style briefings",
        "layout": "One dominant top section followed by three disciplined support blocks.",
        "hierarchy": "Strongest claim first, then supporting evidence in descending order.",
        "tone": "calm, high-trust, disciplined",
    },
    {
        "id": "editorial-column",
        "name": "Editorial Column",
        "best_for": "Blog posts, reports, and vertical explainers",
        "layout": "Tall stacked panels with subtle dividers and a steady reading rhythm.",
        "hierarchy": "Panel-by-panel narrative progression from top to bottom.",
        "tone": "editorial, composed, airy",
    },
    {
        "id": "decision-board",
        "name": "Decision Board",
        "best_for": "Trade-offs, frameworks, comparison visuals, and category maps",
        "layout": "Equal-weight modular grid with short comparison labels.",
        "hierarchy": "Balanced side-by-side comparison with no decorative filler.",
        "tone": "analytical, clean, decisive",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read a structured brief JSON file and emit the default Nano Banana "
            "infographic prompt pack."
        )
    )
    parser.add_argument("--brief", required=True, help="Path to the brief JSON file.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the prompt pack files should be written.",
    )
    return parser.parse_args()


def load_brief(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    normalized = {
        "topic": str(data.get("topic", "")).strip(),
        "core_message": str(data.get("core_message", "")).strip(),
        "audience": str(data.get("audience", "")).strip(),
        "context": str(data.get("context", "")).strip(),
        "title": str(data.get("title", "")).strip(),
        "must_include": [str(x).strip() for x in data.get("must_include", []) if str(x).strip()],
        "stats": [str(x).strip() for x in data.get("stats", []) if str(x).strip()],
        "tone": [str(x).strip() for x in data.get("tone", []) if str(x).strip()],
        "palette": [str(x).strip() for x in data.get("palette", []) if str(x).strip()],
        "avoid": [str(x).strip() for x in data.get("avoid", []) if str(x).strip()],
        "aspect_ratio": str(data.get("aspect_ratio", "16:9")).strip() or "16:9",
        "variant_count": int(data.get("variant_count", 3) or 3),
    }

    if not normalized["topic"]:
        raise SystemExit("Brief is missing 'topic'.")
    if not normalized["core_message"]:
        raise SystemExit("Brief is missing 'core_message'.")
    if not normalized["audience"]:
        raise SystemExit("Brief is missing 'audience'.")

    if not normalized["title"]:
        fallback = normalized["topic"].strip().title()
        normalized["title"] = " ".join(fallback.split()[:5])

    normalized["variant_count"] = max(1, min(3, normalized["variant_count"]))
    if len(normalized["title"].split()) > 5:
        normalized["title"] = " ".join(normalized["title"].split()[:5])

    return normalized


def build_prompt(brief: dict, variant: dict) -> str:
    prompt_lines = [
        "Create a sleek editorial infographic, not a busy poster.",
        "",
        f"Topic: {brief['topic']}",
        f"Audience/context: {brief['audience']} / {brief['context'] or 'general publishing context'}",
        f"Core message: {brief['core_message']}",
        f"Aspect ratio: {brief['aspect_ratio']}",
        f"Variant direction: {variant['name']}",
        "",
        f"Title text: {brief['title']}",
        "",
        "Composition:",
        f"- Layout: {variant['layout']}",
        f"- Hierarchy: {variant['hierarchy']}",
        "- White or near-white background.",
        "- Flat 2D editorial graphics.",
        "- Precise spacing and alignment.",
        "- Use icons only if they replace text cleanly.",
        "",
        "Style:",
        f"- Tone: {variant['tone']}.",
        "- Rich but restrained, premium, calm, and high-trust.",
        "- Do not look like a startup poster or a dashboard collage.",
        "- Generous whitespace.",
    ]

    if brief["palette"]:
        prompt_lines.append(f"- Palette bias: {', '.join(brief['palette'])}.")
    else:
        prompt_lines.append("- Palette bias: one dark neutral, one main accent, one light neutral.")

    prompt_lines.extend(
        [
            "",
            "Must include:",
        ]
    )

    items = brief["must_include"] + brief["stats"]
    for item in items or ["One clean framing device only."]:
        prompt_lines.append(f"- {item}")

    prompt_lines.extend(
        [
            "",
            "Text rules:",
            "- Title max 5 words.",
            "- Labels 1-3 words.",
            "- No sentences, paragraphs, captions, or source notes in the image.",
            "",
            "Avoid:",
            "- busy collage layouts",
            "- gradients, glassmorphism, bevels, glow, drop shadows",
            "- decorative filler icons",
            "- cartoon mascots",
            "- loud poster energy",
        ]
    )

    for avoid in brief["avoid"]:
        prompt_lines.append(f"- {avoid}")

    return "\n".join(prompt_lines).strip() + "\n"


def render_markdown(brief: dict, variants: list[dict]) -> str:
    lines = [
        "# Variant Pack",
        "",
        "## Brief",
        "",
        f"- Topic: {brief['topic']}",
        f"- Core message: {brief['core_message']}",
        f"- Audience: {brief['audience']}",
        f"- Context: {brief['context'] or 'n/a'}",
        f"- Title: {brief['title']}",
        f"- Aspect ratio: {brief['aspect_ratio']}",
        "",
        "## Variants",
        "",
    ]

    for variant in variants:
        lines.extend(
            [
                f"### {variant['name']}",
                "",
                f"- Best for: {variant['best_for']}",
                "",
                "```text",
                variant["prompt"].rstrip(),
                "```",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    brief_path = Path(args.brief).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    brief = load_brief(brief_path)
    selected = DEFAULT_VARIANTS[: brief["variant_count"]]

    variants = []
    for variant in selected:
        prompt = build_prompt(brief, variant)
        payload = {
            "id": variant["id"],
            "name": variant["name"],
            "best_for": variant["best_for"],
            "prompt": prompt,
        }
        variants.append(payload)

        prompt_path = output_dir / f"{variant['id']}.prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")

    manifest = {
        "brief": brief,
        "variants": variants,
    }

    (output_dir / "brief.normalized.json").write_text(
        json.dumps(brief, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "variant-pack.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "variant-pack.md").write_text(
        render_markdown(brief, variants),
        encoding="utf-8",
    )

    print(f"Wrote prompt pack to {output_dir}")


if __name__ == "__main__":
    main()

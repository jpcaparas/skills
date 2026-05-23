#!/usr/bin/env python3
"""Build a static catalog index.html from an oneshot-websites manifest."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


DEFAULT_FAIRNESS = (
    "Each one-shot showcase and its paired PROMPT.md were generated in an isolated "
    "route context so sibling runs do not influence one another. Route generation "
    "is single-pass: no retries were attempted for failures, odd behavior, or "
    "output quirks. This keeps the catalog fair as a model-comparison surface and "
    "shows how the model performs out of the box."
)


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def status_class(status: str) -> str:
    normalized = status.strip().upper()
    if normalized == "OK":
        return "status-ok"
    if normalized == "CURATED":
        return "status-curated"
    return "status-error"


def href_for(path: str) -> str:
    clean = path.strip()
    if not clean:
        return "#"
    return clean


def build_rows(items: list[dict]) -> str:
    rows: list[str] = []
    for item in items:
        path = item.get("path", "")
        prompt = item.get("prompt") or f"{path.rstrip('/')}/PROMPT.md"
        label = item.get("title") or item.get("typeLabel") or item.get("type") or path
        type_label = item.get("typeLabel") or item.get("type", "")
        status = str(item.get("status", "UNKNOWN")).upper()
        rows.append(
            "        <tr>\n"
            f'          <td data-label="Path"><code>/{esc(path).strip("/")}/</code></td>\n'
            f'          <td data-label="Experience"><a href="{esc(href_for(path))}">{esc(label)}</a></td>\n'
            f'          <td data-label="Prompt"><a href="{esc(href_for(prompt))}">PROMPT.md</a></td>\n'
            f'          <td data-label="Type"><code>{esc(type_label)}</code></td>\n'
            f'          <td data-label="Status"><span class="status {status_class(status)}">{esc(status)}</span></td>\n'
            f'          <td data-label="Summary" class="muted">{esc(item.get("summary", ""))}</td>\n'
            "        </tr>"
        )
    return "\n".join(rows)


def build_meta(manifest: dict, count: int) -> str:
    chips = [
        ("Harness", manifest.get("harness", "unspecified")),
        ("Routes", count),
        ("Generated", manifest.get("generated", "unknown")),
        ("Mode", manifest.get("mode", "single-pass")),
        ("Selection", manifest.get("selection", "unspecified")),
    ]
    return "".join(f"<span>{esc(k)}: <code>{esc(v)}</code></span>" for k, v in chips)


def build_html(manifest: dict) -> str:
    title = manifest.get("catalogTitle", "Oneshot Websites")
    items = manifest.get("items", [])
    description = manifest.get(
        "description",
        "A deterministic directory of one-shot website routes. Every route exposes the prompt beside the generated experience.",
    )
    fairness = manifest.get("fairnessNote") or manifest.get("fairness") or DEFAULT_FAIRNESS

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <style>
    :root {{
      --bg: #f5f3ef;
      --panel: #fffdf8;
      --ink: #171513;
      --muted: #5f5b56;
      --line: #d7d0c8;
      --accent: #0f766e;
      --accent-soft: #d9f4ef;
      --curated: #6d28d9;
      --curated-soft: #ede9fe;
      --error: #9f1239;
      --error-soft: #fde7ef;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #fff7e8 0, rgba(255, 247, 232, 0) 28rem),
        linear-gradient(180deg, #efe9df 0%, var(--bg) 18rem);
    }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px 56px; }}
    .hero {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 28px;
      box-shadow: 0 18px 50px rgba(23, 21, 19, 0.08);
    }}
    .eyebrow {{
      margin: 0 0 10px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    h1 {{ margin: 0; font-size: clamp(32px, 5vw, 52px); line-height: 0.98; }}
    .sub {{ max-width: 52rem; margin: 14px 0 0; font-size: 16px; line-height: 1.55; color: var(--muted); }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; font-size: 14px; color: var(--muted); }}
    .meta span {{ background: #f0ebe4; border: 1px solid var(--line); border-radius: 999px; padding: 7px 12px; }}
    code {{
      font-family: "SFMono-Regular", Menlo, Consolas, monospace;
      font-size: 0.92em;
      background: #f4eee7;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 2px 6px;
    }}
    .fairness {{ margin-top: 18px; padding: 18px 20px; background: #f4eee7; border: 1px solid var(--line); border-radius: 18px; }}
    .fairness h2 {{ margin: 0; font-size: 15px; letter-spacing: 0.08em; text-transform: uppercase; }}
    .fairness p {{ margin: 10px 0 0; color: var(--muted); font-size: 15px; line-height: 1.55; }}
    table {{
      width: 100%;
      margin-top: 26px;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      overflow: hidden;
      box-shadow: 0 16px 40px rgba(23, 21, 19, 0.06);
    }}
    thead th {{
      background: #f2ece4;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      text-align: left;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
    }}
    tbody td {{ padding: 16px; border-bottom: 1px solid var(--line); vertical-align: top; font-size: 15px; line-height: 1.45; }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    a {{ color: var(--ink); font-weight: 700; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .status {{ display: inline-block; border-radius: 999px; padding: 5px 10px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; }}
    .status-ok {{ color: var(--accent); background: var(--accent-soft); }}
    .status-curated {{ color: var(--curated); background: var(--curated-soft); }}
    .status-error {{ color: var(--error); background: var(--error-soft); }}
    .muted {{ color: var(--muted); }}
    .footer-note {{
      margin-top: 24px;
      padding: 20px 24px;
      text-align: center;
      background: rgba(255, 253, 248, 0.78);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 10px 30px rgba(23, 21, 19, 0.05);
      color: var(--muted);
      font-size: 15px;
      line-height: 1.5;
    }}
    @media (max-width: 880px) {{
      table, thead, tbody, th, td, tr {{ display: block; }}
      thead {{ display: none; }}
      tbody tr {{ border-bottom: 1px solid var(--line); padding: 8px 0; }}
      tbody td {{ border: 0; padding-top: 9px; padding-bottom: 9px; }}
      tbody td::before {{
        content: attr(data-label);
        display: block;
        margin-bottom: 4px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted);
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <p class="eyebrow">Master Oneshot Catalog</p>
      <h1>{esc(title)}</h1>
      <p class="sub">{esc(description)}</p>
      <div class="meta">{build_meta(manifest, len(items))}</div>
      <section class="fairness">
        <h2>Fairness Note</h2>
        <p>{esc(fairness)}</p>
      </section>
    </section>
    <table>
      <thead>
        <tr>
          <th>Path</th>
          <th>Experience</th>
          <th>Prompt</th>
          <th>Type</th>
          <th>Status</th>
          <th>Summary</th>
        </tr>
      </thead>
      <tbody>
{build_rows(items)}
      </tbody>
    </table>
    <footer class="footer-note">Every route is static and can be opened directly, deployed as a folder, or copied into a static host.</footer>
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to manifest.json")
    parser.add_argument("--out", required=True, help="Destination index.html path")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest.get("items"), list):
        raise SystemExit("manifest must contain an items array")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_html(manifest), encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

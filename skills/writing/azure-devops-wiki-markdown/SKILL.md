---
name: azure-devops-wiki-markdown
description: "Writes, fixes and reviews Azure DevOps wiki Markdown: Mermaid, [[_TOC_]], [[_TOSP_]], details blocks, query tables, mentions, work-item links, KaTeX, videos, code fences, and what renders in wiki vs PR vs README. Not for GitHub-only docs or work item packets."
compatibility: "Optional python3 for scripts/find_code_language.py; its live refresh needs network."
license: MIT
---

# Azure DevOps wiki Markdown

Baseline: Microsoft Learn Azure DevOps Markdown guidance, the Azure Repos Sprint 259 release note (2025-07-17) and the Highlight.js supported-language table, checked 2026-04-09; the Mermaid and wiki-feature sections were re-read against the [Learn markdown guidance](https://learn.microsoft.com/en-us/azure/devops/project/wiki/markdown-guidance?view=azure-devops) (updated 2026-11-03) on 2026-11-10, which changed only the Mermaid fence rule. Statements below describe that baseline for Services, not proof for every Server version. Where a limitation is stale or conflicts with the user's target, check Microsoft Learn for that version (use its Services/Server selector) and use verified newer syntax; an upstream Mermaid or Highlight.js feature does not prove Azure support. If you cannot verify, say so and use the compatible baseline. Propose a sourced correction rather than editing an installed copy. Do not browse for routine known syntax.

Preserve exact macros, code literals and real query or identity GUIDs; never invent identifiers. Follow the page structure the user asked for.

## Rules that differ from ordinary Markdown

- A bare Enter is not a line break. End the line with two spaces, or leave a blank line for a new paragraph.
- Wiki-only: Mermaid, `[[_TOC_]]`, `[[_TOSP_]]`, `query-table`, HTML tags (`<span>`, `<font>`, `<video>`), `<br/>` in table cells, `<details>`. Do not assume they work in PRs, READMEs, widgets or Done fields; check `references/support-matrix.md`.
- `[[_TOC_]]` and `[[_TOSP_]]` are case-sensitive, only the first of each renders, and they need headings or child pages.
- Mermaid uses `::: mermaid` ... `:::` (the safe default); the Learn page re-read on 2026-11-10 also documents a standard ```` ```mermaid ```` fenced block as supported, so a fence the user already has is not an error, but verify it renders on their target. Use `graph TD`/`graph LR`; Microsoft warns that `flowchart` syntax is limited. Avoid HTML in labels, Font Awesome and `---->` long arrows. For a decision tree, one short question per branching node, with the recommendation, risks and next step below the diagram, not inside it. Read `references/mermaid.md` for supported diagram types and limits.
- `<details><summary>` needs a blank line after `</summary>` and spacing after `</details>`. Markdown inside any HTML element needs a blank line after the opening tag.
- `query-table` takes the Azure Boards query GUID, not the name or URL: `::: query-table <guid>` ... `:::`.
- Mentions written in source use `@<{identity-guid}>`, not the alias form from the browser editor.
- Wiki page links use the absolute form `[Text](/parent-page/child-page)`; same-page anchors use the generated heading id (`#### Team #1 : Release Wiki!` → `#team-1--release-wiki`). Repo-relative README link behaviour does not apply. Work items link as `#12345`. Attachments are editor-driven (drag, paste, paperclip); do not invent syntax.
- Checklists (`- [x]`) work in wikis and PRs, but not inside tables.
- KaTeX (`$...$`, `$$...$$`) is documented for PRs and wiki files only; do not extend it to READMEs or widgets without checking. JavaScript and iframes are unsupported; use links, `query-table` or HTML `<video>`.
- Read `references/advanced-features.md` for the details of `[[_TOSP_]]`, collapsible sections, query tables, mentions, KaTeX and video.

## Code-fence languages

Azure points to Highlight.js but does not publish the exact bundle it loads. Prefer mainstream aliases (`bash`, `powershell`, `json`, `yml`, `ts`, `tsx`, `python`, `csharp`, `cpp`, `sql`, `plaintext`). Some Highlight.js languages are third-party packages and some aliases are ambiguous, so do not promise highlighting for uncommon tags until checked: `python3 scripts/find_code_language.py <query>` searches a cached copy of the upstream table offline (`--refresh` fetches the live one). Read `references/code-languages.md` for ambiguous aliases and caveats.

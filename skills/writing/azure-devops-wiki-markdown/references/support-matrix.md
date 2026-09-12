# Support Matrix

Use this file when the question is "does Azure DevOps support this Markdown feature here?"

Primary sources:

- Microsoft Learn, "Markdown syntax for files, widgets, wikis - Azure DevOps," current as checked on April 9, 2026
- Azure Repos Sprint 259 release note, published July 17, 2025

## Core Markdown Features

| Feature | Done | Widget | PR | README | Wiki | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Headers | yes | yes | yes | yes | yes | Hash-style headings work everywhere in the official matrix. |
| Paragraphs and line breaks | yes | yes | yes | yes | yes | Azure DevOps still requires two trailing spaces for an in-paragraph line break. |
| Block quotes | yes | yes | yes | yes | yes | Standard `>` syntax. |
| Horizontal rules | yes | yes | yes | yes | yes | Standard `---` syntax. |
| Emphasis | yes | yes | yes | yes | yes | Bold, italics, strikethrough. |
| Code highlighting | no | no | yes | yes | yes | Use triple backticks and a language identifier. |
| Suggest change | no | no | yes | no | no | PR only. |
| Tables | no | yes | yes | yes | yes | Wiki tables also allow `<br/>` inside cells. |
| Lists | yes | yes | yes | yes | yes | Ordered, unordered, nested. |
| Links | yes | yes | yes | yes | yes | Wiki page links have their own absolute-path syntax. |
| Images | no | yes | yes | yes | yes | |
| Checklist or task list | no | no | yes | no | yes | Do not place checklist items inside tables. |
| Emojis | no | no | yes | no | yes | |
| Ignore or escape Markdown | yes | yes | yes | yes | yes | |
| Attachments | no | no | yes | no | yes | PR comments and wiki pages only. |
| Mathematical notation | no | no | yes | no | yes | Microsoft documents KaTeX for pull requests and wiki files. |

## Wiki-First Features

| Feature | Wiki | Notes |
| --- | --- | --- |
| Mermaid diagrams | yes | Use `::: mermaid` blocks. Treat wiki pages as the safe authoring surface. |
| Table of contents | yes | Use `[[_TOC_]]`. Case-sensitive. |
| Table of subpages | yes | Use `[[_TOSP_]]`. Case-sensitive. |
| Collapsible sections | yes | Use `<details><summary>`. Blank lines matter. |
| Azure Boards query-table | yes | Use `:::` plus `query-table <guid>`. |
| `@` mentions | yes | Browser editor uses alias form; code edits use `@<{identity-guid}>`. |
| HTML tags in wiki pages | yes | Wiki pages accept HTML such as `<span>`, `<video>`, and rich text tags. |
| `<br/>` inside table cells | yes | Documented specifically for wiki tables. |
| Embedded video | yes | Use HTML `<video>` tags with a direct media URL. |

## Mermaid Scope

The current Learn page documents Mermaid under wiki pages. The Azure Repos Sprint 259 release note says Azure DevOps added expanded Mermaid support in wiki pages and file preview, specifically including Entity Relationship and Timeline diagrams. Treat that release note as useful background, but use wiki pages as the canonical authoring surface unless the user explicitly only cares about file preview behavior.

## Practical Routing Rules

- If the task is a normal wiki page, read `references/syntax.md`.
- If the task depends on a wiki-only block or embed, read `references/advanced-features.md`.
- If the task is about diagrams, read `references/mermaid.md`.
- If the task is about code fences or language aliases, read `references/code-languages.md`.
- If the syntax looks plausible but a surface still refuses to render it, read `references/gotchas.md`.

## See Also

- `references/syntax.md`
- `references/advanced-features.md`
- `references/mermaid.md`
- `references/code-languages.md`
- `references/gotchas.md`


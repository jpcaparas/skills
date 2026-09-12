# Advanced Wiki Features

Use this file when the task depends on Azure DevOps wiki-only blocks or richer page behaviors rather than ordinary Markdown alone.

Primary source: Microsoft Learn, "Markdown syntax for files, widgets, wikis - Azure DevOps," current as checked on April 9, 2026.

## Table of Contents

- [TOC and Subpage Tables](#toc-and-subpage-tables)
- [Collapsible Sections](#collapsible-sections)
- [Embedded Query Results](#embedded-query-results)
- [Mentions](#mentions)
- [Mathematical Notation](#mathematical-notation)
- [Embedded Video](#embedded-video)
- [Failure Patterns](#failure-patterns)

## TOC and Subpage Tables

Use these syntax tags in wiki pages:

```md
[[_TOC_]]
[[_TOSP_]]
```

Guidance:

- `[[_TOC_]]` renders a table of contents for hash-style headings on the page.
- `[[_TOSP_]]` renders a "Child Pages" table for the current wiki page's subpages.
- Both tags are case-sensitive.
- Azure DevOps only renders the first instance of each tag on a page.
- `[[_TOSP_]]` is only useful on a page that actually has child pages.

## Collapsible Sections

Use HTML `details` and `summary` tags for collapsible sections:

```html
<details>
<summary>Show retired rollout notes</summary>

Keep the hidden content here. You can use Markdown and HTML inside the body.

</details>
```

Rules that matter:

- Put the section title inside `<summary>...</summary>`.
- Add a blank line after `</summary>`.
- Add a blank line after each closing `</details>` tag when multiple blocks appear on the page.
- Use this for archived instructions, optional detail, or question-and-answer sections.

## Embedded Query Results

Embed Azure Boards query results as a table with a query GUID:

```md
Results from the Azure Boards query:

:::
query-table 6ff7777e-8ca5-4f04-a7f6-9e63737dddf7
:::
```

Guidance:

- The value after `query-table` is the query GUID, not the query name.
- Azure DevOps can insert this block from the editor toolbar, but the Markdown form is deterministic and easier to reproduce in code.
- Keep a short explanatory sentence above the block so the page still reads well if the embedded table changes.

## Mentions

When editing in the browser, mentions use the visible alias pattern:

```md
@<user-alias>
```

When editing the Markdown directly in code, use the identity GUID form documented by Microsoft Learn:

```md
@<{identity-guid}>
```

Guidance:

- Do not mix the two forms when hand-authoring raw Markdown.
- The browser editor can autosuggest users and groups after `@`.
- In repository-backed edits, the GUID form is the reliable literal representation.

## Mathematical Notation

Azure DevOps documents KaTeX support for pull request comments and wiki files.

Inline expression:

```md
$ availability = successful_requests / total_requests $
```

Block expression:

```md
$$
R = \frac{successful\_requests}{total\_requests}
$$
```

Guidance:

- Use single dollar signs for inline math.
- Use double dollar signs for a block expression.
- Keep KaTeX out of README guidance unless the user explicitly confirms a renderer that supports it.

## Embedded Video

Wiki pages allow HTML video embeds:

```html
<video src="https://example.com/video.mp4" width="640" controls>
</video>
```

Guidance:

- Use a direct media URL, not an iframe.
- Keep the `controls` attribute so the page remains usable.
- Do not promise JavaScript-driven media widgets or iframes in Azure DevOps Markdown.

## Failure Patterns

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `[[_TOSP_]]` does not render | Wrong case, duplicate tag, or no child pages | Use uppercase syntax, keep only the first instance, and confirm the page has subpages. |
| Collapsible block renders as raw HTML | Missing blank line after `</summary>` or `</details>` | Add the required blank lines and keep the body outside the summary tag. |
| Query results do not appear | Used a query name or copied the wrong identifier | Use the query GUID from the shared query URL. |
| Mention text stays literal | Used alias syntax while editing raw Markdown in code | Replace the alias form with `@<{identity-guid}>`. |
| Math renders as plain text | Wrong surface or missing `$` delimiters | Use single or double dollar signs and keep the feature to PRs or wiki files. |
| Video does not play | Used an iframe or a page URL instead of a media file | Use `<video>` with a direct media source URL. |

## See Also

- `references/syntax.md`
- `references/support-matrix.md`
- `references/gotchas.md`
- `templates/wiki-page-advanced-starter.md`


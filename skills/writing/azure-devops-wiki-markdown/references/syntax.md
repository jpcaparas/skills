# Syntax Patterns

Use this file when drafting or repairing a normal Azure DevOps wiki page.

Primary source: Microsoft Learn, "Markdown syntax for files, widgets, wikis - Azure DevOps," current as checked on April 9, 2026.

## Safe Wiki Page Skeleton

Use this pattern when the user wants a clean wiki page rather than a loose snippet:

````md
[[_TOC_]]

# Page Title

One-sentence summary.

## Context

Explain the situation in short paragraphs.  
Use two trailing spaces before Enter when you need a soft line break.

## Steps

1. First step
2. Second step
3. Third step

## Links

- [Child page](/parent-page/child-page)
- [External reference](https://example.com)

## Code

```bash
echo "replace with the real command"
```

## Diagram

::: mermaid
graph TD
  A["Start"] --> B["Do the work"]
  B --> C["Done"]
:::
````

For a ready-to-use starter, read `templates/wiki-page-starter.md`.

## High-Value Azure DevOps Rules

### Paragraphs and Line Breaks

Azure DevOps handles line breaks more strictly than many Markdown renderers:

- Press Enter twice to create a new paragraph.
- Add two spaces at the end of a line before pressing Enter to create an in-paragraph line break.

### Wiki Page Links and Header Anchors

For wiki-to-wiki navigation, prefer the documented absolute path form:

```md
[Display text](/parent-page/child-page)
```

For same-page anchors, link to the generated heading ID:

```md
#### Team #1 : Release Wiki!

For more information, [jump to this section](#team-1--release-wiki).
```

Do not assume repo-relative README link behavior applies to wiki pages.

### Tables and Checklists

Standard Markdown tables work in widgets, PRs, READMEs, and wikis. Wiki pages also allow `<br/>` inside a cell:

```md
| Step | Notes |
| --- | --- |
| Build | Queue the pipeline<br/>Confirm the artifact name |
| Deploy | Verify the target environment |
```

Task lists work in wiki pages and pull requests:

```md
- [x] Draft page
- [ ] Review page
- [ ] Publish page
```

Do not place a checklist inside a Markdown table.

### Work Item Links and Attachments

Link to work items by using the hash mark and ID:

```md
- Follow work item #12345 before publishing this page.
```

Attachments are editor-driven in Azure DevOps. When the task is about getting a file into a page or PR, tell the user to attach by drag-and-drop, paste, or the paperclip button instead of inventing undocumented syntax.

### HTML in Wiki Pages

Wiki pages allow HTML tags such as `<span>`, `<font>`, and `<video>`. When mixing Markdown inside an HTML element, leave a blank line after the opening tag:

```html
<p>

This article describes how to **get started** with an Azure DevOps wiki.

</p>
```

For collapsible sections, embedded videos, query tables, mentions, and KaTeX, read `references/advanced-features.md`.

## When to Escalate to Other References

- If the user asks "does this work in README or PR comments too?", read `references/support-matrix.md`.
- If the user asks for Mermaid, read `references/mermaid.md`.
- If the user asks about `[[_TOSP_]]`, `<details>`, `query-table`, `@` mentions, or KaTeX, read `references/advanced-features.md`.
- If the user asks which code-fence language tag to use, read `references/code-languages.md`.
- If the syntax looks right but Azure DevOps still renders it wrong, read `references/gotchas.md`.

## See Also

- `references/advanced-features.md`
- `references/support-matrix.md`
- `references/mermaid.md`
- `references/code-languages.md`
- `references/gotchas.md`
- `templates/wiki-page-starter.md`


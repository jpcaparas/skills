# Gotchas

Use this file when the syntax looks plausible but Azure DevOps still renders something in an unexpected way.

## Symptom / Cause / Fix

| Symptom | Cause | Fix |
| --- | --- | --- |
| A line break disappears inside a paragraph | Azure DevOps does not turn a bare Enter into a soft line break | Add two trailing spaces before pressing Enter, or create a new paragraph with a blank line. |
| `[[_TOC_]]` or `[[_TOSP_]]` does not render | Wrong case, duplicate tag, or missing qualifying content | Use uppercase syntax, keep only the first instance, and confirm the page has headings or child pages. |
| Mermaid renders as code or plain text | Used triple backticks or the wrong surface | Use `::: mermaid` in a wiki page. |
| Mermaid flowchart snippet from the web fails | Generic Mermaid examples often use `flowchart`; Azure DevOps warns that `graph` is the safer element | Convert the snippet to `graph TD`, `graph LR`, and so on. |
| Mermaid styling or icons vanish | Azure DevOps documents limited Mermaid syntax support | Remove most HTML tags, Font Awesome, and LongArrow `---->`. |
| A decision tree renders but is hard to review | Nodes contain too much prose or combine multiple decisions | Keep one short question per branching node and move the recommendation, risks, and next step below the diagram. |
| A table cell ignores a line break | `<br/>` only works in wiki tables | Use `<br/>` only for wiki pages. Do not promise the same behavior in PRs or widgets. |
| A collapsible section renders as raw HTML | Missing blank line after `</summary>` or `</details>` | Add the blank lines exactly where the docs require them. |
| `query-table` does nothing | Used a query name or the wrong identifier | Use the query GUID from the query URL or the editor-generated block. |
| A raw Markdown mention does not notify anyone | Used alias syntax in code instead of the documented GUID form | Replace it with `@<{identity-guid}>`. |
| A code fence language alias is uncertain | Azure DevOps points to Highlight.js but does not publish the exact loaded bundle | Prefer common aliases and run `python3 scripts/find_code_language.py <query>` for edge cases. |
| A code fence alias exists upstream but still might not render | The alias is a third-party Highlight.js package, not core bundled | Verify it locally before promising syntax highlighting. |
| Math renders as plain text | Wrong surface or wrong delimiters | Keep KaTeX to PRs or wiki files and use `$...$` or `$$...$$`. |
| Embedded interactive content does not work | Azure DevOps Markdown does not support JavaScript or iframes | Use static links, `query-table`, or HTML `<video>` where documented. |

## Version Discipline

Microsoft Learn explicitly tells readers to use the version selector for their Azure DevOps platform. When a syntax feature behaves differently than expected:

1. Check whether the user is on Azure DevOps Services, Azure DevOps Server, or Azure DevOps Server 2022.
2. Re-read the relevant section in the matching documentation version.
3. Avoid claiming support for newly documented Mermaid types or wiki features in older server versions without confirmation.

## Fast Triage

- Rendering problem in a whole page -> read `references/syntax.md`
- Proposal decision tree question -> read `references/decision-trees.md`
- "Does this feature exist here at all?" -> read `references/support-matrix.md`
- Diagram issue -> read `references/mermaid.md`
- Wiki-only block or embed issue -> read `references/advanced-features.md`
- Language alias issue -> read `references/code-languages.md`

## See Also

- `references/syntax.md`
- `references/advanced-features.md`
- `references/support-matrix.md`
- `references/decision-trees.md`
- `references/mermaid.md`
- `references/code-languages.md`


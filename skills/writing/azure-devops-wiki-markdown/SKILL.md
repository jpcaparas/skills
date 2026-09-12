---
name: azure-devops-wiki-markdown
description: "Write, fix, or review Azure DevOps wiki Markdown, Mermaid, _TOC_, _TOSP_, details blocks, query tables, mentions, work-item links, KaTeX, videos, and code fences. Use for Azure DevOps surface quirks. Do NOT use for GitHub-only or non-Azure docs."
compatibility: "Requires: python3. Optional network access for scripts/find_code_language.py refresh and live Highlight.js lookups."
license: MIT
---

# Azure DevOps Wiki Markdown

Route Azure DevOps Markdown questions to the right reference, with extra depth on wiki-only blocks, Mermaid-safe authoring, and code-fence language identifiers.

Verified against Microsoft Learn Azure DevOps Markdown guidance, the Azure Repos Sprint 259 release note, and the current Highlight.js supported-language table on April 9, 2026.

## Decision Tree

What do you need to do?

- Draft or repair a normal wiki page -> read `references/syntax.md`
- Check whether a feature works in Done, Widget, PR, README, or Wiki -> read `references/support-matrix.md`
- Use wiki-only features such as `[[_TOSP_]]`, `<details>`, `query-table`, `@` mentions, KaTeX, or video embeds -> read `references/advanced-features.md`
- Draft a proposal decision tree for a plan, rollout, ADR, or dependency discussion -> read `references/decision-trees.md` and `templates/decision-tree-proposal.md`
- Create or debug a Mermaid diagram -> read `references/mermaid.md`
- Pick a fenced-code language tag or alias -> read `references/code-languages.md` and optionally run `python3 scripts/find_code_language.py <query>`
- Diagnose Azure DevOps-specific rendering surprises -> read `references/gotchas.md`

## Quick Reference

| Task | Use |
| --- | --- |
| Create a wiki TOC | `[[_TOC_]]` |
| Create a table of subpages | `[[_TOSP_]]` |
| Force a line break inside a paragraph | end the line with two spaces before pressing Enter |
| Add a Mermaid diagram to a wiki page | `::: mermaid` ... `:::` |
| Add Azure Boards query results | `::: query-table <query-guid>` ... `:::` |
| Mention a user while editing in code | `@<{identity-guid}>` |
| Link to another wiki page | `[Display text](/parent-page/child-page)` |
| Force a line break in a wiki table cell | `<br/>` |
| Verify a code-fence alias | `python3 scripts/find_code_language.py typescript` |

## Reading Guide

| Task | Read |
| --- | --- |
| Page structure, links, line breaks, tables, and standard wiki authoring | `references/syntax.md` |
| Wiki-only features such as subpage tables, collapsible sections, query tables, mentions, KaTeX, and video embeds | `references/advanced-features.md` |
| Proposal decision trees and rollout-plan examples | `references/decision-trees.md` |
| Feature-by-surface support differences | `references/support-matrix.md` |
| Supported Mermaid diagram types, syntax, and limitations | `references/mermaid.md` |
| Safe code-fence aliases, ambiguous aliases, and local verification | `references/code-languages.md` |
| Failure modes, symptoms, and fixes | `references/gotchas.md` |
| Starter wiki page | `templates/wiki-page-starter.md` |
| Starter advanced wiki page | `templates/wiki-page-advanced-starter.md` |
| Starter proposal decision tree | `templates/decision-tree-proposal.md` |
| Starter Mermaid snippets | `templates/mermaid-starter.md` |

## Operating Rules

- Treat wiki pages as the safe target for Mermaid, `[[_TOC_]]`, `[[_TOSP_]]`, `query-table`, HTML tags, table-cell `<br/>`, and collapsible `<details>` sections. Check `references/support-matrix.md` before assuming the same feature works in PRs, READMEs, widgets, or Done fields.
- For flowchart-style Mermaid, prefer `graph TD` or `graph LR`. Microsoft documents Mermaid support but explicitly calls out `flowchart` syntax as a limitation in Azure DevOps.
- For proposal decision trees, keep one branching question per node and put the recommendation, risks, and next step below the diagram.
- Prefer mainstream code-fence aliases such as `bash`, `powershell`, `json`, `yml`, `ts`, `tsx`, `python`, `csharp`, `cpp`, `sql`, and `plaintext`. Use the helper script for edge cases and alias overlaps.
- When a user edits wiki Markdown directly in source control instead of the browser editor, favor literal, documented syntax over UI-only instructions.

## Gotchas

1. Azure DevOps line breaks are stricter than many Markdown renderers. Pressing Enter alone does not create an in-paragraph line break; add two trailing spaces first.
2. Mermaid in Azure DevOps wiki pages uses `::: mermaid` blocks, not triple-backtick ```` ```mermaid ```` fences.
3. Azure DevOps documents Mermaid support but also warns that `flowchart` syntax is limited. Convert generic Mermaid flowcharts to `graph TD` or `graph LR`.
4. `[[_TOC_]]` and `[[_TOSP_]]` are case-sensitive, and only the first instance of each tag renders on a page.
5. `<details><summary>` blocks need a blank line after `</summary>`, and multiple blocks need spacing after `</details>`, or the page can render incorrectly.
6. `query-table` needs a real Azure Boards query GUID, not the query name or the full query URL.
7. When editing in code, `@` mentions use `@<{identity-guid}>`, not the visible alias form from the browser editor.
8. Highlight.js lists some languages as third-party packages or ambiguous aliases. Do not promise highlighting for uncommon tags until you verify them locally.
9. KaTeX math is documented for pull requests and wiki files. Do not project that support onto README files or dashboard widgets without a separate check.

## Verification

- Run `python3 scripts/find_code_language.py <query>` when a user asks whether a language alias exists or whether an alias is ambiguous.
- Run `python3 scripts/validate.py .` from this skill directory after edits.
- Run `python3 scripts/test_skill.py .` to verify eval structure and cross-references locally.

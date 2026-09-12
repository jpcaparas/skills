# Azure DevOps Wiki Markdown

Production skill for writing and repairing Azure DevOps wiki Markdown, Mermaid diagrams, code fences, and wiki-only page features.

## What It Covers

- Standard wiki authoring patterns for links, tables, checklists, line breaks, and attachments
- Wiki-only capabilities such as `[[_TOC_]]`, `[[_TOSP_]]`, collapsible sections, query tables, mentions, KaTeX, and video embeds
- Mermaid diagram authoring and Azure DevOps-specific limitations
- Surface-by-surface support differences across Done, Widget, PR, README, and Wiki
- Highlight.js language alias verification through a local helper script

## Key Files

- `SKILL.md` - authoritative instructions
- `references/syntax.md` - core wiki authoring patterns
- `references/advanced-features.md` - wiki-only advanced blocks and embeds
- `references/mermaid.md` - supported Mermaid types and Azure-safe patterns
- `references/support-matrix.md` - support differences by Azure DevOps surface
- `references/code-languages.md` - code-fence aliases and verification guidance
- `scripts/find_code_language.py` - local language-alias lookup and ambiguity checker


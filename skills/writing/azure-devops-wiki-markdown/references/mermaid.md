# Mermaid Diagrams

Use this file when the user wants an Azure DevOps wiki Mermaid diagram or when a diagram does not render correctly.

Primary sources:

- Microsoft Learn, "Markdown syntax for files, widgets, wikis - Azure DevOps," current as checked on April 9, 2026
- Azure Repos Sprint 259 release note, published July 17, 2025
- Mermaid syntax pages linked directly from Microsoft Learn

## Supported Diagram Types

The current Azure DevOps wiki documentation lists these Mermaid diagram types:

- `sequenceDiagram`
- `gantt`
- `graph` for flowchart-style diagrams
- `classDiagram`
- State diagrams as documented by Mermaid's state-diagram syntax page
- `journey`
- `pie`
- `requirementDiagram`
- `gitGraph`
- `erDiagram`
- `timeline`

The Sprint 259 release note specifically calls out Entity Relationship and Timeline diagrams as expanded support in wiki pages and file preview.

## Azure-Safe Authoring Rules

1. Use `::: mermaid` blocks, not triple-backtick Mermaid fences.
2. Use `graph` for flowchart-style diagrams. Microsoft explicitly warns that Azure DevOps has limited support for `flowchart` syntax and recommends `graph` instead.
3. Keep labels plain. Azure DevOps documents limited Mermaid support and calls out most HTML tags, Font Awesome, and LongArrow `---->` as unsupported.
4. Treat wiki pages as the reliable rendering target. File preview support exists in release notes, but wiki authoring remains the documented primary surface.
5. Keep diagrams compact. Move long explanation into normal Markdown below the diagram.

## Starter Patterns

### Sequence

```md
::: mermaid
sequenceDiagram
  actor User
  participant Wiki as Azure DevOps Wiki
  User->>Wiki: Open page
  Wiki-->>User: Render updated content
:::
```

### Graph

```md
::: mermaid
graph TD
  A["Idea"] --> B["Draft page"]
  B --> C["Review"]
  C --> D["Publish"]
:::
```

### Decision Tree Starter

```md
::: mermaid
graph TD
  A["Proposal"] --> B{"Key decision"}
  B -- Yes --> C["Recommended path"]
  B -- No --> D["Alternative path"]
  C --> E["Next step"]
  D --> F["Next step"]
:::
```

### Entity Relationship

```md
::: mermaid
erDiagram
  PAGE ||--o{ ATTACHMENT : contains
  PAGE {
    string title
    string path
  }
  ATTACHMENT {
    string file_name
    string media_type
  }
:::
```

### Timeline

```md
::: mermaid
timeline
  title Wiki rollout
  2026-03-01 : Draft structure
  2026-03-05 : Add diagrams
  2026-03-08 : Review and publish
:::
```

## Failure Patterns

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Diagram renders as plain text | Wrong fence type or wrong surface | Use `::: mermaid` inside a wiki page. |
| Flowchart example fails | Copied a generic Mermaid `flowchart` snippet | Rewrite it as `graph TD`, `graph LR`, and so on. |
| Icons or styled HTML disappear | Azure DevOps limited Mermaid syntax support | Remove HTML tags, Font Awesome, and unsupported arrow variants. |
| Diagram is hard to review | Nodes contain paragraphs or multiple decisions | Keep node text short and move explanation below the diagram. |
| Entity relationship or timeline example fails in an older environment | Feature level mismatch | Check the Azure DevOps platform or server version before assuming newer support exists. |

## Routing Rules

- If the user needs a whole page, combine this file with `references/syntax.md`.
- If the user needs a proposal or planning decision tree, read `references/decision-trees.md`.
- If the user is unsure whether Mermaid belongs on this surface at all, read `references/support-matrix.md`.
- If the user wants a Mermaid-like code fence language tag, correct them: Mermaid is not a Highlight.js language alias in Azure DevOps wiki docs. Read `references/code-languages.md`.

## See Also

- `references/syntax.md`
- `references/decision-trees.md`
- `references/support-matrix.md`
- `references/code-languages.md`
- `references/gotchas.md`
- `templates/mermaid-starter.md`


::: mermaid
graph TD
  A["Proposal"] --> B{"Key decision"}
  B -- Yes --> C["Recommended path"]
  B -- No --> D["Alternative path"]
  C --> E["Next step"]
  D --> F["Next step"]
:::

::: mermaid
graph TD
  A["Start"] --> B["Choose diagram type"]
  B --> C["Write wiki-safe syntax"]
  C --> D["Publish in Azure DevOps wiki"]
:::

::: mermaid
sequenceDiagram
  actor User
  participant Wiki as Azure DevOps Wiki
  User->>Wiki: Open page
  Wiki-->>User: Render Mermaid diagram
:::

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

::: mermaid
timeline
  title Wiki rollout
  2026-03-01 : Draft page
  2026-03-05 : Add diagram
  2026-03-08 : Publish
:::

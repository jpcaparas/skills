# Portable Skill Contract

Portable packages accept exactly these frontmatter fields:

- `name`: lowercase package identifier
- `description`: model-facing invocation contract

Consumers may reject unknown frontmatter. A portable package must not rely on slash commands, automatic invocation, or manual-only behavior unless a target harness documents that capability.

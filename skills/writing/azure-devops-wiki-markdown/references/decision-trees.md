# Decision Trees for Proposals

Use this file when the user wants Azure DevOps wiki-safe decision trees for engineering proposals, rollout plans, ADR discussions, or dependency handling.

Primary sources:

- Microsoft Learn, "Markdown syntax for files, widgets, wikis - Azure DevOps," current as checked on April 9, 2026
- `references/mermaid.md`

## When to Use This Reference

Use decision trees when:

- a proposal changes based on one or more yes-or-no questions
- the team needs to compare a direct build with a spike, phased delivery, or rollback path
- reviewers need to understand why one branch is recommended
- the proposal depends on approvals, dependencies, or risk thresholds

Do not use a decision tree when the work is purely linear. In that case, a checklist or implementation plan is usually clearer.

## Azure-Safe Authoring Rules

1. Use `::: mermaid` blocks in wiki pages.
2. Use `graph TD` or `graph LR`, not `flowchart`.
3. Keep one decision per branching node.
4. Keep node labels short and factual.
5. Put the recommendation, risks, and next step below the diagram rather than inside it.

## Smallest Useful Pattern

```md
::: mermaid
graph TD
  A["Problem or proposal"] --> B{"Key decision"}
  B -- Yes --> C["Recommended path"]
  B -- No --> D["Alternative path"]
  C --> E["Next step"]
  D --> F["Next step"]
:::
```

## Proposal Patterns

### Decide Between Direct Build, Spike, or Phased Delivery

```md
::: mermaid
graph TD
  A["New feature or technical change"] --> B{"Is the scope well understood"}
  B -- No --> C["Run a time-boxed spike"]
  B -- Yes --> D{"Can we deliver it safely in one sprint"}
  D -- Yes --> E["Propose direct implementation"]
  D -- No --> F["Split into phased delivery"]
  C --> G["Return with findings and estimate"]
  E --> H["Document testing and rollout"]
  F --> I["Define phase boundaries and dependencies"]
:::
```

Use this when the target state is partly known but the delivery shape is still being decided.

### Decide Whether a Feature Flag Is Needed

```md
::: mermaid
graph TD
  A["Customer-facing change"] --> B{"Can the change be hidden behind a feature flag"}
  B -- No --> C["Plan a controlled release window"]
  B -- Yes --> D{"Is rollback likely to be needed"}
  D -- Yes --> E["Use staged rollout with monitoring"]
  D -- No --> F["Use flag for internal or dark launch"]
  C --> G["Document comms and rollback steps"]
  E --> H["Define rollout gates and success metrics"]
  F --> H
:::
```

Use this when deployment risk and rollback speed matter.

### Decide Whether a Lightweight Proposal Is Enough

```md
::: mermaid
graph TD
  A["Proposed technical change"] --> B{"Does it affect security, data, or integrations"}
  B -- Yes --> C{"Is there an existing approved pattern"}
  B -- No --> D{"Is the change reversible"}
  C -- Yes --> E["Reuse the approved pattern"]
  C -- No --> F["Draft ADR or review note"]
  D -- Yes --> G["Use a lightweight proposal"]
  D -- No --> H["Add rollback and approval steps"]
  E --> H
  F --> H
:::
```

Use this when the team is deciding whether formal architecture review is needed.

### Decide How to Handle an External Dependency

```md
::: mermaid
graph TD
  A["Proposed work"] --> B{"Does delivery depend on another team or vendor"}
  B -- No --> C["Plan work inside current sprint scope"]
  B -- Yes --> D{"Can the dependency be mocked or deferred"}
  D -- Yes --> E["Proceed with parallel internal work"]
  D -- No --> F["Put dependency on the critical path"]
  C --> G["Estimate and schedule normally"]
  E --> H["Create follow-up task for integration"]
  F --> I["Add dates, owners, and escalation path"]
:::
```

Use this when a proposal needs to show what stays inside team control and what does not.

## Recommended Supporting Sections

After the diagram, include:

- `Recommendation`: the branch you want approved
- `Why`: the main reasons that branch is preferred
- `Risks`: what could still go wrong
- `Next step`: the next action, owner, or approval needed

## Failure Patterns

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| The diagram is readable in code form but hard to review | Node text is too long | Cut node text down to the decision only and move explanation below the diagram. |
| The flowchart fails after copying a generic Mermaid example | The source used `flowchart` syntax | Rewrite the example as `graph TD` or `graph LR`. |
| Reviewers cannot tell which path is proposed | The diagram shows branches but no conclusion | Add a `Recommendation` section immediately below the diagram. |

## See Also

- `references/mermaid.md`
- `references/syntax.md`
- `references/gotchas.md`
- `templates/decision-tree-proposal.md`


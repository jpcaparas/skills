# Document and Code Dissection

Use this reference for PDFs, slide decks, documents, datasets, source trees, repositories, and code. Extract the system or story the target must preserve, not merely the file’s headings.

## Documents, PDFs, and Decks

Inspect:

- title, purpose, audience, provenance, and explicit constraints
- section or slide sequence and the argument or workflow it creates
- exact high-signal copy, terminology, names, figures, and calls to action
- tables, diagrams, captions, footnotes, and relationships between text and visuals
- repeated visual grammar, page templates, hierarchy, and density
- examples, edge cases, open questions, and unresolved decisions

When the default target is a website or web app, translate document structure into a usable information architecture. Preserve content and hierarchy while choosing interaction and responsive behavior honestly; do not claim the document demonstrated those behaviors.

## Datasets

Identify entities, fields, types, units, ranges, ordering, missing values, relationships, and representative records. Separate sample values from business rules. Require the target to use realistic data shapes and handle empty, invalid, extreme, and partial records when the evidence supports those cases.

## Code and Repositories

Start with repository instructions and run the safest local route that exposes real behavior. Inspect:

- entrypoints, routes, modules, assets, styles, schemas, and configuration
- data flow, state transitions, permissions, validation, and error handling
- user-visible copy and generated content
- tests and fixtures that reveal intended behavior or edge cases
- runtime output at representative states when the project can be run safely

Code structure is evidence, not the deliverable unless the user requests technical replication. Prefer observed runtime behavior over an architectural guess. Do not copy incidental implementation choices into the prompt when a simpler implementation can reproduce the same experience.

## Prompt Translation

Convert source structure into target requirements:

- map sections or modules to pages, flows, scenes, or components
- preserve named entities, rules, and exact literals
- identify which information becomes navigation, interaction, visualization, or progressive disclosure
- carry failure and edge behavior into acceptance criteria
- mark visual or interaction design as a new coherent decision when the source never specified it

**Complete when:** the target prompt preserves the source’s content, rules, hierarchy, and relevant edge cases without confusing document layout or code architecture with observed product behavior.

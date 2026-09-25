---
name: {{SKILL_NAME}}
description: "Guide {{DOMAIN_NAME}} work for {{PRIMARY_USE_CASE}}. Use when {{SEMANTIC_INVOCATION_BRANCHES}}. {{OPTIONAL_BOUNDARY_SENTENCE}}"
---

# {{DOMAIN_NAME}} Reference Skill

Provides progressively disclosed guidance for {{PRIMARY_USE_CASE}}.

## Operating Contract

- In scope: {{IN_SCOPE_TASKS}}
- Out of scope or adjacent owner: {{OUT_OF_SCOPE_BOUNDARY}}
- Primary observable: {{PRIMARY_OBSERVABLE}}
- Current evidence: {{REFERENCE_EVIDENCE}}

## Routing Guide

{{CONDITION_AND_PURPOSE_ROUTES}}

Write each route as a condition plus a purpose, for example: “When working on
the signing flow, read `references/signing.md` to choose the verified key and
rotation procedure.” Route directly to the narrowest useful reference. Include
`references/shared.md` only when multiple branches genuinely need the same
conventions; otherwise co-locate the rule with its single consumer.

## Core Rules

{{ALWAYS_NEEDED_RULES}}

Keep instructions required for every invocation here. Move branch-specific
detail behind the matching route.

## Verified Gotchas

{{EVIDENCED_GOTCHAS_OR_LINK}}

## When Guidance Fails

Resolve stale or incomplete advice against current project evidence and relevant
official or trusted primary sources. Do not browse again when reliable evidence
already settles the question. Keep unknowns explicit when sources are unavailable.
Propose a targeted canonical update or deletion with the affected passage, source,
and an example; do not silently rewrite installed skills or publish changes.

## Completion Gate

Complete when the immediate task reaches {{PRIMARY_OBSERVABLE}} and any material
limits are clear. When maintaining this package, also verify routing and that
branch-specific material is available without loading unrelated references.

## Release Gate

Before release, replace every template token, remove unearned references and
their routes, and remove empty headings, duplicated maps, or filler such as
`TBD` and `N/A`.

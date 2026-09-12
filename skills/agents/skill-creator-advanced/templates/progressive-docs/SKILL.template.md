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

## Completion Gate

Complete when the immediate task reaches {{PRIMARY_OBSERVABLE}}, every route
has one canonical owner, and disclosure checks show unrelated branches remain
unloaded.

## Release Gate

Before release, replace every template token, remove unearned references and
their routes, and remove empty headings, duplicated maps, or filler such as
`TBD` and `N/A`.

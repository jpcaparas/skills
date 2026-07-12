---
name: {{SKILL_NAME}}
description: "Operate the {{API_NAME}} API for {{PRIMARY_USE_CASE}}. Use when {{SEMANTIC_INVOCATION_BRANCHES}}. {{OPTIONAL_BOUNDARY_SENTENCE}}"
---

# {{API_NAME}} API Skill

Operates the {{API_NAME}} API for {{PRIMARY_USE_CASE}} through its verified
{{API_CONTRACT_STYLE}} contract.

## Operating Contract

- Required access or setup: {{ACCESS_PREREQUISITES}}
- Allowed effects: {{AUTHORIZED_EFFECT_BOUNDARY}}
- Primary observable: {{PRIMARY_OBSERVABLE}}
- Current evidence: {{CONTRACT_EVIDENCE_AND_VERSION}}

## Operation Map

| User intent | Contract operation | Effect | Verification |
|-------------|--------------------|--------|--------------|
{{OPERATION_MAP_ROWS}}

Include only operations supported by current evidence. Use the API's own
vocabulary; do not force resource CRUD, HTTP methods, or request-body formats
onto a different contract style.

## Routing Guide

This starter offers four possible references. During drafting, keep only routes
whose detail is independently useful; delete an unearned reference and its route,
or co-locate a short rule here.

- For exact operations, inputs, outputs, and failure contracts, read
  `references/api.md`.
- For access, client installation, configuration, and a safe connectivity
  check, read `references/configuration.md`.
- For supported multi-step, asynchronous, traversal, event, or resilience
  workflows, read `references/patterns.md`.
- For evidenced non-obvious constraints and workarounds, read
  `references/gotchas.md`.

## Verified Gotchas

{{EVIDENCED_GOTCHAS_OR_LINK}}

## Completion Gate

Complete when {{PRIMARY_OBSERVABLE}} is verified at the safest authorized
rung, every claimed operation maps to current contract evidence, and every
unverified limitation is explicit.

## Release Gate

Before release, replace every template token with current evidence, remove
unsupported sections, and remove example credentials or filler such as `TBD`
and `N/A`.

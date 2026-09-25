---
name: {{SKILL_NAME}}
description: "Operate the {{TOOL_NAME}} CLI for {{PRIMARY_USE_CASE}}. Use when {{SEMANTIC_INVOCATION_BRANCHES}}. {{OPTIONAL_BOUNDARY_SENTENCE}}"
---

# {{TOOL_NAME}} CLI Skill

Operates `{{TOOL_NAME}}` for {{PRIMARY_USE_CASE}} against the verified
{{SUPPORTED_TOOL_VERSION_OR_RANGE}} command surface.

## Operating Contract

- Supported environments: {{SUPPORTED_ENVIRONMENTS}}
- Required setup: {{SETUP_PREREQUISITES}}
- Allowed effects: {{AUTHORIZED_EFFECT_BOUNDARY}}
- Primary observable: {{PRIMARY_OBSERVABLE}}

## Command Map

| User intent | Command form | Effect | Verification |
|-------------|--------------|--------|--------------|
{{COMMAND_MAP_ROWS}}

Use the tool's own nouns and verbs. Include only commands supported by current
help or documentation; do not force list/create/show/delete operations onto a
different command model.

## Routing Guide

This starter offers four possible references. During drafting, keep only routes
whose detail is independently useful; delete an unearned reference and its route,
or co-locate a short rule here.

- For exact subcommands, arguments, flags, and outcomes, read
  `references/commands.md`.
- For supported installation paths, identity, configuration, and verification,
  read `references/configuration.md`.
- For evidenced multi-step workflows or composition patterns, read
  `references/patterns.md`.
- For non-obvious version, quoting, parsing, platform, or safety behavior, read
  `references/gotchas.md`.

## Verified Gotchas

{{EVIDENCED_GOTCHAS_OR_LINK}}

## When Guidance Fails

Check the installed tool's help and relevant official version-matched docs when
an example fails or lacks a consequential detail. Validate a compatible command
in a temporary workspace or supported dry run without expanding authority.
Report unresolved syntax instead of guessing. Propose a sourced correction to
the canonical skill, including a reproducer; do not silently edit an installed
copy or publish it.

## Completion Gate

Complete when command syntax matches the supported command surface, the primary
observable passes at the safest non-mutating rung available, and any authorized
effect is explicit and independently verified.

## Release Gate

Before release, replace every template token with current evidence, remove
unsupported sections, and remove machine-specific paths, example credentials,
or filler such as `TBD` and `N/A`.

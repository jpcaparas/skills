---
name: {{SKILL_NAME}}
description: "Wrap the {{TOOL_NAME}} CLI for {{PRIMARY_USE_CASE}}. Use when running {{TRIGGER_CONTEXT_1}}, {{TRIGGER_CONTEXT_2}}, or {{TRIGGER_CONTEXT_3}} with {{TOOL_NAME}}. Triggers on: '{{KEYWORD_1}}', '{{KEYWORD_2}}', '{{KEYWORD_3}}', or when the user needs correct {{TOOL_NAME}} commands, flags, output handling, or shell workflows. Do NOT trigger for {{NEGATIVE_TRIGGER_1}} or {{NEGATIVE_TRIGGER_2}}."
---

# {{TOOL_NAME}} CLI Skill

Wraps the `{{TOOL_NAME}}` command-line tool for {{PRIMARY_USE_CASE}}.

**Version:** {{TOOL_VERSION}} | **Install:** `{{INSTALL_COMMAND}}`

## Quick Reference

| Task | Command | Notes |
|------|---------|-------|
| List {{RESOURCE_PLURAL}} | `{{TOOL_BIN}} {{LIST_COMMAND}}` | {{LIST_NOTES}} |
| Create {{RESOURCE_SINGULAR}} | `{{TOOL_BIN}} {{CREATE_COMMAND}}` | {{CREATE_NOTES}} |
| Show {{RESOURCE_SINGULAR}} | `{{TOOL_BIN}} {{SHOW_COMMAND}}` | {{SHOW_NOTES}} |
| Delete {{RESOURCE_SINGULAR}} | `{{TOOL_BIN}} {{DELETE_COMMAND}}` | {{DELETE_NOTES}} |

## Decision Tree

What do you need from `{{TOOL_NAME}}`?

- Learn the correct subcommand and flags
  -> Read `references/commands.md`

- Install the tool, configure auth, or set environment variables
  -> Read `references/configuration.md`

- Build a repeatable workflow or shell pipeline
  -> Read `references/patterns.md`

- Debug an error, shell quirk, or version mismatch
  -> Read `references/gotchas.md`

## Gotchas

1. **{{GOTCHA_1_TITLE}}**: {{GOTCHA_1_DESCRIPTION}}
2. **{{GOTCHA_2_TITLE}}**: {{GOTCHA_2_DESCRIPTION}}
3. **{{GOTCHA_3_TITLE}}**: {{GOTCHA_3_DESCRIPTION}}

## Reading Guide

| Task | Read |
|------|------|
| Full subcommand and flag reference | `references/commands.md` |
| Install, config, auth, environment variables | `references/configuration.md` |
| Common workflows and shell pipelines | `references/patterns.md` |
| Pitfalls, quoting issues, version gotchas | `references/gotchas.md` |

---
name: {{SKILL_NAME}}
description: "Wrap the {{API_NAME}} API for {{PRIMARY_USE_CASE}}. Use when building {{TRIGGER_CONTEXT_1}}, {{TRIGGER_CONTEXT_2}}, or {{TRIGGER_CONTEXT_3}}. Triggers on: '{{KEYWORD_1}}', '{{KEYWORD_2}}', '{{KEYWORD_3}}', or when working with {{API_NAME}} in any capacity. Do NOT trigger for {{NEGATIVE_TRIGGER_1}} or {{NEGATIVE_TRIGGER_2}}."
---

# {{API_NAME}} API Skill

Wraps the {{API_NAME}} API for {{PRIMARY_USE_CASE}}.

## Authentication

{{AUTH_PATTERN}} authentication is required for all requests.

```bash
# Set your API key
export {{ENV_VAR_NAME}}="your-api-key-here"

# Test the connection
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${{ENV_VAR_NAME}}" \
  {{BASE_URL}}/{{HEALTH_ENDPOINT}}
```

Where to get credentials: {{CREDENTIALS_URL}}

## Quick Reference

| Operation | Method | Endpoint | Notes |
|-----------|--------|----------|-------|
| List {{RESOURCE_PLURAL}} | GET | {{BASE_URL}}/{{RESOURCE_PATH}} | Paginated ({{PAGINATION_TYPE}}) |
| Create {{RESOURCE_SINGULAR}} | POST | {{BASE_URL}}/{{RESOURCE_PATH}} | Requires: {{REQUIRED_FIELDS}} |
| Get {{RESOURCE_SINGULAR}} | GET | {{BASE_URL}}/{{RESOURCE_PATH}}/{{ID_PARAM}} | {{EXPAND_NOTE}} |
| Update {{RESOURCE_SINGULAR}} | {{UPDATE_METHOD}} | {{BASE_URL}}/{{RESOURCE_PATH}}/{{ID_PARAM}} | Partial update |
| Delete {{RESOURCE_SINGULAR}} | DELETE | {{BASE_URL}}/{{RESOURCE_PATH}}/{{ID_PARAM}} | {{DELETE_NOTE}} |

## Decision Tree

What do you need to do?

```
Working with {{API_NAME}}?

- Create, read, update, or delete {{RESOURCE_PLURAL}}
  -> Read references/api.md (CRUD operations section)

- Set up auth, install SDK, configure environment
  -> Read references/configuration.md

- Build a multi-step workflow ({{WORKFLOW_EXAMPLE_1}}, {{WORKFLOW_EXAMPLE_2}})
  -> Read references/patterns.md

- Debug an error or unexpected behavior
  -> Read references/gotchas.md

- Handle pagination, rate limits, or webhooks
  -> Read references/patterns.md (infrastructure section)
```

## Gotchas

1. **{{GOTCHA_1_TITLE}}**: {{GOTCHA_1_DESCRIPTION}}
2. **{{GOTCHA_2_TITLE}}**: {{GOTCHA_2_DESCRIPTION}}
3. **{{GOTCHA_3_TITLE}}**: {{GOTCHA_3_DESCRIPTION}}
4. **Rate limits**: {{RATE_LIMIT_DESCRIPTION}}. See `references/gotchas.md` for retry strategies.
5. **API versioning**: This skill targets API version {{API_VERSION}}. {{VERSIONING_NOTE}}

## Reading Guide

| Task | Read |
|------|------|
| Endpoint details, request/response formats | `references/api.md` |
| Pagination, webhooks, async patterns, retry logic | `references/patterns.md` |
| Auth setup, env vars, SDK installation | `references/configuration.md` |
| Known pitfalls, error codes, workarounds | `references/gotchas.md` |

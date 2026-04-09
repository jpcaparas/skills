# {{API_NAME}} Common Patterns & Workflows

## Table of Contents

- [Pagination](#pagination)
- [Rate Limit Handling](#rate-limit-handling)
- [Webhook Integration](#webhook-integration)
- [Create-Then-Poll](#create-then-poll)
- [Batch Operations](#batch-operations)
- [Idempotent Requests](#idempotent-requests)

---

## Pagination

The {{API_NAME}} API uses {{PAGINATION_TYPE}} pagination.

### Basic Pagination Loop

```{{LANGUAGE}}
{{PAGINATION_LOOP_CODE}}
```

**Termination condition:** {{PAGINATION_TERMINATION}}

**Default page size:** {{DEFAULT_PAGE_SIZE}}
**Maximum page size:** {{MAX_PAGE_SIZE}}

### Collecting All Results

```{{LANGUAGE}}
{{COLLECT_ALL_CODE}}
```

---

## Rate Limit Handling

**Limits:** {{RATE_LIMIT_DETAILS}}

**Headers returned on every response:**

| Header | Description |
|--------|-------------|
| `{{RATE_LIMIT_HEADER_REMAINING}}` | Requests remaining in current window |
| `{{RATE_LIMIT_HEADER_RESET}}` | When the window resets ({{RESET_FORMAT}}) |
| `Retry-After` | Seconds to wait (only on 429 responses) |

### Exponential Backoff Pattern

```{{LANGUAGE}}
{{RETRY_PATTERN_CODE}}
```

---

## Webhook Integration

{{WEBHOOK_SECTION_OR_PLACEHOLDER}}

---

## Create-Then-Poll

For async operations that return a job/task ID:

```{{LANGUAGE}}
{{CREATE_THEN_POLL_CODE}}
```

---

## Batch Operations

{{BATCH_SECTION_OR_PLACEHOLDER}}

---

## Idempotent Requests

{{IDEMPOTENCY_SECTION_OR_PLACEHOLDER}}

---

## See Also

- `references/api.md` -- endpoint details and response formats
- `references/configuration.md` -- auth setup and SDK configuration
- `references/gotchas.md` -- pitfalls with these patterns

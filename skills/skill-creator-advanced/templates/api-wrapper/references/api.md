# {{API_NAME}} API Reference

## Table of Contents

- [Overview](#overview)
- [Base URL and Versioning](#base-url-and-versioning)
- [Common Headers](#common-headers)
- [{{RESOURCE_GROUP_1}}](#{{RESOURCE_GROUP_1_ANCHOR}})
- [{{RESOURCE_GROUP_2}}](#{{RESOURCE_GROUP_2_ANCHOR}})
- [{{RESOURCE_GROUP_3}}](#{{RESOURCE_GROUP_3_ANCHOR}})
- [Error Codes](#error-codes)

---

## Overview

The {{API_NAME}} API uses {{API_STYLE}} with {{DATA_FORMAT}} request and response bodies.

**Base URL:** `{{BASE_URL}}`
**API Version:** `{{API_VERSION}}`
**Authentication:** `{{AUTH_HEADER_FORMAT}}`

## Base URL and Versioning

```
{{BASE_URL}}/{{VERSION_PREFIX}}/
```

{{VERSIONING_DETAILS}}

## Common Headers

Every request requires:

```
Authorization: {{AUTH_HEADER_FORMAT}}
Content-Type: application/json
Accept: application/json
{{ADDITIONAL_REQUIRED_HEADERS}}
```

---

## {{RESOURCE_GROUP_1}}

### List {{RESOURCE_GROUP_1}}

```
GET {{BASE_URL}}/{{RESOURCE_GROUP_1_PATH}}
```

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| {{PAGINATION_PARAM}} | {{PAGINATION_TYPE}} | No | {{PAGINATION_DEFAULT}} | {{PAGINATION_DESCRIPTION}} |
| limit | integer | No | {{DEFAULT_PAGE_SIZE}} | Max {{MAX_PAGE_SIZE}} |
| {{FILTER_PARAM_1}} | string | No | - | {{FILTER_DESCRIPTION_1}} |

**Response:**

```json
{
  "data": [
    {
      "id": "{{EXAMPLE_ID}}",
      "{{FIELD_1}}": "{{FIELD_1_VALUE}}",
      "{{FIELD_2}}": "{{FIELD_2_VALUE}}",
      "created_at": "{{EXAMPLE_TIMESTAMP}}"
    }
  ],
  "{{PAGINATION_RESPONSE_FIELD}}": {{PAGINATION_RESPONSE_VALUE}}
}
```

**Example:**

```bash
curl -X GET "{{BASE_URL}}/{{RESOURCE_GROUP_1_PATH}}?limit=10" \
  -H "Authorization: {{AUTH_HEADER_FORMAT}}"
```

### Create {{RESOURCE_SINGULAR_1}}

```
POST {{BASE_URL}}/{{RESOURCE_GROUP_1_PATH}}
```

**Request Body:**

```json
{
  "{{REQUIRED_FIELD_1}}": "{{REQUIRED_FIELD_1_VALUE}}",
  "{{REQUIRED_FIELD_2}}": "{{REQUIRED_FIELD_2_VALUE}}",
  "{{OPTIONAL_FIELD_1}}": "{{OPTIONAL_FIELD_1_VALUE}}"
}
```

**Required Fields:** {{REQUIRED_FIELD_1}}, {{REQUIRED_FIELD_2}}

**Response:** Returns the created object with status `201 Created`.

### Get {{RESOURCE_SINGULAR_1}}

```
GET {{BASE_URL}}/{{RESOURCE_GROUP_1_PATH}}/{{ID_PARAM}}
```

{{EXPAND_DETAILS}}

### Update {{RESOURCE_SINGULAR_1}}

```
{{UPDATE_METHOD}} {{BASE_URL}}/{{RESOURCE_GROUP_1_PATH}}/{{ID_PARAM}}
```

Send only the fields you want to change. Omitted fields are not modified.

### Delete {{RESOURCE_SINGULAR_1}}

```
DELETE {{BASE_URL}}/{{RESOURCE_GROUP_1_PATH}}/{{ID_PARAM}}
```

{{DELETE_DETAILS}}

---

## {{RESOURCE_GROUP_2}}

{{RESOURCE_GROUP_2_CONTENT}}

---

## {{RESOURCE_GROUP_3}}

{{RESOURCE_GROUP_3_CONTENT}}

---

## Error Codes

| HTTP Status | Error Code | Description | Resolution |
|-------------|-----------|-------------|------------|
| 400 | `{{ERROR_CODE_400}}` | {{ERROR_DESC_400}} | {{ERROR_FIX_400}} |
| 401 | `{{ERROR_CODE_401}}` | {{ERROR_DESC_401}} | {{ERROR_FIX_401}} |
| 403 | `{{ERROR_CODE_403}}` | {{ERROR_DESC_403}} | {{ERROR_FIX_403}} |
| 404 | `{{ERROR_CODE_404}}` | {{ERROR_DESC_404}} | {{ERROR_FIX_404}} |
| 429 | `{{ERROR_CODE_429}}` | {{ERROR_DESC_429}} | {{ERROR_FIX_429}} |
| 500 | `{{ERROR_CODE_500}}` | {{ERROR_DESC_500}} | {{ERROR_FIX_500}} |

**Error Response Format:**

```json
{
  "error": {
    "code": "{{EXAMPLE_ERROR_CODE}}",
    "message": "{{EXAMPLE_ERROR_MESSAGE}}",
    "{{ERROR_DETAIL_FIELD}}": "{{ERROR_DETAIL_VALUE}}"
  }
}
```

---

## See Also

- `references/patterns.md` -- common workflows and pagination patterns
- `references/configuration.md` -- auth setup and SDK installation
- `references/gotchas.md` -- pitfalls specific to these endpoints

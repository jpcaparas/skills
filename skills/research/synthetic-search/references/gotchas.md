# Gotchas

Use this file when Synthetic behaves differently from the published examples or when a clean happy-path request still gives you surprising output.

## 1. `published` Is Documented but Not Reliably Present

### Symptom

The docs or older skills show `results[].published`, but your live response does not include it.

### Cause

The Synthetic docs and older wrapper examples appear ahead of current live behavior.

### Fix

Treat `published` as optional. Print a fallback like `(not returned by API)` and avoid schema assumptions that require the field.

## 2. Empty Query Returns a Blank 500

### Symptom

`{"query":""}` returns `500 Internal Server Error` with an empty body.

### Cause

Input validation currently handles missing `query` more cleanly than empty-string `query`.

### Fix

Reject blank queries before sending the request. The helper script does this locally.

## 3. Local Display Limits Are Not Server-Side Pagination

### Symptom

You pass `-n 3` to the helper and think the API only returned 3 results.

### Cause

The helper trims the displayed list after the request. The server still returned its full result set.

### Fix

Use raw JSON or `--json` when you need the untouched response. Document `--limit` as display-only.

## 4. Quota Numbers Change Faster Than Docs

### Symptom

Docs prose and old examples mention one limit pattern, but your account shows different values.

### Cause

Limits are account-specific and can change over time.

### Fix

Check `GET /v2/quotas` before quoting numeric limits. Treat docs prose as orientation, not authority.

## 5. Unauthorized Responses Are Cleaner Than Some Input Errors

### Symptom

Bad auth gives a useful JSON body, but some malformed inputs do not.

### Cause

Different validation layers appear to generate different error responses.

### Fix

Handle status codes first, then parse the body if present. Do not assume every failure returns JSON.

## 6. The API Is Still Under Development

### Symptom

Fields or behaviors drift from the published examples.

### Cause

Synthetic explicitly says the API is still under development.

### Fix

When a field matters operationally, verify it live with `scripts/probe_synthetic_search.py` before baking it into a workflow.

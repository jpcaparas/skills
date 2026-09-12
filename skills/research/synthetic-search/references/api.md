# API Reference

Use this file when you need the exact Synthetic endpoints, request shapes, or observed response fields.

Verified on April 9, 2026 against the live API.

## Base URL

```text
https://api.synthetic.new/v2
```

## Authentication

Send a bearer token in the `Authorization` header.

```bash
[ -n "$SYNTHETIC_API_KEY" ] && echo "OK: SYNTHETIC_API_KEY is set" || echo "Error: SYNTHETIC_API_KEY not set"
```

```bash
curl -s https://api.synthetic.new/v2/quotas \
  -H "Authorization: Bearer $SYNTHETIC_API_KEY" | jq .
```

## `POST /search`

Run a web search query and receive up to 5 result records.

### Request

```bash
curl -s https://api.synthetic.new/v2/search \
  -H "Authorization: Bearer $SYNTHETIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"rust async await"}'
```

### Observed Response Shape

```json
{
  "results": [
    {
      "url": "https://example.com/page",
      "title": "Page Title",
      "text": "Extracted page content or snippet..."
    }
  ]
}
```

### Documented but Not Reliably Observed

Synthetic's docs and the published `skills.sh` skill also show:

```json
{
  "published": "2025-11-05T00:00:00.000Z"
}
```

Treat `published` as optional. In live testing on April 9, 2026, verified result objects did not contain it.

### Notes

- The docs describe Synthetic Search as zero-data-retention and still under development.
- Live tests returned 5 results for normal queries.
- No server-side result-count parameter is documented for `/search`.

## `GET /quotas`

Retrieve current usage and limit information.

The docs explicitly say `/quotas` does not count against subscription limits.

### Request

```bash
curl -s https://api.synthetic.new/v2/quotas \
  -H "Authorization: Bearer $SYNTHETIC_API_KEY" | jq .
```

### Observed Response Keys

```json
{
  "subscription": {
    "limit": 750,
    "requests": 0,
    "renewsAt": "2026-04-09T14:01:55.033Z"
  },
  "search": {
    "hourly": {
      "limit": 250,
      "requests": 5,
      "renewsAt": "2026-04-09T10:00:18.034Z"
    }
  },
  "freeToolCalls": {
    "limit": 0,
    "requests": 0,
    "renewsAt": "2026-04-10T09:01:55.232Z"
  },
  "weeklyTokenLimit": {
    "nextRegenAt": "2026-04-09T10:33:36.000Z",
    "percentRemaining": 99.91879188888889,
    "maxCredits": "$36.00",
    "remainingCredits": "$35.97",
    "nextRegenCredits": "$0.72"
  },
  "rollingFiveHourLimit": {
    "nextTickAt": "2026-04-09T09:10:48.000Z",
    "tickPercent": 0.05,
    "remaining": 750,
    "max": 750,
    "limited": false
  }
}
```

Do not hard-code the numeric values above. They are an observed sample, not a permanent contract.

## Error Responses

| Scenario | Status | Observed body |
| --- | --- | --- |
| Missing or invalid key on `/search` | `401` | `{"error":"Invalid API Key."}` |
| Missing `query` key | `400` | `{"error":"Invalid POST body: [object Object] failed the following checks:\nmissing key 'query'"}` |
| Empty `query` string | `500` | Empty body in live testing |
| Missing key on `/quotas` | `401` | Unauthorized, body not useful in `curl` testing |

## Source URLs

- `https://dev.synthetic.new/docs/synthetic/search`
- `https://dev.synthetic.new/docs/synthetic/quotas`

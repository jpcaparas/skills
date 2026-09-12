# Configuration

Use this file when you need setup steps, prerequisite checks, or a quick way to confirm the environment is ready.

## Requirements

- `SYNTHETIC_API_KEY`
- `curl`
- Optional: `jq` for filtering JSON
- Optional: Node.js 18+ for `scripts/search.js`
- Optional: Python 3 for `scripts/probe_synthetic_search.py`, `scripts/validate.py`, and `scripts/test_skill.py`

## Set the API Key

```bash
export SYNTHETIC_API_KEY="your-key-here"
```

Never hard-code the key inside scripts, evals, or committed config.

## Check the Environment

```bash
[ -n "$SYNTHETIC_API_KEY" ] && echo "OK: SYNTHETIC_API_KEY is set" || echo "Error: SYNTHETIC_API_KEY not set"
```

```bash
command -v jq >/dev/null && echo "OK: jq installed" || echo "jq optional but useful"
```

```bash
node --version
python3 --version
```

## Fastest Auth Check

`/quotas` is safer than a search query because the docs say it does not count against subscription limits.

```bash
curl -s https://api.synthetic.new/v2/quotas \
  -H "Authorization: Bearer $SYNTHETIC_API_KEY" | jq .
```

If that works, auth is set up correctly.

## When to Use Which Interface

| Interface | Use it when | Why |
| --- | --- | --- |
| Raw `curl` | Another tool or script needs exact JSON | Lowest ambiguity |
| `curl` + `jq` | You only need URLs, titles, or one field | Fast shell pipeline |
| `node scripts/search.js` | A human wants readable output or simple quota summaries | Easier scanning |
| `python3 scripts/probe_synthetic_search.py` | You want a structured probe for live verification | Repeatable diagnostics |

## Source Docs

- `https://dev.synthetic.new/docs/synthetic/search`
- `https://dev.synthetic.new/docs/synthetic/quotas`

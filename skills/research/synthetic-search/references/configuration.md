# Configuration

Use this file for setup steps, prerequisite checks, and choosing an interface.

## Requirements

- `SYNTHETIC_API_KEY` from a Synthetic subscription. All plans list the Web Search API.
- Node.js 18 or newer for `scripts/search.js` (uses built-in `fetch`; no npm install).
- Optional: `curl` and `jq` for raw calls.
- Optional: Python 3.11 or newer for `scripts/probe_synthetic_search.py`, `scripts/test_helper.py`, `scripts/validate.py`, and `scripts/test_skill.py`.

## Provide the Key

Put the key in the environment through your secret manager or shell profile:

```bash
export SYNTHETIC_API_KEY="..."
```

Never hard-code it in scripts, evals, committed config, command arguments, or chat. Check presence without printing it:

```bash
[ -n "$SYNTHETIC_API_KEY" ] && echo "SYNTHETIC_API_KEY is set" || echo "SYNTHETIC_API_KEY is missing"
```

## Free Auth Check

`/quotas` does not consume quota, so it is the safest way to confirm the key works:

```bash
node <skill-dir>/scripts/search.js quotas
```

A `401` means the key is wrong or the header lacks the `Bearer ` prefix.

## Optional Override

`SYNTHETIC_API_BASE_URL` (default `https://api.synthetic.new/v2`) points the helper and probe at another base URL. The offline tests use it to target a local stub; normal use never needs it.

## Choosing an Interface

| Interface | Use it when |
| --- | --- |
| `node scripts/search.js --compact --save FILE` | An agent needs results in context: small output, full pages kept on disk |
| `node scripts/search.js` (default) | A person wants readable terminal output |
| `curl` + `jq` | Node is unavailable, or another tool needs exact JSON |
| `python3 scripts/probe_synthetic_search.py` | Re-verifying limits and error shapes after the API changes |

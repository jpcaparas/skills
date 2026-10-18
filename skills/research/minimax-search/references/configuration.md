# Configuration

Use this file for key setup, region selection, and prerequisites.

## Requirements

- `MINIMAX_API_KEY`: a Token Plan (M Plan) subscription key. MiniMax keeps subscription keys separate from pay-as-you-go API keys.
- Node.js 18 or newer for `scripts/search.js` (built-in `fetch`; no npm install).
- Optional: `curl` and `jq` for raw calls; Python 3.11 or newer for `scripts/test_helper.py`, `scripts/validate.py`, and `scripts/test_skill.py`.

## Region

| Variable | Global (default) | Mainland China |
| --- | --- | --- |
| `MINIMAX_API_HOST` | `https://api.minimax.io` | `https://api.minimaxi.com` |

The key and host must come from the same region; otherwise the API returns `2049 "invalid api key"`.

## Provide the Key

Use your secret manager or shell profile. Never put the key in scripts, evals, committed config, command arguments, or chat. Check presence without printing it:

```bash
[ -n "$MINIMAX_API_KEY" ] && echo "MINIMAX_API_KEY is set" || echo "MINIMAX_API_KEY is missing"
```

## Free Auth Check

```bash
node <skill-dir>/scripts/search.js quota
```

An error of `1004` or `2049` means a wrong key or region.

## Other MiniMax Search Routes

| Route | When it fits |
| --- | --- |
| `scripts/search.js` (this skill) | Agent or shell searches; same backend as the official MCP and CLI |
| Official MCP `minimax-coding-plan-mcp` (`web_search` tool) | An MCP client should expose search as a tool; it calls the same endpoint |
| Official CLI `mmx search "query"` | Interactive terminal use |
| Server tool `web_search` in chat requests | Rarely; see `references/evidence.md` for why it is unreliable for search tasks |

# Configuration

## Key

- Set `Z_AI_API_KEY` (the helper also accepts `ZAI_API_KEY`). Never print, log, or commit it; check presence with `[ -n "${Z_AI_API_KEY:-$ZAI_API_KEY}" ]`.
- Since 2026-10-16 Z.ai issues separate Standard (pay-as-you-go) and Coding Plan keys ([guide](https://docs.z.ai/devpack/notice/api-key-management)). New keys are billed by key type on every endpoint: Standard keys spend the balance, Coding Plan keys spend plan quota. Older keys on accounts that ever had a plan are "Compatible" and billed by endpoint: MCP uses plan quota, REST `/paas/v4` spends cash. This skill's measurements used a Compatible key.
- Use a Coding Plan (or Compatible) key for this skill's default MCP route. With a Standard key, expect every call to cost cash.
- `node scripts/zai.js quota` confirms the plan level, tool calls left, and cash balance without spending either.

## Plans

| Plan | Tool budget (tested account) | Credit-based plans (docs) |
| --- | --- | --- |
| Lite / Pro / Max | Monthly `TIME_LIMIT` counter; 4,000 calls on Max | 1.2 credits per MCP tool call; 5-hour credits 2k / 12k / 28k; weekly 10k / 60k / 140k |

Peak hours (Mon–Fri 14:00–18:00 UTC+8) may cost more on credit-based plans. Plan details change; trust `quota` and the [coding plan overview](https://docs.z.ai/devpack/overview) over this table.

## Hosts

- International: `https://api.z.ai/api` (tested).
- Mainland China (`open.bigmodel.cn`, Zhipu BigModel): not tested. Set `ZAI_API_ROOT` if a key belongs there.

## MCP client setup

The three servers are plain streamable-HTTP MCP servers with a Bearer header, so any MCP client can mount them instead of the helper:

```json
{
  "web-search-prime": { "url": "https://api.z.ai/api/mcp/web_search_prime/mcp", "headers": { "Authorization": "Bearer ${Z_AI_API_KEY}" } },
  "web-reader": { "url": "https://api.z.ai/api/mcp/web_reader/mcp", "headers": { "Authorization": "Bearer ${Z_AI_API_KEY}" } },
  "zread": { "url": "https://api.z.ai/api/mcp/zread/mcp", "headers": { "Authorization": "Bearer ${Z_AI_API_KEY}" } }
}
```

Adapt the shape to the client's config format (Amp `amp.mcpServers`, Claude Code `claude mcp add --transport http`, and so on). Keep the key in the environment, not in a committed file.

## Prerequisites

- Helper: Node.js 18+ (global `fetch`).
- Raw calls: `curl` and `jq`.
- Package tests: Python 3.11+ and Node.js; they use a local stub and never contact Z.ai.

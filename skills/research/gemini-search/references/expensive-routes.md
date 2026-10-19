# Expensive routes

These routes are catalogued so you know when they are worth it. **Never use one without the user's explicit permission in the current conversation.** Before asking, state the route, the expected cost range, the expected time, and why the default `search` and `read` route is not enough. A general "go ahead with the research" does not cover a route whose cost you have not stated.

## Catalogue

| Route | Measured (2026-10-19) | Documented | When it earns its cost |
| --- | --- | --- | --- |
| Deep Research (`deep-research-preview-04-2026`) | 7 searches, 184,963 input (41,635 cached), 9,499 output, 22,219 thinking, 12,366 tool tokens; under 3.3 min; 7,249-character report, 13 sources; about $0.80 | About 80 searches, $1-3 per task, up to 60 min | Multi-source comparisons or literature-style reviews the user wants as a written report |
| Deep Research Max (`deep-research-max-preview-04-2026`) | Same brief: 73 searches, 486,504 input (9,402 cached), 24,521 output, 67,737 thinking, 95,540 tool tokens; 7.6 min; 18,406 characters, 28 sources; about $3.28 | Up to about 160 searches, $3-7 per task | Exhaustive due diligence where breadth matters more than cost |
| `gemini-3.1-pro-preview` with search | 2 queries, 1,262 thinking tokens, 18 s for a one-fact question | $2 / $12 per 1M tokens; $4 / $18 above 200k | Reasoning-heavy synthesis over grounded results |
| `gemini-4-argon` with search | 1 query, 15 s | $2 / $10 per 1M, doubling 2026-12-01; paid tier only | Hard multi-step analysis; not needed for lookups |
| Query caps above 5 | One call ran 32 queries ($0.45 after the free tier) | $14 per 1,000 queries | Almost never; split the question instead |

Cost estimates use the Gemini 3.1 Pro list price for agent tokens because Google does not say which model the agents bill at, plus $0.014 per search after the free 5,000 per month. Treat them as approximate; AI Studio shows actual spend.

Both agents were given the same "keep the report short" brief. Max ignored the length instruction, ran about 10x the searches, and cost about 4x as much. Its report also repeated a stale claim (Gemini 2.5 grounding as a current option) that the cheaper agent made too, so verify agent output either way.

## Running Deep Research once permitted

```bash
node scripts/gemini_search.js research --confirm-cost "Compare X, Y, and Z on price, limits, and free tiers. One table plus five takeaways, with sources."
node scripts/gemini_search.js research --confirm-cost --max "..."   # only when Max was approved
```

The helper starts the agent with `background: true` and `store: true` (required), polls every 10 seconds for up to 65 minutes, prints the report and usage, and deletes the stored interaction unless `--keep` is passed. Agent citations are redirect links; resolve the ones you cite.

Raw API equivalent:

```bash
curl -sS -X POST https://generativelanguage.googleapis.com/v1beta/interactions \
  -H "x-goog-api-key: $GEMINI_API_KEY" -H "Content-Type: application/json" \
  -d '{"agent": "deep-research-preview-04-2026", "input": "...", "background": true, "store": true}' | jq -r .id
curl -sS https://generativelanguage.googleapis.com/v1beta/interactions/$ID -H "x-goog-api-key: $GEMINI_API_KEY" | jq '{status, usage}'
curl -sS -X DELETE https://generativelanguage.googleapis.com/v1beta/interactions/$ID -H "x-goog-api-key: $GEMINI_API_KEY"
```

Documented limits: no custom function tools (remote MCP servers are allowed), no structured output, 60-minute maximum, and collaborative planning through `agent_config.collaborative_planning` with `previous_interaction_id`.

## Using a gated model once permitted

```bash
node scripts/gemini_search.js search --allow-expensive --model gemini-3.1-pro-preview "..."
```

The per-query search fee is the same on every Gemini 3+ model; gated models add token cost and latency, not better search coverage. In testing, all six available models gave the same answer to the same fact question.

## Cheaper alternatives to try first

- Split a broad question into three to five focused `search` calls (about $0.03-0.06 each after the free tier).
- `search` with `--model gemini-3.8-flash` for sharper, site-targeted queries without unlocking anything.
- `read` the two or three best sources for depth; page tokens cost far less than agent loops.

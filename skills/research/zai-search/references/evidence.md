# Evidence and Verification Limits

This is a **2026-10-18 UTC snapshot** from one international-host key with both Coding Plan subscriptions at level Max, not a promise about every plan or future release.

Sources:
- the official docs index ([llms.txt](https://docs.z.ai/llms.txt)), including the Web Search and Web Reader API references, the Web Search, Web Reader, and Zread MCP guides, pricing (Web Search $0.01 per use), the coding plan overview, and error codes;
- the live MCP `tools/list` schemas for all three servers.

## Executed live probes

Several hundred calls across MCP and REST, plus free quota and balance reads. Total cash spent was about $0.62; plan tool usage reached about 200 of 4,000. Raw responses stayed in a scratch directory and were not committed.

| Probe | Result |
| --- | --- |
| MCP handshake | Works with initialize → session header → `notifications/initialized`; without a session, `-401 Api key not found` |
| MCP search baseline (~20 queries) | 6–10 results; `title`, `link`, `content` (~150 chars), `refer`; no dates |
| MCP parameters | `search_recency_filter` changed results; `search_domain_filter`, `content_size: high` identical to control; invalid enum values accepted |
| `site:` placement | First position derailed one query into unrelated "transport" pages; last position kept intent |
| `site:github.com` precision | MCP 4/9, 1/10, 0/9; REST `search-prime` 4/9; `search_std` 7/42 on-domain |
| REST engines | All six accepted; bogus engine `1211`; `search-prime` ≤10 for `count` 1–100; `search_std` 33–41 with excerpts to ~5k chars |
| REST validation | No auth `1001`; bad key `1000`; missing or empty query `1214`; missing engine `1214`; bad JSON 400; 5,000-char and numeric queries accepted |
| REST recency | `oneDay` returned pages dated 2026-10-17 and 2026-10-18 |
| Billing (10 calls each, balance settled) | REST `search-prime` $0.01 per call on both base URLs; `search_pro_sogou` $0.01; `search_std` ~$0.0015; REST reader $0.01 |
| MCP billing (~43 searches, settled) | Balance moved $0.0106 total; quota `search-prime` rose by exactly the 43 successful calls |
| Concurrency | 2/3/5 → 0 errors; 8 → 10/24 `1302`; 10 → 17/30; 12 → 24/36; throttled calls not counted |
| Sequential | 20 searches in 58 s, no errors |
| Reader | arXiv PDF, JavaScript-rendered pricing page, GitHub blob pages OK; asyncio docs 49.7k chars; 404 and dead host `1234` after up to ~10 s; non-URL `-400`; redirecting URL lost its title |
| Zread | encode/httpx, vitejs/vite, psf/requests, synthetic-lab/octofriend indexed; jpcaparas/skills `1210`; 593 KB `read_file` untruncated; missing file `1015` text; some psf/requests questions returned no hits |
| Helper | Live `quota`, MCP `search --compact --site`, `read`, `repo-search`, `repo-tree` on an unindexed repo (hint shown), REST `--site` filtering; local rejection of empty queries and `--engine` without `--rest` |

## Not tested

- The chat-completions `web_search` tool (`tools: [{"type": "web_search", ...}]`) documented for GLM models.
- The mainland China host (`open.bigmodel.cn`) and keys issued there.
- Credit-based plan accounting (1.2 credits per tool call) and peak-hour multipliers; this account used the per-call `TIME_LIMIT` counter.
- Behaviour at quota exhaustion (`1308` / `1310`) and the exact monthly reset.
- Whether the small MCP-period balance drift is a per-call charge or delayed settlement of earlier calls.
- Keys created after the 2026-10-16 split: whether a Standard key can call the MCP servers (and at what price), and whether a new Coding Plan key bills REST search to plan quota. The tested key was a pre-split Compatible key.

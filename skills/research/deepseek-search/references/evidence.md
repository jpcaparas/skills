# Evidence ledger

All probes ran on 2026-10-18 between about 17:00 and 21:30 UTC (a Sunday, off-peak) from one Amp orb, with a pay-as-you-go `DEEPSEEK_API_KEY` that started with a $2.73 balance. About 150 billable searches and fetches, plus a few model calls with search, brought it to $2.61.

## What was measured

| Area | Probe | Result |
| --- | --- | --- |
| Query length | 128 and 129 ASCII, CJK, and emoji characters | 128 passes for all; 129 fails with `400` for all, so the unit is code points |
| Empty query | `""`, whitespace, missing, `null` | All `400` |
| `count` | 0, 1, 10, 50, 51, `"5"`, `5.0`, -1 | 1-50 accepted; others `400`; omitted gives 10 |
| Other fields | `ori_question`, `localization` (IPv4, IPv6, invalid), `need_content` (boolean, string), unknown field | As in `references/api.md`; unknown fields ignored |
| Operators | `site:` with domains and paths, `-site:`, `OR`, parentheses, quotes, `-term`, `-"phrase"`, `lang:` (en, zh, zh,en, xx), `after:` and `before:` with years, dates, and an invalid date | As in `references/api.md`, including year-only `after:2026` returning nothing |
| Determinism | Same request repeated | Identical results |
| Response shape | 10, 50, and `need_content` responses | About 40 KB, 195 KB, and 3x; summary 1,600-4,600 characters; snippet up to about 2,000 |
| Dates | Non-null dates across many queries; PostgreSQL 18.6 checked against its release notes | All `T16:00:00+00:00`; the publication day is the date after adding 8 hours |
| Localization | "bank", "weather forecast", and technical queries with no IP, 8.8.8.8, and other regional IPs | Local-intent overlap with the default was 0-11%; technical 33-67% |
| Fetch | HTML docs, a repeat, JSON, plain text (536,259 characters), a PDF, an image, target 404 and 500, NXDOMAIN, `https:///path`, localhost, 169.254.169.254, credentials, `ftp:`, an 8,200-character URL, a 9-second delayed response, a JavaScript app | As in `references/api.md` and `references/gotchas.md` |
| Fetch identity | Fetching a header-echo endpoint | Firefox on Linux user agent, `Accept-Language: zh-CN` |
| Rate limits | 15 and 8 simultaneous searches; 5-plus simultaneous fetches to one domain and to many | 5 succeed per burst, the rest `429` with no `Retry-After` |
| Billing | Balance before and after billable, empty, and failed calls | Debits in whole cents after a delay of minutes; consistent with $0.75 per 1,000 |
| Model-side search | Anthropic-format endpoint on both models, with and without `max_uses` and `allowed_domains`; Responses format on both models | As in `references/model-search.md` |

## Untested or unverified

- Whether direct API model-side searches are billed per search before 2026-11-01.
- The Fetch per-domain QPS limit's value (not reached with 5 simultaneous same-domain requests).
- `402` and `403` responses (the account had a balance; no URL triggered the security policy).
- Streaming responses for model-side search.
- Behaviour under sustained load beyond short bursts.

## Rerun probes

Run these from a shell with the key set. Each costs at most $0.00075 and none prints the key.

```bash
H=scripts/deepseek_search.js
node $H balance                                                   # free; confirms key and balance
node $H search --compact -n 2 "postgresql 18.6 release"           # dates: published should be 2026-08-13
node $H search --compact --after 2026 -n 3 "rust release"         # expands to after:2026-01-01; raw after:2026 returned []
node $H search --compact -c 20 "tokio select site:github.com OR site:docs.rs" | jq '[.results[].url | split("/")[2]] | group_by(.) | map({(.[0]): length}) | add'
node $H fetch --chars 300 https://www.postgresql.org/docs/18/release-18-6.html   # unescaped "Release date: 2026-08-13"
node $H fetch https://arxiv.org/pdf/1706.03762                    # expect 404, free
for i in $(seq 1 10); do node $H search --urls -n 1 "probe $i" & done; wait   # may show 429 retries on stderr
```

If a result contradicts this ledger, update `references/api.md`, `references/gotchas.md`, and this file in the canonical repository with the new date and evidence.

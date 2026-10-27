# Account Guards

Exa's account controls can block spending, unlike notify-only limits elsewhere, but agents cannot set them with a normal API key. Recommend these to the user.

## Check before and after

| Check | How | Notes |
| --- | --- | --- |
| What a request billed | `costDollars.total` on Search, Contents, Answer; `costDollars` and `usage` on Agent runs | "Estimated total … not an invoice record"; record it in the task report |
| Usage by key | `GET https://admin-api.exa.ai/team-management/api-keys/{id}/usage?start_date=&end_date=` | Needs a **service key** (dashboard → Service keys); a normal API key returned 401 live. History goes back 180 days |
| Balance and invoices | dashboard → Billing | No balance endpoint for normal keys |
| Running monitors | `GET /monitors` | Delete with `DELETE /monitors/{id}` or pause with `PATCH` `{"status": "paused"}`; `POST /monitors/batch` defaults to `dry_run: true` |
| Active Agent runs | `GET /agent/runs?limit=10` | Free; cancel with `POST /agent/runs/{id}/cancel` |

## Settings to recommend

1. **A budget per API key.** `budgetCents` on `POST`/`PUT /api-keys` (Team Management API, enabled per team) or the dashboard's API Keys page. When a key spends its budget for the billing period, requests return `402 API_KEY_BUDGET_EXCEEDED`. This is a real stop, so give each agent or integration its own key with a small budget.
2. **Auto recharge with a monthly maximum.** Auto recharge buys $5–$10,000 each time the balance falls to a threshold; a monthly maximum of $0 or blank means no cap. For a hard ceiling, keep a prepaid balance with auto recharge off and let requests fail with `402 NO_MORE_CREDITS`.
3. **A lower QPS per key** so a runaway loop cannot use the team's whole limit.
4. **The free credit**: $10 that resets on the first of each month with no carry-over (first team only), plus a one-time $10 onboarding bonus that does not expire. It covers about 2,500 `lite` searches or 10,000 single-type `/contents` pages.

## Budgets inside a task

- Agree a dollar budget before Agent `auto`/`ultra`, Connect data sources, contact enrichment, monitors, or more than about 100 requests, and pass it to the estimator: `--budget-usd N`.
- For metered Agent runs the cap is the budget: set `budget.maxCostDollars` to the agreed figure (minimum $1).
- Approval covers the stated worst case once. A retry, follow-up run, a monitor's schedule, or a second batch is new spend.
- After the job, report the summed `costDollars.total` and any monitors or Agent runs still active.

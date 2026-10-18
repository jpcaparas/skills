# Account Guards

Parallel's own controls warn but do not block, so a budget has to be enforced by whoever sends the requests. Agents cannot change account settings; recommend these to the user.

## Check before and after

| Check | How | Notes |
| --- | --- | --- |
| Balance and pending debits | `GET https://api.parallel.ai/service/v1/balance` (`credit_balance_cents`, `pending_debit_balance_cents`, `will_invoice`) or Platform → Usage | Needs an OAuth account token, not the API key |
| What a request billed | the response's `usage` array (`sku_search`, `sku_extract_excerpts`, ...) | Record it in the task report |
| Running monitors | `GET /v1/monitors` (CLI `parallel-cli monitor list`) | Cancel the ones nobody needs: `POST /v1/monitors/{id}/cancel` (irreversible) |
| Running FindAll jobs | `GET /v1beta/findall/runs/{id}` | `POST …/cancel` stops future work only |

Never call `POST /service/v1/balance/add`; it charges the organisation's default card.

## Settings to recommend

1. **Spend limits are notify-only.** "Limits are notify-only; they never block requests." Set them for the warning email, but do not treat them as a cap.
2. **Auto-reload and card top-ups** keep charging when the balance runs low. If the user wants a hard ceiling, keep a prepaid balance without auto-reload and let requests fail with 402.
3. **Separate keys per agent or integration** make the usage page show who spent what.
4. **The $5 monthly free credit** (one per organisation, card on file) expires at month end; it covers about 5,000 fast searches or 1,000 `lite` Task runs.

## Budgets inside a task

- Agree a dollar budget before Task Groups, FindAll, Monitors, or `pro`/`ultra` runs, and pass it to the estimator: `--budget-usd N`.
- Approval covers the stated worst case once. A retry, follow-up, extension, enrichment, or second batch is new spend.
- After the job, report what the `usage` arrays show and any monitors left running.

# Account Guards

Settings and checks that stop one request or one forgotten job from draining the account. Agents can read usage through the API; the spend controls are dashboard-only, so recommend them to the user rather than claiming to set them.

## Check before and after

| Check | Call | Cost |
| --- | --- | --- |
| Remaining credits and billing period | `GET /v2/team/credit-usage` or `firecrawl_guard.py balance` | free (live) |
| Usage history, per key | `GET /v2/team/credit-usage/historical?byApiKey=true` | read-only; not tested |
| Queue depth and concurrency | `GET /v2/team/queue-status` | free (live) |
| Running crawls | `GET /v2/crawl/active` | free (live) |
| Monitors and their monthly estimate | `GET /v2/monitor` (MCP `firecrawl_monitor_list`) | free (live) |

`GET /v2/activity` is listed in some docs but returned 404 on 2026-10-18.

When investigating a surprising bill, list monitors and active crawls first. They spend without anyone asking.

## Dashboard controls to recommend

1. **Monthly pay-as-you-go limit** (billing settings). When the plan allotment runs out, pay-as-you-go charges the card $5 at a time. With the limit blank there is no cap; set it to `0` to turn pay-as-you-go off, so requests return HTTP 402 instead. The limit rounds down to whole $5 increments.
2. **Overage allowance.** Even with a limit, the plan lets a burst run past zero by 1,500 (Hobby), 30,000 (Standard), 150,000 (Growth), or 600,000 (Scale) credits while a top-up settles. Only a crawl `limit` stops an individual job.
3. **Per-key spend limits** (API keys page, "Set limit"). A credit cap per day, week, or month for one key, regardless of the team balance. Give agents, CI, and each integration its own capped key so one runaway loop cannot spend everything. A blocked request gets a 402.
4. **Plan credits expire monthly** (except annual Scale and Enterprise rollover). Bought top-up credits persist until the subscription is cancelled.

## Budgets inside a task

- Ask for, or set, a credit budget before multi-page work, and pass it to the guard: `--budget N`.
- Treat the user's approval as covering the stated worst case once. A retry, a second crawl, or a wider scope is a new spend.
- After the job, report `creditsUsed` from the responses and the new balance.

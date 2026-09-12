# maintainable-app

Installable passive skill for building self-healing applications with stronger edge-case coverage, safer background work, and observability that explains production behavior without creating noise.

## Install

```bash
npx skills add jpcaparas/skills --skill maintainable-app
```

## Includes

- `SKILL.md` as the canonical workflow
- `references/principles.md` for self-healing application defaults
- `references/jobs-and-queues.md` for jobs, queues, webhooks, and stuck work
- `references/distributed-systems.md` for retries, idempotency, outbox/inbox, sagas, and reconciliation
- `references/observability.md` for purposeful logging, metrics, tracing, alerts, and dashboards
- `references/review-rubric.md` for severity-first resilience reviews
- `references/gotchas.md` for common production traps
- `scripts/analyze_app_resilience.py` as a lightweight review prompt scanner

Use this when an agent is coding, reviewing, or planning an application feature that should keep running smoothly without frequent developer intervention.

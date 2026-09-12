# Staging observation

On 2026-06-18, the staging run completed in 42 seconds for 120 records. The p95 value was 310 ms, compared with 355 ms in the previous run. We observed an `idempotency key` on every request. This may indicate a useful change, but it does not establish production impact.

The operator wrote, “The queue settled after the second read.” No customer study or production test is included here.

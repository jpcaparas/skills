# Ledgerbird fixture

Ledgerbird receives payout requests, records immutable intent, and dispatches each accepted payout exactly once. Users and upstream systems may retry the same request.

The design separates deterministic domain policy, application orchestration, persistence, and external dispatch. Delivery failures remain pending for reconciliation rather than being silently treated as success.

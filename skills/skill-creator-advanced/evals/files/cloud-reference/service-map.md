# Cloud Reference Service Map

This fixture defines the complete scope for the evaluation. All services use the shared `references/identity.md` account and credential-selection rules.

| Goal | Service | Required depth |
|---|---|---|
| Run code | Function Forge | choice guide + invocation contract |
| Run code | Container Bay | choice guide + deployment contract |
| Run code | Batch Loom | choice guide only |
| Run code | Job Relay | choice guide only |
| Run code | Edge Spark | choice guide + runtime limits |
| Store data | Object Harbor | choice guide + API contract |
| Store data | Table Grove | choice guide + consistency notes |
| Store data | Queue Vault | choice guide only |
| Store data | Archive Shelf | choice guide only |
| Store data | Cache Spring | choice guide + expiry behavior |
| Connect systems | Event Bridge | choice guide + event contract |
| Connect systems | Message Ferry | choice guide + delivery behavior |
| Connect systems | Workflow Rail | choice guide + workflow contract |
| Connect systems | Gateway Port | choice guide only |
| Connect systems | Stream Canal | choice guide + continuation behavior |
| Secure workloads | Key Foundry | choice guide + rotation procedure |
| Secure workloads | Secret Locker | choice guide + access contract |
| Secure workloads | Policy Guard | choice guide only |
| Secure workloads | Audit Beacon | choice guide + evidence format |
| Secure workloads | Threat Lens | choice guide only |

The skill must route first by the four user goals. A service receives only the listed depth. Do not manufacture per-service setup, API, pattern, or gotcha files when the map asks for a choice guide only.

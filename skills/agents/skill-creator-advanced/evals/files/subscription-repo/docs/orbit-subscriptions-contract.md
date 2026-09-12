# Orbit Subscriptions API Contract

Contract version: `2026-06-30`

This file is the authoritative contract snapshot for the evaluation. Do not infer operations or fields not listed here.

## Access

- Staging base URL: `https://staging.subscriptions.orbit.example/v2`
- Production base URL: `https://subscriptions.orbit.example/v2`
- Requests use `Authorization: OrbitKey $ORBIT_STAGING_KEY` in staging.
- Evaluation may use staging only. Production mutations are not authorized.

## Promised operations

| User goal | Operation | Effect | Safe evaluation route |
|---|---|---|---|
| Create a checkout session | `POST /checkout-sessions` | Creates staging state | Contract parse plus a staging request with the fixture customer only |
| Change a subscription | `POST /subscriptions/{id}/change` | Mutates staging state | Documented staging dry run using `preview=true` |
| Verify a signed callback | `verifyCallback(rawBody, signature, secret)` | Local computation | Fixed signed fixture; no outbound call |
| Create a marketplace payout | `POST /marketplace/payouts` | Moves funds | Static contract validation only; no live request |

Checkout input requires `customer_id`, `plan_id`, and `return_uri`. Success returns `session_id`, `redirect_uri`, and `expires_at`.

Subscription changes require `plan_id` and accept `preview`. Preview success returns `effective_at`, `proration`, and `currency`; it does not mutate the subscription.

Signed callbacks use the raw request bytes and the `Orbit-Signature` value. Parsing or re-encoding the body before verification invalidates the signature.

Payout input requires `connected_account`, `amount_minor`, `currency`, and `idempotency_key`. A successful live payout would return `payout_id` and `state`, but no live payout is authorized for this evaluation.

## Failure and continuation rules

- `E_INVALID_INPUT` is terminal.
- `E_TEMPORARY` is retryable only when the response includes `retry_after_ms`; honor that value and cap attempts at three.
- `E_DUPLICATE_KEY` returns the original operation result and must not be retried with a new key.
- This contract exposes no pagination or webhook-registration operation.

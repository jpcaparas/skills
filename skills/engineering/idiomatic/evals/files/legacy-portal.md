# Ledgerbridge workspace evidence fixture

This is a synthetic, deliberately incomplete inspection packet, not a runnable application or a claim about a real repository. Treat the listed paths as evidence anchors in the hypothetical workspace. No credentials, network calls, application boot or live queries are available or approved. Files not described here have not been inspected. Do not substitute the skill-authoring repository for this application.

## Workspace and versions

- Revision label: `fixture-baseline-A`; worktree clean in this packet. Deployed revision is unknown.
- `apps/api/composer.json` requires `laravel/framework: ^10.0`; `composer.lock` resolves `10.48.22`. The installed vendor directory is absent.
- `apps/web/package.json` requires `next: ^14.2.0`; `pnpm-lock.yaml` resolves `14.2.18`. Dependencies are not installed in this packet.
- `packages/money/src/round.mjs` is a small functional JavaScript package with a documented signed-zero contract and passing historical unit results. No current results are supplied.
- `ops/worker.conf` starts the API queue worker; `ops/deploy.sh` updates web and API together but does not restart workers. Running versions and oldest queued payloads are unknown.
- `apps/api/app/Console/Commands/ImportAccounts.php` imports nightly vendor CSVs and writes `accounts.external_ref` without normalisation. The scheduler registration exists; its production schedule and load are unknown.
- `apps/api/tests/bootstrap.php` loads a shared `.env.testing` unless explicitly overridden. Its database target has not been verified. `composer test` invokes this bootstrap. Do not run it blindly.
- `apps/web/package.json` defines `test:unit` as `vitest run` and `build` as `next build`; build-time API calls have not been inspected. These are known script definitions, not safe/executed checks.
- `ops/support.md` records recurring uncertainty about which billing path handles a failed acknowledgement. It contains no time, incident-rate or cost baseline.

## API flows

`apps/api/routes/api.php` registers `POST /invoices/{invoice}/send` with tenant middleware and routes it to `InvoiceController::send`.

`apps/api/app/Http/Controllers/InvoiceController.php`:

1. Finds the invoice through the current tenant's relationship.
2. Validates input inline, formats the vendor request and calls a static vendor SDK.
3. Sends `external_ref` exactly as stored, including leading zeros and trailing spaces.
4. Receives HTTP 200 with either `{"accepted":true,"receipt":"R1"}` or `{"accepted":false,"reason":"later"}`.
5. Marks the invoice sent only when `accepted` is true; otherwise leaves it pending.
6. Enqueues `App\Jobs\SendInvoice` for a retry path. Duplicate delivery and timeout-after-acceptance behaviour are undocumented.

`apps/api/app/Jobs/SendInvoice.php` duplicates the response-body parsing with one difference: the `later` case is retried after a delay. Its fully qualified class name is stored in queued payloads. The number and age of those payloads are unknown.

`apps/api/tests/Feature/InvoiceTest.php` covers HTTP validation and tenant filtering but mocks the entire vendor SDK as accepted; it never exercises the real response parser or the job's retry path.

`apps/api/modules/Tax/Rules.php` is registered under the `Ledger\Tax` Composer PSR-4 namespace. Its non-default directory has a documented team owner and contract tests; no defect is reported. Moving it would not fix the billing ambiguity.

`apps/api/database/migrations/create_accounts.php` defines nullable `external_ref`, unique per tenant when non-null. No evidence establishes whether whitespace/case are significant to every producer and consumer.

## Web flows

`apps/web/pages/billing.tsx` uses Pages Router `getServerSideProps`, forwards the session to the API and must preserve tenant checks and the `/billing` URL. It renders a known error state when invoice submission remains pending.

`apps/web/app/(marketing)/page.tsx` is an App Router marketing page. No route collision is reported. Feature-local UI helpers are colocated under `app/(marketing)/_components/`.

`apps/web/lib/billing-client.ts` parses the API's existing pending/sent response shape. The mobile consumer lives outside this workspace and its release cadence is unknown.

No evidence suggests migrating the billing page to App Router is a prerequisite for isolating the API adapter. Authentication, accessibility and production caching behaviour have not been deeply inspected.

## Version-specific evidence available to the evaluator

- Laravel 10 directory-structure guidance: `https://laravel.com/docs/10.x/structure#introduction` permits custom class organisation when Composer can autoload it. This supports keeping `modules/Tax`, not a claim that the billing lifecycle is correct.
- Next.js 14 incremental App Router migration guide: `https://nextjs.org/docs/14/app/building-your-application/upgrading/app-router-migration` describes incremental coexistence. The presence of both routers alone is not a defect.

These are fixture source pointers. If the run cannot retrieve them, distinguish the supplied evidence from a freshly checked source. No current security/support assessment or upgrade approval is supplied.

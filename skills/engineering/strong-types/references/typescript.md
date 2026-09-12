# TypeScript Strong Typing

How to write TypeScript that is actually strongly typed instead of JavaScript with decorations.

## Table of Contents

- [Non-Negotiable Baseline](#non-negotiable-baseline)
- [Compiler Configuration](#compiler-configuration)
- [The any Ban](#the-any-ban)
- [unknown + Parsing at Boundaries](#unknown--parsing-at-boundaries)
- [Discriminated Unions and Exhaustiveness](#discriminated-unions-and-exhaustiveness)
- [The Fallback-Chain Fix](#the-fallback-chain-fix)
- [Nullability and Optionals](#nullability-and-optionals)
- [Branded Types](#branded-types)
- [satisfies, as const, and Inference Control](#satisfies-as-const-and-inference-control)
- [Suppression Policy](#suppression-policy)

## Non-Negotiable Baseline

1. `strict: true` plus `noUncheckedIndexedAccess` in `tsconfig.json`.
2. No `any` — written, inferred, or laundered through casts.
3. External data enters as `unknown` and is parsed (zod/valibot/manual guards) before use.
4. Closed sets of states are discriminated unions or `as const` literal unions with exhaustive switches.
5. `@ts-ignore` is banned; `@ts-expect-error` requires an adjacent reason.

## Compiler Configuration

Golden reference `tsconfig.json` (checking-related options):

```jsonc
{
  "compilerOptions": {
    "strict": true,                       // the umbrella: strictNullChecks, noImplicitAny, ...
    "noUncheckedIndexedAccess": true,     // arr[i] is T | undefined — because it is
    "exactOptionalPropertyTypes": true,   // missing !== undefined
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "noPropertyAccessFromIndexSignature": true,
    "useUnknownInCatchVariables": true    // implied by strict; catch (e: unknown)
  }
}
```

`strict: false`, or a missing `strict` key, makes every other rule in this file unenforceable. If the project cannot flip it globally, add a stricter `tsconfig` for new directories and expand its `include` over time.

## The any Ban

`any` is not a type; it is an instruction to stop checking. It also **infects**: every expression touching an `any` becomes `any`.

**Bad — one any poisons the file:**

```typescript
async function fetchUser(id: string): Promise<any> {
  const res = await fetch(`/api/users/${id}`);
  return res.json();
}

const user = await fetchUser("42");
user.naem.toUpperCase(); // typo compiles fine, explodes at runtime
```

**Golden reference:**

```typescript
const UserSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string().email(),
});
type User = z.infer<typeof UserSchema>;

async function fetchUser(id: string): Promise<User> {
  const res = await fetch(`/api/users/${id}`);
  return UserSchema.parse(await res.json()); // fails loudly, types truthfully
}
```

Common any-laundering patterns to reject:

```typescript
data as any as User          // double cast — pure fiction
JSON.parse(text) as Config   // parse returns any; the cast is unverified
(window as any).myGlobal     // declare the global properly instead
function cb(handler: Function) // Function erases parameters; type the signature
const items = []             // infers any[]; annotate: const items: Order[] = []
```

Enforce mechanically: ESLint `@typescript-eslint/no-explicit-any`, `no-unsafe-assignment`, `no-unsafe-member-access`, `no-unsafe-return` (all in the `strict-type-checked` preset).

## unknown + Parsing at Boundaries

`unknown` is the honest type for untrusted data: you can hold it but not touch it until you prove its shape.

```typescript
function handleWebhook(body: unknown): void {
  const event = WebhookEventSchema.parse(body); // typed or thrown
  switch (event.type) { ... }
}

try {
  ...
} catch (error: unknown) {
  if (error instanceof HttpError) { ... }       // narrow, don't assume
  throw error;
}
```

Boundaries that must parse: `fetch(...).json()`, `JSON.parse`, `process.env`, `localStorage`, query params, message-bus payloads, form data, anything typed by a hand-written `.d.ts` for a remote service you do not control.

For `process.env`, parse once at startup into a typed config object; never read `process.env.FOO` in business logic.

## Discriminated Unions and Exhaustiveness

Model states so the compiler tracks which fields exist in which state.

**Golden reference:**

```typescript
type FetchState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: AppError };

function render(state: FetchState<User[]>): JSX.Element {
  switch (state.status) {
    case "idle":    return <Idle />;
    case "loading": return <Spinner />;
    case "success": return <UserList users={state.data} />;   // data exists here only
    case "error":   return <ErrorBox error={state.error} />;  // error exists here only
    default: {
      const unreachable: never = state; // adding a state breaks this line at compile time
      throw new Error(`Unhandled: ${JSON.stringify(unreachable)}`);
    }
  }
}
```

The `never` assignment (or a shared `assertNever(x: never)` helper) is the exhaustiveness contract. Do not replace it with `default: return <Idle />` — that reintroduces silent state-handling gaps.

## The Fallback-Chain Fix

The canonical offense, TypeScript flavor:

```typescript
const image = location.preview ?? location.banner ?? location.thumbnail;
// image: Image | undefined — and the policy is duplicated at every use
```

**Golden reference — one typed owner:**

```typescript
interface Location {
  preview?: Image;
  banner?: Image;
  thumbnail?: Image;
}

/** Display image by preference: preview, banner, thumbnail. */
function primaryImage(location: Location): Image {
  const image = location.preview ?? location.banner ?? location.thumbnail;
  if (!image) throw new MissingImageError(location);
  return image;
}

// or, when absence is a designed state:
function primaryImageOrPlaceholder(location: Location): Image {
  return location.preview ?? location.banner ?? location.thumbnail ?? PLACEHOLDER_IMAGE;
}
```

Related smell — `||` for defaults. `||` treats `0`, `""`, and `false` as missing:

```typescript
const port = config.port || 3000;   // port 0 silently becomes 3000
const port = config.port ?? 3000;   // only null/undefined fall back
```

Use `??` for absence, and reserve `||` for genuinely boolean logic.

## Nullability and Optionals

- With `strictNullChecks`, `T | undefined` and `T | null` are real distinct types. Pick one convention for "absent" per codebase (usually `undefined` internally, `null` at JSON edges) and convert at the boundary.
- Ban the non-null assertion `!` in application code. Each `x!` is an unchecked cast:

```typescript
const el = document.getElementById("app")!;        // bad: hope
const el = document.getElementById("app");
if (!el) throw new Error("missing #app mount point"); // good: evidence
```

- `noUncheckedIndexedAccess` makes `users[0]` typed as `User | undefined`. That is the truth; handle it or use `.at(0)` with the same handling, rather than turning the flag off.
- Optional chaining is for reading, not for policy. `a?.b?.c ?? d` scattered around is the fallback chain again — extract an owner.

## Branded Types

Structural typing means any `string` fits any `string` parameter. Brand identifiers that must not mix:

```typescript
type UserId = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };

const UserId = (raw: string): UserId => {
  if (!/^u_[a-z0-9]+$/.test(raw)) throw new Error(`bad user id: ${raw}`);
  return raw as UserId; // the ONE sanctioned cast, adjacent to its evidence
};

function refund(orderId: OrderId, requestedBy: UserId): void { ... }
refund(userId, orderId); // compile error — argument swap caught
```

Use for IDs, validated strings (email, ISO dates), and unit-bearing numbers (cents vs dollars). zod's `.brand<"UserId">()` produces the same effect inside schemas.

## satisfies, as const, and Inference Control

`satisfies` checks a value against a type **without widening it** — use it instead of annotations that destroy literal information:

```typescript
const routes = {
  home: "/",
  user: "/users/:id",
} satisfies Record<string, `/${string}`>;

routes.user; // still the literal "/users/:id", but the shape was verified
```

`as const` freezes literals for union derivation:

```typescript
const STATUSES = ["pending", "paid", "failed"] as const;
type Status = (typeof STATUSES)[number]; // "pending" | "paid" | "failed"
```

Prefer deriving types from runtime sources of truth (schemas, const arrays) over maintaining parallel hand-written types that drift.

## Suppression Policy

- `@ts-ignore`: banned. It suppresses *whatever* error appears on the next line, forever.
- `@ts-expect-error`: allowed with a reason, because it errors when the underlying problem is fixed:

```typescript
// @ts-expect-error upstream types lack the `signal` option (lib v2.3); remove on upgrade
client.request(url, { signal });
```

- `eslint-disable @typescript-eslint/no-explicit-any`: same rule — single line, with a reason, never file-wide.
- Vendored or generated `.d.ts` files are the only acceptable home for broad suppressions, and they stay out of application directories.

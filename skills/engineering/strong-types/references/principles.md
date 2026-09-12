# Strong Typing Principles

Universal, language-independent rules for eliminating type ambiguity, with golden references. Language-specific mechanics live in the sibling reference files.

## Table of Contents

- [What "Strongly Typed" Means Here](#what-strongly-typed-means-here)
- [Principle 1: Signatures Are Contracts](#principle-1-signatures-are-contracts)
- [Principle 2: Parse, Don't Validate](#principle-2-parse-dont-validate)
- [Principle 3: Make Illegal States Unrepresentable](#principle-3-make-illegal-states-unrepresentable)
- [Principle 4: Nullability Has One Owner](#principle-4-nullability-has-one-owner)
- [Principle 5: Name Your Data Shapes](#principle-5-name-your-data-shapes)
- [Principle 6: Kill Primitive Obsession](#principle-6-kill-primitive-obsession)
- [Principle 7: Narrow, Don't Cast](#principle-7-narrow-dont-cast)
- [Principle 8: Generics Preserve Knowledge](#principle-8-generics-preserve-knowledge)
- [Principle 9: Exhaustiveness Is a Compiler Job](#principle-9-exhaustiveness-is-a-compiler-job)
- [Principle 10: Strictness Ratchets Up](#principle-10-strictness-ratchets-up)

## What "Strongly Typed" Means Here

A codebase is strongly typed when, for any expression, a reader can state its exact type without executing the code, and the compiler or checker would agree. This is a property of how the code is written, not just which language it is written in. TypeScript full of `any` is weakly typed; PHP with `strict_types`, typed properties, and PHPStan level 9 is strongly typed.

Three failure modes produce almost all type ambiguity:

1. **Escape hatches** — `any`, `mixed`, `interface{}`, `Object`, bare `dict`/`array`. The type system is present but bypassed.
2. **Unowned nullability** — values that might be null, resolved ad hoc at every call site with `??`/`||` chains instead of once at a defined owner.
3. **Anonymous shapes** — data whose structure exists only in the author's head: associative arrays, raw dicts, untyped JSON blobs.

Every principle below attacks one of these.

## Principle 1: Signatures Are Contracts

The signature is the unit of trust. A fully typed signature lets every caller and every reader stop reading at the boundary.

**Bad — the reader must read the body to learn anything:**

```php
function process($order, $options = [])
```

**Golden reference:**

```php
/**
 * @param list<OrderLine> $lines
 */
function process(Order $order, ProcessingOptions $options, array $lines): Receipt
```

Rules of thumb:

- Return types are mandatory, including `void`/`None`/`Unit`. An omitted return type is a question mark on every call site.
- Optional parameters get real defaults with real types, never `= []` or `= None` standing in for "figure it out later".
- If a parameter can be two unrelated things, that is two functions or a union type with narrowing — not one loose parameter.

## Principle 2: Parse, Don't Validate

Validation checks a shape and throws away the knowledge. Parsing checks a shape and **records the knowledge in the type system**. Always prefer the second.

**Bad — validation; the type stays `array`/`dict` forever:**

```python
def handle(payload: dict) -> None:
    if "email" not in payload or "@" not in payload["email"]:
        raise ValueError("bad email")
    send_welcome(payload["email"])  # still just a dict key access
```

**Golden reference — parse once at the edge, typed forever after:**

```python
@dataclass(frozen=True)
class SignupRequest:
    email: EmailAddress
    plan: Plan

    @classmethod
    def parse(cls, payload: Mapping[str, object]) -> "SignupRequest":
        return cls(
            email=EmailAddress.parse(payload.get("email")),
            plan=Plan(str(payload.get("plan", "free"))),
        )

def handle(raw: Mapping[str, object]) -> None:
    request = SignupRequest.parse(raw)   # the only place raw shapes exist
    send_welcome(request.email)          # typed from here on
```

Boundaries where parsing is mandatory: HTTP request bodies, queue messages, webhook payloads, environment variables, CLI arguments, third-party API responses, database rows in schemaless columns, file contents.

## Principle 3: Make Illegal States Unrepresentable

Design types so invalid combinations cannot be constructed, rather than checking for them at runtime.

**Bad — four fields, nine representable states, three legal:**

```typescript
interface Payment {
  status: string;            // "pending" | "paid" | "failed"... probably
  paidAt: Date | null;       // set iff paid?
  failureReason: string | null; // set iff failed?
}
```

**Golden reference — three states, three representable states:**

```typescript
type Payment =
  | { status: "pending" }
  | { status: "paid"; paidAt: Date }
  | { status: "failed"; failureReason: FailureReason };
```

The same move exists everywhere: discriminated unions (TypeScript), sealed interfaces + records (Java), sealed classes (Kotlin), enums with associated values (Swift, Rust), enums + value objects (PHP), tagged `Literal` unions (Python).

Corollary: two boolean parameters that interact (`isDraft`, `isPublished`) are a state machine in disguise. Replace them with one enum.

## Principle 4: Nullability Has One Owner

Every nullable value needs exactly one place that decides what happens when it is null. When call sites resolve nullability themselves, you get the canonical offense:

```php
$image = $location->preview ?? $location->banner ?? $location->thumbnail;
```

Problems: the fallback policy is duplicated at every call site, can drift between them, the resulting type is still nullable, and nothing documents *why* three properties compete.

**Golden reference — one owner, one policy, one type:**

```php
final class Location
{
    /** Preferred display image: preview, else banner, else thumbnail. */
    public function primaryImage(): Image
    {
        return $this->preview ?? $this->banner ?? $this->thumbnail
            ?? throw new MissingImageException($this->id);
    }

    public function primaryImageOrPlaceholder(): Image
    {
        return $this->preview ?? $this->banner ?? $this->thumbnail
            ?? Image::placeholder();
    }
}
```

Choosing the owner:

| Situation | Owner |
|---|---|
| Domain object with competing optional fields | A named accessor method with a non-nullable return |
| Config value with a default | The config loader, applying the default at load time |
| Database column with a sensible default | The schema (`DEFAULT`), not application code |
| Optional relation | A method that returns the relation or a Null Object / throws |
| Truly optional domain state ("no discount applied") | Keep it nullable/Optional — and name it so (`appliedDiscount`) |

The last row matters: nullability is fine when absence is a real domain state. The rule is that it gets resolved **once**, by an owner, not repeatedly by callers.

## Principle 5: Name Your Data Shapes

Any data crossing a function, module, or process boundary gets a named type: DTO, record, dataclass, struct, TypedDict.

**Bad — the shape lives in the author's memory:**

```php
return [
    'id' => $user->id,
    'name' => $user->name,
    'roles' => $roleNames,   // list of... strings? Role objects?
];
```

**Golden reference:**

```php
final readonly class UserSummary
{
    /** @param list<string> $roles */
    public function __construct(
        public int $id,
        public string $name,
        public array $roles,
    ) {}
}
```

Anonymous shapes are tolerable only for private, short-lived, single-function plumbing — and even there a local type is usually cheaper than the ambiguity.

## Principle 6: Kill Primitive Obsession

A `string` that must be an email, a `float` that must be money, an `int` that must be a user ID — these are domain types wearing primitive costumes. Passing them as primitives lets a user ID slot into an order ID parameter without complaint.

**Golden reference (any language):**

```kotlin
@JvmInline value class UserId(val value: Long)
@JvmInline value class OrderId(val value: Long)

fun refund(orderId: OrderId, requestedBy: UserId): Refund
```

Now `refund(userId, orderId)` argument swaps are compile errors. Equivalents: `readonly` value objects (PHP), `NewType` (Python), branded types (TypeScript), newtype structs (Rust, Go, Swift).

Apply this to identifiers, money, quantities with units, and validated strings (email, URL, slug). Do not apply it to every string in sight; the target is values with rules or values that can be confused for each other.

## Principle 7: Narrow, Don't Cast

A cast tells the checker "trust me". Narrowing shows the checker evidence. Prefer evidence.

**Bad:**

```typescript
const user = data as User;            // trust me
```

**Golden reference — narrowing the checker can verify:**

```typescript
function isUser(value: unknown): value is User {
  return typeof value === "object" && value !== null
    && "id" in value && typeof (value as { id: unknown }).id === "number";
}

if (!isUser(data)) throw new InvalidPayloadError();
data.id; // typed, and earned
```

Narrowing tools by language: type guards and discriminated-union switches (TypeScript), `instanceof`/`match` (PHP 8, Python), pattern matching (C#, Java 21, Kotlin `when`, Swift, Rust), `isinstance` + `TypeGuard` (Python), schema parsers (zod, pydantic) that return typed values.

A cast is acceptable only when the invariant is real but inexpressible, and then it must be adjacent to the check that establishes it, with a comment naming the invariant.

## Principle 8: Generics Preserve Knowledge

Containers and helpers that erase types force every caller to cast, multiplying ambiguity outward.

**Bad:**

```java
List<Object> findAll(String table);           // caller must cast every element
```

**Golden reference:**

```java
<T> List<T> findAll(Class<T> entity);         // knowledge flows through
Repository<Order> orders;                     // or parameterize the type itself
```

In gradually typed languages, generics live in annotations and are enforced by the analyzer: `@return Collection<int, Order>` (PHP + PHPStan), `list[Order]` (Python), `Array<Order>` (TypeScript). Write them anyway — the checker reads them even when the runtime does not.

## Principle 9: Exhaustiveness Is a Compiler Job

Every branch over a closed set of states must be checked by the compiler so that adding a state breaks the build, not production.

**Golden reference (TypeScript pattern; equivalents exist everywhere):**

```typescript
function label(status: PaymentStatus): string {
  switch (status) {
    case "pending": return "Awaiting payment";
    case "paid": return "Paid";
    case "failed": return "Failed";
    default: {
      const unreachable: never = status;  // compile error if a case is missed
      throw new Error(`Unhandled status: ${unreachable}`);
    }
  }
}
```

Equivalents: `match` without wildcard arm (Rust), exhaustive `when` on sealed types (Kotlin), `switch` on sealed interfaces (Java 21), exhaustive `switch` on enums (Swift, C# with warnings-as-errors), `match` + `assert_never` (Python), `match (true)` with enum + PHPStan (PHP).

Never add a `default: return somethingSafe` arm to a closed switch — it converts future compile errors back into silent runtime bugs.

## Principle 10: Strictness Ratchets Up

Checker strictness only moves in one direction. The practical protocol:

1. New code meets the strictest level the toolchain supports (`strict: true`, PHPStan level 9/10, mypy `--strict`).
2. Legacy code gets a generated baseline (PHPStan baseline, mypy per-module overrides, tsc `include` growth) so existing debt is frozen, not blessed.
3. Suppressions are targeted (specific error code + reason), never blanket file- or rule-wide.
4. The baseline shrinks over time; CI fails if it grows.

Turning a rule off because it is noisy on old code is how strongly typed projects rot. Freeze the noise instead.

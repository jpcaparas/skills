# PHP Strong Typing

How to write PHP where every expression has one knowable type. PHP is gradually typed with weak coercion by default; this file turns everything strict.

## Table of Contents

- [Non-Negotiable Baseline](#non-negotiable-baseline)
- [strict_types Everywhere](#strict_types-everywhere)
- [Typed Signatures and Properties](#typed-signatures-and-properties)
- [The Fallback-Chain Fix](#the-fallback-chain-fix)
- [Enums Over Magic Strings](#enums-over-magic-strings)
- [DTOs Over Associative Arrays](#dtos-over-associative-arrays)
- [Generics via PHPDoc + Static Analysis](#generics-via-phpdoc--static-analysis)
- [Laravel / Eloquent Specifics](#laravel--eloquent-specifics)
- [Narrowing and Match](#narrowing-and-match)
- [Static Analysis Configuration](#static-analysis-configuration)

## Non-Negotiable Baseline

Every new PHP file:

1. `declare(strict_types=1);` as the first statement.
2. Every parameter, return, and property typed. `mixed` requires a justification comment.
3. Classes holding data are `final` and use `readonly` promoted properties unless mutation is a designed feature.
4. Closed sets of values are `enum`s.
5. PHPStan (level 9+) or Psalm runs green on the file.

## strict_types Everywhere

Without it, PHP silently coerces: `strlen(42)` works, `function f(int $x)` accepts `"7"`. With it, wrong types throw `TypeError` at the call boundary — exactly where the bug is.

```php
<?php

declare(strict_types=1);
```

The declaration is per-file and applies to calls made *from* that file. That is why every file needs it, not just the library code. Enforce with a CI grep or PHPStan's `declareStrictTypes` rule (phpstan-strict-rules).

## Typed Signatures and Properties

**Bad:**

```php
class ReportService
{
    private $client;                       // type unknown
    public $cache = [];                    // public mutable untyped state

    public function generate($user, $from = null, $to = null)
    {
        // reader must reverse-engineer everything
    }
}
```

**Golden reference:**

```php
final class ReportService
{
    /** @var array<string, Report> */
    private array $cache = [];

    public function __construct(
        private readonly MetricsClient $client,
    ) {}

    public function generate(
        User $user,
        ?DateTimeImmutable $from = null,
        ?DateTimeImmutable $to = null,
    ): Report {
        // ...
    }
}
```

Details that matter:

- `?Type` documents nullability; an untyped parameter hides it.
- Union types are legal and honest: `int|string $id` beats an untyped `$id` — but a dedicated `Id` value object beats both.
- Never use `array` alone across a boundary; pair it with a PHPDoc shape (`@param list<OrderLine> $lines`) or replace it with a DTO/collection.
- `mixed` is a deliberate statement that anything goes. It is almost always wrong outside of serializer internals and generic infrastructure.

## The Fallback-Chain Fix

The canonical offense:

```php
$image = $location->preview ?? $location->banner ?? $location->thumbnail;
```

Step 1 — find out why each property is nullable. Usually: three nullable columns where the domain concept is "the location's display image with a preference order".

Step 2 — give the policy an owner with a non-nullable return:

```php
final class Location extends Model
{
    /**
     * Display image, by preference: preview, banner, thumbnail.
     *
     * @throws MissingImageException when the location has no image at all
     */
    public function primaryImage(): Image
    {
        return $this->preview ?? $this->banner ?? $this->thumbnail
            ?? throw new MissingImageException($this->getKey());
    }
}
```

Step 3 — pick the all-null policy explicitly. Three honest options:

```php
public function primaryImage(): Image        // throw: absence is a bug
public function primaryImageOrNull(): ?Image // nullable: absence is a real state, resolved by ONE caller-facing name
public function primaryImageOrDefault(): Image // Null Object: absence has a safe default
{
    return $this->preview ?? $this->banner ?? $this->thumbnail ?? Image::placeholder();
}
```

Step 4 — replace every call-site chain with the named method. The `??` chain now exists in exactly one place, typed and documented.

If the underlying columns are untyped model magic, also fix the property types (see Laravel section).

## Enums Over Magic Strings

**Bad:**

```php
if ($order->status === 'shipped' || $order->status === 'delivered') { ... }
```

**Golden reference:**

```php
enum OrderStatus: string
{
    case Pending = 'pending';
    case Shipped = 'shipped';
    case Delivered = 'delivered';
    case Cancelled = 'cancelled';

    public function isFulfilled(): bool
    {
        return match ($this) {
            self::Shipped, self::Delivered => true,
            self::Pending, self::Cancelled => false,
        };
    }
}

if ($order->status->isFulfilled()) { ... }
```

The `match` without a `default` arm is the exhaustiveness guarantee: adding a case makes PHPStan (and runtime `UnhandledMatchError`) flag every incomplete match. Never add `default` to a match over an enum you own.

Backed enums parse at boundaries: `OrderStatus::from($row['status'])` throws on unknown values; `tryFrom` returns null for a designed fallback.

## DTOs Over Associative Arrays

**Bad — the shape is folklore:**

```php
function summarize(array $invoice): array
{
    return [
        'total' => $invoice['amount'] * (1 + $invoice['tax_rate']),
        'label' => $invoice['customer']['name'] ?? 'Unknown',
    ];
}
```

**Golden reference:**

```php
final readonly class InvoiceSummary
{
    public function __construct(
        public Money $total,
        public string $label,
    ) {}
}

function summarize(Invoice $invoice): InvoiceSummary
{
    return new InvoiceSummary(
        total: $invoice->amount->withTax($invoice->taxRate),
        label: $invoice->customer?->name ?? 'Unknown',
    );
}
```

Where arrays are unavoidable (framework config, JSON edges), constrain them with PHPStan array shapes:

```php
/**
 * @param array{amount: int, tax_rate: float, customer?: array{name: string}} $payload
 */
public static function fromPayload(array $payload): self
```

Array shapes are the parse boundary; DTOs are what travels inward.

## Generics via PHPDoc + Static Analysis

The runtime erases generics, but PHPStan and Psalm enforce them.

```php
/**
 * @template T of object
 */
interface Repository
{
    /** @return T|null */
    public function find(int $id): ?object;

    /** @return list<T> */
    public function all(): array;
}

/**
 * @implements Repository<Order>
 */
final class OrderRepository implements Repository { ... }
```

Collection annotations to use routinely:

- `list<Order>` — sequential array of Orders
- `array<string, Order>` — string-keyed map
- `non-empty-list<Order>`, `non-empty-string`, `positive-int` — refined types that delete whole classes of checks
- `Collection<int, Order>` — Laravel/Doctrine collections

An unparameterized `array` or `Collection` return type forces every caller to guess. Treat it like `mixed`.

## Laravel / Eloquent Specifics

Eloquent models are `mixed` factories by default: `$model->anything` type-checks. Contain the magic:

1. **Casts make attribute types real:**

```php
protected function casts(): array
{
    return [
        'status' => OrderStatus::class,
        'paid_at' => 'immutable_datetime',
        'meta' => AsArrayObject::class,
    ];
}
```

2. **`@property` annotations teach the analyzer the columns** (generate with `barryvdh/laravel-ide-helper` or write by hand):

```php
/**
 * @property int $id
 * @property ?Image $preview
 * @property ?Image $banner
 * @property ?Image $thumbnail
 * @property OrderStatus $status
 */
final class Location extends Model
```

3. **Larastan** (`phpstan/phpstan` + `larastan/larastan`) understands relations, builders, and collections — use it, and parameterize relations: `@return HasMany<Image, $this>`.

4. Request input is untyped; parse it. Form Requests + a `toDto(): CreateLocationData` method keep controllers free of raw `array` access.

## Narrowing and Match

Prefer checks the analyzer can follow over casts and assumptions:

```php
// instanceof narrows
if ($event instanceof OrderShipped) {
    $event->trackingNumber; // typed
}

// match on enums narrows and enforces exhaustiveness
$label = match ($status) {
    OrderStatus::Pending => 'Waiting',
    OrderStatus::Shipped, OrderStatus::Delivered => 'On the way or done',
    OrderStatus::Cancelled => 'Cancelled',
};

// assertions for invariants the checker cannot see (use sparingly, adjacent to evidence)
assert($user !== null); // only after logic that guarantees it
```

Avoid: `(array)`, `(object)` casts to silence errors; `@phpstan-ignore-next-line` without an error identifier and reason; `->getAttribute()` string access when a typed accessor exists.

## Static Analysis Configuration

Golden reference `phpstan.neon` for new projects:

```neon
includes:
    - vendor/phpstan/phpstan-strict-rules/rules.neon

parameters:
    level: 9              # 10 adds full mixed-tracking; adopt when ready
    paths: [app, src, tests]
    checkMissingCallableSignature: true
    treatPhpDocTypesAsCertain: true
```

For legacy adoption: generate a baseline (`phpstan analyse --generate-baseline`), commit it, fail CI if it grows, and delete entries as files are touched. Never lower the level to make old code pass.

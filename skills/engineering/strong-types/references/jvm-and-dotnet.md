# C#, Java, and Kotlin Strong Typing

Statically typed languages can still harbor ambiguity: nulls outside the type system, stringly typed state, erased generics, and cast-driven design. This file closes those gaps.

## Table of Contents

- [C#](#c)
- [Java](#java)
- [Kotlin](#kotlin)
- [Shared Golden References](#shared-golden-references)

## C#

### Baseline

1. `<Nullable>enable</Nullable>` in every project file, warnings as errors: `<WarningsAsErrors>nullable</WarningsAsErrors>`.
2. No `object` parameters/returns in application code; no `dynamic` outside genuine interop.
3. Records for data, exhaustive `switch` expressions for closed hierarchies.
4. Null-forgiving `!` treated like a cast: evidence adjacent, comment attached.

### Nullable Reference Types

**Bad — pre-nullable habits:**

```csharp
public string GetDisplayName(User user)
{
    return user.Nickname ?? user.FullName ?? user.Email; // still returns null sometimes
}
```

With `#nullable enable`, encode truth in the signature and give the fallback an owner:

```csharp
public sealed record User(string Email, string? Nickname, string? FullName)
{
    /// Display name by preference: nickname, full name, email.
    public string DisplayName => Nickname ?? FullName ?? Email; // Email is non-null: chain is total
}
```

The chain is acceptable *here* because it terminates in a non-nullable property and lives in one named member — that is the difference between a policy and scattered guessing.

- `!` (null-forgiving) is a promise the compiler cannot check. Prefer restructuring; when unavoidable, keep the guaranteeing logic adjacent and commented.
- `ArgumentNullException.ThrowIfNull(arg)` at public API edges guards against callers compiled without nullable context.

### Modeling State

```csharp
public abstract record Payment
{
    public sealed record Pending : Payment;
    public sealed record Paid(DateTimeOffset PaidAt) : Payment;
    public sealed record Failed(FailureReason Reason) : Payment;
    private Payment() { }
}

public static string Label(Payment payment) => payment switch
{
    Payment.Pending => "Awaiting payment",
    Payment.Paid p => $"Paid {p.PaidAt:d}",
    Payment.Failed f => f.Reason.Describe(),
    _ => throw new UnreachableException(), // keep; compiler warns on missing cases (CS8509 as error)
};
```

Turn on `CS8509` (non-exhaustive switch expression) as an error. Avoid `enum` + parallel nullable fields for stateful data — that is the illegal-states trap from `principles.md`.

## Java

### Baseline

1. Records for data carriers; no getter/setter bean mutability by default.
2. Sealed interfaces + pattern-matching `switch` (Java 21+) for closed hierarchies, no `default` arm on sealed switches.
3. `Optional<T>` for optional returns; never `null` collections (return empty).
4. No raw generic types (`List` without `<T>`), no unchecked casts without a contained, commented `@SuppressWarnings("unchecked")`.
5. JSpecify/`@Nullable` annotations + NullAway or Error Prone in the build for null tracking.

### Golden Reference — Sealed States

```java
public sealed interface Payment permits Pending, Paid, Failed {}
public record Pending() implements Payment {}
public record Paid(Instant paidAt) implements Payment {}
public record Failed(FailureReason reason) implements Payment {}

static String label(Payment payment) {
    return switch (payment) {           // no default: adding a state breaks compilation
        case Pending p -> "Awaiting payment";
        case Paid p -> "Paid " + p.paidAt();
        case Failed f -> f.reason().describe();
    };
}
```

### Nulls and Optionals

```java
// Bad: null-riddled getter chain
String city = user.getAddress().getCity(); // NPE roulette

// Golden: Optional at the boundary, resolved once
public Optional<Address> address() { ... }

String city = user.address()
    .map(Address::city)
    .orElseThrow(() -> new MissingAddressException(user.id()));
```

Rules: `Optional` is a return type, not a field or parameter type; `Optional.get()` without an `isPresent` proof is banned (use `orElseThrow` with a real exception); annotate nullability (`@Nullable`, JSpecify `@NullMarked` packages) so tooling enforces the rest.

### Generics

- Raw types (`List list`) silently erase checking for every element — always parameterize.
- `List<Object>` in an API forces caller casts; use a type parameter (`<T> List<T> loadAll(Class<T> type)`).
- Unchecked casts, when truly required (reflection, serialization), are isolated in one helper with `@SuppressWarnings("unchecked")` on the smallest possible scope and a comment naming the invariant.

## Kotlin

### Baseline

1. Nullability is designed, not defaulted: `?` only where absence is a domain state.
2. `!!` is banned in production code paths.
3. Sealed classes/interfaces + exhaustive `when` for closed sets; no `else` on sealed `when`.
4. Data classes / value classes for shapes and identifiers; no `Map<String, Any>` payloads.
5. Platform types from Java interop are annotated away at the boundary.

### The !! Ban

```kotlin
// Bad: hope-driven development
val image = location.preview!!

// Golden: resolve once with a policy
val image = location.primaryImage()   // non-null return, throws MissingImageException

// or when the caller owns the decision:
val image = location.primaryImageOrNull() ?: Placeholder.image
```

`?:` (elvis) is Kotlin's `??`. One elvis applying a documented default is fine; chains of them on raw properties are the canonical offense — extract a named member.

### Sealed + Exhaustive when

```kotlin
sealed interface Payment {
    data object Pending : Payment
    data class Paid(val paidAt: Instant) : Payment
    data class Failed(val reason: FailureReason) : Payment
}

fun label(payment: Payment): String = when (payment) { // expression form forces exhaustiveness
    is Payment.Pending -> "Awaiting payment"
    is Payment.Paid -> "Paid ${payment.paidAt}"
    is Payment.Failed -> payment.reason.describe()
}
```

Use `when` as an expression (or return it) so the compiler enforces exhaustiveness; a statement `when` with a missing branch only warns.

### Value Classes and Interop

```kotlin
@JvmInline value class UserId(val value: Long)
@JvmInline value class Cents(val value: Long)

fun refund(orderId: OrderId, amount: Cents, requestedBy: UserId): Refund
```

Java interop returns platform types (`String!`) that bypass null checking. At every Java boundary, immediately assign to an explicit Kotlin type (`val name: String = javaUser.name` — crashing early — or `String?` — handling absence), so platform ambiguity does not travel.

## Shared Golden References

### Parse at the Boundary

```csharp
// C#: System.Text.Json into records with required properties
public sealed record CreateOrderRequest
{
    public required string Sku { get; init; }
    public required int Quantity { get; init; }
}
var request = JsonSerializer.Deserialize<CreateOrderRequest>(body)
    ?? throw new BadRequestException("empty body");
```

```kotlin
// Kotlin: kotlinx.serialization fails loudly on shape mismatch
@Serializable
data class CreateOrderRequest(val sku: String, val quantity: Int)
val request = Json.decodeFromString<CreateOrderRequest>(body)
```

### Identifier Confusion

All three languages support zero-or-low-cost distinct identifier types: C# `readonly record struct UserId(Guid Value)`, Java `record UserId(UUID value)`, Kotlin `@JvmInline value class`. Use them for any pair of IDs that could plausibly be swapped in an argument list.

### Suppression Policy

- C#: `#pragma warning disable` only with the specific code, a reason, and a matching restore a few lines later.
- Java: `@SuppressWarnings` on the narrowest element, never class-wide, with a comment.
- Kotlin: `@Suppress` follows the same rule; `!!` is not a suppression mechanism, it is a landmine.

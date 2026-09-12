# Go, Rust, and Swift Strong Typing

These languages are statically typed, but each has an idiomatic escape hatch culture to police: `interface{}`/`any` in Go, `unwrap()` in Rust, force-unwraps in Swift.

## Table of Contents

- [Go](#go)
- [Rust](#rust)
- [Swift](#swift)

## Go

### Baseline

1. `interface{}` / `any` only at genuine serialization or plugin boundaries, parsed immediately.
2. Generics (Go 1.18+) instead of `any` for type-preserving helpers.
3. Named struct types for boundary data; no `map[string]interface{}` traveling through business logic.
4. Sentinel or typed errors checked with `errors.Is`/`errors.As`, not string matching.
5. Type assertions always use the two-value form.

### any Is Not a Type Strategy

**Bad:**

```go
func Process(payload map[string]interface{}) (interface{}, error) {
    name := payload["name"].(string) // panics on shape drift
    ...
}
```

**Golden reference — decode into a named struct at the edge:**

```go
type CreateUserRequest struct {
    Name  string `json:"name"`
    Email string `json:"email"`
}

func Process(r io.Reader) (User, error) {
    var req CreateUserRequest
    dec := json.NewDecoder(r)
    dec.DisallowUnknownFields()
    if err := dec.Decode(&req); err != nil {
        return User{}, fmt.Errorf("decode create-user request: %w", err)
    }
    return newUser(req)
}
```

Generic helpers preserve types where `any` would erase them:

```go
func First[T any](items []T, want func(T) bool) (T, bool) {
    for _, item := range items {
        if want(item) {
            return item, true
        }
    }
    var zero T
    return zero, false
}
```

### Assertions and Narrowing

```go
// Bad: single-value assertion panics
s := value.(string)

// Golden: two-value form, handled
s, ok := value.(string)
if !ok {
    return fmt.Errorf("expected string, got %T", value)
}

// Golden: type switch for closed sets of concrete types
switch v := event.(type) {
case OrderShipped:
    handleShipped(v)
case OrderCancelled:
    handleCancelled(v)
default:
    return fmt.Errorf("unhandled event type %T", event)
}
```

Go has no sealed types; the compiler cannot enforce exhaustiveness. Compensate with a `default` that returns an error (never silently ignores), and consider `exhaustive` linters for enum-style `iota` constants.

### Identifier Types

```go
type UserID int64
type OrderID int64

func Refund(orderID OrderID, requestedBy UserID) error
```

Defined types cost nothing and make `Refund(userID, orderID)` a compile error. Same for units: `type Cents int64`, `time.Duration` over bare `int64` milliseconds.

## Rust

Rust's compiler enforces most of this skill already. The remaining discipline is about not opting out.

### Baseline

1. `unwrap()`/`expect()` banned in production paths; `?` and typed errors instead. `expect()` with an invariant message is acceptable in genuinely unreachable arms and tests.
2. Newtypes for identifiers and units; enums over booleans and strings.
3. `match` without `_` arm over enums you own.
4. `#[deny(warnings)]`-adjacent hygiene: `#![warn(clippy::unwrap_used, clippy::expect_used)]` in application crates.

### Golden References

```rust
// Newtypes: argument swaps become compile errors
struct UserId(u64);
struct OrderId(u64);
fn refund(order: OrderId, requested_by: UserId) -> Result<Refund, RefundError> { ... }

// Enums with data: illegal states unrepresentable
enum Payment {
    Pending,
    Paid { paid_at: DateTime<Utc> },
    Failed { reason: FailureReason },
}

fn label(payment: &Payment) -> String {
    match payment {                       // no `_` arm: new variants break the build
        Payment::Pending => "Awaiting payment".into(),
        Payment::Paid { paid_at } => format!("Paid {paid_at}"),
        Payment::Failed { reason } => reason.describe(),
    }
}

// Parse, don't validate: TryFrom at boundaries
impl TryFrom<&str> for EmailAddress {
    type Error = EmailError;
    fn try_from(raw: &str) -> Result<Self, Self::Error> {
        if raw.contains('@') { Ok(EmailAddress(raw.to_owned())) } else { Err(EmailError::Invalid) }
    }
}
```

Anti-patterns to flag in review: `unwrap()` chains on `Option`/`Result` in request paths; stringly typed errors (`Result<T, String>`); `as` numeric casts where `TryFrom` should guard range; boolean function parameters (`fn render(compact: bool, dark: bool)`) instead of an options enum/struct.

## Swift

### Baseline

1. Force-unwrap `!` and implicitly unwrapped optionals (`String!`) banned outside IBOutlets and tests.
2. `guard let` / `if let` narrowing at the top of scope; optionals resolved once.
3. Enums with associated values for state; `switch` without `default` over enums you own.
4. `Codable` structs for boundary data; no `[String: Any]` traveling inward.

### Optional Discipline

```swift
// Bad: hope
let image = location.preview!

// Bad: the canonical offense, Swift flavor
let image = location.preview ?? location.banner ?? location.thumbnail // Image? and duplicated policy

// Golden: one owner with an explicit policy
extension Location {
    /// Display image by preference: preview, banner, thumbnail.
    var primaryImage: Image {
        get throws {
            guard let image = preview ?? banner ?? thumbnail else {
                throw LocationError.missingImage(id: id)
            }
            return image
        }
    }
}
```

`guard let` keeps the unwrapped value flowing for the rest of the scope:

```swift
guard let user = session.currentUser else {
    throw AuthError.notSignedIn
}
// user: User (non-optional) from here on
```

### Enums and Exhaustiveness

```swift
enum Payment {
    case pending
    case paid(paidAt: Date)
    case failed(reason: FailureReason)
}

func label(_ payment: Payment) -> String {
    switch payment {                    // no default: new cases break the build
    case .pending: return "Awaiting payment"
    case .paid(let paidAt): return "Paid \(paidAt)"
    case .failed(let reason): return reason.describe()
    }
}
```

For enums from frameworks that may grow (`@unknown default`), handle the unknown case explicitly — that is a designed escape, unlike a blanket `default`.

### Boundary Parsing

```swift
struct CreateOrderRequest: Codable {
    let sku: String
    let quantity: Int
}

let request = try JSONDecoder().decode(CreateOrderRequest.self, from: body) // fails loudly, typed after
```

`[String: Any]` dictionaries from legacy APIs get converted to typed structs at the first opportunity; every `as?` chain deep in business logic is a boundary parse that never happened.

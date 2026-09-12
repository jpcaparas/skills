# Python Strong Typing

How to write Python where the type checker, not the traceback, finds type bugs.

## Table of Contents

- [Non-Negotiable Baseline](#non-negotiable-baseline)
- [Checker Configuration](#checker-configuration)
- [Signatures: Annotate Everything](#signatures-annotate-everything)
- [The Any Ban](#the-any-ban)
- [Dataclasses, TypedDict, and Pydantic Over Raw Dicts](#dataclasses-typeddict-and-pydantic-over-raw-dicts)
- [Enums and Literal Over Magic Strings](#enums-and-literal-over-magic-strings)
- [The Fallback-Chain Fix](#the-fallback-chain-fix)
- [Optional Discipline](#optional-discipline)
- [Protocols and Generics](#protocols-and-generics)
- [Narrowing: TypeGuard, isinstance, assert_never](#narrowing-typeguard-isinstance-assert_never)
- [Suppression Policy](#suppression-policy)

## Non-Negotiable Baseline

1. Every function signature fully annotated, including `-> None`.
2. mypy `--strict` or pyright `strict` mode green on new code.
3. No `Any` in application code — explicit or inferred through untyped calls.
4. Boundary data parsed into dataclasses/pydantic models/TypedDicts; raw `dict[str, Any]` does not travel.
5. Closed sets are `Enum` or `Literal` with exhaustive `match` + `assert_never`.

## Checker Configuration

Golden reference `pyproject.toml` (mypy):

```toml
[tool.mypy]
strict = true                       # umbrella: disallow_untyped_defs, no_implicit_optional, ...
warn_unreachable = true
disallow_any_explicit = true        # bans written Any in your code
enable_error_code = ["ignore-without-code", "possibly-undefined"]

# Legacy ratchet: freeze old modules, keep new code strict
[[tool.mypy.overrides]]
module = "legacy.*"
disallow_untyped_defs = false
```

Or pyright in `pyproject.toml`:

```toml
[tool.pyright]
typeCheckingMode = "strict"
reportMissingTypeStubs = "warning"
```

Untyped third-party libraries get stubs (`types-*` packages) or a `py.typed`-aware alternative — not a project-wide strictness downgrade.

## Signatures: Annotate Everything

**Bad:**

```python
def send_invoice(user, amount, notify=True, meta=None):
    ...
```

**Golden reference:**

```python
def send_invoice(
    user: User,
    amount: Money,
    *,
    notify: bool = True,
    meta: Mapping[str, str] | None = None,
) -> InvoiceReceipt:
    ...
```

Details that matter:

- `-> None` is information; an unannotated return is a hole (`Any` under non-strict settings).
- Default `None` requires `X | None` in the annotation — with strict mode there is no implicit Optional.
- Accept abstract types (`Mapping`, `Sequence`, `Iterable`), return concrete ones (`dict`, `list`). Callers gain flexibility; readers gain precision.
- Mutable default arguments (`meta: dict = {}`) are both a type smell and a bug; use `None` + narrow, or `field(default_factory=dict)` in dataclasses.

## The Any Ban

`Any` is bidirectional: it silently becomes everything and everything becomes it. One `Any` return value contaminates every downstream variable.

**Bad:**

```python
def load_config() -> Any:
    return json.load(open("config.json"))

cfg = load_config()
cfg.databse_url  # typo; checker is blind here
```

**Golden reference:**

```python
@dataclass(frozen=True)
class Config:
    database_url: str
    pool_size: int

    @classmethod
    def parse(cls, raw: Mapping[str, object]) -> "Config":
        url = raw.get("database_url")
        size = raw.get("pool_size", 10)
        if not isinstance(url, str) or not isinstance(size, int):
            raise ConfigError(raw)
        return cls(database_url=url, pool_size=size)

def load_config(path: Path) -> Config:
    with path.open() as fh:
        return Config.parse(json.load(fh))
```

Prefer `object` over `Any` for "some value I will not touch": `object` forces narrowing before use; `Any` permits everything. `json.load` returns `Any` — wrap it at every boundary as above (or use pydantic/msgspec which do this for you).

## Dataclasses, TypedDict, and Pydantic Over Raw Dicts

| Tool | Use when |
|---|---|
| `@dataclass(frozen=True, slots=True)` | Internal domain values and DTOs; no validation needed beyond construction |
| pydantic `BaseModel` / msgspec `Struct` | Boundary parsing with validation, coercion, and good errors |
| `TypedDict` | You must keep an actual `dict` (JSON-adjacent code, kwargs) but want a checked shape |
| `NamedTuple` | Tiny immutable records where tuple behavior is desired |

**Bad — dict-shaped folklore:**

```python
def charge(payment: dict) -> dict:
    return {"id": gateway.charge(payment["token"], payment["cents"]), "ok": True}
```

**Golden reference:**

```python
@dataclass(frozen=True, slots=True)
class ChargeRequest:
    token: CardToken
    cents: int

@dataclass(frozen=True, slots=True)
class ChargeResult:
    charge_id: str
    ok: bool

def charge(request: ChargeRequest) -> ChargeResult:
    return ChargeResult(charge_id=gateway.charge(request.token, request.cents), ok=True)
```

`**kwargs` passthroughs deserve typing too: `Unpack[TypedDict]` (PEP 692) or explicit parameters. An untyped `**kwargs` boundary is a `dict[str, Any]` in disguise.

## Enums and Literal Over Magic Strings

```python
class OrderStatus(StrEnum):
    PENDING = "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

# Parse at the boundary; unknown values raise ValueError:
status = OrderStatus(row["status"])
```

`Literal` suits small closed parameter sets without enum ceremony:

```python
def resize(image: Image, mode: Literal["fit", "fill", "crop"]) -> Image: ...
resize(img, "flil")  # checker error, not a silent no-op
```

Never accept `str` for a closed set: the checker cannot help, and typos become data.

## The Fallback-Chain Fix

The canonical offense, Python flavor:

```python
image = location.preview or location.banner or location.thumbnail
```

`or` is worse than PHP's `??`: it also swallows `""`, `0`, and empty collections. First replace truthiness with explicit None-checks, then give the policy an owner:

```python
@dataclass(frozen=True)
class Location:
    preview: Image | None
    banner: Image | None
    thumbnail: Image | None

    @property
    def primary_image(self) -> Image:
        """Display image by preference: preview, banner, thumbnail."""
        image = self.preview if self.preview is not None else \
                self.banner if self.banner is not None else self.thumbnail
        if image is None:
            raise MissingImageError(self)
        return image

    @property
    def primary_image_or_placeholder(self) -> Image:
        try:
            return self.primary_image
        except MissingImageError:
            return PLACEHOLDER_IMAGE
```

Call sites use one name with one non-Optional type; the preference order lives in one documented place.

## Optional Discipline

- `X | None` means absence is a designed state. If a value "shouldn't really be None", it should not be Optional — fix the producer.
- Narrow once, early, and let the non-None type flow:

```python
user = find_user(user_id)
if user is None:
    raise UserNotFound(user_id)
# user: User from here on — no further checks, no `user and user.name`
```

- Do not return `None` to signal errors when callers must not ignore them; raise, or return a small result union (`Ok | Err` dataclasses) matched exhaustively.
- `getattr(obj, "field", None)` and `dict.get` chains are the dynamic version of the fallback chain; parse the object into a typed structure instead.

## Protocols and Generics

`Protocol` types dependencies by capability, keeping signatures honest without inheritance coupling:

```python
class SendsEmail(Protocol):
    def send(self, to: EmailAddress, message: Message) -> None: ...

def notify(mailer: SendsEmail, user: User) -> None: ...  # accepts any conforming sender
```

Generics preserve types through helpers (PEP 695 syntax, Python 3.12+):

```python
def first[T](items: Sequence[T], where: Callable[[T], bool]) -> T | None:
    return next((item for item in items if where(item)), None)

class Repository[T]:
    def find(self, id: int) -> T | None: ...
```

`NewType` gives zero-cost distinct identifiers:

```python
UserId = NewType("UserId", int)
OrderId = NewType("OrderId", int)

def refund(order_id: OrderId, requested_by: UserId) -> None: ...
refund(user_id, order_id)  # checker error — swap caught
```

## Narrowing: TypeGuard, isinstance, assert_never

```python
# isinstance narrows unions
def describe(value: int | str) -> str:
    if isinstance(value, int):
        return f"number {value:d}"
    return value.upper()  # str here

# TypeGuard for custom shape checks
def is_string_list(items: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(item, str) for item in items)

# Exhaustive match over closed types
def label(status: OrderStatus) -> str:
    match status:
        case OrderStatus.PENDING: return "Waiting"
        case OrderStatus.SHIPPED | OrderStatus.DELIVERED: return "Moving or done"
        case OrderStatus.CANCELLED: return "Cancelled"
        case _:
            assert_never(status)  # compile-time exhaustiveness (typing.assert_never)
```

`cast()` is the last resort, adjacent to the evidence that justifies it, with a comment. A `cast` that merely silences a checker error is a suppression wearing a costume.

## Suppression Policy

- `# type: ignore` without a code is banned (`ignore-without-code` error code enforces this):

```python
value = legacy_call()  # type: ignore[no-untyped-call]  # legacy module, typed in TICKET-123
```

- Per-module strictness downgrades live in config (visible, reviewable), never as file-top blanket ignores.
- `# noqa`-style reflexes ("add ignore until it passes") are how typed Python rots; each ignore names an error code and a reason or does not merge.

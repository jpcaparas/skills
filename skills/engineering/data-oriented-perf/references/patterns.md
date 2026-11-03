# Data-Oriented Patterns

Worked versions of the moves in `SKILL.md`. The snippets are sketches in whichever language shows the idea most plainly; translate them into the project's idioms. Every pattern here is a candidate to measure, not a guaranteed win.

## Contents

- Dense IDs and flat arrays instead of hash tables
- Indices instead of pointers
- Packing hot data into the high bits of an index
- Structure of arrays and hot/cold splitting
- Redesigning away a cache
- Language and runtime notes

## Dense IDs and flat arrays instead of hash tables

A hash lookup costs hashing, probing, and a likely cache miss. When the program assigns the keys itself (entity IDs, symbol IDs, node IDs, interned strings), make them dense integers starting at zero and index a plain array.

```rust
// Before: HashMap<SymbolId, SymbolInfo> where SymbolId was a random u64
// After: SymbolId is assigned sequentially at intern time
#[derive(Clone, Copy)]
struct SymbolId(u32);

struct Symbols {
    info: Vec<SymbolInfo>, // info[id.0 as usize]
}
```

- **Interning is the bridge.** Keep one hash map at the boundary, from the external key to the dense ID, and use the ID everywhere inside. The hot path never hashes.
- **Sparse keyspaces do not fit.** If keys are external, sparse, or unbounded (user IDs, URLs, timestamps), a flat array wastes memory or is impossible. Intern them or keep the map.
- **Removal needs a policy.** Swap-remove changes other elements' indices. A tombstone or free list keeps indices stable. Pick one deliberately; see the next section.

## Indices instead of pointers

Replace references between records with integer indices into contiguous storage, often called handles.

- A 32-bit index is half the size of a 64-bit pointer, so more records fit in each cache line.
- Indices survive reallocation, can be serialized and memory-mapped directly, and do not make a garbage collector trace an object graph.
- The cost is an extra base-plus-offset step and the loss of language-level lifetime checking. Replace that checking with a stated invariant.

```zig
const NodeIndex = enum(u32) { none = std.math.maxInt(u32), _ };

const Node = struct {
    first_child: NodeIndex,
    next_sibling: NodeIndex,
    kind: Kind,
};

nodes: std.ArrayListUnmanaged(Node),
```

Stale handles are the main hazard. If slots are reused, pair each index with a generation counter and check it on access. If the structure is append-only, such as an AST built once per parse, slots never move and plain indices are safe.

## Packing hot data into the high bits of an index

If almost every access first asks a small question, such as the record's kind, whether it is resolved, or which table it lives in, store the answer in unused high bits of the index. One load then answers both "where" and "what".

```ts
// 28 bits of index (up to 268,435,455 records) + 4 bits of kind
const INDEX_BITS = 28;
const INDEX_MASK = (1 << INDEX_BITS) - 1;

function pack(index: number, kind: Kind): number {
  if (index > INDEX_MASK) throw new RangeError("index exceeds 28-bit capacity");
  return ((kind << INDEX_BITS) | index) >>> 0;
}
const indexOf = (ref: number) => ref & INDEX_MASK;
const kindOf = (ref: number): Kind => ref >>> INDEX_BITS;
```

- Decide the split from real capacity requirements, not hope, and enforce it with a compile-time assertion or a checked constructor.
- Put the masks and shifts in one place behind named functions. Scattered bit arithmetic is where these designs break.
- Pack only data that is genuinely hot and stable. A field that changes often forces rewriting every copy of the reference.
- Check that the language's integer semantics behave as intended. JavaScript bitwise operators work on signed 32-bit values, hence the `>>> 0` above.

## Structure of arrays and hot/cold splitting

An array of structures (AoS) stores records whole. A structure of arrays (SoA) stores each field in its own array. A loop that reads `position` and `velocity` for a million particles but never their `name` or `spawn_time` streams far fewer bytes with SoA, and the separate arrays are easier to vectorise.

```rust
// AoS
struct Particle { pos: Vec3, vel: Vec3, name: String, spawned_at: Instant }
let particles: Vec<Particle>;

// SoA
struct Particles {
    pos: Vec<Vec3>,
    vel: Vec<Vec3>,
    name: Vec<String>,
    spawned_at: Vec<Instant>,
}
```

- **Choose by access pattern.** SoA wins when loops touch a few fields of many records. AoS wins when code handles one record at a time and uses most of its fields. Many real designs mix them: hot fields in SoA, cold fields in a side table.
- **Hot/cold split** is the lighter version: move rarely used fields out to a parallel array or a separate allocation and keep the frequently read struct small.
- **Use library support where it exists.** Examples are Zig's `std.MultiArrayList`, ECS frameworks, columnar formats like Apache Arrow, and dataframe libraries. Hand-rolling parallel arrays invites length mismatches.
- **Keep the arrays in sync.** All columns must be appended, removed, and reordered together. Wrap them in one type that owns those operations.

## Redesigning away a cache

Before keeping, adding, or removing a cache, ask why the uncached path is slow. Common answers and redesigns:

| Why the base path is slow | Redesign |
|---|---|
| It repeats a lookup through a hash table or pointer chain | Dense IDs and flat arrays make the lookup a load |
| It recomputes something derivable once from stable input | Compute it eagerly when the input is built, and store it alongside the data |
| It walks wide records to read a few fields | SoA or a hot/cold split |
| It allocates per call | Reuse buffers, use arenas, or return indices instead of new objects |
| It parses or decodes repeatedly | Decode once into a compact internal representation and keep that |

Then classify any existing cache before touching it:

- **Pure performance memo.** It is safe to drop when the redesigned path measures at least as fast without it.
- **Correctness or cost bearing.** Idempotency keys, dedup sets, consistency snapshots, rate-limit protection, offline data, and responses from paid or rate-limited services. Keep it, and report it as out of scope for removal.
- **Owned elsewhere.** HTTP, CDN, database buffer pool, OS page cache, a build cache. It is not this change's to delete.

## Language and runtime notes

These are starting points. Measure on the target runtime.

- **C, C++, Rust, Zig, Odin:** Full control over layout. Use `u32` newtype indices, contiguous vectors or arenas, explicit packing, and static assertions on struct size.
- **Go:** Slices of structs are contiguous, but pointer-heavy structs make the garbage collector scan more. Indices into slices and pointer-free hot structs reduce GC work. Parallel slices give SoA.
- **Java, Kotlin, C#:** Objects are individually allocated references. Primitive arrays, C# `struct` arrays and `Span<T>`, or parallel primitive arrays give real contiguity. Be wary of boxing in generic collections.
- **JavaScript and TypeScript:** An array of objects is an array of references. `TypedArray`s give contiguous numeric columns, and keeping object shapes monomorphic helps engines optimise property access. Benchmark in the engine you ship on.
- **Python:** Per-object overhead dominates. Move hot numeric data into NumPy arrays, the `array` module, or a columnar library, and process it in bulk rather than per element.

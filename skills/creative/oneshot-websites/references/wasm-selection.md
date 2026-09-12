# WebAssembly Selection for One-Shot Leads

Use this reference as operational lead guidance only when the request or supplied source presents a plausible WebAssembly boundary. Never append it to the prepared actual prompt or `artifact/PROMPT.md`. The prompt states the experience; this reference helps the owning lead choose its implementation.

WebAssembly complements the web layer rather than replacing it. Keep HTML, CSS, accessible DOM behavior, navigation, forms, ordinary application state, and network orchestration in the normal web stack. Give WASM one narrow, named responsibility only when reuse, portability, exact semantics, browser-local execution, or representative measurements earn the extra build and runtime complexity.

## Decision Gate

Use WASM when direct evidence establishes a strong fit, such as:

- an existing C, C++, Rust, or other compiled engine has a viable browser build and its tested behavior should be reused
- the experience needs a mature codec, parser, database engine, emulator, virtual machine, physics core, geometry kernel, DSP library, or numerical solver
- a sustained CPU-bound hot path processes large numeric arrays or binary buffers through a few coarse calls
- one deterministic core must run across browser and native or server targets, and sharing it materially reduces semantic drift
- offline, private, low-latency, or large-file browser-local processing is required and an established engine is a better fit than rebuilding its semantics in JavaScript

Run a bounded spike when the workload sounds suitable but the evidence does not establish a win. Compare the simplest credible JavaScript or TypeScript implementation with a narrow WASM candidate on representative data. Measure cold start, module and glue size, initialization time, steady-state throughput or latency, peak memory, main-thread responsiveness, and boundary-copy cost. Keep WASM only when the measurements show a material product benefit or when reuse, exact semantics, or portability independently justifies it.

Prefer the ordinary web stack when the work is dominated by DOM updates, accessibility, routing, forms, fetches, storage orchestration, remote-server latency, small or occasional calculations, string-heavy object manipulation, or chatty cross-boundary calls. CSS, Canvas, WebGL, WebGPU, or a maintained web library normally owns visual work without an existing compiled core. An ordinary CRUD application, elaborate marketing animation, Rust-backed API, or vaguely “complex” 3D scene does not earn WASM by itself.

## Lead Contract When WASM Fits

1. Name the module boundary and why it belongs in WASM. Keep browser integration and product state outside it.
2. Keep crossings coarse. Batch typed arrays, `ArrayBuffer` payloads, or similarly explicit data rather than crossing for individual UI events or tiny values.
3. Define buffer ownership, memory growth limits, error mapping, cancellation, and cleanup. Account for encoding, copying, and marshalling costs.
4. Move long-running work into a Worker when the interaction must remain responsive. Specify progress and cancellation without assuming threads or SIMD are universally available.
5. Build reproducibly and bundle the `.wasm` file and required glue inside `artifact/`. Use casing-correct local URLs, feature detection, and a deliberate initialization fallback. If streaming compilation depends on a MIME type the static host may not provide, include a tested non-streaming load path.
6. Verify source-engine parity or representative correctness fixtures, plus the performance acceptance criterion when performance justified the choice. Exercise cold and warm loading, failed initialization, cancellation, and unsupported-capability behavior.
7. Keep the complete artifact within the skill’s static envelope, including the 5 MiB per-file limit. If the required module cannot meet the portable handoff contract, choose another viable architecture or report the limitation honestly instead of marking the run `OK`.
8. Record the decision, module boundary, build command, important dependencies, measurements or reuse rationale, and final browser verification in `worker-report.json` using its existing technology and verification fields.

Do not rewrite the whole application in a WASM-targeting language. Reuse the smallest stable compiled core and expose a typed adapter that the web layer can test independently.

## Sample Scenarios

| Scenario | Decision | Lead approach |
| --- | --- | --- |
| Browser photo lab backed by a proven C++ RAW decoder | Strong fit | Compile decoding and batch pixel processing to WASM, process whole buffers in a Worker, and keep file picking, previews, controls, accessibility, and export orchestration in TypeScript. Verify output parity, startup, memory, and batch latency. |
| Crowd, transit, fluid, or physics simulation with a tested native engine | Strong fit when that engine is real source evidence | Reuse the simulation core, expose coarse step and snapshot operations, render and control it from the web layer, and test deterministic scenarios against the source engine. |
| Browser music workstation using a mature C or C++ DSP library | Strong fit | Put buffer processing and DSP in WASM, keep project state and UI in the web layer, and prove the audio path meets its representative latency and glitch budget. |
| CAD, map, scientific, or archival tool using a proven native binary parser or geometry kernel | Strong fit | Compile the narrow parser or kernel, validate malformed inputs, return typed batched results, and keep editing and visualization interactions outside it. |
| Offline research archive that must open an existing SQLite database locally | Strong fit when SQLite semantics and local persistence matter | Use the supported SQLite WASM distribution with an appropriate Worker-backed persistence route. Keep queries coarse and test migration, concurrency, recovery, and browser support. Do not choose it for a tiny settings store. |
| Emulator, language runtime, or established game engine being brought to the browser | Strong fit | Reuse the portable core, keep browser integration in a thin adapter, and verify timing, save state, input boundaries, accessibility wrappers, and representative compatibility cases. |
| Novel route optimizer or procedural simulation with no existing native core | Spike first | Build the simplest TypeScript baseline, profile representative workloads, and test one stable numeric kernel in WASM only if profiling isolates it. Retain it only with a recorded keep/remove decision. |
| Analytics dashboard with filters, tables, forms, and remote API calls | Poor fit | Keep the application in TypeScript and optimize rendering, queries, and network behavior first. |
| Marketing or portfolio experience with elaborate transitions | Poor fit | Use CSS, Canvas, WebGL, or WebGPU as the visuals warrant. WASM adds no fidelity merely because motion is elaborate. |
| CRUD frontend for a Rust backend | Poor fit | The server language does not create a browser WASM requirement. Use the ordinary web stack unless a separate browser-local compiled core is evidenced. |

**Complete when:** the lead has chosen a justified and testable WASM boundary, run a representative spike with an explicit keep/remove result, or deliberately rejected WASM because the ordinary web stack is the better fit—and the prepared actual prompt remains unchanged.

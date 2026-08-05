# WebAssembly Selection

Read this reference only when the source or requested target presents a plausible WebAssembly boundary. Use it to decide whether the fresh-session prompt should require WASM, ask for a focused spike, or leave the implementation in JavaScript or TypeScript.

WebAssembly complements the web layer; it does not replace it. Keep HTML, CSS, accessible DOM, navigation, forms, ordinary application state, and network orchestration in the normal web stack. Give WASM a narrow, named responsibility only when its reuse, portability, correctness, or measured workload earns the added build and runtime complexity.

## Decision Gate

Require WASM when direct evidence establishes a strong fit, such as:

- the source contains a proven C, C++, Rust, or other compiled engine whose exact behavior should be reused in the browser
- the target must preserve a mature codec, parser, database engine, emulator, virtual machine, physics core, geometry kernel, or numerical solver that already has a viable WASM build path
- a sustained CPU-bound hot path processes large numeric arrays or binary buffers and can be exposed through a small number of coarse calls
- the same deterministic core must run across web and native or server targets, and sharing it materially reduces semantic drift
- browser-local processing is required for offline operation, privacy, latency, or large-file handling, and the relevant engine is a better fit than rebuilding its semantics in JavaScript

Ask the future session to run a bounded WASM spike when the workload sounds suitable but the evidence does not yet establish a win. The spike must use representative data and compare the simplest credible non-WASM path. Measure cold start, module and glue size, initialization time, steady-state throughput or latency, peak memory, main-thread responsiveness, and boundary-copy cost. Retain WASM only when the result shows a material benefit or when reuse, exact semantics, or portability independently justifies it.

Prefer JavaScript or TypeScript when the work is dominated by:

- DOM updates, accessibility behavior, routing, forms, fetches, storage orchestration, or server latency
- small calculations, occasional transforms, string-heavy object manipulation, or chatty calls across the JavaScript/WASM boundary
- a visual effect that WebGL, WebGPU, Canvas, CSS, or an existing web library already handles without a compiled core
- an ordinary CRUD product whose difficulty is product behavior rather than local computation
- a server-only workload that can use its native library directly and has no demonstrated portability or sandboxing requirement

The words “fast,” “complex,” “3D,” or “written in Rust” are not sufficient by themselves. Do not prescribe WASM for prestige, novelty, or speculative future scale.

## Prompt Contract When WASM Fits

Put these requirements into the fresh-session prompt at the level the target earns:

1. Name the module boundary and its reason. State which algorithms or existing library belong in WASM and which browser responsibilities remain outside it.
2. Keep crossings coarse. Batch work around typed arrays, `ArrayBuffer` data, or similarly explicit payloads instead of bouncing through the boundary for individual UI events or tiny values.
3. Define ownership of input and output buffers, memory growth limits, error mapping, cancellation, and cleanup. Do not imply that linear memory removes the cost of encoding, copying, or marshalling data.
4. Keep long-running work off the main thread when the target requires responsive interaction. Specify progress, cancellation, and deterministic fallback or failure behavior without assuming threads or SIMD are universally available.
5. Require reproducible release builds, correct loading of the `.wasm` artifact, feature detection for optional capabilities, and a deliberate degradation path for unsupported or failed initialization.
6. Verify both product fidelity and the reason WASM was chosen. Include representative correctness fixtures, parity checks against the source engine when one exists, and performance acceptance criteria only when performance is part of the justification.
7. Budget startup, binary size, memory, caching, and debugging alongside runtime speed. A faster hot loop does not justify a slower or more fragile product by itself.

Do not demand a total rewrite into a WASM-targeting language. Reuse the smallest stable compiled core and expose a typed adapter that the web application can test independently.

## Sample Scenarios

| Scenario | Decision | What the prompt should say |
| --- | --- | --- |
| Browser photo lab backed by an existing C++ RAW decoder and batch color pipeline | Strong fit | Compile the decoder and pixel pipeline to WASM, process whole image buffers in a Worker, and keep file picking, previews, controls, accessibility, and export orchestration in TypeScript. Verify output parity and measure startup, memory, and batch latency. |
| Transit or crowd simulation with a tested Rust engine updating thousands of agents per step | Strong fit when the engine is source evidence | Reuse the simulation core as WASM, expose coarse step and snapshot operations, render and control it from the web layer, and test deterministic scenarios against the original engine. |
| Browser music workstation reusing a mature C or C++ DSP library | Strong fit | Put sample-buffer processing and DSP in WASM, keep project UI and state in the web layer, and prove the audio path meets its latency and glitch budget with representative devices. |
| CAD, map, scientific, or archival tool that must parse a complex legacy binary format using a proven native library | Strong fit | Compile the parser or geometry kernel, validate hostile and malformed files, return typed results in batches, and keep visualization and editing interactions outside the module. |
| Offline research archive that must open an existing SQLite database and preserve SQL semantics locally | Strong fit when those semantics matter | Use the supported SQLite WASM distribution and an appropriate Worker-backed persistence route; keep queries coarse, surface persistence limitations, and test migration, concurrency, and recovery behavior. Do not choose it merely for a small settings store. |
| Emulator, language runtime, or established game/physics engine being brought to the browser | Strong fit | Reuse the portable core, keep browser integration in a thin adapter, declare asset and input boundaries, and verify timing, save state, accessibility wrappers, and representative compatibility cases. |
| Analytics dashboard with filters, tables, forms, and remote API calls | Poor fit | Keep the product in TypeScript; optimize rendering, queries, and network behavior first. Add a WASM spike only if profiling later isolates a substantial local numeric hot path. |
| Marketing site with elaborate transitions and scroll effects | Poor fit | Use CSS, Canvas, WebGL, or WebGPU as the visual implementation warrants. WASM adds no fidelity merely because the motion is elaborate. |
| Small checksum, date calculation, or occasional JSON transformation | Poor fit | Use the platform or a maintained JavaScript library unless an exact audited native implementation is an explicit requirement. |
| Server endpoint already able to call the native library directly | Usually poor fit | Use the native server integration. Choose WASM only when a separately evidenced portability, isolation, or shared-core requirement outweighs the extra runtime layer. |

**Complete when:** the handoff prompt either names a justified and testable WASM boundary, requests a representative spike with a keep/remove criterion, or deliberately leaves WASM out because the normal web stack is the better fit.

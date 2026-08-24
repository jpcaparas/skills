# Executable Directional-Control Gate

Read this reference only when the prepared run records `interaction.directionalControls.required: true`. Use it to connect the artifact’s real production control state to the coordinator-owned browser gate. This contract supplements the rendered gauntlet; it does not replace mouse, complete-keyboard, pointer, touch, controller, rotation, transform, or visible-label checks.

## What the finished prompt must require

The sealed actual prompt must tell the lead that the final artifact will be rejected unless all of these statements are true:

- `A` and `ArrowLeft` independently produce observable left in the active control frame.
- `D` and `ArrowRight` independently produce observable right in that same frame.
- The artifact exposes the production-state probe below so a coordinator can reset one deterministic state, send browser-level key events, and measure the result.
- The probe reads the real player, vehicle, camera, or orbit state used by the rendered experience. A parallel test-only simulation, hard-coded answer, remapped sample, or direct invocation of movement functions is not acceptable.
- The ordinary rendered gauntlet still checks `W`/`ArrowUp`, `S`/`ArrowDown`, the full mouse-and-keyboard primary path, transformed orientations, other exposed aliases, and visible instructions.

State these requirements in language native to the requested game or 3D experience. Do not append them to passive 3D scenes or ordinary websites with no directional interaction.

## Probe contract

Applicable artifacts expose `window.__ONESHOT_DIRECTIONAL_CONTROL_PROBE__` in the built `artifact/index.html` runtime. It may be attached only while the query string contains `oneshot-directional-probe=1`, but it must be part of the same portable built artifact and operate on the same production state and input listeners.

The contract is equivalent to this TypeScript shape:

```ts
type DirectionalVector = readonly [number, number] | readonly [number, number, number];

interface OneshotDirectionalControlProbe {
  readonly schemaVersion: "1.0";
  reset(): void | Promise<void>;
  sample(): DirectionalControlSample | Promise<DirectionalControlSample>;
}

interface DirectionalControlSample {
  readonly frame: string;
  readonly measurement: "position" | "heading";
  readonly position: DirectionalVector;
  readonly forward: DirectionalVector;
  readonly right: DirectionalVector;
}
```

`reset()` returns the real experience to one seeded, stable, ready-to-control state. It may perform deterministic setup that would otherwise require a countdown or menu, but it must not replace the production controls or state model. `sample()` returns finite vectors from that real state:

- `frame` names the active semantic frame, such as `screen-lane`, `vehicle`, `player-camera`, or `orbit-camera`. It remains stable during one isolated key check.
- `measurement: "position"` tells the verifier to project the production position change onto the initial `right` basis.
- `measurement: "heading"` tells the verifier to compare the production forward-vector change against the initial `right` basis.
- `right` means semantic visible or control-frame right at the reset state—not an assumed global axis. `forward` and `right` use the same two- or three-dimensional coordinate space as `position`.

The coordinator verifier resets before every key, sends `KeyA`, `ArrowLeft`, `KeyD`, and `ArrowRight` independently through Chromium’s DevTools input domain, and applies one fixed sign contract. Left must be negative beyond the fixed response epsilon; right must be positive. Missing adapters, zero response, inverted response, browser failure, failed checks, and stale evidence all block successful catalogue validation.

## Representative implementations

### Two-dimensional lane or screen-relative movement

Use `measurement: "position"`. Return the actual rendered entity position and the active screen or lane basis. For a conventional unmirrored screen plane, `right` may be `[1, 0]`; after a mirrored container or transformed canvas, derive the basis that corresponds to what the player actually sees.

### Vehicle or character steering

Use `measurement: "heading"` when steering primarily changes orientation. Return the real world-space vehicle or character position, its rendered forward vector, and the active steering-frame right vector after parent transforms. Do not reuse a local `+X` assumption after a mirrored parent, negative scale, camera-relative mode, or handedness conversion.

### Camera orbit or look controls

Use `measurement: "heading"`. Return the production camera view direction and its active right basis. Reset to a deterministic orbit target and orientation before every key. A deliberate, visible user-selectable look inversion remains allowed, but the default presented left/right controls cannot silently swap.

### Mixed steering and lateral drift

Choose the single measurement that most directly represents the presented control. The executable gate does not need to prove every motion component; the rendered gauntlet still checks the full behavior under representative speed, rotation, transform, and mode changes.

## Coordinator sequence

After the lead finalizes the run and removes its run-local `.tmp/`, run:

```bash
"${ONESHOT_WEBSITES_PYTHON:-python3}" scripts/verify_directional_controls.py \
  --run "<exact-run-directory>"
```

Set `ONESHOT_WEBSITES_BROWSER` or pass `--browser` only when automatic Chromium-family discovery does not find the desired compatible executable. The helper launches an isolated loopback-only static server and browser profile, sends browser-level keyboard events, hashes the complete artifact tree, and writes the result to the coordinator-owned evidence path prepared in the receipt.

If the helper fails, do not create another run. Resume the existing lead and namespace, move both statuses back to `RUNNING`, recreate only that run’s `.tmp/`, send the failed key evidence as a correction, and repeat normal finalization. Run the helper again on the repaired `OK` artifact. `scripts/validate_catalog.py` accepts an applicable successful run only when the passing evidence covers all four keys and its artifact digest, file count, and byte count still match.

## Non-applicable cases

A passive WebGL gallery, a product model viewer with no orbit or directional controls, a chess board, and an ordinary dashboard do not earn this adapter merely because they use canvas, 3D rendering, or keyboard shortcuts. The coordinator can force the gate with `prepare_run.py --directional-controls required` when automatic analysis misses an unusual but real directional experience; there is no command-line option that downgrades an automatically applicable run.

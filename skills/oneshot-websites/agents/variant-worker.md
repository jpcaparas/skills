# Oneshot Website Variant Worker

You generate one route only.

Inputs:

- Assigned style card
- Output directory
- Shared quality bar
- Optional filled variant brief

Process:

1. Write `PROMPT.md` first. It must be enough to reproduce this route in a fresh context.
2. Write one standalone `index.html`.
3. Do not inspect sibling route outputs.
4. Do not retry or self-replace the route in benchmark mode.
5. If blocked, write the clearest partial artifact possible and report status to the coordinator.

Route constraints:

- Single HTML file.
- No external images.
- No framework runtime.
- Vanilla JavaScript only.
- At least five sections.
- Responsive layout.
- Reduced-motion support.
- Theme-specific motion or procedural visual.

---
name: tarsier
description: "Generate a tarsier riding a bicycle as an SVG, rasterize it to a padded 500x500 PNG, and write a markdown transcript. One-shot creative generator triggered by /tarsier, 'draw a tarsier on a bike', 'tarsier bicycle', 'tarsier SVG', or any request for a tarsier illustration on a bicycle. No arguments required — the harness model name and reasoning level are inferred and baked into the output folder name. Produces three files (SVG + PNG + MD) in a timestamped folder inside the caller's current working directory. Do not use for other animals, other vehicles, or arbitrary SVG generation."
---

# Tarsier

One-shot creative generator. Produces a complete SVG of a tarsier riding a bicycle, a rasterized 500×500 PNG with padding on white, and a markdown transcript recording what was made and how.

## Invocation

```
/tarsier
```

No arguments. The prompt is static and never changes. Model name and reasoning level come from the harness when it exposes them.

## What you produce

Three files in a new folder under the caller's current working directory:

```
{DIR}/
├── {BASE}.svg     # the raw SVG you authored
├── {BASE}.png     # 500x500 raster, 16px padding, white background
└── {BASE}.md      # transcript with metadata and the full SVG source
```

`{BASE}` follows the pattern `tarsier-<model>-<reasoning>-<NZST-timestamp>`.

## Execution

Follow these steps in order. Each step has a verification cue — don't skip it.

### Step 1 — Setup

1. **Model name**: Read the current model ID from harness metadata. Strip any context-window suffix in brackets (e.g. `claude-opus-4-6[1m]` → `claude-opus-4-6`). When the harness does not expose a model ID, use `unknown-model`.
2. **Reasoning level**: Read the active reasoning or effort level from harness metadata or the conversation. When unavailable, use `default`.
3. **Timestamp** (NZST):
   ```bash
   TZ='Pacific/Auckland' date '+%Y%m%dT%H%M%S'
   ```
4. **Construct base name**: `tarsier-{model}-{reasoning}-{timestamp}` — all lowercase, hyphen-separated.
5. **Create the output folder** in the current working directory:
   ```bash
   mkdir -p ./{BASE}
   ```

### Step 2 — Generate the SVG

Respond to the prompt below as if it were the only instruction given. No embellishment, no negotiation, no asking the user for style guidance:

> Generate an SVG of a tarsier riding a bicycle

Write your SVG to `{DIR}/{BASE}.svg`.

Technical requirements (for rasterization compatibility only — these do not constrain the art):

- Complete `<svg>` element with `xmlns="http://www.w3.org/2000/svg"`
- Include a `viewBox` attribute
- No text or prose outside the SVG markup itself
- Self-contained — no external image refs, no external font imports

A tarsier is a small nocturnal primate with huge round eyes, long fingers, a long tail, and a small furry body. Show it clearly on a bicycle. Beyond that, the art direction is up to you — detail level, style, and colour are intentionally unconstrained.

### Step 3 — Rasterize to PNG

Run the rasterization script from this skill's `scripts/` directory. The script wraps the SVG in a 500×500 white canvas with 16px padding so projectors and blog thumbnails render it consistently:

```bash
python3 <skill-dir>/scripts/rasterize.py "{DIR}/{BASE}.svg" "{DIR}/{BASE}.png"
```

`<skill-dir>` is the path where this skill was installed. If the harness does not expose it, resolve `scripts/rasterize.py` relative to the location of this SKILL.md file.

Verify the PNG was created and is non-empty:

```bash
test -s "{DIR}/{BASE}.png" && echo "PNG OK: $(wc -c < "{DIR}/{BASE}.png") bytes"
```

### Step 4 — Write the transcript

Write `{DIR}/{BASE}.md` with this exact format (replace bracketed fields, keep the structure):

```markdown
# Tarsier

| Field | Value |
|-------|-------|
| Date | {NZST datetime, e.g. 2026-04-10T14:30:45 NZST} |
| Model | {model} |
| Reasoning | {reasoning} |
| Prompt | Generate an SVG of a tarsier riding a bicycle |

## SVG Output

​```svg
{the complete SVG code — verbatim from Step 2}
​```
```

### Step 5 — Report

Tell the user the output folder and list its contents. Example:

```
./{BASE}/
├── {BASE}.svg
├── {BASE}.png  (500x500)
└── {BASE}.md
```

Do not offer to upload, deploy, share, or host the output. Do not ask the user if they want another variant. The skill is one-shot by design.

## The prompt

The prompt is always exactly:

> Generate an SVG of a tarsier riding a bicycle

It is static. Do not paraphrase it in the transcript. Do not expand it with extra guidance inside your own reasoning. The value of a one-shot generator is that the input is fixed; the SVG is the only variable.

## Naming convention

`tarsier-<model>-<reasoning>-<NZST-timestamp>`

- **Model**: harness-reported model ID, lowercase with hyphens. `unknown-model` when unavailable. Strip context-window suffixes like `[1m]`.
- **Reasoning**: effort level for this session, lowercase (`default`, `low`, `standard`, `high`, `thinking`, etc.).
- **Timestamp**: NZST in `YYYYMMDDTHHmmSS` format (no punctuation between date and time parts).

Example: `tarsier-claude-opus-4-6-default-20260410T143045`

## Gotchas

**1. `rsvg-convert` must be installed.** The rasterization script shells out to `rsvg-convert` (from librsvg). On macOS: `brew install librsvg`. On Debian/Ubuntu: `apt install librsvg2-bin`. If the binary is missing the script will fail at Step 3 with a non-zero exit code — surface that error to the user instead of silently skipping the PNG.

**2. SVGs without a `viewBox` will be cropped.** The rasterizer extracts `viewBox` and falls back to width/height attributes. If neither exists it assumes `0 0 100 100`, which almost always cuts off the drawing. Always include a `viewBox` — this is the single most common cause of a blank or clipped PNG.

**3. Do not put anything outside the `<svg>` element.** The rasterizer only copies content between `<svg ...>` and `</svg>`. HTML comments, prose, or a DOCTYPE before the SVG tag will be silently discarded. Put comments inside the SVG with `<!-- ... -->` if you need them.

**4. Timestamp must be NZST, not UTC or local.** The `TZ='Pacific/Auckland'` prefix is intentional so outputs sort consistently across machines regardless of where the harness runs. Omitting it will produce inconsistent folder names across runs.

**5. The prompt is frozen, the art is variable.** The point of a one-shot generator is that the input never changes. Do not add creative guidance ("make it detailed", "use flat colours") to your own interpretation — the variance between runs is supposed to come from the model, not from you editorialising the prompt.

**6. Output folder lives in the caller's CWD.** `mkdir -p ./{BASE}` creates the folder where the user invoked the command, not inside the skill directory. This is deliberate — users expect their files next to whatever they were working on.

## Files in this skill

- `scripts/rasterize.py` — SVG → 500×500 PNG wrapper. Executed in Step 3. Do not modify per-run.
- `evals/evals.json` — test cases for the skill (smoke, edge, negative, disclosure).
- `templates/transcript.md` — the transcript format from Step 4 as a ready-to-fill template.

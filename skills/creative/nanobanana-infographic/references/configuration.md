# Configuration And Verification

## Table of Contents

- [Requirements](#requirements)
- [Environment Variables](#environment-variables)
- [Generate A Preset Prompt Pack](#generate-a-preset-prompt-pack)
- [Custom Prompts And Packs](#custom-prompts-and-packs)
- [Render An Approved Pack In Parallel](#render-an-approved-pack-in-parallel)
- [Run A Live Probe](#run-a-live-probe)
- [Recommended Workflow](#recommended-workflow)

## Requirements

- `python3`
- optional `GEMINI_API_KEY` for live render verification

No SDK is required. The included probe script uses Python's standard library only.

Nano Banana 2 note:

- public launch name: `Nano Banana 2`
- callable Developer API model verified on April 9, 2026: `gemini-3.1-flash-image-preview`

That dated verification does not guarantee current availability. If an ID or request field is uncertain or fails, use the official sources in `references/api.md`; do not silently switch models.

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | only for live probes | authenticates to the Gemini Developer API |

Provide the key through the environment or the host's secret store. Do not paste it into chat, prompts, committed files, or logs. Live examples below incur external calls and spend; prompt generation and batch `--dry-run` do not require a key. Ensure the content is authorized for transmission and protect saved request/response files.

## Generate A Preset Prompt Pack

Use this optional helper when the low-noise editorial preset fits. `templates/brief.json` and the eval briefs contain illustrative claims, not sourced facts; replace them with the user's verified content.

```bash
python3 scripts/build_variant_pack.py \
  --brief templates/brief.json \
  --output-dir ./out/prompt-pack
```

This writes:

- `variant-pack.json`
- `variant-pack.md`
- one `.prompt.txt` file per variant
- `brief.normalized.json`

Supported brief customization and limits:

- `aspect_ratio` overrides the helper's `16:9` default.
- `variant_count` selects the first 1-4 preset directions; omitted or zero defaults to four, and values outside 1-4 are clamped. It cannot select arbitrary designs or make six variants.
- `palette` adds a palette bias and `avoid` appends exclusions. They do not remove the built-in white/near-white base, flat graphics, or style exclusions.
- Titles are truncated to five words. Generated prompts prescribe 1-3-word labels and no sentences, captions, or source notes.
- `tone` is stored in the normalized brief but the prompt uses each preset's tone, not that field.
- The only builder flags are `--brief` and `--output-dir`; there are no custom-style or count CLI flags. Review every generated prompt before using it.

Do not force a conflicting brief through this helper. Use the custom route below for dark/bold styles, longer exact wording, different compositions, or other counts.

## Custom Prompts And Packs

Write a UTF-8 prompt file directly with the requested composition and exact text. It need not come from the builder. The single-image example below uses this route.

For multiple custom directions, author a pack with the requested number of entries:

```json
{
  "brief": {"aspect_ratio": "4:5"},
  "variants": [
    {
      "id": "dark-radial",
      "name": "Dark radial explainer",
      "prompt": "Create a 4:5 infographic on a dark navy canvas with luminous teal and coral accents. Use a radial composition with readable high-contrast text. Exact title: How our community turns ideas into action. Exact labels: Listen, Build, Share. Do not invent statistics."
    }
  ]
}
```

The batch renderer consumes each entry's `id`, `name`, and `prompt`; it does not enforce the builder's four-variant limit. Use unique filesystem-safe IDs (letters, digits, hyphens; no paths) because IDs become output directory names. Use one ratio per pack, or split packs when ratios differ. Edit JSON `prompt` values for batch rendering: editing the sibling `.prompt.txt` files alone does not change the batch input.

## Render An Approved Pack In Parallel

First inspect the job count without contacting Gemini:

```bash
python3 scripts/render_variant_pack.py \
  --variant-pack ./out/prompt-pack/variant-pack.json \
  --output-dir ./out/renders/batch \
  --model gemini-3.1-flash-image-preview \
  --image-size 512 \
  --passes 1 \
  --max-concurrency 2 \
  --dry-run
```

Omit `--dry-run` only for an authorized live batch. `--aspect-ratio` overrides the pack's ratio, so keep the prompts consistent with it. `--model` accepts a callable ID but does not enforce Nano Banana 2 identity; that check belongs to the caller.

Batch behavior:

- schedules all included variants, with one request per variant per pass
- defaults to all jobs concurrent unless `--max-concurrency` bounds them
- uses one output subdirectory per variant
- writes a top-level `batch-manifest.json`
- keeps failures isolated to the affected variant

## Run A Live Probe

For one authorized image, save your custom prompt as `./out/custom.prompt.txt`, then run:

```bash
python3 scripts/probe_gemini_image_api.py \
  --prompt-file ./out/custom.prompt.txt \
  --output-dir ./out/renders/custom \
  --model gemini-3.1-flash-image-preview \
  --aspect-ratio 4:5 \
  --image-size 1K \
  --passes 1
```

This script accepts arbitrary prompt text through `--prompt-file` or `--prompt` and supports `--model`, `--aspect-ratio`, `--image-size`, and `--passes`. It has no `--dry-run`; running it with credentials makes live requests. Keep `--passes 1` for a single-image request unless additional attempts are authorized.

The probe writes:

- `request-01.json`
- `response-01.json`
- saved image files
- `manifest.json`

## Recommended Workflow

1. Derive the format, count, style, and exact facts from the brief; resolve only material gaps.
2. Author custom prompts or use the optional preset builder when its constraints fit.
3. Review the actual render input for facts, wording, ratio, and style. A prompt-only task ends without an API call.
4. For authorized renders, use the single-prompt route or a reviewed batch plan. Check request count, size, privacy, and spend before executing.
5. Inspect returned images for factual fidelity, text, contrast, and intended composition. A successful HTTP call or manifest is not a visual-quality check.
6. Deliver the requested count, with a text equivalent where needed. Report defects and bound additional paid attempts; do not generate extras just to fill a review sheet.
7. Choose resolution for the delivery and budget. A lower-resolution preview can save spend when iteration is needed, but is not a mandatory extra render before a requested final image.

If the render comes back noisy, shorten the prompt and simplify the composition before raising the model size.

## See Also

- `references/patterns.md` for the variant and iteration system
- `references/api.md` for request structure
- `references/gotchas.md` for failure modes

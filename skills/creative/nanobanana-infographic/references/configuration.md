# Configuration And Verification

## Table of Contents

- [Requirements](#requirements)
- [Environment Variables](#environment-variables)
- [Generate A Prompt Pack](#generate-a-prompt-pack)
- [Run A Live Probe](#run-a-live-probe)
- [Recommended Workflow](#recommended-workflow)

## Requirements

- `python3`
- optional `GEMINI_API_KEY` for live render verification

No SDK is required. The included probe script uses Python's standard library only.

Nano Banana 2 note:

- public launch name: `Nano Banana 2`
- callable Developer API model verified on April 9, 2026: `gemini-3.1-flash-image-preview`

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | only for live probes | authenticates to the Gemini Developer API |

Set the key in the current shell:

```bash
export GEMINI_API_KEY="your-key-here"
```

## Generate A Prompt Pack

Create the four default variants from a structured brief:

```bash
python3 scripts/build_variant_pack.py \
  --brief templates/brief.json \
  --output-dir ./out/prompt-pack
```

This writes:

- `variant-pack.json`
- `variant-pack.md`
- one `.prompt.txt` file per variant

## Render The Whole Pack In Parallel

Render every variant concurrently from the generated pack:

```bash
python3 scripts/render_variant_pack.py \
  --variant-pack ./out/prompt-pack/variant-pack.json \
  --output-dir ./out/renders/batch \
  --model gemini-3.1-flash-image-preview \
  --image-size 512
```

Default behavior:

- launches the whole pack concurrently
- uses one output subdirectory per variant
- writes a top-level `batch-manifest.json`
- keeps failures isolated to the affected variant

## Run A Live Probe

Render one of the generated prompts against Gemini:

```bash
python3 scripts/probe_gemini_image_api.py \
  --prompt-file ./out/prompt-pack/executive-snapshot.prompt.txt \
  --output-dir ./out/renders/executive-snapshot \
  --model gemini-3.1-flash-image-preview \
  --aspect-ratio 16:9 \
  --image-size 1K \
  --passes 1
```

The probe writes:

- `request-01.json`
- `response-01.json`
- saved image files
- `manifest.json`

## Recommended Workflow

1. Fill `templates/brief.json` or create your own brief file with the same shape.
2. Run `scripts/build_variant_pack.py`.
3. Review the four prompt files and adjust only the factual content that needs to be exact.
4. Render the whole pack with `scripts/render_variant_pack.py`.
5. Re-run a single direction with `scripts/probe_gemini_image_api.py` only when you are refining one variant.
6. Keep the strongest 2-3 reviewables and refine from there.
7. Only move to `2K` or `4K` after the `1K` verification pass already looks right.

If the render comes back noisy, shorten the prompt and simplify the composition before raising the model size.

## See Also

- `references/patterns.md` for the variant and iteration system
- `references/api.md` for request structure
- `references/gotchas.md` for failure modes

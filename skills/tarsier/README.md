# tarsier

One-shot creative generator that produces an SVG of a tarsier riding a bicycle, a rasterized 500×500 PNG with padding on white, and a markdown transcript of the run.

See `SKILL.md` for the authoritative instructions. This README is a thin wrapper for repository presentation.

## Invocation

```
/tarsier
```

No arguments. Model name and reasoning level are inferred from the harness when available.

## Output

Three files in a timestamped folder under the caller's current working directory:

```
tarsier-<model>-<reasoning>-<NZST-timestamp>/
├── <base>.svg   # raw SVG
├── <base>.png   # 500x500, 16px padding, white background
└── <base>.md    # transcript with model, reasoning, date, prompt, SVG source
```

## Dependencies

- Python 3
- `rsvg-convert` (from librsvg)
  - macOS: `brew install librsvg`
  - Debian/Ubuntu: `apt install librsvg2-bin`

## Install

```bash
npx --yes skills add https://github.com/jpcaparas/skills tarsier
```

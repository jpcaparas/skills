# sprite-decompose

Installable skill for separating an existing sprite sheet, sprite atlas, or illustration contact sheet into reviewed, tightly cropped transparent PNGs with stable filenames and a deterministic extraction manifest.

## Install

```bash
npx skills add jpcaparas/skills --skill sprite-decompose
```

`SKILL.md` is the canonical workflow. The package includes a typed Pillow/NumPy extractor, a compact region-spec template, a visual-review reference, deterministic tests, and release eval definitions.

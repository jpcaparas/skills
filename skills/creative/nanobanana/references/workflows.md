# Workflows

Ready-to-run recipes. Resolve `scripts/nanobanana.py` from the skill directory. Every command prints a JSON summary with saved paths, dimensions, the interaction ID (when stored), token usage and an estimated USD cost. Inspect each image before reporting it.

## Generate

```bash
python3 scripts/nanobanana.py generate --ratio 4:5 --size 1K --out hero.jpg \
  "A studio photograph of a matte black insulated bottle on a pale sage plinth, soft key light from the left, gentle gradient background. Purpose: product page hero."
python3 scripts/nanobanana.py generate --prompt-file brief.txt --ratio 16:9 --size 2K --thinking high --out slide.jpg
python3 scripts/nanobanana.py generate --size 512 --thinking minimal --out draft.jpg "A rough concept of ..."   # cheapest draft
```

`--dry-run` prints the request (with `<base64>` placeholders) without sending it or needing a key.

## Edit, restyle, inpaint

```bash
python3 scripts/nanobanana.py generate --ref living-room.jpg --out sofa.jpg \
  "Replace the grey sofa with a mustard velvet Chesterfield. Keep everything else exactly the same: camera angle, lighting, plant, lamp, rug, artwork."
python3 scripts/nanobanana.py generate --ref photo.jpg --ref mask.png --out table.jpg \
  "Image 2 is a black-and-white mask for image 1. Inside the white area only, replace the coffee table with a round white marble table. Change nothing outside the mask."
```

Omit `--ratio` to keep the input's shape.

## Multi-reference composite

```bash
python3 scripts/nanobanana.py generate --ref bottle.png --ref sneaker.png --ref headphones.png --ratio 4:3 --out flatlay.jpg \
  "Images 1, 2 and 3 are product shots. Create one top-down flat-lay photograph on a light oak desk featuring all three products exactly as they appear in the references ..."
```

Up to 14 references. Files over 20 MB are uploaded through the Files API automatically (kept 48 hours); smaller files are sent inline.

## Multi-turn refinement

```bash
python3 scripts/nanobanana.py generate --ratio 1:1 --out mascot-1.jpg "A cheerful round kiwi bird mascot, flat vector, white background."
# take interaction_id from the JSON summary
python3 scripts/nanobanana.py generate --continue v1_... --ratio 1:1 --out mascot-2.jpg "Give the same mascot a yellow raincoat. Keep everything else identical."
```

- Pass `--ratio`, `--size` and `--thinking` on every turn; they apply only to that turn.
- Each earlier image is billed again as about 1,150 input tokens (≈ $0.002) per turn.
- Stored interactions are kept 55 days on the paid tier (1 day on free). Use `--no-store` for one-off sensitive work (it cannot be continued) and `delete <interaction_id>` to remove a stored turn.

## Search-grounded

```bash
python3 scripts/nanobanana.py generate --search --ratio 3:4 --out poster.jpg \
  "Search the web for the latest stable Python release and its release date, then create a minimalist announcement poster with the exact version and date."
python3 scripts/nanobanana.py generate --search --image-search --ratio 3:4 --out takahe.jpg \
  "Use image search for accurate references of the takahē (Porphyrio hochstetteri), then create a field-guide card with the heading \"Takahē\"."
```

The summary lists the search queries and sources, and `<out>.search.html` holds Google's search-suggestion widget. Grounded requests use generateContent, so they cannot use `--continue` or size `512`. To keep refining, start a new conversation with the grounded image as `--ref`.

## Batch (half price, asynchronous)

```bash
cat > jobs.jsonl <<'EOF'
{"key": "boat", "prompt": "A paper boat on a puddle, photograph.", "ratio": "1:1", "size": "1K", "thinking": "minimal"}
{"key": "marble", "prompt": "A glass marble on black velvet, macro photograph.", "ratio": "4:3"}
EOF
python3 scripts/nanobanana.py batch-submit jobs.jsonl --name product-shots      # prints batches/...
python3 scripts/nanobanana.py batch-fetch batches/... --out-dir shots --wait 1800  # exit 3 while still running
```

A two-image test batch finished in about 2.6 minutes; Google's target is 24 hours. Inline batches must stay under 20 MB.

## Transparent assets

The model only returns JPEG, and asking for a "transparent background" draws a fake checkerboard. Instead, generate on a flat key colour that does not appear anywhere in the subject, then build the alpha locally:

```bash
# Green subjects: key magenta. Prompt: "... centred on a perfectly flat, uniform pure magenta (#FF00FF) background. No shadow, no gradient, no reflections, no floor."
magick in.jpg \( +clone -fx "1-clamp((min(r,b)-g)*3)" -morphology Erode Disk:1.5 -blur 0x1 \) -alpha off \
  -compose CopyOpacity -composite -channel R -fx "min(r,max(g,b))" -channel B -fx "min(b,max(g,r))" +channel out.png
# Other subjects: key green (#00FF00).
magick in.jpg -channel G -fx "min(g,(r+b)/2+0.04)" +channel \( in.jpg -fx "1-clamp((g-max(r,b)-0.05)*4)" \
  -morphology Erode Disk:2 -blur 0x1 \) -alpha off -compose CopyOpacity -composite out.png
```

A matte basil sprig keyed on magenta was clean; a glossy red apple on green kept a faint pale rim. Composite every cut-out over dark and light backgrounds and inspect the edges before delivering. Use a dedicated matting tool when edges must be perfect.

## Post-processing

| Need | Command |
| --- | --- |
| Smaller than 512 px | generate at `512` or `1K`, then `magick in.jpg -resize 256x256 out.jpg` |
| Exact pixel size | generate at the nearest ratio, then `magick in.jpg -resize 1200x630^ -gravity center -extent 1200x630 out.jpg` |
| PNG or WebP | `magick in.jpg out.png` (no transparency is created) |
| Left-handed subject (no visible text) | `magick in.jpg -flop out.jpg` |
| Exact logo, legal line, or dial | composite the vector or text over the render with ImageMagick or a design tool |
| Review several variants | `magick a.jpg b.jpg c.jpg -resize x400 +append sheet.jpg` and inspect the sheet |

## Free contract check

```bash
python3 scripts/nanobanana.py contract   # exit 0 = matches the helper; 4 = drift
```

It sends deliberately invalid values, which the API rejects with HTTP 400 and a "Supported values" list, so it generates nothing and costs nothing. Rerun it when a request fails unexpectedly or before trusting this skill after a model update.

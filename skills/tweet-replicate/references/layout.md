# Layout

This preset targets a light-theme desktop-style X post crop.

## Fixed heuristics

- canvas width: `594px`
- horizontal padding: `16px`
- content width: `562px`
- media max width: `506px`
- media max height: `606px`
- avatar size: `48px`
- media corner radius: `24px`
- quoted-card media max width: `506px`
- quoted-card media max height: `606px`

## Media sizing rule

Scale the media shell to fit within both:

- `506px` max width
- `606px` max height

Keep aspect ratio. Align the media shell to the left edge of the tweet content column. Render the actual `<video>` or `<img>` at `width: 100%`, `height: 100%`, with `object-fit: cover` so the rounded media frame is fully filled without blank bars inside the shell.

## Capture sizing rule

- measure the final `.tweet-root` height after fonts and media metadata are ready
- record the WebM at the CSS canvas width of `594px` and the measured tweet height
- keep `record_video_size` in CSS pixels; use `device_scale_factor` only for sharper rasterization, not for a larger stage

If the export shows the tweet stranded in the upper-left with empty space on the right or bottom, debug the capture geometry first. Do not retune the snapshot or media CSS until the output frame matches the canvas.

## GIF sizing rule

The GIF is built from the final MP4, not directly from the live source media. That matters because the size cap applies to the local reconstructed post, not just the raw embedded video.

When the first GIF attempt is too large, the renderer reduces:

1. output width
2. frame rate
3. palette size

Do not try to preserve full-quality GIF output at the expense of breaking the 24 MB ceiling.

## Tuning strategy

If the user says the result is off:

1. adjust CSS in `templates/tweet_replica.html`
2. re-render from the same `snapshot.json`
3. compare again before touching extraction
4. if the whole tweet is underfilled or padded, inspect the recorder dimensions before changing media-shell bounds

## What to tune first

- text size and line height
- author row spacing
- media max width and height
- capture width and measured height
- metric row icon size and gaps
- divider spacing

## Intentional non-goals

- authenticated chrome
- dark theme
- browser-native X player controls
- quote-tweet nests deeper than one level
- carousel pagination

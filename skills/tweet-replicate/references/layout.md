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

Scale the primary media to fit within both:

- `506px` max width
- `606px` max height

Keep aspect ratio. Align the media to the left edge of the tweet content column. This gives a good first-pass approximation of the way portrait media is constrained in X's desktop layout.

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

## What to tune first

- text size and line height
- author row spacing
- media max width and height
- metric row icon size and gaps
- divider spacing

## Intentional non-goals

- authenticated chrome
- dark theme
- browser-native X player controls
- quote-tweet nests deeper than one level
- carousel pagination

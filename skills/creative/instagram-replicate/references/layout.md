# Layout

This preset targets a light-theme desktop Instagram post page similar to the logged-out public post view, but without conversion popups or the lower related-post grid.

## Fixed heuristics

- canvas width: `1492px`
- page side padding: `70px`
- top header height: `112px`
- main post max width: `1352px`
- media max width: `678px`
- media max height: `1204px`
- sidebar width: `674px`
- main post top margin: `65px`
- avatar size: `58px`
- comment avatar size: `42px`
- bottom divider margin-top: `72px`

## Media sizing rule

Scale the primary media to fit within both:

- `678px` max width
- `1204px` max height

Keep aspect ratio. Align the media flush to the left edge of the post container. Keep the sidebar the same visual height as the media whenever possible so the post reads like a desktop split-pane Instagram page.

## GIF sizing rule

The GIF is built from the final MP4, not directly from the raw Instagram video. That matters because the size cap applies to the local reconstructed page, not just the source media.

When the first GIF attempt is too large, the renderer reduces:

1. output width
2. frame rate
3. palette size

Do not try to preserve full-quality GIF output at the expense of breaking the 24 MB ceiling.

## Tuning strategy

If the user says the result is off:

1. adjust CSS in `templates/instagram_replica.html`
2. re-render from the same `snapshot.json`
3. compare again before touching extraction

## What to tune first

- media and sidebar widths
- caption and comment spacing
- header logo scale and button sizing
- divider placement inside the sidebar
- bottom action-row icon size and gaps

## Intentional non-goals

- authenticated chrome
- dark theme
- popups or signup modals
- related-post grids
- carousel pagination
- exact browser-native Instagram player controls

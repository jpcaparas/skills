# Gotchas

## Snapshot drift beats CSS drift

If a user says the numbers are wrong, confirm whether they want:

- a fresh live snapshot, or
- the original frozen counts preserved

Do not silently refetch when they are iterating on visuals.

## Media expiry

The remote X video URL is only a lead. The downloaded local media file inside `assets/` is the durable input for rerenders.

## Scope boundary

This version intentionally handles:

- one public status
- one primary media item or no media
- optionally one nested quoted post card with its own media
- a deterministic local rebuild

Do not stretch it into thread compositing or exact X DOM replay without explicitly changing the skill.

## Audio expectations

Playwright's viewport recording does not capture page audio. The renderer muxes the original media audio back into the final MP4 when a local media file contains an audio track.

If the timing looks off, debug the start-playback timing before changing ffmpeg.

The GIF is silent by design.

## MP4 master quality

Treat the MP4 as the master output, not the file that absorbs the GIF budget. Keep the MP4 visually sharp and let the GIF absorb the size-driven quality reductions.

When a rerender is needed, prefer restoring the original local media or re-downloading the highest-quality source variant instead of lowering the MP4 encode target.

## GIF ceiling

The renderer treats the 24 MB GIF limit as a hard constraint. If the first pass is too large, it will reduce frame rate, width, and palette depth until the GIF fits.

That means the GIF can look materially softer than the MP4 for long or visually busy posts. This is a deliberate tradeoff, not a bug.

## Pixel-perfect language

Do not say "exact clone" unless you have literally compared against the live X render and the user accepts the remaining differences. Default language should be:

- "faithful replica"
- "frozen-state rebuild"
- "deterministic local recreation"

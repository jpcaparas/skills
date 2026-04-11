# Gotchas

## Snapshot drift beats CSS drift

If a user says the numbers are wrong, confirm whether they want:

- a fresh live snapshot, or
- the original frozen counts preserved

Do not silently refetch when they are iterating on visuals.

## Media expiry

The remote Instagram video URL is only a lead. The downloaded local media file inside `assets/` is the durable input for rerenders.

## Scope boundary

This version intentionally handles:

- one public Instagram post or reel
- one primary media item or no media
- one clean desktop post-page reconstruction
- a deterministic local rebuild

Do not stretch it into profile-grid reconstruction, carousel playback, Stories, or exact DOM replay without explicitly changing the skill.

## Audio expectations

Playwright's viewport recording does not capture page audio. The renderer muxes the original media audio back into the final MP4 when the local media file contains an audio track.

If the timing looks off, debug the start-playback timing before changing ffmpeg.

The GIF is silent by design.

## GIF ceiling

The renderer treats the 24 MB GIF limit as a hard constraint. If the first pass is too large, it will reduce frame rate, width, and palette depth until the GIF fits.

That means the GIF can look materially softer than the MP4 for long or visually busy posts. This is a deliberate tradeoff, not a bug.

## Pixel-perfect language

Do not say "exact clone" unless you have literally compared against the live Instagram render and the user accepts the remaining differences. Default language should be:

- "faithful replica"
- "frozen-state rebuild"
- "deterministic local recreation"

## Metadata gaps

Instagram does not expose every public-field cleanly through one stable endpoint. The skill fetches counts and comments from `yt-dlp`, the avatar from the public profile page, and verification as best-effort from the public profile DOM.

If an avatar or verification badge cannot be recovered, keep the build working and disclose the fallback.

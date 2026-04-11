---
name: instagram-replicate
description: "Rebuild one public Instagram video post or reel into a deterministic local replica with a frozen snapshot, local HTML/CSS, Playwright capture, MP4 export, and a companion GIF capped under 24 MB. Use when asked to replicate an Instagram post, freeze an Instagram reel into video, make an Instagram video look like the desktop post page offline, or create rerenderable Instagram assets with a saved build folder. Trigger on: 'replicate this Instagram post', 'turn this reel into MP4', 'make this Instagram post into a GIF too', 'freeze this Instagram video locally'. Do NOT use for plain caption extraction, raw media download only, live Instagram browser capture, authenticated pages, carousels, Stories, DMs, or promises of a pixel-perfect private Instagram renderer."
compatibility: "Requires: python3, ffmpeg, ffprobe, yt-dlp, Playwright with Chromium, and outbound HTTPS for snapshotting public Instagram metadata and media."
metadata:
  version: "1.0.0"
  repo_tags:
    - video-generation
    - social-media
---

# Instagram Replicate

Freeze one public Instagram video post or reel into a rerenderable local build that always emits both `instagram-replica.mp4` and `instagram-replica.gif`, with the GIF kept under 24 MB.

Verified against public Instagram pages on April 12, 2026.

## Call-Bluff First

Do not promise a browser-level or forever-stable clone of Instagram. Instagram can change layout, counters drift, login interstitials appear, and media URLs expire. The local renderer is intentionally deterministic rather than a replay of Instagram's private renderer.

What this skill does well:

- capture one public Instagram post into a frozen `snapshot.json`
- download the profile avatar, poster frame, and primary video locally
- rebuild the desktop logged-out post chrome in deterministic local HTML/CSS
- record that local page with Playwright
- export a stable MP4 and a companion GIF in the same directory

## Decision Tree

1. If the user wants one public Instagram video post or reel rebuilt as local video assets, run `scripts/render_instagram_replica.py`.
2. If they only need caption text, counts, comments, or media URLs, use a text/media extraction workflow instead of this skill.
3. If they only need the raw media file, use a media downloader instead of this skill.
4. If they want a live browser capture of Instagram itself, stop and explain that this skill is for deterministic local replicas, not recordings of the real Instagram UI.
5. If they need carousels, profile grids, Stories, DMs, or authenticated states, explain that this version supports one public post page replica with one primary media item.

## Default Save Path Rule

When the user does not give a destination, propose `./pieces/` first. If they agree or do not care, run with `--save-root ./pieces` or let the script default to the current working directory's `pieces/` folder.

The generated build layout stays the same:

```text
<save-root>/instagram-replicate-post-<shortcode>-<timestamp>/
  assets/
  snapshot.json
  instagram-replica.html
  capture.webm
  instagram-replica.mp4
  instagram-replica.gif
```

## Quick Reference

| Task | Command | Why |
| --- | --- | --- |
| Render from a public Instagram post into the default designated save root | `python3 scripts/render_instagram_replica.py 'https://www.instagram.com/p/...' --save-root ./pieces` | Creates a rerenderable build folder under `./pieces/` |
| Re-render the same frozen post later | `python3 scripts/render_instagram_replica.py ./instagram-build/snapshot.json` | Saves beside the snapshot and avoids count drift |
| Keep everything in one named build folder | `python3 scripts/render_instagram_replica.py '<url>' --workdir ./instagram-build` | Leaves snapshot, local assets, HTML, WebM, MP4, and GIF together |
| Inspect the extracted snapshot only | `python3 scripts/fetch_instagram_snapshot.py '<url>' --output ./instagram-build/snapshot.json --asset-dir ./instagram-build/assets` | Useful before layout tuning |
| Record a prepared HTML replica only | `python3 scripts/record_instagram_replica.py ./instagram-build/instagram-replica.html ./instagram-build/capture.webm` | Useful when tuning CSS without refetching |
| Run real pipeline checks against live Instagram URLs | `python3 scripts/probe_instagram_replica.py 'https://www.instagram.com/p/...' --save-root ./tmp-tests --cleanup` | Verifies MP4, GIF, durations, and GIF size cap |

## Scope

### Positive triggers

- "replicate this Instagram post"
- "replicate this reel"
- "turn this Instagram video into mp4 and gif"
- "freeze this Instagram post into video"
- "make this post look like Instagram"
- "Instagram screenshot but playable"
- "preserve caption, counts, comment preview, playback, and a rerenderable build"

### Negative triggers

- simple Instagram caption reading or extraction
- raw media download only
- live embed debugging
- profile grids, feeds, Stories, DMs
- carousel reconstruction
- claims that the output is an exact browser-level clone of Instagram

## Working Rule

Treat the snapshot as the truth, not the live Instagram page. Fetch once, freeze the data, then iterate locally from `snapshot.json`.

## Reading Guide

| Need | Read |
| --- | --- |
| End-to-end workflow, save-root behavior, and artefact layout | `references/workflow.md` |
| Layout heuristics, sizing rules, and tuning knobs | `references/layout.md` |
| Failure modes, GIF sizing, drift, and unsupported cases | `references/gotchas.md` |

## Gotchas

1. Counts drift quickly. Re-render from `snapshot.json` when the user cares about likes or comments from a specific moment.
2. The GIF is a preview asset, not a second master video. The renderer will lower GIF resolution, frame rate, and palette depth as needed to stay under 24 MB.
3. This renderer rebuilds the desktop post chrome locally. It does not claim byte-for-byte or pixel-for-pixel parity with Instagram's own renderer.
4. Public Instagram media URLs can expire. Keep the downloaded local media inside the workdir if the output may need to be reproduced later.
5. Playwright's viewport recording is visual-only. The final MP4 muxes original media audio back in when the local video file has an audio stream. The GIF never carries audio.
6. Login popups, related-post grids, and some account metadata vary by region and time. This skill intentionally renders the clean post page shell instead of replaying every live interstitial.

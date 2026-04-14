---
name: tweet-replicate
description: "Rebuild a public X/Twitter status into a deterministic local replica with a frozen snapshot, local HTML/CSS, Playwright capture, a high-quality MP4 master, and a companion GIF capped under 24 MB. Use when asked to replicate a tweet/X post, freeze a status into video, make a tweet look like X offline, or create rerenderable tweet assets with a saved build folder. Trigger on: 'replicate this tweet', 'turn this X post into MP4', 'make this tweet into a GIF too', 'freeze this status locally'. Do NOT use for plain tweet text extraction, raw media download only, live X browser capture, authenticated pages, DMs, or promises of a pixel-perfect private X renderer."
compatibility: "Requires: python3, ffmpeg, ffprobe, yt-dlp, Playwright with Chromium, and outbound HTTPS for snapshotting and media downloads."
metadata:
  version: "1.0.0"
  repo_tags:
    - video-generation
    - social-media
---

# Tweet Replicate

Freeze a public X/Twitter post into a rerenderable local build that always emits a high-quality `tweet-replica.mp4` master and a companion `tweet-replica.gif` preview, with only the GIF kept under 24 MB.

Verified against live public statuses on April 9, 2026.

## Call-Bluff First

Do not promise a browser-level or forever-stable clone of X. X can change layout, metrics drift, media URLs expire, and the local renderer is intentionally deterministic rather than a replay of X's private renderer.

What this skill does well:

- capture a public status into a frozen `snapshot.json`
- download the avatar and primary media locally at the highest available quality
- rebuild the tweet chrome in deterministic local HTML/CSS
- record the replica viewport with Playwright
- export a high-quality MP4 master and a companion GIF in the same directory

## Decision Tree

1. If the user wants one public X/Twitter post rebuilt as local video assets, run `scripts/render_tweet_replica.py`.
2. If they only need tweet text, metrics, or media URLs, use a text/media extraction workflow instead of this skill.
3. If they only need the raw media file, use a media downloader instead of this skill.
4. If they want a live browser capture of X itself, stop and explain that this skill is for deterministic local replicas, not recordings of the real X UI.
5. If they need full threads, deep quote stacks, carousels, or authenticated states, explain that this version supports one public status plus one nested quoted post card.

## Default Save Path Rule

When the user does not give a destination, propose `./pieces/` first. If they agree or do not care, run with `--save-root ./pieces` or let the script default to the current working directory's `pieces/` folder.

The generated build layout stays the same:

```text
<save-root>/tweet-replicate-status-<id>-<timestamp>/
  assets/
  snapshot.json
  tweet-replica.html
  capture.webm
  tweet-replica.mp4
  tweet-replica.gif
```

## Quick Reference

| Task | Command | Why |
| --- | --- | --- |
| Render from a status URL into the default designated save root | `python3 scripts/render_tweet_replica.py 'https://x.com/.../status/...' --save-root ./pieces` | Creates a rerenderable build folder under `./pieces/` with a high-quality MP4 master |
| Re-render the same frozen post later | `python3 scripts/render_tweet_replica.py ./tweet-build/snapshot.json` | Saves beside the snapshot and avoids count drift |
| Keep everything in one named build folder | `python3 scripts/render_tweet_replica.py '<url>' --workdir ./tweet-build` | Leaves snapshot, local high-quality assets, HTML, WebM, MP4, and GIF together |
| Inspect the extracted snapshot only | `python3 scripts/fetch_tweet_snapshot.py '<url>' --output ./tweet-build/snapshot.json --asset-dir ./tweet-build/assets` | Useful before layout tuning |
| Record a prepared HTML replica only | `python3 scripts/record_tweet_replica.py ./tweet-build/tweet-replica.html ./tweet-build/capture.webm` | Useful when tuning CSS without refetching |
| Run real pipeline checks against live tweet URLs | `python3 scripts/probe_tweet_replica.py 'https://x.com/.../status/...' --save-root ./tmp-tests --cleanup` | Verifies MP4, GIF, durations, and GIF size cap |

## Scope

### Positive triggers

- "replicate this tweet"
- "replicate this X post"
- "turn this tweet into mp4 and gif"
- "freeze this tweet into video"
- "make this status look like X"
- "tweet screenshot but playable"
- "preserve caption, counts, playback, and a rerenderable build"

### Negative triggers

- simple tweet reading or extraction
- raw media download only
- live embed debugging
- feeds, search pages, DMs, Spaces
- multi-post thread cinematics
- claims that the output is an exact browser-level clone of X

## Working Rule

Treat the snapshot as the truth, not the live tweet page. Fetch once, freeze the data, keep the downloaded local media at full quality, then iterate locally from `snapshot.json`.

## Reading Guide

| Need | Read |
| --- | --- |
| End-to-end workflow, save-root behavior, and artefact layout | `references/workflow.md` |
| Layout heuristics, sizing rules, and tuning knobs | `references/layout.md` |
| Failure modes, GIF sizing, drift, and unsupported cases | `references/gotchas.md` |

## Gotchas

1. Counts drift quickly. Re-render from `snapshot.json` when the user cares about likes, reposts, or views from a specific moment.
2. The GIF is a preview asset, not a second master video. The renderer keeps the MP4 as the high-quality master and only lowers GIF resolution, frame rate, and palette depth as needed to stay under 24 MB.
3. This renderer rebuilds the tweet chrome locally. It does not claim byte-for-byte or pixel-for-pixel parity with X's own renderer.
4. Public X media URLs can expire. Keep the downloaded local media inside the workdir if the output may need to be reproduced later.
5. Playwright's viewport recording is visual-only. The final MP4 preserves the recorded visual master at high quality and muxes original media audio back in when a local video file has an audio stream. The GIF never carries audio.
6. One nested quoted post is supported, including quoted video playback, but deeper quote chains and full thread reconstruction are out of scope.

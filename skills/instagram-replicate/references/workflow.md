# Workflow

`{{ skill:instagram-replicate }}` is a deterministic rebuild pipeline, not a live embed.

## Pipeline

1. Offer a designated save root first. Default to `./pieces/` if the user does not care.
2. Run `scripts/fetch_instagram_snapshot.py` on a public Instagram post or reel URL.
3. Save a frozen `snapshot.json`.
4. Download the avatar, poster frame, and primary media into the chosen asset directory.
5. Run `scripts/render_instagram_replica.py` to turn the snapshot into local HTML.
6. Record that HTML with `scripts/record_instagram_replica.py`.
7. Transcode the recorded WebM to MP4 and mux original audio when present.
8. Derive a GIF from the final MP4 and step down quality until it fits under 24 MB.

## Recommended build layout

```text
pieces/instagram-replicate-post-<shortcode>-<timestamp>/
  assets/
    avatar.jpg
    media.mp4
    poster.jpg
  snapshot.json
  instagram-replica.html
  capture.webm
  instagram-replica.mp4
  instagram-replica.gif
```

## Primary command

```bash
python3 scripts/render_instagram_replica.py \
  'https://www.instagram.com/p/DXACsN4oG6L/' \
  --save-root ./pieces
```

This writes to `./pieces/` by default unless `--save-root`, `--workdir`, or `--output` points somewhere else.

## Why freeze first

- the live page can change
- counts can drift between attempts
- media URLs can expire
- login popups and page chrome can vary by region
- CSS iteration is much faster once everything is local

## Re-render loop

When the user says "make it closer":

1. keep the existing `snapshot.json`
2. tweak `templates/instagram_replica.html`
3. re-run `scripts/render_instagram_replica.py ./instagram-build/snapshot.json`

Do not refetch unless the user explicitly wants a fresh live snapshot.

## Test helper

Use `scripts/probe_instagram_replica.py` when you want a structured live test instead of hand-running the workflow:

```bash
python3 scripts/probe_instagram_replica.py \
  'https://www.instagram.com/p/DXACsN4oG6L/' \
  --save-root ./tmp-tests \
  --cleanup
```

The probe verifies that:

- the snapshot and local assets exist
- the MP4 exists and has non-zero duration
- the GIF exists and stays under the configured byte limit
- the output summary is parseable JSON

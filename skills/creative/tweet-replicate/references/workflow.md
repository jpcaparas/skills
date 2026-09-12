# Workflow

`{{ skill:tweet-replicate }}` is a deterministic rebuild pipeline, not a live embed.

## Pipeline

1. Offer a designated save root first. Default to `./pieces/` if the user does not care.
2. Run `scripts/fetch_tweet_snapshot.py` on a public status URL.
3. Save a frozen `snapshot.json`.
4. Download the avatar and primary media into the chosen asset directory, preferring the highest-quality media variant available.
5. Run `scripts/render_tweet_replica.py` to turn the snapshot into local HTML.
6. Record that HTML with `scripts/record_tweet_replica.py`.
7. Transcode the recorded WebM to a high-quality MP4 master and mux original audio when present.
8. Derive a GIF from the final MP4 and step down only the GIF quality until it fits under 24 MB.

## Recommended build layout

```text
pieces/tweet-replicate-status-<id>-<timestamp>/
  assets/
    avatar.jpg
    media.mp4
  snapshot.json
  tweet-replica.html
  capture.webm
  tweet-replica.mp4
  tweet-replica.gif
```

## Primary command

```bash
python3 scripts/render_tweet_replica.py \
  'https://x.com/kunchenguid/status/2041900381350117648' \
  --save-root ./pieces
```

This writes to `./pieces/` by default unless `--save-root`, `--workdir`, or `--output` points somewhere else.

## Why freeze first

- the live page can change
- counts can drift between attempts
- media URLs can expire
- CSS iteration is much faster once everything is local

## Re-render loop

When the user says "make it closer":

1. keep the existing `snapshot.json`
2. tweak `templates/tweet_replica.html`
3. re-run `scripts/render_tweet_replica.py ./tweet-build/snapshot.json`

Do not refetch unless the user explicitly wants a fresh live snapshot.

## Test helper

Use `scripts/probe_tweet_replica.py` when you want a structured live test instead of hand-running the workflow:

```bash
python3 scripts/probe_tweet_replica.py \
  'https://x.com/kunchenguid/status/2041900381350117648' \
  --save-root ./tmp-tests \
  --cleanup
```

The probe verifies that:

- the snapshot and local assets exist
- the MP4 exists and has non-zero duration
- the GIF exists and stays under the configured byte limit
- the output summary is parseable JSON

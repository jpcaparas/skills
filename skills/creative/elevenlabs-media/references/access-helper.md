# Access, billing, transport and recovery

## Authentication is not entitlement

Send `xi-api-key` from `ELEVENLABS_API_KEY` only to the approved ElevenLabs API origin. The helper pins `https://api.elevenlabs.io`; it does not support regional residency routing. If residency is required, consult the [official residency contract](https://elevenlabs.io/docs/overview/administration/data-residency) and configure the official SDK for that account. Do not silently send residency-bound data to the default origin.

Keys can restrict endpoint scopes, credits, source IPs and expiry. Seven enabled media switches do not imply access to user details, models, voices, history, dubbing, assets or Studio. A `401 missing_permissions` is not proof the key is invalid. Read the missing-scope message privately or request the exact necessary scope; do not rotate or broaden the key automatically.

Useful reads:

| Endpoint | Use |
| --- | --- |
| `GET /v1/user/subscription` | Plan, credit usage/limit and extension settings; requires `user_read` |
| `GET /v1/models` | Speech capabilities and request text limits; requires `models_read` |
| `GET /v2/voices` | Workspace-accessible voices; paginate `has_more`/`next_page_token` |
| `GET /v1/history` | Recover generated speech where history is enabled and permitted |
| `GET /v1/flows/image` or `GET /v1/flows/video` | Reconcile API-created visual jobs; cursor pagination |

Usage reads are observations, not reserved budget; another caller can spend concurrently. Provider key caps are the hard control. Never enable overage, raise limits or upgrade plans without approval. Music generation/upload, previews, training and dubbing can incur charges even though their response is not a final artifact. There is no verified general visual cost-estimation endpoint. Do not invent one or treat the speech-oriented model catalog as a pricing catalog.

Sources: [authentication](https://elevenlabs.io/docs/api-reference/authentication), [key controls](https://elevenlabs.io/docs/overview/administration/workspaces/api-keys), [subscription](https://elevenlabs.io/docs/api-reference/user/subscription/get), [errors](https://elevenlabs.io/docs/eleven-api/resources/errors).

## Helper wire contract

Set `EL` to the installed `scripts/elevenlabs_media.py`. Use Python 3.11+; the helper has no package dependencies. Parent output directories must exist. JSON/file paths are local, not uploaded implicitly.

```bash
python3 "$EL" request GET /v1/user/subscription --out subscription.json --execute
python3 "$EL" request GET /v1/models --out models.json --execute

# request.json holds a JSON object. No body content or key is printed.
python3 "$EL" request POST /v1/music --json request.json \
  --query output_format=auto --expect audio --out song.mp3 --execute

# Multipart names are API-specific. Repeated --file sends repeated form parts.
python3 "$EL" request POST /v1/speech-to-text \
  --field model_id=scribe_v2 --field diarize=true \
  --file file=meeting.wav --out transcript.json --execute

# Long text or JSON-encoded form values can come from a local text file.
python3 "$EL" request POST /v1/forced-alignment \
  --file file=narration.mp3 --field-file text=transcript.txt \
  --out alignment.json --execute
```

- Without `--execute`, `request` only builds and checks the local request. It does **not** validate plan entitlement, every endpoint field, media content or price. It does not require the key in preview mode.
- `--json` and multipart `--field`/`--file` are mutually exclusive. `--field-file name=path` reads UTF-8 text, not a file part. `--query name=value` handles URL encoding. Never pass auth headers or a key on the command line.
- Output modes: `--expect json` by default; `audio`, `image`, `video`, `zip` enforce the MIME family. `raw` preserves multipart/SSE/NDJSON or raw PCM without decoding; choose it intentionally, not to mask an unexpected JSON error.
- The helper creates private files with no overwrite: `output`, `output.meta.json`, and an in-progress `output.part`. Receipts retain safe response headers, byte count and SHA-256; they omit the key, request body and signed URL. JSON result files can still contain private transcripts or signed URLs: do not commit them.
- Headers are saved before reading media. Failed/interrupted work leaves a non-complete receipt and any partial bytes, never a completed output. Reconcile those files and the request/job ID. Choosing a new filename and re-running POST is still a new billable request.
- `--timeout` is a per-socket-I/O timeout, not a total rendering deadline. Uploads spool to disk, downloads stream in 64 KiB blocks. Defaults of 512 MiB upload and 1 GiB output are local safeguards, **not provider limits**; raise them deliberately. JSON responses/records are capped at 16 MiB; use a streaming SDK for larger JSON.
- TLS is verified. Redirects and automatic retries are disabled. Proxy environment variables are not used. Downloads only accept HTTPS on `storage.googleapis.com` or ElevenLabs subdomains, without the API key. If the provider returns another CDN, verify its origin before using a separate client; do not broaden to arbitrary URLs to bypass an error.
- Exit 0 means local preview/completion succeeded, 1 means operational failure, 2 means invalid CLI syntax. An HTTP create success can still mean only “queued.”

## Polling and downloads

For Flows image/video/speech generation only:

```bash
python3 "$EL" wait image "$GENERATION_ID" --deadline 600 --out completed.json
python3 "$EL" download --from-json completed.json \
  --expect image --out result.png

# Current dubbing target completion uses a nested URL instead.
python3 "$EL" download --from-json target.json \
  --url-field outputs.lossless_audio --expect audio --out dub.flac
```

The wait loop polls images at least two seconds apart and video at least ten, with exponential backoff capped at a minute. It never resubmits jobs. It stops on failure, unfamiliar state, request error or deadline; restart a read with the same ID. A network read begun before the deadline can run until its socket timeout. For production callbacks, authenticate on the original raw body, deduplicate events, acknowledge promptly, and reconcile with GET. Configure callback destinations only with approval; never default to broadcasting private outputs to every workspace webhook.

Signed URLs expire; re-fetch the owning result for a fresh URL. Do not persist signed URLs as stable IDs or forward ElevenLabs credentials to object storage.

## Decode timing audio without losing alignment

```bash
python3 "$EL" decode-audio speech-timing.json --out speech.mp3
python3 "$EL" decode-audio speech-stream.ndjson --ndjson --out speech.mp3
```

These commands decode REST `audio_base64` records, in order, without deleting the timing source. They do not parse WebSocket `audio`, voice-design `audio_base_64`, or music SSE. Preserve per-chunk alignments and offsets; simply concatenating timing arrays can give incorrect global timestamps.

## Failure decisions

| Observation | Response |
| --- | --- |
| 401 missing scope / expired or invalid key | Distinguish the error code and necessary scope; do not dump credentials |
| 402 paid plan or quota failure | Stop spending; report entitlement/budget boundary |
| 403 IP/model/region access denial | Check documented access; never route around regional restrictions |
| 400/422 incompatible parameters | Inspect endpoint-specific schema and local request; correct only the rejected request |
| 429 concurrency/rate limit | Reduce concurrency; obey `Retry-After` for safe reads; don't replay an ambiguous POST |
| 5xx, disconnect, timeout | Preserve receipt/partial and IDs; verify whether creation happened before considering a retry |
| Completed job but expired URL | Refresh GET, download again without a new generation |
| HTTP success with error JSON or wrong MIME | Do not label it an MP3/image; inspect the response contract |

`enable_logging=false` is an enterprise zero-retention feature on supported endpoints, not a universal privacy promise. It can remove history/stitching/recovery features. Confirm retention, region and permission before sending sensitive medical, personal or confidential material.

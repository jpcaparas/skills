# Dubbing projects, language targets and legacy resources

## Current project API

Create `POST /v1/dubbing/project` with multipart exactly one `file` or public `source_url`, optional source language, initial target language, reference and configured webhook IDs. Current default `model_id=dubbing_v2` is fixed at project creation. Language identifiers are BCP-47 with supported-dialect restrictions, not necessarily the two-letter IDs used by legacy dubbing.

```bash
python3 "$EL" request POST /v1/dubbing/project \
  --file file=authorized-source.mp4 --field model_id=dubbing_v2 \
  --field target_language=es-MX --field reference=local-job-123 \
  --out project.json --execute
```

Creation returns HTTP 201 with `project_id`, status and `language_ids`. **Creating a project incurs a minimum one-language charge even before output exists**, prepaying the first target. Additional targets are charged separately. `reference` is correlation metadata, not a verified idempotency key. Upload ceiling is 3 GiB; the helper's default local limit is smaller and must be raised deliberately for a larger authorized upload.

Track these separately:

| Resource | Read route | States / completion |
| --- | --- | --- |
| Project/source | `GET /v1/dubbing/project/{project_id}` | `queued → preparing → ready` or `failed`; ready means transcription/source preparation, **not a finished dub** |
| Language target | `GET /v1/dubbing/project/{project_id}/language/{language_id}` | `queued → processing → completed` or `failed`; edits may make it `stale` |
| Output | Target's `outputs.lossless_audio` | Signed FLAC URL, expires after about one hour; refresh target GET |

Add a target using `POST /v1/dubbing/project/{project_id}/language` with JSON `{"target_language":"fr"}` and supported optional voice settings. It may queue before source readiness. Keep project ID, language ID and requested language together; they are not interchangeable. List projects/targets for reconciliation, not an unbounded full-workspace scan.

Callbacks include `dubbing_project_ready`, `dubbing_project_failed`, `dubbing_language_completed`, `dubbing_language_failed`. Delivery can repeat; authenticate, deduplicate and reconcile against GET. Inspect error code, retryability and warnings rather than matching human-readable wording. An automatic retry of a failed target is still new work unless documented otherwise.

Sources: [create](https://elevenlabs.io/docs/api-reference/dubbing/create-project), [targets](https://elevenlabs.io/docs/api-reference/dubbing/language-targets/create-language-target), [target outputs](https://elevenlabs.io/docs/api-reference/dubbing/language-targets/get-language-target), [capabilities](https://elevenlabs.io/docs/overview/capabilities/dubbing).

## Transcript edits do not regenerate audio

Read source `GET /v1/dubbing/project/{project_id}/transcript` after ready; target `GET /v1/dubbing/project/{project_id}/language/{language_id}/transcript` after its first output. Early reads may return conflict. Segments have identity, text/translation, speaker and `start_s`/`end_s` timing.

Enterprise editing supports source/target segment PATCH and target `POST .../transcript/regenerate` (202). Source corrections can affect translations; targeted translation edits preserve deliberate wording. Track `revision` against `output_revision`: a stale output can remain downloadable but is not the revised dub. Repeated regeneration without edits or during processing may return 409. Bring-your-own transcripts/translations are separate enterprise capabilities.

Keep the original source and downloaded prior output. Verify translation fidelity, names, speaker consistency, pacing and lip/timing compatibility. Downloaded FLAC does not automatically contain the original video's visual track; mux locally as needed, preserving the source and checking final synchronization.

Source: [refine and regenerate](https://elevenlabs.io/docs/eleven-api/guides/how-to/dubbing/refine-and-regenerate).

## Legacy API: keep its IDs and states separate

Only use the legacy workflow for an existing `dubbing_id` or a supported need it owns:

| Operation | Contract |
| --- | --- |
| Create | `POST /v1/dubbing`, multipart `file` or source URL, `source_lang`, `target_lang`; optional `dubbing_studio=true` |
| Status | `GET /v1/dubbing/{dubbing_id}`; wait for **`dubbed`**, stop on `failed` |
| Original auto output | `GET /v1/dubbing/{dubbing_id}/audio/{language_code}`; audio/video stream |
| Transcript | `GET /v1/dubbing/{dubbing_id}/transcript/{language_code}?format_type=srt`; also `webvtt`/`json` with Studio restrictions |
| Editable resource | `GET /v1/dubbing/resource/{dubbing_id}` |
| Edit segment | `PATCH /v1/dubbing/resource/{dubbing_id}/segment/{segment_id}/{language}` |
| Transcribe | `POST .../transcribe` with segment IDs; no automatic translate/dub |
| Translate | `POST .../translate` with segments/languages; no automatic dub |
| Dub | `POST .../dub` with segments/languages; fills missing earlier stages |
| Render edited resource | `POST .../render/{language}` with render type, then poll the resource's `renders[render_id]` |

Legacy render states are `processing → complete|failed` (not `completed`). Download `media_ref.url`. The original auto-output endpoint does not represent later Studio edits. Dub all intended segments before rendering; undubbed segments can be omitted. Manual CSV mode is experimental. `disable_voice_cloning=true` uses similar library voices and can require spare voice slots and library-add permission.

Sources: [legacy create](https://elevenlabs.io/docs/api-reference/legacy/dubbing/create), [legacy resource](https://elevenlabs.io/docs/api-reference/legacy/dubbing/resources/get-resource), [legacy render](https://elevenlabs.io/docs/api-reference/legacy/dubbing/resources/render-project).

## Realtime translation/dubbing is a separate surface

The current documentation index lists `WebSocket /v1/dubbing/realtime` and `WebSocket /v1/translate/realtime` references. Their detailed contracts were inaccessible during this package's research. Do not infer framing, supported languages, entitlement or a working example from those names. Fetch the [dubbing realtime reference](https://elevenlabs.io/docs/api-reference/dubbing/realtime/v-1-dubbing-realtime) or [translate realtime reference](https://elevenlabs.io/docs/api-reference/realtime-translate/v-1-translate-realtime) when requested, and report blocked access rather than substituting batch dubbing as “live.”

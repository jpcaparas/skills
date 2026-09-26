# Original music, plans, edits and stems

## Select the actual request contract

| Operation | Method/path | Request → response |
| --- | --- | --- |
| Compose | `POST /v1/music` | JSON → binary audio; retain `song-id` header |
| Stream audio | `POST /v1/music/stream` | JSON → binary chunks, not SSE |
| Compose plus metadata | `POST /v1/music/detailed` | JSON → `multipart/mixed` metadata and audio |
| Stream plus metadata | `POST /v1/music/detailed/stream` | JSON → SSE, with base64 audio events |
| Plan without audio | `POST /v1/music/plan` | JSON → composition plan |
| Import music for edits | `POST /v1/music/upload` | Multipart `file` → song ID and optional analysis; **billed** |
| Separate stems | `POST /v1/music/stem-separation` | Multipart `file` → ZIP |
| Score video | `POST /v1/music/video-to-music` | Multipart repeated `videos` → audio, not a muxed video |
| Custom music model | `GET/POST /v1/music/finetunes` | Separate training/management workflow |

Music API access requires a paid plan. The published default still uses `music_v1`; explicitly select the intended model. Current `music_v2`/`music_v2_5` plans use **chunks**, while v1 uses **sections**. Do not translate SDK field names directly into REST camelCase.

Sources: [compose](https://elevenlabs.io/docs/api-reference/music/compose), [quickstart](https://elevenlabs.io/docs/eleven-api/guides/cookbooks/music), [live schema](https://api.elevenlabs.io/openapi.json).

## Prompt-led instrumental

```json
{
  "model_id":"music_v2_5",
  "prompt":"Original warm marimba and acoustic bass, playful rhythmic movement, a gentle resolved ending.",
  "music_length_ms":10000,
  "force_instrumental":true,
  "store_for_inpainting":true
}
```

Use **either** `prompt` or `composition_plan`. Prompt max 4,100 characters. `music_length_ms` is 3,000–600,000 for prompt mode, or omit it for model-selected duration. The overview still mentions five minutes; the endpoint/plan schema allows ten. Verify before a large spend. `force_instrumental` is prompt-only; false does not force singing. `seed` is plan-only, 0–2,147,483,647, and is not a reproducibility guarantee.

Specify musical function, instrumentation, energy, tempo and evolution when useful; do not require these fields for every creative brief. Use original lyrics and descriptive musical attributes rather than artist/band names or copyrighted lyrics. On `bad_prompt`/`bad_composition_plan`, inspect returned suggestions privately, then revise within the user's brief—do not evade moderation.

## Exact lyrics and structure

For v2/v2.5:

```json
{
  "model_id":"music_v2_5",
  "composition_plan":{"chunks":[
    {"text":"[Verse]\nMorning light is on its way\nWe begin another day",
     "duration_ms":10000,"positive_styles":["warm acoustic pop","clear vocals"]},
    {"text":"[Outro]","duration_ms":5000,"positive_styles":["gentle marimba","instrumental"],"negative_styles":["vocals"]}
  ]}
}
```

Generated chunks require `text`, `duration_ms` and `positive_styles`. Text accepts section labels `[Verse]`, lyrics separated by newlines, and `{directions}`. Parentheses represent sung phonetic sounds, not generic stage directions. Empty lyric content plus appropriate styles expresses instrumental chunks; do not add prompt-only `force_instrumental` to a plan request.

Up to 30 chunks/sections; generated chunks last 3–120 seconds and complete v2/v2.5 plans 3 seconds–10 minutes. Style lists have at most 50 entries. Chunk text max 6,132 characters; section/lyric sublimits also apply (up to 30 lines, 200 characters each). Use English style descriptions; lyrics may be multilingual. `respect_sections_durations` applies only to v1; v2/v2.5 enforce durations.

For v1, a plan contains `positive_global_styles`, `negative_global_styles`, and `sections[]` with `section_name`, `positive_local_styles`, `negative_local_styles`, `duration_ms`, and `lines`. Do not send that plan to v2.5.

`POST /v1/music/plan` accepts `prompt`, optional `music_length_ms`, `model_id`, and `source_composition_plan`. It produces a plan, not audio. Inspect/edit it before submitting it as `composition_plan`; creating a plan is not evidence a song has been generated.

Source: [composition plans](https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans).

## Extend, replace and condition

There is no need to invent a `POST /music/edit` route. Compose using a mixture of generated chunks and references:

```json
{
  "model_id":"music_v2_5",
  "composition_plan":{"chunks":[
    {"song_id":"STORED_SONG_ID","range":{"start_ms":0,"end_ms":5000}},
    {"text":"[Outro]","duration_ms":5000,"positive_styles":["soft piano","instrumental"],"negative_styles":["vocals"]}
  ]}
}
```

Replace the symbolic ID with an actual stored song long enough for that range. References copy existing audio; generated chunks replace/add material. `conditioning_ref: {song_id, range}` instead guides new generation. Conditioning ranges are at most 30 seconds; minimum reference interval 50 ms. `context_adherence=low|medium|high` controls neighbor consistency; `condition_strength=low|medium|high|xhigh` controls conditioning. Inspect transitions: matching duration does not prove matching tempo, key or phrasing.

Request `store_for_inpainting=true` on the original generation, or import owned/authorized audio. Upload uses `file`, optional `extract_composition_plan=music_v2_5`, `with_timestamps`, `with_waveform_visual`. Boolean extraction is deprecated and yields the v1 format. **Upload is priced like generation; copyright-screening rejection still costs half the request price.** Do not use it as free asset storage or upload third-party music to test the filter.

Sources: [inpainting](https://elevenlabs.io/docs/eleven-api/guides/how-to/music/inpainting), [upload](https://elevenlabs.io/docs/api-reference/music/upload).

## Formats and metadata are endpoint-specific

Compose-family `output_format=auto` selects `mp3_44100_128` for v1 and `mp3_48000_192` for v2/v2.5. The newer family allows additional MP3 rates/bitrates; stem separation/video-to-music use a narrower enum without `auto`. Do not copy formats between them. `sign_with_c2pa` is MP3-only on endpoints that expose it; neither streaming endpoint documents this flag.

Detailed output contains a composition plan and `song_metadata` (title, description, genres, languages, explicit flag), optional word timestamps in **milliseconds**, and waveform values (four samples/second, −1000…1000). Save the original metadata.

- `POST /v1/music/detailed` returns multipart, not one JSON object or MP3. Preserve its full `Content-Type` boundary in the receipt and parse with a MIME parser/compatible SDK. Do not split binary bytes on a guessed delimiter or trust a supplied filename as a filesystem path.
- `POST /v1/music/detailed/stream` returns SSE; join `data:` lines per event and decode audio chunks individually. The public schema does not fully specify every event payload. Inspect the installed SDK/current contract before building a parser. A line-by-line JSON reader is not a general SSE decoder.
- The helper's `--expect raw` saves the envelope unchanged for these two endpoints. It does not unpack them. `decode-audio` is for speech timing responses, not music SSE.

Sources: [detailed](https://elevenlabs.io/docs/api-reference/music/compose-detailed), [detailed stream](https://elevenlabs.io/docs/api-reference/music/compose-detailed-stream), [streaming guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/music/streaming).

## Stems, scoring and finetunes

```bash
python3 "$EL" request POST /v1/music/stem-separation \
  --file file=owned-song.mp3 --field stem_variation_id=six_stems_v1 \
  --query output_format=mp3_44100_128 --expect zip --out stems.zip --execute

python3 "$EL" request POST /v1/music/video-to-music \
  --file videos=clip.mp4 --field model_id=music_v2_5 \
  --expect audio --out soundtrack.mp3 --execute
```

Stem variants are `two_stems_v1` and default `six_stems_v1` (vocals, drums, bass, guitar, piano, other). Inspect ZIP entry paths, symlinks, declared sizes and total expansion before extraction; never blindly extract provider archives into the repository. Listen for leakage and reconstruction artifacts.

Video scoring accepts 1–10 videos concatenated in request order, 200 MB/600 seconds combined, optional description up to 1,000 characters and up to ten tags. Mux returned audio locally only after checking synchronization and preserving the source audio when wanted.

Finetunes have list/get/create/update/delete endpoints. Creation uses multipart `name`, `primary_genre`, optional authorized `files`, `tags`, visibility and base model. Training is a separate costly, persistent action; do not create one as an ordinary music spike. Confirm the ready state before using `finetune_id`; failures/progress and workspace visibility matter.

Sources: [stems](https://elevenlabs.io/docs/api-reference/music/separate-stems), [video-to-music](https://elevenlabs.io/docs/api-reference/music/video-to-music), [finetunes](https://elevenlabs.io/docs/api-reference/music/finetunes/create).

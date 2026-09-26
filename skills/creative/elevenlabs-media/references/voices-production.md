# Voices, pronunciation and long-form production

## Discover voices and capability

`GET /v2/voices` supports search/filters and pages up to 100. Iterate `has_more`/`next_page_token`; do not trust a changing `total_count` as a stopping rule. `GET /v1/voices/{voice_id}` returns details/settings/fine-tuning. `GET /v1/shared-voices` searches the library, which is distinct from the workspace's usable voice list. Adding a shared voice or editing default settings changes persistent account state.

Inspect speech-model flags including TTS/voice conversion, style, speaker boost, professional-voice serving, language coverage and `maximum_text_length_per_request`. Deprecated per-tier text fields are not the enforced limit. If model reads are denied, use current documentation with uncertainty; do not silently grant permissions or present a static voice ID as discovered.

Sources: [voices](https://elevenlabs.io/docs/api-reference/voices/search), [models](https://elevenlabs.io/docs/api-reference/models/list).

## Design or remix, then choose whether to save

Design `POST /v1/text-to-voice/design`:

```json
{"voice_description":"A warm adult narrator with measured pacing, clear diction and a softly resonant delivery.","model_id":"eleven_ttv_v3","auto_generate_text":true}
```

Description 20–1,000 characters; supplied preview text 100–1,000 characters or request automatic text. The default is `eleven_multilingual_ttv_v2`; v3 design is **`eleven_ttv_v3`**, not TTS `eleven_v3`. Response `previews[]` contains `generated_voice_id`, `audio_base_64`, media type and duration. `stream_previews=true` returns IDs for `GET /v1/text-to-voice/{generated_voice_id}/stream` instead of inline audio.

Previewing does not save a reusable voice. After selecting/approving a preview, `POST /v1/text-to-voice` with `voice_name`, `voice_description`, `generated_voice_id` returns the durable **`voice_id`**. Do not use the preview ID in TTS. Check voice slots and authority before saving; do not fill the account with experimental voices.

Remix uses `POST /v1/text-to-voice/{voice_id}/remix` with a description of desired changes, optional generated/supplied preview text and supported guidance/session fields. It returns previews rather than silently changing the original. Reference audio in design/remix requires rights/consent; design is not an impersonation loophole.

Sources: [design](https://elevenlabs.io/docs/api-reference/text-to-voice/design), [save](https://elevenlabs.io/docs/api-reference/text-to-voice/create), [remix](https://elevenlabs.io/docs/api-reference/text-to-voice/remix).

## Cloning has explicit consent and verification boundaries

- Instant voice cloning: `POST /v1/voices/add`, multipart `name` plus repeated `files`. Response has `voice_id` and `requires_verification`; honor verification. One–two minutes of clean single-speaker material is quality guidance, not an API minimum.
- Professional cloning starts at `POST /v1/voices/pvc`, then authorized sample upload, verification and training. Only the owner may professionally clone/verify **their own voice**, even if another person gave consent. Have that person create it and share it instead.
- Voice creation is not training completion. Inspect model-specific fine-tuning state before synthesis. Do not automate or bypass identity/voice verification, fabricate consent, or delete samples/voices as implicit cleanup.

Sources: [IVC](https://elevenlabs.io/docs/api-reference/voices/ivc/create), [consent and quality](https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/instant-voice-cloning), [PVC ownership](https://elevenlabs.io/docs/help-center/product/voices/voice-cloning/can-i-create-a-professional-voice-clone-of-someone-elses-voice).

## Pronunciation dictionaries

Create dictionaries from PLS files (`POST /v1/pronunciation-dictionaries/add-from-file`) or rules (`.../add-from-rules`), then reference the returned dictionary/version IDs in supported synthesis requests. Alias and phoneme rules are model-dependent. Updates/add/remove/set-rules are persistent mutations and can affect collaborators. Pin the intended version for reproducibility; test a short phrase before converting a book. TTS supports up to three dictionary locators.

Do not “fix pronunciation” by editing the user's visible source text without preserving the original. A pronunciation alias and a content correction serve different purposes.

Sources: [dictionary guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/pronunciation-dictionaries), [dictionary API](https://elevenlabs.io/docs/api-reference/pronunciation-dictionaries/create-from-rules).

## Studio: chapters and snapshots, not one giant TTS request

For books, articles and long-form productions, Studio provides project creation/import, project/chapter content editing, conversion, and audio snapshots:

| Intent | Endpoint family |
| --- | --- |
| List/create projects | `GET/POST /v1/studio/projects`; creation uses multipart |
| Read/update a project | `GET/POST /v1/studio/projects/{project_id}` |
| Update imported content | `POST .../{project_id}/content`, multipart |
| Convert project | `POST .../{project_id}/convert` |
| Chapters | `.../{project_id}/chapters`, per-chapter reads/edits/conversion |
| Snapshots | `GET .../{project_id}/snapshots`, corresponding chapter snapshots |
| Retrieve a render | Snapshot `POST .../stream` for audio or `.../archive` for ZIP |

Creation/import, conversion and successful downloadable snapshot are different milestones. Inspect the current project schema for required default voices/model, imported source and conversion flags; do not default to converting all chapters on an edit. Snapshot IDs capture the render version; an old snapshot remains old after content changes. Treat imports, shared changes and conversions as authorized persistent/paid work. Verify chapter order, missing text, voices, pronunciation and final audio.

Sources: [Studio API scope](https://elevenlabs.io/docs/api-reference/studio-api-information), [create project](https://elevenlabs.io/docs/api-reference/studio/add-project), [snapshots](https://elevenlabs.io/docs/api-reference/studio/get-snapshots).

## Generate a podcast from source material

`POST /v1/studio/podcasts` uses JSON with required `model_id`, `mode`, `source`. For a conversation, mode is `{type:"conversation",conversation:{host_voice_id,guest_voice_id}}`; bulletin uses its own single-voice shape. Source can be text, a URL, or a list of supported sources. Select actual accessible voices.

Optional `duration_scale=short|default|long`, `language`, intro/outro, instructions, highlights and quality preset shape the result. Duration scales are approximate, not exact runtime. Set `quality_preset` deliberately: the documented default selects the highest quality available to the subscription. Source summarization can omit or hallucinate facts; compare the spoken script with the source. A `callback_url` publishes conversion status to that endpoint—configure only an authorized destination.

Source: [podcast creation](https://elevenlabs.io/docs/api-reference/studio/create-podcast).

## Audio Native and human production

Audio Native creates embeddable narrated content (`POST /v1/audio-native` multipart), reads project settings and updates content. It is a publishing/integration workflow, not merely a private MP3 generator. Inspect visibility, permitted domains, source content and generated embed behavior before publishing. Do not place the API key in the embed.

ElevenProductions supports human-reviewed production orders and deliverables. Those endpoints are procurement/submission workflows, not ordinary generation spikes. Discuss scope, price and approval before creating/submitting an order; use its separate [lifecycle documentation](https://elevenlabs.io/docs/eleven-api/concepts/elevenproductions-api-lifecycle).

Sources: [Audio Native](https://elevenlabs.io/docs/api-reference/audio-native/create), [Audio Native updates](https://elevenlabs.io/docs/api-reference/audio-native/update).

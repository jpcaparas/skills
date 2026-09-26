# Images, video, references and Flows

## Entitlement and job lifecycle

The public image/video API requires Pro or above and Image & Video/Flows permission. A lower tier can return `402 paid_plan_required` even if the dashboard switch says Access. ByteDance models require explicit approval and have regional restrictions; never work around them. Enterprise admins may need to approve individual models. App free-image allowances do not establish API access.

`POST /v1/flows/image` and `POST /v1/flows/video` take model-specific JSON, returning `{id,status:"pending"}`. Poll `GET /v1/flows/image/{id}` or `GET /v1/flows/video/{id}`: `pending → generating → completed|failed`. Completion supplies `content_url` and `content_mime_type`; failure supplies `failure_reason` and `error_message`. Store IDs immediately, then use the helper's bounded `wait` and keyless `download`. Terminal failure is not a reason to automatically repeat the paid request.

Images: poll no faster than every two seconds. Video: every ten seconds; allow minutes and back off. Signed URLs expire roughly one hour after a response; re-fetch to refresh. Failed visual generations are documented as not charged. Costs depend on model, settings and inputs; the app displays prices, but no public universal estimate endpoint was found.

List routes accept `cursor`, `page_size` (1–100), optional `status`/`model_id`, returning `generations`, `has_more`, `next_cursor`. These lists include this API's generations, not all app-created media. Use bounded pagination and stop on `has_more=false`; treat cursors as opaque and reject repeated cursors in automation.

Sources: [quickstart](https://elevenlabs.io/docs/eleven-api/guides/cookbooks/image-and-video), [image create](https://elevenlabs.io/docs/api-reference/flows/image/create), [video create](https://elevenlabs.io/docs/api-reference/flows/video/create).

## Image request families

All require `model_id` and `prompt`; optional `images` references and configured `webhook`. The table is a documented snapshot, not a promise that the account can use every model. Inspect the current create schema before sending a model-specific field.

| Model ID | References | Output controls |
| --- | --- | --- |
| `gpt-image-1`, `gpt-image-1.5` | Up to five; optional mask | Aspect 1:1/3:2/2:3, quality low/medium/high, background transparent/opaque/auto |
| `gpt-image-2` | Up to ten; mask | Broader aspect set, resolution 1K/2K/4K, quality low/medium/high; **no background field** |
| `gpt-image-2.5-sunburst`, `gpt-image-2.5-flare` | Up to ten; mask | Broader aspects, 1K/2K/4K, quality through xhigh/max; high default |
| `gemini-2.5-flash-image` | Up to five | Aspect only; no resolution field |
| `gemini-3-pro-image` | Up to ten | Aspect, 1K/2K/4K |
| `gemini-3.1-flash-image` | Up to fourteen | Extended aspects, `512`/1K/2K/4K |
| `gemini-3.1-flash-lite-image` | Up to fourteen | Aspect, 1K only |
| `bytedance-seedream-5-lite` | Up to ten | Aspect, 2K/3K, optional seed |
| `bytedance-seedream-5-pro` | Up to ten | Aspect, 1K/2K, optional seed |

```json
{"model_id":"gemini-3.1-flash-image","prompt":"A warm lantern on a quiet harbour wall at dusk.","aspect_ratio":"16:9","resolution":"1K"}
```

There is no universal `width`, `height`, `num_outputs`, `n`, `negative_prompt` or `background` parameter. Unknown fields are rejected. For transparent assets, select a model whose API supports transparency and verify actual alpha; a checkerboard-looking image is not proof. A mask requires images; fully transparent mask pixels mark the editable region of the **first** reference image.

Source: [image schema](https://elevenlabs.io/docs/api-reference/flows/image/create).

## Video request families

| Model ID | Inputs and limits | Important controls |
| --- | --- | --- |
| `veo-3.1-generate-001`, `veo-3.1-fast-generate-001` | Prompt; frames **or** up to three role-tagged image references | 4/6/8 seconds; 16:9/9:16; 720p/1080p/`4K`; audio and enhance-prompt flags; optional seed/negative prompt |
| `bytedance-seedance-v2` | Prompt; frames **or** images ≤9, videos ≤3, audios ≤3, combined ≤12 | 4–15 integer seconds; 480p/720p/1080p/`4k`; audio, seed |
| `bytedance-seedance-v2-fast`, `bytedance-seedance-v2-mini` | Same v2 reference rules | 4–15 seconds; 480p/720p |
| `bytedance-seedance-v2.5` | Prompt; frames **or** images ≤30, videos ≤10, audios ≤10; audio-only references allowed | 4–30 seconds; 480p/720p; schema also lists 1080p, unlike the quickstart; no seed |
| `creatify-aurora` | Required `image` and `audio` | Talking portrait/lip-sync; 480p/720p, guidance scales 0–5; no public prompt/duration/aspect field |

```json
{"model_id":"veo-3.1-fast-generate-001","prompt":"A slow camera move past a harbour lantern at dusk.","duration_secs":4,"aspect_ratio":"16:9","resolution":"720p","generate_audio":false}
```

`end_frame` requires `start_frame`. Do not combine frames with reference arrays. Veo image references require eight seconds and are `{image:<reference>,role:"subject"|"style"}`. Seedance v2 audio requires an image or video; v2.5 allows audio-only references. Resolution case matters (`4K` versus `4k`). Downstream model constraints may be stricter than enum validation; use a supported minimal combination before scaling.

Source: [video schema](https://elevenlabs.io/docs/api-reference/flows/video/create).

## Reference shapes and uploaded assets

Use one of these objects in the field the model accepts; symbolic IDs below must come from actual responses:

```json
{"type":"asset","asset_id":"UPLOADED_ASSET_ID"}
```

```json
{"type":"generation","generation_id":"EXISTING_GENERATION_ID"}
```

```json
{"type":"inline_base64","content_base64":"BASE64_OF_AUTHORIZED_FILE","mime_type":"image/png"}
```

There is no documented arbitrary-URL reference variant. Inline limit is 25 MB decoded per reference. Image types include JPEG/PNG/WebP/HEIC/HEIF; audio MPEG/WAV; video MP4/QuickTime/WebM. Inline references are ephemeral. Persisted assets use multipart `POST /v1/assets` with **`asset` and `name`**, not `file`:

```bash
python3 "$EL" request POST /v1/assets --file asset=reference.png \
  --field name=reference.png --out asset.json --execute
```

`GET /v1/assets` lists with cursor/page-size/search; `GET /v1/assets/{asset_id}` returns a fresh URL (which can be null while processing). `DELETE` removes a persistent shared resource; require appropriate authorization, and check dependents rather than deleting all spike assets indiscriminately. Plan storage quotas apply to uploads, not generated outputs.

A generation reference can point to a pending generation: the server waits for the dependency. A failed dependency becomes `dependency_failed`; do not report both stages as completed because both POSTs returned IDs. For first runs, inspect the image before chaining expensive video if that avoids spending on a bad reference.

Source: [references and assets](https://elevenlabs.io/docs/eleven-api/guides/how-to/image-and-video/references).

## Webhooks and reusable workflows

Optional `webhook` is `{type:"ids",ids:[...]}` or `{type:"all"}` for **existing configured** Flows subscribers, not an arbitrary callback URL. Prefer explicitly scoped recipients for private work. Terminal `flows_generation` data matches terminal GET. Verify raw-body signatures, deduplicate and reconcile; do not configure external recipients silently.

Flows also exposes asynchronous speech through `POST /v1/flows/text-to-speech` for Flash v2.5, Multilingual v2 and v3. It uses its own discriminated request schema and generation references; do not assume the ordinary TTS JSON body is interchangeable.

Reusable template execution is separately public: list with `GET /v1/flows/templates`, get the selected template by appending its ID, inspect its input ports and published versions, then `POST /v1/flows/templates/{template_id}/runs` with `inputs` keyed by port ID and optionally `version_id`. Every required port must be supplied and unknown IDs are rejected. Pin a published version for repeatability; the live draft is never run. Inspect the template's billable nodes and recipients before authorizing a run. Get/list runs under that template; terminal callback type is `flows_template_run`, not `flows_generation`. The helper's generation `wait` does not handle template runs; follow their own schema.

Sources: [webhooks](https://elevenlabs.io/docs/eleven-api/guides/how-to/image-and-video/webhooks), [Flows speech](https://elevenlabs.io/docs/api-reference/flows/text-to-speech/create), [template runs](https://elevenlabs.io/docs/api-reference/flows/templates/runs/create).

## Do not invent app-only APIs

The [capability overview](https://elevenlabs.io/docs/overview/capabilities/image-video) marks API-supported models with API IDs. Kling, Runway, FLUX, many lip-sync/upscale/background-removal tools and some edit/extend controls may be app-only. Their presence in the UI is not proof of a REST route. Use the live OpenAPI's `ImageGenerationRequest`/`VideoGenerationRequest` discriminator for model discovery; `GET /v1/models` is speech-oriented. Browser automation is a different authorized workflow, not a reason to imitate private application APIs.

# Evidence and verification limits

This is a **2026-09-26 UTC snapshot**, not a promise about every account, model or future release. Official endpoint links live beside the relevant instructions. Research used the [documentation index](https://elevenlabs.io/docs/llms.txt), endpoint references, capability guides and the public [OpenAPI document](https://api.elevenlabs.io/openapi.json). The inspected OpenAPI bytes had SHA-256 `4a6716242c9ed6dafa43ccbff4447818e7f4295d2c4aef89489e9649e642e643`.

## Executed live probes

These were authorized, short requests against a configured key, using original synthetic content and accessible premade voices. Receipts, account resource IDs, signed URLs and raw responses were kept private rather than committed. A successful API response proves transport and the checked result, not subjective quality or every option in that family.

| Operation | Observed result |
| --- | --- |
| Voice discovery | `GET /v2/voices` returned five premade voices and `has_more=true`; this was one page, not a complete inventory |
| Multilingual v2 narration | HTTP 200; MP3, 44.1 kHz mono, 5.015510 seconds |
| Scribe v2 batch | HTTP 200; recovered the test sentence with word/spacing entries and English detection; normalized “harbour” to “harbor” and omitted final punctuation |
| TTS streaming with timestamps | HTTP 200; saved NDJSON, decoded ordered base64 chunks to a 5.015500-second MP3; timing source retained |
| V3 HTTP dialogue with timestamps | HTTP 200; two voice segments with two distinct IDs; decoded MP3, 4.284082 seconds |
| Multilingual STS v2 | HTTP 200; converted the synthetic recording to a second premade voice; 5.015510-second MP3 |
| Audio isolation | HTTP 200; processed narration mixed locally with pink noise; 5.015510-second MP3; perceptual cleanup quality not established |
| Sound effects v2 | HTTP 200; requested two seconds, received 2.037551-second stereo MP3 |
| Music v2.5 prompt | HTTP 200, song ID header; five-second request produced 6.504000-second 48 kHz stereo MP3—duration must be measured |
| Music detailed | HTTP 200; MIME parser recovered one JSON metadata part and one audio part; plan/metadata/timing/waveform keys present; 5.040000-second MP3 |
| Two-stem separation | HTTP 200; ZIP contained `vocals.mp3` and `instrumental.mp3`, each 104,534 bytes; paths, sizes and CRCs checked before extraction; leakage not listening-tested |
| Video-to-music | HTTP 200; scored the generated four-second clip; 4.048938-second stereo MP3, not a muxed video |
| Original voice design | HTTP 200; three base64-decodable previews with duration metadata; no voice was saved, cloned or trained |
| Image | `gemini-3.1-flash-image`; create → completed → keyless signed-URL download; actual PNG 1376×768. Inspected; normalized locally to the repository's 1024×576 skill card |
| Image-to-video | `veo-3.1-fast-generate-001`, generation reference to that image; create → completed → download; H.264 1280×720, 24 fps, exactly four seconds, no audio stream |
| Realtime Scribe | Raw 16 kHz mono PCM in 250 ms chunks, manual commit; received partial, committed and timestamped committed events; full sentence recovered |
| Ordinary TTS WebSocket | Flash v2.5; initialization → short text with flush → empty-text close; final event and 23,032 decoded audio bytes, 1.436688-second MP3 |
| V3 dialogue WebSocket | Explicit v3, two registered voices, new turn, flush and close; final event and 41,004 decoded audio bytes |

Narration test text: “The lantern is blue. Seven small boats are waiting by the quiet harbour.” Both batch and realtime Scribe recovered those words, with spelling/punctuation normalization. This round trip supports lexical fidelity; it is not an independent assessment of pronunciation, voice identity or naturalness.

The image was visually inspected. Four sampled video frames preserved the scene and fixed camera, but the ribbon and projected orb changed more than the requested subtle glow. This is a usable protocol spike, not proof of perfect prompt fidelity. Direct audio/video analysis was unavailable in the execution environment; audio was checked through decoding, ffprobe, timing structure and transcription, not listening. Sampled frames do not establish smooth playback.

## Blocked or deliberately untested

- Subscription and model reads returned **401 `missing_permissions`**, specifically `user_read` and `models_read`. Forced alignment, current dubbing-project listing and Studio-project listing also returned `missing_permissions`. Other media operations succeeding disproved the inference that the whole key was invalid. No permissions were changed.
- Exact aggregate spending could not be reconciled because subscription reads were denied and some successful media responses lacked charge headers. Recorded per-response costs are not a complete invoice.
- Cloning, verification, training/finetuning, saving/sharing voices, dictionary mutations, Studio/podcast generation, Audio Native publication, human-production orders and external callback configuration were not performed. They are documented workflows with separate authority and entitlement requirements.
- Music inpainting/conditioning/upload, detailed SSE, multichannel/entity/redaction STT, async callback delivery, masks/transparency, other image/video models, template runs, multi-context sockets, and Speech Engine deployment were not live-verified. Schema checks do not establish cross-field runtime acceptance or availability.
- Realtime dubbing/translation appeared in the official index, but the detailed pages were inaccessible during research. There is intentionally no invented wire example.
- Documentation conflicts remain explicit: batch/forced-alignment file limits, music maximum duration, some Seedance resolutions, and STT webhook naming/retry guidance. Apply the branch's conservative contract and recovery route.

## Reproduce the local checks without credentials

From the installed skill directory:

```bash
python3 scripts/validate.py .
python3 scripts/test_skill.py .
```

The helper suite exercises offline transport doubles with real files: credential/origin isolation, previews, Unicode/multipart bytes, no-clobber publication, interrupted/truncated/empty responses, size limits, no implicit retries, signed downloads, bounded polling and ordered timing decoding. The tests replace the ambient key and prohibit real socket connections. They are executable regressions, **not live provider tests**.

`evals/evals.json` contains 14 authored behavioral cases; `evals/trigger-evals.json` contains 19 invocation cases. Package validation checks their structure. No matched with-skill/baseline agent evaluation or trigger-accuracy run has been executed, so no behavioral score is claimed.

## Recheck the request examples against an explicit schema snapshot

Sixteen synthetic requests in `evals/files/contracts.json` passed JSON Schema validation against the downloaded OpenAPI snapshot. They contain no account IDs or private input. This check sends **no requests to ElevenLabs** and does not validate undocumented runtime constraints.

Download the public schema into a scratch directory. With `uv` available, run from this skill directory (or use a disposable virtual environment with compatible `jsonschema` 4.18–4.x):

```bash
curl --fail --silent --show-error https://api.elevenlabs.io/openapi.json -o /tmp/elevenlabs-openapi.json
uv run --with 'jsonschema>=4.18,<5' python - /tmp/elevenlabs-openapi.json <<'PY'
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator

spec = json.loads(Path(sys.argv[1]).read_text())
cases = json.loads(Path("evals/files/contracts.json").read_text())["requests"]
for case in cases:
    operation = spec["paths"][case["path"]][case["method"]]
    schema = operation["requestBody"]["content"][case["content_type"]]["schema"]
    root = {"$ref": "#/request", "request": schema, "components": spec["components"]}
    Draft202012Validator(root).validate(case["body"])
    print(case["name"], "PASS")
PY
```

For another live check, use the relevant branch's smallest authorized request, a fresh output path, and the same ID for subsequent reads. Do not run the entire capability table as an automatic test suite. Repeating stochastic generations until one looks good neither proves reliability nor bounds spending.

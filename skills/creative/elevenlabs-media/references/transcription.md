# Transcription, captions and forced alignment

## Batch Scribe

`POST /v1/speech-to-text` uses multipart; `model_id` is required. Use `scribe_v2` for general batch work; medical and realtime models have separate contracts.

```bash
python3 "$EL" request POST /v1/speech-to-text \
  --field model_id=scribe_v2 --file file=meeting.wav \
  --field diarize=true --field timestamps_granularity=word \
  --out transcript.json --execute
```

Send one `file` or `source_url`; `cloud_storage_url` is deprecated. Remote fetching discloses the URL and content to the provider—confirm authorization, especially for signed/private URLs. Omit `language_code` for detection or supply ISO 639-1/639-3. Defaults include `diarize=false`, `tag_audio_events=true`, and word timestamps. Granularity supports `none|word|character`.

Results include text, detected language/probability and `words`. Entries can be `word`, `spacing` or `audio_event`; punctuation, spaces and sounds are not all speaker utterances. `speaker_id` is diarization identity, not a verified person's name. `num_speakers` (1–32) is a maximum expected count. `diarization_threshold` (0.1–0.4) is allowed with diarization and without `num_speakers`.

Source: [batch endpoint](https://elevenlabs.io/docs/api-reference/speech-to-text/convert).

### Multichannel and long recordings

Use `use_multi_channel=true`, `diarize=false` for one known speaker per channel, at most five channels. Ordinary multichannel output wraps `transcripts[]`; `multichannel_output_style=combined` merges timestamped words with `channel_index`. Combined output requires timestamps and is incompatible with entity detection/redaction. Billing scales per channel.

Docs disagree on upload/duration limits: the endpoint schema says under 5 GB while the capability page says 3 GB; multichannel duration guidance also conflicts. Use the stricter documented limit until verified, not the largest number found. Very short input must contain at least 100 ms of audio. For splitting, retain overlap and absolute offsets, deduplicate boundary text deliberately, and disclose that independent chunks may reset speaker IDs.

Source: [multichannel guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/batch/multichannel-transcription).

### Async transcription and retrieval

Multipart `webhook=true`, optional configured `webhook_id`, and JSON-string `webhook_metadata` submit asynchronous transcription. Metadata is an object, at most two levels/16 KB. `webhook_id` is not a callback URL. Omitting it can reach all configured STT webhooks; choose destinations explicitly for private material.

Acceptance can be HTTP 202 (the schema also includes an acceptance response in the 200 union), containing `request_id`. Persist it before waiting. The documented completion envelope is `type: speech_to_text_transcription` with `data.request_id`, `data.webhook_metadata`, `data.transcription`. `GET /v1/speech-to-text/transcripts/{transcription_id}` retrieves a stored result; it is not a general request-ID job-status route. DELETE removes it and needs authorization.

Verify signatures over raw request bytes; don't parse then reserialize JSON before HMAC. Reconcile/deduplicate callbacks. The STT cookbook contradicts itself about event names/retries; prefer its documented payload plus the current general verification contract, and do not promise retry delivery. A webhook receiver's mere existence does not prove it received the result.

Sources: [STT webhooks](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/batch/webhooks), [general webhooks](https://elevenlabs.io/docs/eleven-api/resources/webhooks).

### Vocabulary, entities and editing

Scribe supports keyterm prompting for domain vocabulary, optional entity detection/redaction and transcript transformation/editing features. Use the [keyterm guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/batch/keyterm-prompting), [entity guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/batch/entity-detection) or [editing guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/batch/transcript-editing) for current models and exact form serialization. Do not equate redacted output with zero-retention processing. Medical transcription requires the relevant privacy/compliance agreement; an API key alone establishes neither consent nor regulatory compliance.

## Captions

Derive captions from word times or an endpoint-supported export format. Preserve Unicode, punctuation, source duration and speaker transitions; never create equal-duration subtitles from plain text and present them as aligned. Handle spacing/audio events explicitly. Choose line length, gap and reading-speed constraints for the target platform. SRT uses comma milliseconds; WebVTT uses period milliseconds and a `WEBVTT` header. Rebase chunk offsets before exporting. Spot-check early, middle and late cues against playback and prevent negative/overlapping times caused by rounding.

## Forced alignment

Use this when the transcript is known and must match existing audio:

```bash
python3 "$EL" request POST /v1/forced-alignment \
  --file file=recording.wav --field-file text=verbatim.txt \
  --out alignment.json --execute
```

Response contains character/word spans in seconds, word `loss` and aggregate `loss`. Loss is an alignment score, not a calibrated probability. Speaker labels are not speech and can harm alignment. No diarization is supplied. The endpoint says file under 1 GB; a capability page says 3 GB. Prefer the stricter endpoint limit. Capability docs list ten-hour audio and 675,000-character text ceilings; verify before large jobs.

Aligning incorrect text does not validate that those words were spoken. Compare the transcript first; transcribe if it is unknown. Use [Realtime](realtime.md) for live input instead of uploading chunks as unrelated batch jobs.

Sources: [forced alignment endpoint](https://elevenlabs.io/docs/api-reference/forced-alignment/create), [capabilities](https://elevenlabs.io/docs/overview/capabilities/forced-alignment).

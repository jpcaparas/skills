# Speech, dialogue, sound effects and cleanup

Examples are REST JSON/form contracts. Replace symbolic voice IDs with accessible IDs. Query parameters such as `output_format` belong in `--query`, not JSON. Review the returned format before naming the output extension.

## Text to speech

`POST /v1/text-to-speech/{voice_id}` accepts JSON and returns binary audio:

```json
{"text":"The next train arrives at seven thirty.","model_id":"eleven_multilingual_v2"}
```

| Need | Model/route consideration |
| --- | --- |
| Consistent long-form narration | `eleven_multilingual_v2` is the documented HTTP default |
| Low-latency speech | `eleven_flash_v2_5`; check the voice/model capabilities |
| Expressive delivery/audio tags | `eleven_v3`; use natural-language tags such as `[whispering]` |
| Multiple speakers | Text-to-Dialogue, not separate TTS calls joined without context |
| Character timing | `POST /v1/text-to-speech/{voice_id}/with-timestamps`; JSON with base64 audio |
| HTTP low-latency consumption | `POST /v1/text-to-speech/{voice_id}/stream`; binary chunks |
| HTTP streaming with timing | `POST /v1/text-to-speech/{voice_id}/stream/with-timestamps`; newline-delimited JSON, not SSE |
| Incremental input/live output | Use the separate protocols in [Realtime](realtime.md) |

TTS uses `voice_settings` (e.g. stability, similarity boost, style, speed, speaker boost); controls are model-specific. Discover supported capabilities instead of copying every setting onto v3. Supply `language_code` only where supported; Multilingual v2 does not enforce this parameter. `seed` is best-effort, not deterministic reproduction.

The overview lists v3 5,000, Multilingual v2 10,000, Flash v2.5 40,000 characters per request; prefer discovered `maximum_text_length_per_request`. Avoid chopping a sentence mid-word to meet a limit. For chunk continuity use surrounding `previous_text`/`next_text`, or preceding/following request IDs (up to three on each side); IDs take precedence. Keep continuity within the same compatible voice/model/settings.

Pronunciation is model-specific. V3 does not support SSML `<break>` and documents native slash-delimited IPA; older XML phoneme examples do not imply universal multilingual support. Use dictionaries/aliases where supported, and listen to names/numbers rather than assuming normalization was correct. `apply_text_normalization` is `auto|on|off`; Japanese language normalization can add substantial latency.

Default output is `mp3_44100_128`. PCM/μ-law are raw samples, not WAV containers. MP3 192 kbps and PCM/WAV 44.1 kHz can be tier-gated. Use the format enum for the exact endpoint: music and isolation differ. Do not blindly use deprecated `optimize_streaming_latency` or `use_pvc_as_ivc`.

Sources: [convert](https://elevenlabs.io/docs/api-reference/text-to-speech/convert), [timing](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps), [stream timing](https://elevenlabs.io/docs/api-reference/text-to-speech/stream-with-timestamps), [models](https://elevenlabs.io/docs/overview/models), [prompting](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices).

## Dialogue

Use `POST /v1/text-to-dialogue`; alternatives are `POST /v1/text-to-dialogue/stream`, `POST /v1/text-to-dialogue/with-timestamps`, and `POST /v1/text-to-dialogue/stream/with-timestamps`:

```json
{
  "model_id":"eleven_v3",
  "inputs":[
    {"text":"[curious] Is the recording ready?","voice_id":"VOICE_A"},
    {"text":"[cheerful] Yes. Let's begin.","voice_id":"VOICE_B"}
  ],
  "settings":{"stability":0.5}
}
```

HTTP dialogue uses `settings`, not TTS `voice_settings`. Maximum ten unique voices; current reference recommends at most 2,000 total input characters—do not substitute the general v3 ceiling. Keep speaker turns semantically coherent. Audio tags are expressive guidance, not a closed validation enum.

Timing responses contain `audio_base64`, nullable `alignment` and `normalized_alignment`, plus dialogue `voice_segments`. REST character times are in seconds. Voice segments include voice ID, input index, time span and exclusive character-end index. Preserve normalization distinction and chunk offsets. The helper decodes the audio while keeping this JSON intact.

Sources: [dialogue](https://elevenlabs.io/docs/api-reference/text-to-dialogue/convert), [dialogue timing](https://elevenlabs.io/docs/api-reference/text-to-dialogue/convert-with-timestamps).

## Change a recorded performance's voice

`POST /v1/speech-to-speech/{voice_id}` or `POST /v1/speech-to-speech/{voice_id}/stream` takes multipart, returns binary audio:

```bash
python3 "$EL" request POST "/v1/speech-to-speech/$VOICE_ID" \
  --file audio=performance.wav --field model_id=eleven_multilingual_sts_v2 \
  --field 'voice_settings={"stability":0.5}' \
  --query output_format=mp3_44100_128 --expect audio --out changed.mp3 --execute
```

The default model is the English STS model, not the multilingual one. `voice_settings` is a JSON-encoded **form string**. STS preserves the input performance's delivery; it is not translation. Source segments have a documented five-minute ceiling. `remove_background_noise` defaults false. `file_format=pcm_s16le_16` means raw signed 16-bit little-endian, 16 kHz mono specifically; use default `other` for ordinary encoded audio.

Sources: [STS contract](https://elevenlabs.io/docs/api-reference/speech-to-speech/convert), [capability](https://elevenlabs.io/docs/overview/capabilities/voice-changer).

## Sound effects

`POST /v1/sound-generation` takes JSON, returns audio:

```json
{"text":"Light rain tapping on a hollow metal roof, no voices or music.","model_id":"eleven_text_to_sound_v2","duration_seconds":4,"loop":true,"prompt_influence":0.3}
```

V2 supports loops; duration is 0.5–30 seconds or omitted for automatic selection. Specify the event, environment, texture, perspective, progression and loop requirement rather than a rigid prose template. Listen at the seam to assess whether a requested loop is usable. A low-latency UI cue and a cinematic ambience need different envelopes.

Source: [sound effects](https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert).

## Audio isolation

`POST /v1/audio-isolation` or `POST /v1/audio-isolation/stream`: multipart `audio`, optional `file_format`, returns audio. There is no documented model ID or output-format selector.

```bash
python3 "$EL" request POST /v1/audio-isolation --file audio=noisy.wav \
  --expect audio --out isolated.mp3 --execute
```

Documented capability ceiling is 500 MB/one hour. Isolation targets speech cleanup, not separation into vocals, drums and bass. Use music stem separation for that. Keep the original and compare consonants, breaths, overlap and musical content: denoising can destroy wanted signal.

Sources: [contract](https://elevenlabs.io/docs/api-reference/audio-isolation/convert), [limits](https://elevenlabs.io/docs/overview/capabilities/voice-isolator).

## Inspect and combine locally

`ffprobe -v error -show_format -show_streams -of json output.mp3` checks the actual codec, sample rate, channels and duration. It does not evaluate speech fidelity. Decode/play the file and compare with the brief. For mixing, keep speech intelligible, avoid clipping, and choose delivery loudness from the target platform rather than imposing one LUFS value on every artifact. Preserve source files and identify any resampling, normalization, ducking or muxing in the handoff.

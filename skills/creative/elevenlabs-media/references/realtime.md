# Realtime protocols are not interchangeable

Use the installed official SDK where it correctly implements the selected protocol. Read its version-matched method/types and the linked AsyncAPI page before writing integration code. The bundled HTTP helper does not implement WebSockets. Keep one server-side adapter responsible for auth, framing, cancellation and errors.

For supported browser transports, mint a single-use token server-side through `POST /v1/single-use-token/{token_type}`. Documented types: `realtime_scribe`, `batch_scribe`, `tts_websocket`; tokens expire after fifteen minutes and are consumed on use. Authenticate/rate-limit your minting endpoint. Do not put the long-lived key into client code, query strings, logs or a committed `.env`.

Source: [single-use tokens](https://elevenlabs.io/docs/api-reference/tokens/create).

## Incremental-input TTS

`wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_flash_v2_5&output_format=mp3_44100_128`

Conceptual message sequence (authenticated handshake or documented initialization auth):

```json
{"text":" "}
{"text":"Hello, world. ","flush":true}
{"text":""}
```

The first text is a single space, ordinary text chunks should end in a space, `flush` generates buffered text, and empty text closes the stream. `try_trigger_generation` is not flush; it still has a threshold. Default chunk schedule is `[120,160,250,290]`, configurable entries 50–500. Inactivity defaults to twenty seconds, configurable up to 180. **Do not select eleven_v3 on this ordinary TTS WebSocket.**

Responses use `audio`, `isFinal`, `normalizedAlignment`; alignment fields use camelCase and **milliseconds relative to the chunk**. Do not apply REST seconds or `audio_base64` decoding field names. Accumulate audio/timing offsets deliberately. Multi-context TTS uses `wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/multi-stream-input`; use its actual context-close messages rather than assuming ordinary empty text closes only one context.

Source: [TTS AsyncAPI](https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-stream-input).

## V3 dialogue WebSocket

`wss://api.elevenlabs.io/v1/text-to-dialogue/stream-input?model_id=eleven_v3&sync_alignment=true`

```json
{"voices":["VOICE_A","VOICE_B"],"voice_settings":{"stability":0.5}}
{"inputs":[{"text":"[curious] Ready to begin?","voice_id":"VOICE_A"}]}
{"inputs":[{"text":"Absolutely.","voice_id":"VOICE_B","new_turn":true}],"flush":true}
{"close_socket":true}
```

Register actual voices on the first message. Voice settings/dictionaries are initial-message-only. Unlike HTTP dialogue, WebSocket settings use `voice_settings`. The default model is `eleven_v3_conversational` and allows one voice; explicitly select `eleven_v3` for up to ten. Flush short endings; buffering normally waits for roughly forty characters/eight words. `new_turn` or a voice change finalizes the preceding prosodic turn. `keep_alive=true` resets the fixed twenty-second receive timeout.

Responses use snake_case `is_final`, `is_final_audio_for_turn`, `char_start_times_ms`, `char_durations_ms`; normalized alignment is reserved. An open socket reserves a dialogue session for its lifetime. `wss://api.elevenlabs.io/v1/text-to-dialogue/multi-stream-input` supports at most five contexts with `context_id`; close contexts and sockets when done, and account for protocol errors closing the connection.

Sources: [TTS versus dialogue](https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/tts-vs-ttd-websockets), [dialogue AsyncAPI](https://elevenlabs.io/docs/api-reference/text-to-dialogue/ttd-websocket), [multi-context dialogue](https://elevenlabs.io/docs/api-reference/text-to-dialogue/ttd-multi-websocket).

## Live Scribe

`wss://api.elevenlabs.io/v1/speech-to-text/realtime?model_id=scribe_v2_realtime&audio_format=pcm_16000&commit_strategy=manual&include_timestamps=true`

Send base64 of **raw samples**, not a WAV/MP3 container:

```json
{"message_type":"input_audio_chunk","audio_base_64":"BASE64_PCM_SAMPLES","sample_rate":16000,"commit":false}
{"message_type":"input_audio_chunk","audio_base_64":"","sample_rate":16000,"commit":true}
```

Supported signed 16-bit little-endian mono PCM rates are 8/16/22.05/24/44.1/48 kHz, plus 8 kHz μ-law. Do not assume 32 kHz or stereo. Decode/downmix/resample upstream, preserving source time. Roughly 0.1–1-second chunks are guidance, not a hard size contract. `previous_text` belongs only with the first chunk.

`session_started`, replaceable `partial_transcript`, stable `committed_transcript`, and `committed_transcript_with_timestamps` are different event types. Do not append both committed variants as duplicate utterances. Manual commit is default; VAD is a separate strategy. Manual sessions can auto-commit after roughly 36 seconds. Handle size/time/quota/rate/resource errors and close cleanly; no verified universal session-length ceiling was found.

Realtime is not batch Scribe with smaller uploads. Batch diarization is not exposed as a realtime option merely because a shared response type contains `speaker_id`. SDK URL helpers may use local FFmpeg to stream samples; they do not imply a server-side `source_url` WebSocket field.

Sources: [Scribe AsyncAPI](https://elevenlabs.io/docs/api-reference/speech-to-text/v-1-speech-to-text-realtime), [audio/commit guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/realtime/transcripts-and-commit-strategies), [events](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/realtime/event-reference).

## Speech Engine: transport for an application-owned LLM

Speech Engine combines STT/TTS, turn-taking and interruptions while the application owns LLM logic. Its setup creates a persistent engine with a public `wss` upstream, runs a server adapter, and uses a server-minted conversation token/WebRTC client. The user's ElevenLabs key alone does not provide an external LLM key, callback server or deployment permission.

Use the official [Speech Engine quickstart](https://elevenlabs.io/docs/eleven-api/guides/cookbooks/speech-engine) and [maintained Speech Engine skill](https://github.com/elevenlabs/skills/tree/main/speech-engine) when implementing that application. Inspect external skill/server code before installation. Cancel LLM work on interruption, protect token issuance, keep debug transcript logs off for private conversations, and treat spoken text as untrusted input. Agent administration, telephony and outbound calls remain outside ordinary media generation.

## Verify a realtime integration

Exercise short final phrases, silence, interruptions, disconnects, partial audio, duplicate final events and stream cancellation. Assert what plays or is transcribed—not merely that a socket opens. Bound buffering and concurrent sessions, apply backpressure, and measure time to first **audible** output separately from connection/open or first text. Do not replay already-spoken or already-transcribed buffers automatically after reconnect without an explicit continuity policy.

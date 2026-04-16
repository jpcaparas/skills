# audify Gotchas & Tribal Knowledge

## Prompting Gotchas

- Gemini TTS only accepts text input and only returns audio output. Do not send HTML, Markdown, or URL-heavy text straight to the model.
- Google documents false rejections and cases where the model reads the instructions aloud when the prompt is too vague. Keep a hard preamble like `Synthesize speech only` and a labeled `TRANSCRIPT` block.
- Google also warns that voice choice and directorial notes can clash. A deeply mature voice plus a "young child" nuance is more likely to sound wrong than clever.

## Output Format Gotchas

- The Gemini API TTS path currently returns PCM audio, not MP3. `ffmpeg` conversion is part of the wrapper, not an optional afterthought.
- Convert once after concatenating all PCM chunks. Re-encoding each chunk separately makes the final MP3 harder to join cleanly.

## Reliability Gotchas

- Gemini 3.1 Flash TTS Preview can intermittently fail with `500`. Google attributes this to rare cases where the model emits text tokens instead of audio tokens. Retry transient failures automatically, then bail.
- Do not retry `401`, `403`, or `404` blindly. Those are configuration errors, not transient failures.

## Resource-Cleaning Gotchas

- HTML extraction is approximate. Nav bars, cookie banners, or related-links sections can still survive on some pages. If the preview looks wrong, stop and ask for a narrower resource.
- Bare URLs are removed because hearing full tracking links is almost never useful. Preserve link anchor text instead.
- Fenced code blocks are dropped on purpose. If the remaining content is still code-heavy, bail rather than narrating syntax.
- DOCX extraction from the lightweight wrapper is good for paragraphs, but it is not a full Word rendering engine. Complex tables, comments, and floating objects are not preserved perfectly.

## Product-Surface Gotchas

- This skill is for exact-text narration, not the Live API. Do not use it when the user wants interactive, conversational, low-latency audio chat.
- This skill is not a general accessibility auditor. It can produce a narration artifact, but it should not claim the source is accessible simply because audio was generated.

## See Also

- `references/api.md` for the supported models and voice list
- `references/configuration.md` for setup failures
- `references/patterns.md` for the recommended wrapper workflows

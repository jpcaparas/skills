# Gotchas

Common pitfalls and how to handle them.

## No Captions Available

**Symptom:** Script exits with code 2 and reports "Transcripts are disabled" or "No transcript found".

**Cause:** The creator disabled captions, the video is too new for auto-generated captions, or the video is private/deleted.

**What to do:**
1. Tell the user no transcript could be retrieved; distinguish an access failure from confirmed missing captions.
2. If metadata was fetched, offer to summarize the video description and tags instead.
3. Suggest the user provide their own transcript (paste text or upload a file).
4. Do not hallucinate content. If there is no transcript, say so.

## Auto-Generated Caption Quality

**Symptom:** Transcript `source` is `auto-generated` and contains obvious errors in names, numbers, or technical terms.

**Cause:** YouTube speech-to-text is approximate. It struggles with accents, background noise, fast speech, and domain-specific jargon.

**What to do:**
1. Add a note at the top of the dossier: "Transcript is auto-generated; names and terms may contain errors."
2. Flag uncertain transcriptions outside the quotation; do not insert markers or silently repair text inside a verbatim quote.
3. Do not treat transcribed proper nouns as verified. If a name looks wrong, note it as "transcribed as X, may be Y".
4. Prefer verbatim quotes only when the text is unambiguous. For noisy sections, summarize the point instead of quoting directly.

## Incomplete or Truncated Transcripts

**Symptom:** The transcript ends before the video does, or has large time gaps between snippets.

**Cause:** The caption track may be manually edited, only covering part of the video. Or the video has long silent sections with no speech.

**What to do:**
1. Compare the last transcript timestamp with the video duration from metadata.
2. If there is a significant gap, note it: "Transcript covers 00:00–42:30 of a 58:00 video."
3. Do not assume the video ended when the transcript did.

## Music and Sound Effects

**Symptom:** The transcript is full of `[♪♪♪]`, `[Music]`, `[Applause]`, `[Laughter]` markers.

**Cause:** YouTube captions include non-speech audio markers.

**What to do:**
1. Omit irrelevant markers from takeaways and topic descriptions, but preserve raw exports and mark any omissions inside quotes explicitly.
2. Note when a section of the video is primarily music or a non-verbal demo (e.g. "[03:20–05:10] Instrumental intro / sound check").
3. Do not try to describe what the music sounds like unless the user asks.

## Timestamp Drift

**Symptom:** A topic or quote timestamp does not align with what the user sees on screen.

**Cause:** Transcript timestamps reflect spoken audio, not visual content. Slides, demos, and visual overlays may appear at different times than the narration.

**What to do:**
1. Use transcript timestamps as-is — they are the best available anchors.
2. If the user reports a mismatch, note that timestamps are audio-based and may not align with visual content.
3. For demo-heavy videos, group timestamps by demo section rather than exact moment.

## Age-Restricted Videos

**Symptom:** Script fails with "Video unavailable" or returns an error for a video that works in the browser.

**Cause:** Access restrictions or upstream failures may prevent retrieval; browser playback does not prove API access.

**What to do:**
1. Read `references/fetching.md` for the dated upstream authentication baseline and helper limitations.
2. Verify current upstream documentation when support is uncertain; neither cookies nor upgrading guarantees access.
3. Use only an authorized user-provided cookie file when support is established. Never extract browser session credentials automatically or bypass restrictions.
4. If retrieval remains unavailable, request a transcript the user is authorized to provide.

## Very Long Videos

**Symptom:** The transcript exceeds the working context or makes coverage difficult to track.

**Cause:** Long lectures, podcasts, and conference talks.

**What to do:**
1. Use the supplied transcript or fetch when needed, preferably as JSON for exact source text and timing.
2. Choose chunks by topic or timestamp range when context limits or requested coverage justify it; do not chunk just because a video exceeds a fixed duration.
3. Track source ranges and merge only the topics, quotes, or takeaways relevant to the task.
4. Return the requested concise summary or unified dossier, not a forced section set per chunk.

## Multi-Line Snippet Text

**Symptom:** Some transcript snippets have multi-line text with embedded newlines.

**Cause:** YouTube caption tracks split long phrases across lines for display.

**What to do:**
1. Preserve quote wording; display-only line wrapping is acceptable, but do not repair or combine unrelated phrases silently.
2. Preserve original raw JSON or supplied transcript text exactly. The helper's plain-text formatter normalizes whitespace, so do not present that rendering as a byte-exact raw copy.

## Live Stream Replays

**Symptom:** The video is a recorded live stream with very long duration and a disjointed transcript.

**Cause:** Live stream auto-captions are generated in real time and are lower quality than post-produced captions.

**What to do:**
1. Note in the header that the source is a live stream recording.
2. Expect lower accuracy and more gaps in the transcript.
3. Group topics by major stream segments (intro, main content, Q&A) rather than fine-grained timestamps.

## yt-dlp Version Drift

**Symptom:** Metadata fields are missing or named differently than expected.

**Cause:** yt-dlp updates frequently and occasionally renames or restructures JSON fields.

**What to do:**
1. The script only extracts fields from a curated list; unknown fields are ignored.
2. If a field the user needs is missing, check the raw yt-dlp output: `yt-dlp --dump-json --skip-download "<url>" | python3 -m json.tool`.
3. The script's metadata extraction is resilient to missing fields — it simply omits them.

## See Also

- `references/fetching.md` — script usage, output formats, and language preference
- `references/dossier-format.md` — dossier structure and quality bar

# Dossier Format

How to structure the synthesized dossier from a YouTube transcript.

These sections are options for a full dossier, not a minimum for every summary. Follow the user's requested length, focus, and format; omit empty or unhelpful sections rather than inventing content. Supplied transcripts need no refetch just to fill metadata.

## Section Definitions

### Header

For a full dossier, identify the source using available metadata. Do not invent missing title, channel, duration, or dates. A short answer need not include this table:

```markdown
# {title}

| Field | Value |
| --- | --- |
| Channel | {channel} |
| URL | {url} |
| Duration | {formatted duration} |
| Uploaded | {formatted date} |
| Transcript Source | {manual or auto-generated} |
| Language | {language} |
```

Format the upload date from YYYYMMDD to a readable form (e.g. 20091025 → Oct 25, 2009). Format duration from seconds to MM:SS or HH:MM:SS.

### Executive Summary

Capture the video's core message at the length requested. Answer: what is this video about and why would someone watch it? No fixed sentence count is required.

Do not list every topic here. The summary should give a reader enough context to decide whether the full dossier is worth reading.

### Key Topics

The major themes or sections of the video, each with a timestamp range:

```markdown
## Key Topics

- **[00:00–02:15] Introduction and motivation** — Why the speaker chose this topic and what problem it solves.
- **[02:15–08:40] Core concept** — The main technical idea explained with examples.
- **[08:40–12:00] Demo** — Live demonstration of the concept in practice.
```

Group by topic, not by transcript snippet order. A topic may span multiple non-contiguous timestamps if the speaker revisits it.

### Notable Quotes

Verbatim quotes that are memorable, controversial, or encapsulate a key idea. Each with a timestamp:

```markdown
## Notable Quotes

> "The best error message is the one that never shows up." — [04:32]

> "Premature optimization is the root of all evil." — [07:15]
```

Include quotes only when useful and supported by actual transcript text. Keep wording exact; never silently repair names or numbers. If a quote spans contiguous snippets, preserve their order and use the first snippet's timestamp. Mark omissions explicitly and put uncertainty or corrections outside the quotation. The examples above illustrate format, not quotes to insert into an unrelated dossier.

### Key Takeaways

Distilled points worth remembering. These are the "if you remember nothing else" items:

```markdown
## Key Takeaways

1. Start with the simplest solution that works, then optimize only when profiling shows a bottleneck.
2. Code reviews catch more bugs than automated tests alone.
3. Documentation debt compounds faster than technical debt.
```

Each takeaway should be a complete, standalone sentence. Not a topic name — a claim or lesson.

### Follow-Ups

When useful or requested, include concrete action items supported by the video. Distinguish the speaker's recommendations from your own suggested follow-ups. Use verb-first phrasing:

```markdown
## Follow-Ups

- [ ] Read the paper on <topic> mentioned at [12:30]
- [ ] Compare <tool A> vs <tool B> for the use case shown at [08:40]
- [ ] Try the benchmark shown in the demo on a local dataset
- [ ] Watch the related talk linked in the description
```

Make each follow-up specific enough to act on without rewatching the video. "Research X" is weak; "Compare X's approach to Y's approach for <specific use case>" is strong.

### References Mentioned

People, tools, books, papers, URLs, and concepts named in the video:

```markdown
## References Mentioned

- **Donald Knuth** — cited at [07:15] regarding premature optimization
- **React** — framework demonstrated at [08:40]
- *The Pragmatic Programmer* — book recommended at [15:20]
```

Include the timestamp where each reference appears so the user can hear the original context.

## Quality Bar

- **Anchor with available timestamps.** Topics, quotes, and key points retain source timing. If supplied text has no timestamps, disclose that limit rather than inventing anchors or fetching solely to populate a template.
- **Separate fact from inference.** The transcript is evidence; the dossier is interpretation. Mark uncertain claims explicitly.
- **Filter synthesis, not evidence.** Omit irrelevant non-speech from summaries; leave raw exports unchanged. Preserve markers inside quotations or mark omissions explicitly.
- **Respect transcript source.** When the source is `auto-generated`, names and technical terms may be wrong. Do not treat transcribed proper nouns as verified. Add a note at the top: "Transcript is auto-generated; names and terms may contain errors."
- **Preserve named references.** Keep exact tool names, library names, paper titles, and URLs as transcribed, but note when the transcript source is auto-generated.
- **Chunk when useful.** Choose topic or timestamp chunks based on context capacity and requested coverage, not a fixed duration threshold. Preserve provenance and avoid duplicate takeaways when merging.

## What NOT to Include

- The full raw transcript unless requested (a separate raw export is available)
- Personal opinions about the speaker or channel
- Speculation about what the speaker meant (unless explicitly marked as inference)
- Timestamps for every sentence (only for topics, quotes, and key points)

## See Also

- `references/fetching.md` — how to get the transcript and metadata
- `references/gotchas.md` — handling transcript quality issues
- `templates/dossier.md` — optional full-dossier skeleton

# audify Common Patterns & Workflows

## Table of Contents

- [When to ask a question](#when-to-ask-a-question)
- [Supported resource types](#supported-resource-types)
- [Production commands](#production-commands)
- [Runtime expectations and user updates](#runtime-expectations-and-user-updates)
- [Output bundle layout](#output-bundle-layout)
- [Cleaning and bail behavior](#cleaning-and-bail-behavior)

## When to Ask a Question

Ask one short question when the user cares about delivery but did not specify voice or nuance:

```text
Which voice and delivery should I use? If you do not care, I will use Kore with a clear neutral narrator style.
```

Do not ask when:

- the user explicitly says "use the default"
- the content is a generic article, memo, or note and there is no stylistic constraint
- the request is urgent and a neutral narrator is clearly acceptable

## Supported Resource Types

`scripts/audify.py` handles:

- raw text passed as the positional argument
- `--stdin`
- `--file` for plain text, markdown, HTML, XML, JSON, and DOCX
- `--url` for HTTP or HTTPS pages that return text-like content

Treat these as hard stops:

- binary files that are not plain-text-readable
- media files, archives, or images
- sources that still look like code or logs after cleaning
- URLs that cannot be fetched or decoded after all read attempts

## Production Commands

Turn a URL into an MP3 bundle:

```bash
python3 scripts/audify.py "https://example.com/"
```

Turn a local markdown or HTML file into an MP3 bundle:

```bash
python3 scripts/audify.py --file templates/sample-input.md --voice Sulafat --nuance "Warm, reflective narrator with gentle pacing."
```

Turn stdin into an MP3 bundle:

```bash
cat templates/sample-input.md | python3 scripts/audify.py --stdin --voice Achird --nuance "Friendly explainer who sounds natural, not theatrical."
```

Preview cleaning and bail heuristics without calling Gemini:

```bash
python3 scripts/audify.py --url "https://example.com/" --check-only
```

Write a WAV bundle instead of MP3:

```bash
python3 scripts/audify.py --file templates/sample-input.md --format wav
```

## Runtime Expectations and User Updates

Set expectations once before long synthesis runs instead of narrating every short poll.

Practical guidance:

- 1 short chunk, roughly under 250 cleaned words: usually under 1 minute
- 1-2 chunks, roughly up to 600 cleaned words: often 1-3 minutes
- 2-4 chunks, roughly up to 1500 cleaned words: often 2-6 minutes
- 5 or more chunks: can take 5-10+ minutes

The wrapper now prints an upfront estimate and chunk progress to `stderr`, for example:

```text
audify: 810 words across 3 chunk(s); expected runtime often 2-6 minutes. Wait about 90 seconds between status checks.
audify: Longer TTS jobs can stay quiet between chunk completions. Do not treat 30-90 seconds of silence as failure.
audify: synthesizing chunk 1/3 (1915 chars)
audify: finished chunk 1/3 in 1 attempt(s)
```

Use that to shape the user-facing update cadence:

- give one expectation-setting message before synthesis starts
- do not keep saying "still running" every few seconds
- only send another update when a chunk finishes, a retry happens, or the run completes

When a large chunk times out or hits a transient 5xx, keep the same synthesis parameters and retry that chunk as smaller subchunks. Example status stream:

```text
audify: chunk 1/1 hit a transient failure; retrying as 3 smaller chunks while keeping model, voice, and nuance unchanged
audify: synthesizing chunk 1/1.1 (1124 chars)
audify: finished chunk 1/1.1 in 1 attempt(s)
```

That fallback should not:

- reset the selected voice
- rewrite the nuance prompt
- switch models silently
- start a brand-new output bundle unless the whole run actually failed

Observed benchmark from a real local run:

- `cleaned.txt` length: 810 words, 5180 bytes
- chunking: 3 chunks
- completion time: a bit over 2 minutes

That is a normal long-form run, not a warning sign.

## Output Bundle Layout

The wrapper creates a timestamped folder by default:

```text
audify-output/
  20260416-143500-example-article/
    audio.mp3
    cleaned.txt
    manifest.json
```

`manifest.json` records:

- original source
- detected source type
- selected voice
- nuance string
- chunk count
- planned chunk count before fallback
- retry counts
- rejected or removed content metrics
- runtime expectation label and recommended poll interval in the wrapper JSON output
- fallback event metadata when large chunks had to be subdivided

## Cleaning and Bail Behavior

The cleaner preserves visible prose and removes transport markup:

- Markdown links become their visible anchor text
- HTML tags are stripped after article or body extraction
- bare URLs are removed
- fenced code blocks are dropped
- YAML frontmatter and reference-link definitions are dropped

The wrapper bails when the result still does not sound like speech:

- heavy code or log patterns
- symbol density that is too high for natural narration
- too little human-readable text after cleaning

Use `--check-only` before synthesis when you are unsure whether the source is actually narration-friendly.

## See Also

- `references/api.md` for the REST payload and voice catalog
- `references/configuration.md` for setup and model availability checks
- `references/gotchas.md` for retry behavior and Google-documented edge cases

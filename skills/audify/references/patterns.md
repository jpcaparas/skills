# audify Common Patterns & Workflows

## Table of Contents

- [When to ask a question](#when-to-ask-a-question)
- [Supported resource types](#supported-resource-types)
- [Production commands](#production-commands)
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
- retry counts
- rejected or removed content metrics

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

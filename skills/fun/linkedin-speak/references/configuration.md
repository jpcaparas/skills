# Configuration

Use `scripts/linkedin_speak.py` as the deterministic engine. It reads text from a positional argument, stdin, or `--input-file`.

## Prerequisites

- `python3`
- plain UTF-8 text input

No external API key is required.

## Input Sources

| Source | Example |
| --- | --- |
| Positional argument | `python3 scripts/linkedin_speak.py "I got a new job."` |
| Stdin | `printf '%s' "I shipped the feature." \| python3 scripts/linkedin_speak.py` |
| File | `python3 scripts/linkedin_speak.py --input-file ./status.txt` |

## Core Flags

| Flag | Meaning |
| --- | --- |
| `--mode translate` | Plain English to LinkedIn-speak |
| `--mode reverse` | LinkedIn-speak to plain English |
| `--mode both` | Returns both directions in one response |
| `--format text` | Human-readable output |
| `--format json` | Structured output with metadata |
| `--intensity 1..5` | Controls hype, sentence count, and default hashtag volume |
| `--no-hashtags` | Suppress trailing hashtags |
| `--no-emoji` | Suppress the celebratory emoji |
| `--compare-kagi-url` | Include a prefilled Kagi Translate URL for manual comparison |

## Kagi Comparison Mode

Kagi's LinkedIn Speak feature is publicly visible through the web translator, but no documented public API surfaced during research. Use `--compare-kagi-url` when the user wants a manual side-by-side check:

```bash
python3 scripts/linkedin_speak.py \
  --compare-kagi-url \
  "Today, I've completed an interesting project!"
```

That prints a URL like:

```text
https://translate.kagi.com/?from=en&to=linkedin&text=...
```

Open it in a browser to compare the local deterministic output against Kagi's live web UI.

## Read Next

- `references/commands.md` for exact command shapes and output structure
- `references/patterns.md` for the transformation rules
- `references/gotchas.md` for the parody limits and edge cases

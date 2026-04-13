# Commands

Use `scripts/linkedin_speak.py` for the actual translation work and `scripts/probe_linkedin_speak.py` for verification.

## Main CLI

### Translate

```bash
python3 scripts/linkedin_speak.py "I got a new job."
```

### Reverse

```bash
python3 scripts/linkedin_speak.py \
  --mode reverse \
  "Thrilled to announce that I’m starting a new chapter today! Grateful for everyone who made this possible. 🚀 #GrowthMindset #Leadership"
```

### JSON

```bash
python3 scripts/linkedin_speak.py \
  --mode both \
  --format json \
  --intensity 4 \
  "We launched the dashboard."
```

Example JSON shape:

```json
{
  "mode": "both",
  "input": "We launched the dashboard.",
  "translation": "Excited to share ...",
  "reverse": "We launched the dashboard.",
  "metadata": {
    "intensity": 4,
    "hashtags_included": true,
    "emoji_included": true,
    "kagi_compare_url": "https://translate.kagi.com/?from=en&to=linkedin&text=We%20launched..."
  }
}
```

### Stdin

```bash
cat ./draft.txt | python3 scripts/linkedin_speak.py --mode translate --format text
```

### File Input

```bash
python3 scripts/linkedin_speak.py --input-file ./draft.txt --mode reverse
```

## Probe

Run the built-in behavior probe:

```bash
python3 scripts/probe_linkedin_speak.py
```

The probe checks that:

- translate mode produces a hype-style opener
- reverse mode removes hashtags and emoji
- JSON mode returns the expected keys
- the Kagi comparison URL is generated correctly

## Validator And Test Commands

```bash
python3 scripts/validate.py skills/linkedin-speak
python3 scripts/test_skill.py skills/linkedin-speak
```

## Read Next

- `references/configuration.md` for setup and input rules
- `references/patterns.md` for the translation heuristics
- `references/gotchas.md` for limits and edge cases

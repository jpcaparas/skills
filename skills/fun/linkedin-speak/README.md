# linkedin-speak

Installable parody skill for translating plain English into deterministic LinkedIn-speak and back again.

`linkedin-speak` is a fun, reproducible wrapper around a local heuristic engine that mimics the viral "LinkedIn Speak" style popularized by Kagi Translate's novelty language launch in March 2026.

## What it covers

- deterministic plain-English to LinkedIn-speak translation
- reverse translation from bloated post to blunt English
- adjustable cringe intensity
- optional emoji and hashtag control
- Kagi web-UI comparison links for side-by-side checking

## Key files

- `SKILL.md` — authoritative instructions
- `scripts/linkedin_speak.py` — translator and reverse-translator CLI
- `scripts/probe_linkedin_speak.py` — lightweight behavior probe
- `references/patterns.md` — transformation rules and examples
- `references/gotchas.md` — limits, edge cases, and anti-patterns

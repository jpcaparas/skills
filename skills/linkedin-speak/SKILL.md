---
name: linkedin-speak
description: "Turn plain English into comically polished LinkedIn-speak and reverse bloated thought-leadership posts back into blunt English. Use when the user wants to sound like a corporate influencer, parody announcement culture, translate into or out of LinkedIn voice, add hashtags and gratitude without improvising, or generate deterministic meme text that stays reproducible across runs. Trigger on: 'linkedin speak', 'translate this into linkedin', 'make this sound like a thought leader', 'reverse this linkedin post into normal english', 'turn my update into corporate cringe'. Do NOT use for real translation between human languages, serious executive communications that must stay tasteful, or cases where the user wants subtle editing instead of full parody."
compatibility: "Requires: python3. Optional side-by-side comparison link for Kagi Translate's LinkedIn Speak web UI."
metadata:
  version: "1.0.0"
  repo_tags:
    - parody
    - writing
    - cli-tool
---

# LinkedIn Speak

Translate ordinary text into gloriously overcaffeinated LinkedIn-speak, or strip a bloated post back down to plain English.

Verified against the observable Kagi Translate rollout and press examples published in March and April 2026.

## Decision Tree

1. If the user wants a deterministic parody of LinkedIn announcement culture, run `scripts/linkedin_speak.py --mode translate`.
2. If the user pasted a breathless growth-journey post and wants the actual meaning, run `scripts/linkedin_speak.py --mode reverse`.
3. If they want both versions for comparison, run `scripts/linkedin_speak.py --mode both --format json`.
4. If they want a side-by-side check against Kagi's public web translator, add `--compare-kagi-url`.
5. If they want tasteful professional editing instead of satire, stop and use `{{ skill:better-writing }}` instead.

## Quick Reference

| Task | Command | Why |
| --- | --- | --- |
| Translate plain text into LinkedIn-speak | `python3 scripts/linkedin_speak.py "I finished the project."` | Fast happy path with deterministic output |
| Reverse a corporate-cringe post into plain English | `python3 scripts/linkedin_speak.py --mode reverse "Thrilled to announce..."` | Removes hype, hashtags, and filler |
| Compare both directions as JSON | `python3 scripts/linkedin_speak.py --mode both --format json "I got a new job."` | Easier to feed another tool |
| Dial the cringe up or down | `python3 scripts/linkedin_speak.py --intensity 5 "We shipped the feature."` | Controls sentence count, hype, and hashtags |
| Drop hashtags and emoji | `python3 scripts/linkedin_speak.py --no-hashtags --no-emoji "I fixed the bug."` | Keeps the parody cleaner |
| Build a Kagi comparison URL | `python3 scripts/linkedin_speak.py --compare-kagi-url "I built a dashboard."` | Opens the same input in Kagi's public web UI |
| Run the local probe suite | `python3 scripts/probe_linkedin_speak.py` | Verifies core translation behavior |

## Scope

### Positive triggers

- "translate this into linkedin speak"
- "make this sound like a linkedin influencer"
- "turn this into a corporate announcement"
- "reverse this linkedin post into plain english"
- "add hashtags and fake gratitude"
- "give me the full growth mindset cringe version"

### Negative triggers

- actual multilingual translation
- subtle resume polish
- sober launch notes
- legal, HR, or investor communications
- real executive ghostwriting

## Working Rule

Default to the deterministic local translator first. It is reproducible, fast, and does not depend on external APIs. Use the Kagi comparison link only when the user wants to compare the local parody against the public LinkedIn Speak translator.

## What The Script Actually Does

- expands a plain statement into a short announcement arc
- chooses an opener, reflection sentence, gratitude sentence, emoji, and hashtags deterministically from the input text
- maps common actions like shipping, learning, hiring, speaking, leading, fixing, and launching onto predictable corporate phrasing
- reverses inflated posts by stripping hashtags, emoji, boilerplate hype, and vague self-congratulation

## Reading Guide

| Need | Read |
| --- | --- |
| CLI flags, input methods, and Kagi comparison links | `references/configuration.md` |
| Output patterns, intensity rules, and deterministic heuristics | `references/patterns.md` |
| Full command catalog and JSON output shape | `references/commands.md` |
| Failure modes, limits, and where the parody can get too repetitive | `references/gotchas.md` |

## Gotchas

1. The translator is intentionally satirical, not subtle. If the user wants "better LinkedIn copy," this skill is the wrong tool.
2. The reverse translator removes hype heuristically. It will simplify the message well, but it cannot perfectly recover every omitted fact if the original post never stated them plainly.
3. Deterministic output means the same input stays stable across runs. That is useful for tests and memes, but it also means the phrasing can feel formulaic on repeated use.
4. Kagi's public LinkedIn Speak implementation is not a documented API. This skill uses a local engine by default and only emits a comparison URL for the web UI.
5. Hashtag selection is keyword-driven. If the input is too vague, the fallback tags will lean generic on purpose.

## Recommended Destination

Recommended destination: `skills/linkedin-speak`
Reason: this repo is already a public installable skills source that stores canonical skills under `skills/<skill-name>/`.
Alternative: none needed for this repository.

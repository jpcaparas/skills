# namethatui

Production skill for identifying unfamiliar interface components from descriptions, screenshots, live pages, or DOM/code clues. It returns ranked names, aliases, plain-English distinctions, prompt-ready wording, and direct authoritative examples without accessing `namethatui.com`.

The authoritative instructions live in `SKILL.md`.

## Key files

- `SKILL.md` — canonical workflow and answer contract
- `references/component-families.md` — behavior-first comparison of confusable patterns
- `references/visual-intake.md` — local screenshot-analysis route
- `references/research-and-sources.md` — search API, agent-browser, source, and blocked-host policy
- `scripts/prepare_research.py` — bounded query planning and URL guard
- `scripts/check_benchmark_evidence.py` — exact-current assertion, run-provenance, and resource-metric consistency check
- `evals/evals.json` — behavioral release cases

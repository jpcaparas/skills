# preventing-ui-slop

A standing guardrail for UI creation, edits, reviews, and generation prompts.
It rejects decorative defaults, unsupported status, and redundant copy while
preserving explicit design intent and meaningful state. It complements
`interface-design-taste` rather than choosing one visual style for every product.

```bash
npx skills add jpcaparas/skills --skill preventing-ui-slop
```

Read [SKILL.md](SKILL.md) for the instructions.
The description requests automatic use for UI tasks; discovery and compliance
still depend on the agent harness. This is guidance, not an enforced UI linter.

Package maintenance requires Python 3.11+ and PyYAML; using the skill does not:

```bash
python3 scripts/validate.py .
python3 scripts/test_skill.py .
```

Run those commands from the installed package directory. The scripts check
packaging and eval integrity, not visual quality or model behaviour. See the
[evaluation notes](evals/README.md) before claiming behavioural evidence.

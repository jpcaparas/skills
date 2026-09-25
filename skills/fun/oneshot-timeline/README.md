# oneshot-timeline

Builds a working, accessible explainer timeline with topic-matched visual direction and source-backed storytelling. Pastel-paper collage is a default, not a required style.

Example requests:

- “Make a timeline website that explains what happens when I type a web address.”
- “Build an investigative timeline of the Enron collapse for someone who knows no accounting.”

Each project contains editable `workspace/` source and a portable `artifact/` site. A coding environment and browser are needed to build and verify the result; web and image tools enhance research and artwork when available.

See [SKILL.md](SKILL.md) for the authoritative workflow. Package checks use Python 3.11+:

```bash
python3 scripts/validate.py .
python3 scripts/test_skill.py .
```

These check package integrity, not model behaviour or the accessibility of a generated website. Behavioural scenarios and invocation queries live in `evals/`.

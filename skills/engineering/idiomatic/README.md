# idiomatic

A framework-, library- and paradigm-agnostic skill for turning a legacy workspace into a defensible, phased improvement plan. It investigates why unusual code exists, protects fragile contracts and proposes useful native conventions without prescribing a rewrite.

Try: “Use idiomatic to assess this workspace. Give me an endorsement-ready plan we can tackle in short sessions; don't change code yet.” Or: “Use idiomatic, plan the work and execute the safe local phases. Production changes require a separate decision.”

`SKILL.md` is authoritative. Documentation MCP servers and authorised production evidence improve precision but are not prerequisites. The skill works with repository evidence and makes missing access explicit.

The references cover fragile-behaviour harnesses, production-data preparation, and human/agent handoffs. Scripts are package-maintenance checks, not an automated architecture assessor:

```bash
python3 scripts/validate.py .
python3 scripts/test_skill.py .
```

These require Python 3.11+ and PyYAML. They validate packaging and authored evals, not the quality of a generated plan. See `evals/README.md` for behavioural verification and its limits.

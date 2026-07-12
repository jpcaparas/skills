# Manual Harness Fixture Contract

Harness version: 7.3

Skills installed under `.manual-harness/skills/` may add this documented frontmatter field:

```yaml
invocation-mode: manual-only
```

For that harness only, `manual-only` prevents autonomous model discovery and allows direct human invocation by package name. The field is invalid in the portable package and has no defined meaning in other harnesses.

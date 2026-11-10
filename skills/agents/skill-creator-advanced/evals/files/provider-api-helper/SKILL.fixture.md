---
name: provider-api-helper
description: "Call the Orbit provider API to inspect projects and deployments."
---

# Provider API Helper

Use the provider token from `ORBIT_TOKEN`.

## Inspect a project

```bash
curl --fail-with-body "https://api.orbit.example/v1/projects/$PROJECT_ID"
```

The request is read-only.

## Reference Files

Read `references/gotchas.md` before writing or reviewing request examples; use it to apply cross-example safety rules.

---
name: repository-readme-writer
description: "Create or improve concise, useful, agent-safe repository READMEs. Use for new README drafts, rewrites, quickstarts, local setup, getting started, contributor docs, or README reviews. Do NOT use for API reference, full product docs, changelogs, or landing pages."
compatibility: "Requires: python3 for `scripts/repo_readme_probe.py`, `scripts/validate.py`, and `scripts/test_skill.py`."
metadata:
  version: "1.0.0"
references:
  - foundations
  - repository-audit
  - quickstart-design
  - rewrite-patterns
  - gotchas
---

# Repository README Writer

Create or improve repository READMEs that help humans and agents understand the project quickly without overfitting to fragile implementation details.

## Decision Tree

What kind of README work is this?

- Creating a new README from a repository
  Inspect relevant repository evidence; consult `references/repository-audit.md` and adapt `templates/repository-readme.md` when useful.

- Improving an existing README
  Read `references/rewrite-patterns.md`, then preserve useful sections and remove stale or overly specific material.

- Fixing only the setup path
  Read `references/quickstart-design.md` and make the quickstart the shortest verified path from clone to useful local feedback.

- Reviewing README quality without editing yet
  Review the requested scope against repository evidence. The probe and `templates/readme-review.md` are optional aids for broader reviews, not prerequisites for a wording or link review.

- Unsure which path applies
  Start with `references/foundations.md`, then inspect the repository before writing.

## Quick Reference

| Task | Do this | Read |
|---|---|---|
| Draft a new README | Inspect purpose, package manager, commands, config, checks, and deployment signals before writing | `references/repository-audit.md` |
| Improve an existing README | Keep accurate high-signal content, cut brittle inventory, add or repair quickstart | `references/rewrite-patterns.md` |
| Design quickstart | Use the fewest commands needed to install, configure, run, and verify | `references/quickstart-design.md` |
| Avoid over-documenting | Keep implementation detail out unless it changes day-one usage | `references/foundations.md` |
| Catch common failures | Check version pins, path inventories, stale commands, and agent-hostile wording | `references/gotchas.md` |
| Get repo signals quickly | Run `python3 scripts/repo_readme_probe.py <repo>` | `references/repository-audit.md` |

## Operating Contract

1. Inspect before writing. A README that guesses commands, package managers, ports, or deployment shape is worse than no README.
2. Write for the reader's first useful action. Apps may need runnable setup; libraries need usage, datasets need access and schema, and archived repositories may need status and migration guidance instead.
3. Explain roles and boundaries, using verified stable source paths when they help navigation. Avoid exhaustive directory tours, not useful paths.
4. Document supported version ranges when useful. Prefer manifests, lockfiles, version manager files, or CI for exact pins; repeat an exact requirement in prose when it materially helps and link its source of truth.
5. Keep examples executable and few. A README should show the happy path and the main verification command, not every script in the project.
6. Make it safe for AI agents. Do not over-constrain future agents with brittle rules, exhaustive inventories, or stale assumptions that they may follow verbatim.

## Default README Shape

For a runnable application, this is a starting point, not a required nine-section structure. Follow the user's requested form and include only sections useful to this repository.

1. Title
2. One-sentence project summary
3. Quickstart
4. Project shape or architecture boundary
5. Configuration
6. Local development
7. Quality checks
8. Deployment or release notes, if discoverable
9. Troubleshooting, only for common day-one failures

For small repositories, merge related sections. For large repositories, keep the root README high-level and link to dedicated docs instead of copying them.

## Section Standards

### Summary

Say what the project is and what it is for in one or two sentences. Do not open with internal tooling unless the tooling is the product.

### Quickstart

Include a quickstart when first use involves executable steps. It should lead to a visible verification point using evidence-backed commands, with only necessary configuration. Use an import example for a library or access/schema guidance for data when that better serves the reader. Do not invent commands or a build system for a static or archived repository.

### Project Shape

Explain boundaries and responsibilities. A sentence such as "the CMS owns content and the website reads through server-side API routes" can include stable source links that help readers find those components.

### Configuration

Name required environment variables or configuration groups only when they are necessary for local use or deployment. Avoid dumping every variable.

### Quality

Give the single shared quality gate first. Add targeted commands only when they help a common workflow.

### Deployment

Document the deployment model and required services. Avoid provider-specific minutiae unless the repository clearly depends on them.

## Templates

- `templates/repository-readme.md`
  Optional application-oriented starter; omit, reorder, or replace irrelevant sections.

- `templates/readme-review.md`
  Optional review outline; keep findings within the requested scope.

## When guidance is insufficient

When guidance is stale, incomplete, or conflicts with a repository, inspect its manifests, source, tests, and maintained docs first. Consult current official tool documentation only for unresolved behavior. Use compatible verified commands within the user's authority, distinguish inspected from executed checks, and disclose gaps. Propose a canonical skill correction with the source and an example or reproducible check; do not silently change an installed copy or browse for routine wording edits.

## Gotchas

1. A path inventory feels helpful on day one and becomes stale after the first refactor.
2. Exact version prose rots faster than manifests, lockfiles, version manager files, and CI.
3. A giant command catalog hides the one command a new contributor actually needs.
4. A README written only for humans may omit machine-useful commands; a README written only for agents may become too literal and brittle.
5. If quickstart commands are not verified, label uncertainty or inspect further before presenting them as authoritative.

## Reading Guide

| Need | Read |
|---|---|
| Core README philosophy and section rules | `references/foundations.md` |
| Repository inspection workflow and evidence ranking | `references/repository-audit.md` |
| Quickstart structure, command selection, and verification | `references/quickstart-design.md` |
| Existing README rewrite tactics | `references/rewrite-patterns.md` |
| Failure modes and recovery patterns | `references/gotchas.md` |

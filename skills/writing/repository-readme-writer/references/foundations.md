# Foundations

Repository READMEs should make the project understandable and runnable without becoming a fragile mirror of the current file tree.

## What A Good README Does

- Names the project and its purpose plainly.
- Gives the fastest reliable path from checkout to useful local feedback.
- Explains the main architectural boundary in stable language.
- Points to configuration, quality checks, and deployment expectations.
- Leaves deeper details to dedicated docs, source comments, manifests, and scripts.

## What To Avoid

- Long path inventories. Directory names and workspace layouts change.
- Exact tool versions in prose. Use the repository's manifest, lockfile, version manager file, or CI config as the source of truth.
- Exhaustive command catalogs. Readers need the shared gate and the few task-specific commands that matter.
- Generic filler such as "This project is a modern web application."
- Overly rigid instructions that future agents may follow verbatim after the project has changed.

## Reader Model

Write for three readers at once:

- A human deciding whether the repository is relevant.
- A contributor trying to run it locally.
- An agent that needs enough orientation to make good edits without being trapped by stale instructions.

The README should not replace repository inspection. It should tell the reader what matters first.

## Stability Ladder

Prefer stable facts over fragile facts.

| More stable | Less stable |
|---|---|
| Product purpose | Current folder names |
| App/service responsibility | Exact source paths |
| Package manager family | Tool patch versions |
| Shared quality gate | Every available script |
| Deployment model | Provider dashboard steps |
| Required configuration groups | Complete env variable dump |

Use fragile details only when they are required for day-one success and verified from the repository.

## Voice

Use short direct sections. Prefer present tense. Avoid sales copy, ceremonial introductions, and apology language.

Good:

```markdown
# Project Name

A scheduling service for coordinating appointment slots across clinics.
```

Weak:

```markdown
# Project Name

This repository contains the source code for a modern, scalable, robust scheduling application.
```

## Default Section Rules

### Quickstart Is Mandatory

Every repository README needs a quickstart. If the project cannot run locally, write the closest useful first-run path and say what external dependency blocks a full run.

### Architecture Stays High-Level

Explain how the major pieces talk to each other. Do not list every package or subdirectory unless the repository is a library where import paths are part of the interface.

### Commands Are Verified

Only present commands that are supported by manifests, scripts, Makefiles, task runners, CI, or existing docs. If a command is inferred but untested, inspect further or mark it as an assumption in review notes, not in the final README.

### Links Beat Duplication

When the repository already has detailed docs, keep the README short and link to the right place. Do not copy long setup or deployment docs into the root README.

## Output Standard

The final README should feel useful at a glance:

- headings are predictable
- command blocks are few
- setup steps are ordered
- project boundaries are clear
- known failure recovery is short
- nothing reads like generated filler

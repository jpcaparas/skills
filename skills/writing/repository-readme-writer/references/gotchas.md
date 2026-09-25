# Gotchas

Common README failure modes and how to recover from them.

## Quickstart Missing Or Late

For a runnable project, keep the first-use path easy to find. Do not add a quickstart to a static or archived repository merely to fill a section, or reorder unrelated content during a scoped review.

## Version Pins In Prose

Duplicate pins can decay. Prefer the configured toolchain as their source of truth, while retaining useful supported ranges or exact requirements with a source link. Do not remove a real compatibility boundary in the name of evergreen prose.

## Path Tours

A path tour is not architecture. Explain project roles and boundaries, retaining verified stable source paths when they help readers navigate or contribute. Cut noise, not useful orientation.

## AI-Hostile Over-Specification

Agents may follow README text literally long after it becomes stale. Avoid rules that sound permanent when they are just current observations. Use stable concepts and link to source-of-truth files when details evolve.

## Unverified Commands

Do not present guessed commands as fact. If command verification is expensive, at least ground commands in manifest scripts or CI. In review mode, label unverified commands as risks.

## Env Var Dumps

Long env lists make READMEs noisy and stale. Group configuration by purpose and mention required local values. Keep the complete list in example env files or configuration docs.

## Too Much Troubleshooting

Troubleshooting should cover common day-one failures only. If the section becomes a runbook, move it into docs and link to it.

## Marketing Voice

Repository READMEs are not landing pages. Remove inflated claims, vague adjectives, and "modern/scalable/robust" filler unless those qualities are backed by concrete design.

## Monorepo Confusion

Monorepos benefit from a root-level mental model and a clear path to the relevant package's first-use instructions. Do not invent a root quickstart when packages are independently operated. Keep useful package commands and links.

## README As Policy Document

Do not turn the README into an agent policy file. Repository-specific operating rules belong in agent instruction files when the repo uses them. The README should remain public, practical, and durable.

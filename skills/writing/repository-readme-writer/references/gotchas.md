# Gotchas

Common README failure modes and how to recover from them.

## Quickstart Missing Or Late

If the README starts with background, architecture, badges, screenshots, or philosophy before setup, move quickstart up. Readers should not hunt for the first command.

## Version Pins In Prose

Pinned versions decay. Replace prose pins with guidance to use the repository's configured toolchain. Keep exact versions in manifests, lockfiles, version manager files, CI, or package manager configuration.

## Path Tours

A path tour is not architecture. Collapse directory lists into project roles and boundaries. Keep paths only for commands, files the user must edit, or public import paths.

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

Monorepos need a root-level mental model and a root-level quickstart. Package-specific commands belong only when they are common, stable, and helpful.

## README As Policy Document

Do not turn the README into an agent policy file. Repository-specific operating rules belong in agent instruction files when the repo uses them. The README should remain public, practical, and durable.

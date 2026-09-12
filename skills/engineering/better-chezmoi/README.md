# better-chezmoi

Safe, version-aware chezmoi workflows for daily dotfile work, multi-machine templates, secrets, recovery, and current official-reference research.

The skill keeps source, destination, local state, remote Git, and external effects separate. It includes curated workflow references, a searchable snapshot of selected official `chezmoi.io` pages, a rollback-safe refresh tool, and an isolated CLI contract probe.

`SKILL.md` is the canonical instruction file. References provide branch-specific detail; scripts provide deterministic scraping, search, validation, and disposable command verification.

## Requirements

- chezmoi for dotfile operations and the optional isolated CLI probe
- Python 3.10 or newer for documentation tooling and package checks

## Install

```sh
npx skills add jpcaparas/skills --skill better-chezmoi
```

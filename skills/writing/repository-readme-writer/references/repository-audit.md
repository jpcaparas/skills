# Repository Audit

Inspect the repository before writing or rewriting a README. Ground every setup command and project claim in files that actually exist.

## First Pass

Run the probe when you have filesystem access:

```bash
python3 scripts/repo_readme_probe.py <repo>
```

Use the output as evidence, not as README content. The probe intentionally finds paths and files; the README should usually translate those signals into stable project concepts.

## Manual Inspection Checklist

Look for these signals in order:

1. Existing README, docs, package manifests, task runners, and lockfiles.
2. Application or library entrypoints.
3. Local environment examples and required services.
4. Test, lint, typecheck, build, and combined quality commands.
5. CI workflows and deployment configuration.
6. Container, database, queue, object storage, or external API dependencies.
7. Agent instructions that describe repository-specific workflows.

## Evidence Ranking

| Signal | Use it for | Notes |
|---|---|---|
| Manifest scripts | install, run, check, build, test commands | Prefer the combined script if it exists |
| Lockfile | package manager | Do not mention lockfile details unless needed |
| Version manager file | runtime version source | Refer to it instead of copying exact versions |
| Env examples | local configuration | Mention only required local setup |
| CI workflow | quality gate and deployment hints | CI may be stricter than local docs |
| Existing docs | deeper links | Link instead of duplicating |
| Source entrypoints | purpose and architecture | Translate paths into roles |

## Package Manager Signals

Prefer the package manager implied by lockfiles and scripts:

- `pnpm-lock.yaml` implies pnpm
- `yarn.lock` implies Yarn
- `package-lock.json` implies npm
- `bun.lock` or `bun.lockb` implies Bun
- `uv.lock` implies uv
- `poetry.lock` implies Poetry
- `Cargo.lock` implies Cargo
- `go.mod` implies Go tooling

Do not pin package manager or runtime versions in README prose. If exact versions matter, tell readers to use the repository's configured toolchain.

## Command Selection

Choose the smallest truthful command set:

- install dependencies
- create local config, if required
- run the project
- run the shared quality gate
- run a narrow command only when common and discoverable

Prefer project-level commands over workspace-specific commands unless the user asked for a package README or the repository clearly expects package-level work.

## Architecture Extraction

Write a one-paragraph architecture summary from roles and boundaries:

- public app, admin app, API, worker, package, CLI, library, database
- client/server boundary
- content/data ownership
- external services
- build/deploy boundary

Avoid converting the source tree directly into prose.

## When Evidence Is Missing

If the repository lacks enough evidence:

- draft a minimal README that states only known facts
- leave placeholders out of the final README
- ask targeted questions after the draft or in review notes
- do not invent scripts, ports, cloud providers, or architecture

## Root README vs Package README

For root READMEs, explain the whole project at a stable level. For package READMEs, focus on the package's public interface, local development for that package, and how it fits the larger workspace.

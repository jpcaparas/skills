# Project Analysis

Audit the target project before you decide anything about OpenCode hooks.

## Inspect First

- repo root and whether the target path lives inside a Git repo
- languages, package managers, and task runners
- lint, test, typecheck, format, and validation entry points
- existing OpenCode files:
  - `opencode.json`
  - `opencode.jsonc`
  - `.opencode/plugins/`
  - `.opencode/package.json`
  - `.opencode/tools/`
  - `.opencode/agents/`
- existing user instructions:
  - `AGENTS.md`
  - `README*`
  - project-specific automation docs
- existing Git hooks or repo automation:
  - `.husky/`
  - `lefthook.yml`
  - `.githooks/`
- sensitive paths:
  - `.env`
  - `.env.*`
  - lockfiles
  - migrations
  - infra directories
  - generated output

## Questions To Answer

1. Should the hooks travel with the repo?
   - yes -> project-local `.opencode/plugins/`
   - no -> global `~/.config/opencode/plugins/`

2. Does the plugin logic need external dependencies?
   - no -> plain local JavaScript or TypeScript module is enough
   - yes -> merge dependencies into the config-dir `package.json`

3. Does the repo already have OpenCode plugins?
   - yes -> default to `additive`
   - no -> start with a clean managed layer

4. Does the repo already rely on npm plugin packages?
   - yes -> preserve those config entries and decide whether the new scaffold is `hybrid`
   - no -> keep config untouched unless the plan explicitly needs npm packages

5. Which plugin pattern fits the repo?
   - secret guardrails -> `tool.execute.before`
   - post-turn lint or test -> `tool.execute.after` plus `event` for `session.idle`
   - runtime env injection -> `shell.env`
   - extra project tools -> `tool`
   - context carry-over -> `experimental.session.compacting`

## Recommended Defaults

- Use project-local scope for real repos unless the user explicitly wants a personal global hook.
- Use JavaScript by default for the first scaffold because it avoids unnecessary dependency or type-check friction.
- Only add config-dir dependencies when the generated plugin code actually imports external packages.
- Prefer local plugin files over npm plugin publishing for the first iteration. Promote to npm only after the behavior stabilizes.


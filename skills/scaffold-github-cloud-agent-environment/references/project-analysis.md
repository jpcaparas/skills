# Project Analysis

Audit the target repository before choosing steps, runners, or troubleshooting paths.

## Audit Order

1. Find the repo root and canonical project path.
2. Inspect `.github/workflows/copilot-setup-steps.yml` first if it already exists.
3. Inspect CI workflows under `.github/workflows/` for runner hints and existing setup conventions.
4. Inspect package managers, lockfiles, and toolchain version files.
5. Inspect `.gitattributes` for Git LFS usage.
6. Inspect `.devcontainer/`, Dockerfiles, and Compose files for environment and service hints.
7. Inspect private-registry config files such as `.npmrc`, `.yarnrc.yml`, `pip.conf`, `.pypirc`, `.cargo/config.toml`, `nuget.config`, and `settings.xml`.
8. Inspect repo instructions:
   - `.github/copilot-instructions.md`
   - `.github/instructions/**/*.instructions.md`
   - `AGENTS.md`
   - `CLAUDE.md`
   - `GEMINI.md`
9. Inspect package scripts or task runners for likely install, build, test, and lint commands.
10. Decide what can be solved in-repo versus what requires GitHub settings access.

Run `scripts/audit_project.sh /path/to/project` first. The audit script reports facts and ambiguity signals so the plan stays explicit.

## Signals That Matter

| Signal | Why it matters |
|--------|----------------|
| Existing `copilot-setup-steps.yml` | Determines whether you should bootstrap or refresh |
| Multiple lockfiles or package managers | Usually means you need to ask which workflow is authoritative |
| Toolchain version files like `.nvmrc`, `.python-version`, `go.mod`, `global.json` | Let you scaffold setup steps without guessing runtime versions |
| `.gitattributes` with `filter=lfs` | Means checkout should use `lfs: true` |
| `.npmrc`, `.yarnrc.yml`, `pip.conf`, `.pypirc`, `nuget.config`, or `settings.xml` | Indicates registry auth, mirror, or firewall questions |
| Windows markers like `*.sln`, `*.csproj`, `Directory.Build.props` | May force a Windows decision or at least a question |
| Compose files or service definitions | Suggest the app may need `services` or a user decision |
| Existing CI runner labels | Strong signal for compatible runner choices |
| Missing `.github/copilot-instructions.md` | Copilot may still install dependencies, but build and validation behavior will stay underspecified |

## Questions To Ask Only When Needed

Ask only the questions the repo facts cannot answer. Useful examples:

- Does Copilot need Windows to build or validate this repository, or is Ubuntu sufficient?
- Must Copilot run on self-hosted or larger runners to reach internal resources?
- Which package manager is authoritative when the repo contains more than one lockfile?
- Which secrets or variables must exist in the `copilot` environment for private registries or internal tools?
- Should the setup workflow install every detected toolchain, or only the primary one?
- Are service containers safe to declare in GitHub Actions `services`, or do they depend on external infrastructure?

## Recommended Audit Output

The audit should leave you with:

- the canonical project root
- whether the repo already has a Copilot setup workflow
- languages, package managers, and toolchain version signals
- LFS, registry, container, and Windows hints
- instruction files and likely validation commands
- ambiguity signals that must become explicit questions

Do not silently convert ambiguity into hardcoded YAML.

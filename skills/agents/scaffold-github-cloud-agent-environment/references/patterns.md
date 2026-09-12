# Patterns

Use these patterns after the repo audit. Prefer the simplest setup that removes uncertainty without overfitting.

## General Rules

- Install dependencies, not the full application lifecycle.
- Use version files when they exist. Ask a question when the repo needs a version but does not declare one clearly.
- Prefer official GitHub actions for runtime setup when the version signal is strong.
- Keep service containers explicit and minimal. If the service topology is ambiguous, ask.
- Pair the workflow with `.github/copilot-instructions.md` when build, test, and validation commands are not already obvious.

## Node.js

### High-confidence signals

- `package.json`
- `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock`, or `bun.lockb`
- `.nvmrc` or `.node-version`
- `package.json` `engines.node`

### Preferred pattern

1. Check out the code.
2. If the repo declares a Node version, add `actions/setup-node`.
3. Install dependencies with the authoritative package manager.
4. For `pnpm` or `yarn`, enable Corepack before installing.

### Recommended install commands

| Package manager | Command |
|-----------------|---------|
| `npm` | `npm ci` |
| `pnpm` | `corepack enable` then `pnpm install --frozen-lockfile` |
| `yarn` | `corepack enable` then `yarn install --immutable` |

### Ask when

- the repo has more than one lockfile
- the repo uses Bun and there is no clear Bun bootstrap convention
- the repo needs a Node version but no version signal exists

## Python

### High-confidence signals

- `requirements.txt`
- `pyproject.toml`
- `poetry.lock`
- `.python-version`

### Preferred pattern

1. Check out the code.
2. If the repo declares a Python version, add `actions/setup-python`.
3. Install dependencies with the least surprising tool:
   - `python -m pip install -r requirements.txt`
   - `python -m pip install poetry && poetry install --no-interaction --no-root`

### Ask when

- `pyproject.toml` exists but the packaging tool is unclear
- the repo needs a Python version but does not declare one

## Go

### High-confidence signals

- `go.mod`

### Preferred pattern

1. Check out the code.
2. Add `actions/setup-go` using `go.mod` as the version file.
3. Run `go mod download`.

### Ask when

- multiple Go modules need different bootstrapping behavior
- the repo depends on private modules or internal proxies

## Ruby

### High-confidence signals

- `Gemfile`
- `.ruby-version`

### Preferred pattern

1. Check out the code.
2. Add `ruby/setup-ruby` when the Ruby version is declared clearly.
3. Let Bundler install dependencies, ideally through the action's cache support.

### Ask when

- the repo needs a Ruby version but only implies it indirectly
- the repo depends on private gems or internal gem mirrors

## JVM and .NET

Treat these as medium-confidence unless the repo clearly declares versions.

### Good signals

- `pom.xml`, `.mvn/`, `gradlew`, `.java-version`
- `global.json`, `*.sln`, `*.csproj`

### Preferred behavior

- Ask about the required runtime version if the repo does not declare it clearly.
- Ask whether Ubuntu is sufficient or whether Windows is required.
- Do not silently assume that a Windows marker means the entire setup must move to Windows.

## LFS

If `.gitattributes` contains `filter=lfs`, use `actions/checkout@v5` with `lfs: true`.

Do not infer LFS from large files alone.

## Private Registries and Internal Hosts

When registry config files or internal hostnames appear:

- add a question about required `copilot` environment secrets or variables
- add a manual-settings note about firewall allowlists or self-hosted networking
- prefer explicit registry auth over ad hoc shell scripts in the workflow

## Containers and Services

Signals:

- `.devcontainer/`
- `Dockerfile*`
- `docker-compose*.yml`
- `compose*.yml`

What they mean:

- `.devcontainer/` is a useful hint about dependencies and tools, but it is not automatically a valid GitHub Actions `services` design
- Docker or Compose files can reveal databases, caches, or queues that tests depend on
- if the service graph is simple and well-understood, `services` may be appropriate
- if the topology is complex or tied to external infrastructure, ask first

## Custom Instructions Companion Pattern

If the workflow can install dependencies but the repo does not clearly tell Copilot how to validate changes, recommend adding `.github/copilot-instructions.md`.

Good custom instructions usually include:

- the primary build command
- the primary test command
- the primary lint or format command
- important folder conventions
- any commands the agent must run before it considers work complete

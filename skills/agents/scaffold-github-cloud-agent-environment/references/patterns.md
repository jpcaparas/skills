# Ecosystem patterns

Check out the code first, add a runtime setup action only when the repo declares a version (`.nvmrc`, `.node-version`, `engines.node`, `.python-version`, `go.mod`, `.ruby-version`), then install with the authoritative tool. Action refs below are examples; keep the repo's own pins.

| Ecosystem | Install | Ask when |
|---|---|---|
| npm | `npm ci` | more than one lockfile; no Node version signal |
| pnpm | `corepack enable`, then `pnpm install --frozen-lockfile` | as npm |
| yarn | `corepack enable`, then `yarn install --immutable` | as npm |
| Bun | no standard bootstrap here | always, unless the repo documents one |
| Python | `python -m pip install -r requirements.txt`, or `python -m pip install poetry && poetry install --no-interaction --no-root` | `pyproject.toml` without a clear packaging tool; undeclared version |
| Go | `actions/setup-go` with `go.mod`, then `go mod download` | several modules; private modules or proxies |
| Ruby | `ruby/setup-ruby` with Bundler caching | version only implied; private gems |
| JVM, .NET | version from `.java-version`, `global.json` | undeclared version; whether Windows is really required (a `*.sln` or `*.csproj` does not imply it) |

Other signals:

- LFS only when `.gitattributes` contains `filter=lfs`, never from large files alone.
- Registry config (`.npmrc`, `.yarnrc.yml`, `pip.conf`, `.pypirc`, `.cargo/config.toml`, `nuget.config`, `settings.xml`) or internal hostnames: add a question about `copilot` environment secrets and a manual-settings note about firewall allowlists or networking.
- `.devcontainer/`, Dockerfiles and Compose files hint at dependencies and services but are not a valid Actions `services` design by themselves. Use `services` only when the topology is simple and well understood.

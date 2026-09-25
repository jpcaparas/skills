# Narrow Test, Lint, and Container Commands

Run the smallest stack-native command that can answer the question.

## Presence-Gated Tools

Prefer these tools when they exist on `PATH`. If a tool is missing, fall back to the project's native scripts or documented workflow instead of inventing a replacement.

| Tool | Start command | Narrowing knobs | Notes |
| --- | --- | --- | --- |
| `cargo test` | `cargo test name -- --nocapture` | test name, package path, `-- --nocapture` | Best for one Rust test or module first |
| `npm test` | `npm test -- <runner-args>` | args after `--` | Check help if runner flags are unknown |
| `ruff check` | `ruff check path/` | file path, directory path, `--fix` | Keep autofix explicit |
| `pytest` | `pytest -q tests/test_file.py -k expr` | file path, node id, `-k`, `-q` | Quiet output cuts noise without hiding failures |
| `go test` | `go test ./pkg/... -run Pattern` | package path, `-run`, `-count=1` | Package scoping matters more than global suite speed |
| `docker ps` | `docker ps --format '{{json .}}'` | `--filter`, compact table formats | Structured rows are easier to summarize |

## Command Patterns

### Rust

```bash
cargo test login_flow -- --nocapture
```

Use name filters or narrow package paths for focused feedback, and full crate or workspace runs when the task or repository gates require them.

### Node

```bash
# When the runner's flags are unknown
npm test -- --help

# When the project uses a runner supporting this flag
npm test -- --runInBand
```

The exact flags depend on the underlying runner. The `--` separator is the important invariant.

### Ruff

```bash
ruff check src/
ruff check src/module.py
```

Use `--fix` for relevant, reviewable changes within already-authorized implementation or cleanup work; no separate confirmation is needed for ordinary authorized autofixes. Keep read-only investigations read-only and avoid unrelated fixes.

### Pytest

```bash
pytest -q tests/test_api.py -k login
pytest -q tests/test_api.py::test_login
```

`-q` trims noise without hiding assertion output.

### Go

```bash
go test ./internal/auth/... -run Login
```

Start with the narrowest package tree that covers the suspect code path.

### Docker

```bash
docker ps --format '{{json .}}'
docker ps --filter name=api --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
```

Use `--filter` early. Raw `docker ps` tables are readable, but compact formats are easier to summarize or pipe into other tools.

## Decision Rules

- If the user only needs a smoke check, choose one target, not the whole suite.
- If the failure surface is unknown, start with the closest package or file to the changed code.
- If the project wraps everything in `make`, `just`, or package scripts, inspect those first instead of forcing a foreign command shape.
- A slow command alone does not require confirmation. Run required repository gates; obtain authority for external writes, paid operations, or destructive effects not already authorized by the task.

## Availability Probe

If a comprehensive check is useful, run `python3 scripts/probe_implicit_token_savings.py --format pretty` to see which runners exist and which behaviors were verified. Otherwise use known runner information or check only the needed executable.

See `references/patterns.md` for fallbacks and `references/gotchas.md` for argument-forwarding and daemon traps.

# Froggy Hook Events

> **Drift, 2026-11-10 (unresolved).** `opencode-froggy` 1.7.0+ no longer loads `.opencode/hook/hooks.md`, and OpenCode marks the `plugin` config key deprecated in favour of `plugins`. This scaffold still targets the 0.12.0-era Froggy behaviour below. Evidence and open questions: `assets/hook-events.json` under `drift_2026_11_10`. Until the owner decides (pin a hook-capable Froggy, or move to a native OpenCode plugin), do not tell a user the generated hooks will run on a current Froggy; check with `opencode plugin list` and a live session.

`opencode-froggy` exposes a smaller hook DSL on top of OpenCode's plugin API.

## Hook File Shape

```markdown
---
hooks:
  - event: session.idle
    conditions: [isMainSession]
    actions:
      - bash: "npm run lint"
---
```

## Events

| Event | Use |
|-------|-----|
| `session.created` | Run root-session bootstrap or baseline scripts |
| `session.deleted` | Cleanup session state |
| `session.idle` | Run post-turn checks after OpenCode edits files |
| `tool.before.*` | Run before every tool; bash exit `2` blocks |
| `tool.before.<name>` | Run before a specific tool, such as `tool.before.write` |
| `tool.after.*` | Observe every tool after execution |
| `tool.after.<name>` | Observe a specific tool after execution |

## Conditions

| Condition | Meaning |
|-----------|---------|
| `isMainSession` | Skip child/subagent sessions |
| `hasCodeChange` | Run only when Froggy tracked edited files with known code extensions |

Do not use `hasCodeChange` for Markdown-heavy skills repositories unless skipping Markdown-only changes is acceptable.

## Actions

| Action | Meaning |
|--------|---------|
| `bash` | Run a shell command through `bash -c` |
| `command` | Invoke a Froggy/OpenCode command |
| `tool` | Ask the session to use a tool with fixed arguments |

## Bash Context

Froggy injects:

- `OPENCODE_PROJECT_DIR`
- `OPENCODE_SESSION_ID`

It also writes JSON to stdin. Common fields are `session_id`, `event`, `cwd`, `files`, `tool_name`, and `tool_args`.

For `tool.before.*` and `tool.before.<name>`, bash exit code `2` blocks the tool and stderr becomes the block reason. Other nonzero exits are reported but do not block later OpenCode work.

Keep exit codes and output streams separate:

- Exit code controls success, failure, or blocking.
- Stderr is for diagnostics, failure detail, and block reasons.
- Successful routine skips should write to stdout, or stay quiet if stdout would conflict with the hook protocol.

Froggy displays stdout and stderr separately in the bash-result message, so a successful skip written to stderr looks like a warning even with exit `0`.

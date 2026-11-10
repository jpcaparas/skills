# Gotchas

> **Drift, 2026-11-10 (unresolved).** `opencode-froggy` 1.7.0+ no longer loads `.opencode/hook/hooks.md`, and OpenCode marks the `plugin` config key deprecated in favour of `plugins`. This scaffold still targets the 0.12.0-era Froggy behaviour below. Evidence and open questions: `assets/hook-events.json` under `drift_2026_11_10`. Until the owner decides (pin a hook-capable Froggy, or move to a native OpenCode plugin), do not tell a user the generated hooks will run on a current Froggy; check with `opencode plugin list` and a live session.

## 1. Froggy is a plugin plus a hook file

`hooks.md` is inert unless `opencode.json` loads `opencode-froggy`.

## 2. `hook` and `plugins` are different directories

Froggy config lives in `.opencode/hook/hooks.md`. OpenCode local plugin modules live in `.opencode/plugins/`. The new scaffold writes the former and cleans up only old scaffold-owned files in the latter.

## 3. Bash output is visible

Froggy sends bash action results back to the session. Redirect stdout for scripts that only set up state, such as baseline capture.

## 4. Exit code and stderr are different signals

Exit code controls success, failure, or blocking. Stderr is only for diagnostics, failure detail, and block reasons. Do not write successful status or routine skip messages to stderr; Froggy will show them as `Stderr:` even when the hook exits `0`.

## 5. Markdown is not a Froggy code-change extension

The `hasCodeChange` condition follows Froggy's extension list. It skips Markdown-only edits, which is wrong for many skill repositories.

## 6. Exit code 2 only blocks before-tool hooks

Use exit `2` for `tool.before.*` and `tool.before.<name>` guardrails. For `session.idle`, a nonzero exit is feedback, not a hard stop in the same way Claude/Codex stop hooks behave.

## 7. Preserve custom hooks

If `.opencode/hook/hooks.md` has an unfamiliar frontmatter shape, stop and ask for manual merge rather than rewriting it.

## 8. Old dependency artifacts are removable only when proven managed

Remove `.opencode/package.json`, lockfiles, and `node_modules` only when the package file contains only the old scaffold's `@opencode-ai/plugin` dependency or the user explicitly asks.

# Plugin Patterns

Use these patterns when the user wants an actual OpenCode hook workflow, not just a blank plugin file.

## 1. Minimal Lifecycle/Action Plugin

Use this as the default when the user wants to mirror existing lifecycle hooks, run validation after agent work, inject session context, repair generated-file drift, check dependency setup, or run policy checks.

Generate one live plugin file. Do not generate the full hook-surface catalog unless the user asks for a broad scaffold.

Reusable shape:

- root `session.created` injects no-reply context from a repo-owned session-context script.
- root `session.idle` or another meaningful event runs a repo-owned validation, formatter, dependency, generated-file, or policy script.
- child or subagent sessions are skipped. Record child IDs when `session.created` includes `info.parentID`, because later `session.idle` events expose only the session ID.
- background work shows TUI toasts for start, success, warning, and error states.
- first failure sends one repair prompt without `noReply`.
- persistent failure sends a final no-reply notice and stops prompting.

Keep these state flags:

- `inFlight`
- `repairPromptSent`
- `persistentFailureReported`

Keep this cross-event state:

- `childSessionIDs`

Use repo-owned scripts for project-specific behavior. The plugin should orchestrate lifecycle, visibility, and follow-up; the script should own validation, formatting, dependency checks, generated-file checks, or policy details.

Resolve repo scripts from OpenCode's active plugin context (`worktree`, `directory`, then project fields) before falling back to the plugin file location. This keeps the same generated plugin usable when it is project-local, global, or loaded from a custom config directory.

## 2. TUI Toasts For Background Work

`client.app.log()` is diagnostic. It is not enough for user-visible TUI feedback.

Add this helper to generated plugins that do meaningful background work:

```ts
type ToastVariant = "info" | "success" | "warning" | "error"

async function showToast(
  client: { tui?: { showToast(input: { body: { message: string; variant?: ToastVariant } }): Promise<unknown> } },
  variant: ToastVariant,
  message: string,
) {
  try {
    await client.tui?.showToast({ body: { message, variant } })
  } catch {
    // Toast failures must never break hook behavior.
  }
}
```

Use `info` when work starts, `success` when it completes, and `warning` or `error` when intervention is needed. Apply this generically to `session.idle`, `tool.execute.after`, `command.executed`, `file.edited`, `installation.updated`, `session.error`, and custom cross-event workflows whenever they perform meaningful work.

Keep logging separate:

- `client.app.log()` for structured diagnostics and captured details
- `client.tui.showToast()` for what the user should see

## 3. Controlled Automatic Repair

Use this pattern when a hook can reasonably ask OpenCode for one follow-up turn.

Rules:

- guard with `inFlight` so overlapping events do not launch duplicate work
- on first failure, set `repairPromptSent = true` and call `client.session.prompt()` without `noReply`
- on persistent failure, set `persistentFailureReported = true` and call `client.session.prompt()` with `noReply: true`
- after persistent failure has been reported, do not ask for another automatic repair turn
- clear repair state only after a successful run

This fits validation failures, formatter failures, generated-file drift, missing dependency setup, policy checks, and other automatable outcomes.

## 4. Guardrails Before Tool Execution

Use `tool.execute.before` when the plugin should deny or rewrite risky actions before they run.

Typical cases:

- block `.env` reads
- block destructive shell commands
- rewrite shell args to escape dangerous input
- deny edits to generated or protected files

Minimal pattern:

```ts
const plugin = async () => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "read" && output.args.filePath.includes(".env")) {
        throw new Error("Do not read .env files")
      }
    },
  }
}

export default plugin
```

## 5. Post-Turn Lint or Test Feedback

The article pattern is still the best practical example:

1. watch `tool.execute.after`
2. mark when edit tools ran
3. wait for `event` with `session.idle`
4. apply a cooldown
5. run lint or tests
6. feed output back with `client.session.prompt()`

Use this when the repo has strong formatter, lint, typecheck, or affected-test commands the agent should satisfy automatically.

From the official SDK docs, add `noReply: true` when you only want to inject context without forcing an immediate assistant reply. Leave `noReply` off when you want the agent to act on the validation output right away.

Prefer calling a repo-owned validation script from the plugin over hard-coding command lists in the plugin body. This keeps project logic reusable across OpenCode, Codex, CI, and local shell workflows.

## 6. Shell Environment Injection

Use `shell.env` when the plugin should add environment variables to shell execution without hard-coding them into repo scripts.

Typical cases:

- expose a project root variable
- inject temporary API endpoints
- attach per-project feature flags to shell tools

## 7. Custom Tools

Use the `tool` surface when the repo needs a reusable domain-specific tool instead of repeated shell commands.

Typical cases:

- query a project-specific database
- run a workflow behind one stable description
- replace a noisy shell sequence with a single high-signal tool

This is the point where you usually need `@opencode-ai/plugin`.

## 8. Compaction Context

Use `experimental.session.compacting` when important project state gets lost during long sessions and the default compaction prompt is not enough.

Keep this experimental and low-risk. Do not make core safety policies or business-critical behavior depend on it.

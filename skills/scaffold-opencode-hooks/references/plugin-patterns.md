# Plugin Patterns

Use these patterns when the user wants an actual OpenCode hook workflow, not just a blank plugin file.

## 1. Guardrails Before Tool Execution

Use `tool.execute.before` when the plugin should deny or rewrite risky actions before they run.

Typical cases:

- block `.env` reads
- block destructive shell commands
- rewrite shell args to escape dangerous input
- deny edits to generated or protected files

Minimal pattern:

```js
export default async () => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "read" && output.args.filePath.includes(".env")) {
        throw new Error("Do not read .env files")
      }
    },
  }
}
```

## 2. Post-Turn Lint or Test Feedback

The article pattern is still the best practical example:

1. watch `tool.execute.after`
2. mark when edit tools ran
3. wait for `event` with `session.idle`
4. apply a cooldown
5. run lint or tests
6. feed output back with `client.session.prompt()`

Use this when the repo has strong formatter, lint, typecheck, or affected-test commands the agent should satisfy automatically.

From the official SDK docs, add `noReply: true` when you only want to inject context without forcing an immediate assistant reply. Leave `noReply` off when you want the agent to act on the validation output right away.

## 3. Shell Environment Injection

Use `shell.env` when the plugin should add environment variables to shell execution without hard-coding them into repo scripts.

Typical cases:

- expose a project root variable
- inject temporary API endpoints
- attach per-project feature flags to shell tools

## 4. Custom Tools

Use the `tool` surface when the repo needs a reusable domain-specific tool instead of repeated shell commands.

Typical cases:

- query a project-specific database
- run a workflow behind one stable description
- replace a noisy shell sequence with a single high-signal tool

This is the point where you usually need `@opencode-ai/plugin`.

## 5. Compaction Context

Use `experimental.session.compacting` when important project state gets lost during long sessions and the default compaction prompt is not enough.

Keep this experimental and low-risk. Do not make core safety policies or business-critical behavior depend on it.


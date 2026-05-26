/**
 * Skills repository stop checks for OpenCode.
 *
 * This is a thin project-local adapter around scripts/agent-stop-checks.sh.
 * Keep validation policy in repo-owned shell/Python scripts so Codex,
 * OpenCode, Git hooks, GitHub Actions, and humans can share it.
 */

import { execFile } from "node:child_process"
import { promisify } from "node:util"

type ToastVariant = "info" | "success" | "warning" | "error"
type TextPart = { type: "text"; text: string }

type OpenCodeClient = {
  app?: {
    log(input: {
      body: {
        service: string
        level: "debug" | "info" | "warn" | "error"
        message: string
        extra?: Record<string, unknown>
      }
    }): Promise<unknown>
  }
  session?: {
    prompt(input: {
      path: { id: string }
      body: {
        noReply?: boolean
        parts: TextPart[]
      }
    }): Promise<unknown>
  }
  tui?: {
    showToast(input: {
      body: {
        message: string
        variant?: ToastVariant
      }
    }): Promise<unknown>
  }
}

type PluginInput = {
  client: OpenCodeClient
  directory?: string
  worktree?: string
  project?: {
    root?: string
    directory?: string
    path?: string
    worktree?: string
  }
}

type OpenCodeEvent = {
  type: string
  properties?: {
    sessionID?: string
    info?: { id?: string }
  }
}

type ScriptResult = {
  ok: boolean
  status: number | string
  stdout: string
  stderr: string
}

const execFileAsync = promisify(execFile)
const serviceName = "skills-repo-stop-check"
const outputTailLines = 180
const timeoutMs = 10 * 60 * 1000
const sessionState = new Map<string, { inFlight: boolean; repairPromptSent: boolean }>()

function textTail(text: string, lineCount: number): string {
  const trimmed = text.trimEnd()
  if (!trimmed) return "(no output captured)"
  return trimmed.split(/\r?\n/).slice(-lineCount).join("\n")
}

function stateFor(sessionID: string) {
  const existing = sessionState.get(sessionID)
  if (existing) return existing

  const next = { inFlight: false, repairPromptSent: false }
  sessionState.set(sessionID, next)
  return next
}

async function showToast(client: OpenCodeClient, variant: ToastVariant, message: string) {
  try {
    await client.tui?.showToast({ body: { message, variant } })
  } catch {
    // TUI feedback is best-effort only.
  }
}

async function log(client: OpenCodeClient, level: "info" | "warn" | "error", message: string, extra = {}) {
  try {
    await client.app?.log({ body: { service: serviceName, level, message, extra } })
  } catch {
    // Diagnostics must not break hook behavior.
  }
}

async function repoRootFrom(candidate: string): Promise<string> {
  try {
    const result = await execFileAsync("git", ["-C", candidate, "rev-parse", "--show-toplevel"], {
      maxBuffer: 1024 * 1024,
      timeout: 10_000,
    })
    return String(result.stdout || "").trim() || candidate
  } catch {
    return candidate
  }
}

function candidateDirectory(input: PluginInput): string {
  return (
    input.worktree ||
    input.directory ||
    input.project?.worktree ||
    input.project?.root ||
    input.project?.directory ||
    input.project?.path ||
    process.cwd()
  )
}

async function runStopChecks(repoRoot: string): Promise<ScriptResult> {
  try {
    const result = await execFileAsync("bash", ["scripts/agent-stop-checks.sh", repoRoot], {
      cwd: repoRoot,
      maxBuffer: 20 * 1024 * 1024,
      timeout: timeoutMs,
    })
    return {
      ok: true,
      status: 0,
      stdout: String(result.stdout || ""),
      stderr: String(result.stderr || ""),
    }
  } catch (error: unknown) {
    const execError = error as {
      signal?: string
      code?: number | string
      stdout?: string | Buffer
      stderr?: string | Buffer
      message?: string
    }
    return {
      ok: false,
      status: execError.signal || execError.code || "failed",
      stdout: String(execError.stdout || ""),
      stderr: String(execError.stderr || execError.message || ""),
    }
  }
}

async function promptFailure(client: OpenCodeClient, sessionID: string, result: ScriptResult, noReply: boolean) {
  const output = textTail(`${result.stdout}\n${result.stderr}`, outputTailLines)
  await client.session?.prompt({
    path: { id: sessionID },
    body: {
      noReply,
      parts: [
        {
          type: "text",
          text: `Stop checks failed with exit code ${result.status}.

Fix the reported issue, then run \`bash scripts/agent-stop-checks.sh\` before finishing.

Output tail:
${output}`,
        },
      ],
    },
  })
}

export default async function skillsRepoStopCheck(input: PluginInput) {
  const { client } = input
  const repoRoot = await repoRootFrom(candidateDirectory(input))

  return {
    async event({ event }: { event: OpenCodeEvent }) {
      if (event?.type !== "session.idle") return

      const sessionID = event.properties?.sessionID || event.properties?.info?.id || "default"
      const state = stateFor(sessionID)
      if (state.inFlight) return

      state.inFlight = true
      try {
        const result = await runStopChecks(repoRoot)
        if (result.ok) {
          await log(client, "info", "Stop checks passed", { sessionID })
          return
        }

        await showToast(client, "error", "Skills stop checks failed")
        await log(client, "error", "Stop checks failed", {
          sessionID,
          status: result.status,
          output: textTail(`${result.stdout}\n${result.stderr}`, outputTailLines),
        })

        if (state.repairPromptSent) {
          await promptFailure(client, sessionID, result, true)
          return
        }

        state.repairPromptSent = true
        await promptFailure(client, sessionID, result, false)
      } finally {
        state.inFlight = false
      }
    },
  }
}

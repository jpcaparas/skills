#!/usr/bin/env bun

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, resolve } from "node:path"
import { flagValue } from "./opencode_json_utils.ts"

type HookAction =
  | { command: string | { name: string; args?: string } }
  | { tool: { name: string; args: Record<string, unknown> } }
  | { bash: string | { command: string; timeout?: number } }

type FroggyHook = {
  event: string
  conditions?: string[]
  actions: HookAction[]
  notes?: string
}

type FrontmatterParts = {
  frontmatter: string
  body: string
}

const BEGIN_MARKER = "  # BEGIN scaffold-hooks managed opencode-froggy"
const END_MARKER = "  # END scaffold-hooks managed opencode-froggy"

function splitFrontmatter(text: string): FrontmatterParts | null {
  if (!text.startsWith("---")) return null
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n)?([\s\S]*)$/)
  if (!match) return null
  return { frontmatter: match[1], body: match[2] ?? "" }
}

function jsonString(value: string): string {
  return JSON.stringify(value)
}

function renderAction(action: HookAction): string[] {
  if ("command" in action) {
    if (typeof action.command === "string") {
      return [`      - command: ${jsonString(action.command)}`]
    }
    const lines = ["      - command:", `          name: ${jsonString(action.command.name)}`]
    if (action.command.args !== undefined) lines.push(`          args: ${jsonString(action.command.args)}`)
    return lines
  }

  if ("tool" in action) {
    return [
      "      - tool:",
      `          name: ${jsonString(action.tool.name)}`,
      `          args: ${JSON.stringify(action.tool.args)}`,
    ]
  }

  if (typeof action.bash === "string") {
    return [`      - bash: ${jsonString(action.bash)}`]
  }

  const lines = ["      - bash:", `          command: ${jsonString(action.bash.command)}`]
  if (action.bash.timeout !== undefined) lines.push(`          timeout: ${action.bash.timeout}`)
  return lines
}

function renderManagedBlock(hooks: FroggyHook[]): string {
  const lines = [BEGIN_MARKER]
  for (const hook of hooks) {
    lines.push(`  - event: ${jsonString(hook.event)}`)
    if (hook.notes) lines.push(`    # ${hook.notes.replace(/\r?\n/g, " ")}`)
    if (hook.conditions && hook.conditions.length > 0) {
      lines.push("    conditions:")
      for (const condition of hook.conditions) lines.push(`      - ${jsonString(condition)}`)
    }
    lines.push("    actions:")
    for (const action of hook.actions) lines.push(...renderAction(action))
  }
  lines.push(END_MARKER)
  return `${lines.join("\n")}\n`
}

function topLevelKeys(frontmatter: string): Array<{ key: string; index: number }> {
  const keys: Array<{ key: string; index: number }> = []
  const lines = frontmatter.split(/\r?\n/)
  let offset = 0
  for (const line of lines) {
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_-]*)\s*:/)
    if (match) keys.push({ key: match[1], index: offset })
    offset += line.length + 1
  }
  return keys
}

function canAppendToExistingHooks(frontmatter: string): boolean {
  const keys = topLevelKeys(frontmatter)
  const hooksIndex = keys.findIndex((item) => item.key === "hooks")
  if (hooksIndex === -1) return true
  return hooksIndex === keys.length - 1
}

function replaceManagedBlock(frontmatter: string, block: string): string | null {
  const start = frontmatter.indexOf(BEGIN_MARKER)
  const end = frontmatter.indexOf(END_MARKER)
  if (start === -1 || end === -1 || end < start) return null

  const before = frontmatter.slice(0, start).replace(/\s+$/, "\n")
  const after = frontmatter.slice(end + END_MARKER.length).replace(/^\s+/, "")
  return `${before}${block}${after}`.trimEnd()
}

function renderNewDocument(block: string): string {
  return [
    "---",
    "hooks:",
    block.trimEnd(),
    "---",
    "",
    "# OpenCode Froggy Hooks",
    "",
    "Managed by scaffold-hooks. Edit the scaffold plan and rerun /scaffold-hooks to refresh this block.",
    "",
  ].join("\n")
}

function renderMergedDocument(existing: string, block: string, mode: string, hooksFile: string): string {
  if (!existing.trim()) return renderNewDocument(block)

  const parts = splitFrontmatter(existing)
  if (!parts) {
    throw new Error(`${hooksFile} exists but does not use YAML frontmatter; preserving it instead of overwriting custom hooks.`)
  }

  const replaced = replaceManagedBlock(parts.frontmatter, block)
  if (replaced !== null) {
    return `---\n${replaced}\n---\n${parts.body}`
  }

  if (parts.body.includes("Managed by scaffold-hooks") && mode === "overhaul") {
    return renderNewDocument(block)
  }

  if (!canAppendToExistingHooks(parts.frontmatter)) {
    throw new Error(
      `${hooksFile} has custom top-level frontmatter after hooks:. Move custom hooks above the managed block or merge manually.`
    )
  }

  let nextFrontmatter = parts.frontmatter.trimEnd()
  if (!topLevelKeys(parts.frontmatter).some((item) => item.key === "hooks")) {
    nextFrontmatter = `${nextFrontmatter}\nhooks:`
  }
  nextFrontmatter = `${nextFrontmatter}\n${block}`.trimEnd()
  const body = parts.body || "\n# OpenCode Froggy Hooks\n"
  return `---\n${nextFrontmatter}\n---\n${body}`
}

function validateHooks(value: unknown): FroggyHook[] {
  if (!Array.isArray(value)) throw new Error("--hooks-json must be an array")
  return value.map((item, index) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      throw new Error(`Hook at index ${index} must be an object`)
    }
    const hook = item as Partial<FroggyHook>
    if (typeof hook.event !== "string" || hook.event.length === 0) {
      throw new Error(`Hook at index ${index} is missing event`)
    }
    if (!Array.isArray(hook.actions) || hook.actions.length === 0) {
      throw new Error(`Hook ${hook.event} must define at least one action`)
    }
    if (hook.conditions !== undefined && !Array.isArray(hook.conditions)) {
      throw new Error(`Hook ${hook.event} conditions must be an array`)
    }
    return {
      event: hook.event,
      conditions: hook.conditions,
      actions: hook.actions,
      notes: hook.notes,
    }
  })
}

const args = process.argv.slice(2)
const hooksFile = flagValue(args, "--hooks-file")
const hooksJson = flagValue(args, "--hooks-json")
const mode = flagValue(args, "--mode") ?? "additive"
const managedID = flagValue(args, "--managed-id") ?? "scaffold-hooks/opencode-froggy"

if (!hooksFile || hooksJson === undefined) {
  console.error("Usage: render_froggy_hooks.ts --hooks-file FILE --hooks-json JSON_ARRAY [--mode additive|overhaul] [--managed-id ID]")
  process.exit(1)
}

if (mode !== "additive" && mode !== "overhaul") {
  throw new Error(`Mode must be additive or overhaul. Got: ${mode}`)
}

const hookConfigPath = resolve(hooksFile)
const hooks = validateHooks(JSON.parse(hooksJson))
const block = renderManagedBlock(hooks)
const existing = existsSync(hookConfigPath) ? readFileSync(hookConfigPath, "utf8") : ""
const rendered = renderMergedDocument(existing, block, mode, hookConfigPath).replace(
  "Managed by scaffold-hooks.",
  `Managed by scaffold-hooks (${managedID}).`
)

mkdirSync(dirname(hookConfigPath), { recursive: true })
writeFileSync(hookConfigPath, rendered.endsWith("\n") ? rendered : `${rendered}\n`, "utf8")
console.log(JSON.stringify({ hooks_file: hookConfigPath, hooks: hooks.length }, null, 2))

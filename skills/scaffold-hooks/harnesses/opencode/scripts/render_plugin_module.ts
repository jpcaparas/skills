#!/usr/bin/env bun

import { readFileSync, writeFileSync } from "node:fs"
import { flagValue } from "./opencode_json_utils.ts"

const args = process.argv.slice(2)
const templatePath = flagValue(args, "--template")
const importsPath = flagValue(args, "--imports")
const handlersPath = flagValue(args, "--handlers")
const outputPath = flagValue(args, "--output")
const pluginName = flagValue(args, "--name") ?? ""
const notes = flagValue(args, "--notes") ?? ""
const surfaces = flagValue(args, "--surfaces") ?? ""
const contextScript = flagValue(args, "--context-script") ?? "scripts/agent-session-context.sh"
const actionScript = flagValue(args, "--action-script") ?? "scripts/validate-project.sh"
const actionLabel = flagValue(args, "--action-label") ?? "Project validation"
const serviceName = flagValue(args, "--service-name") ?? "opencode-lifecycle-hooks"

function stringLiteralBody(value: string): string {
  return JSON.stringify(value).slice(1, -1)
}

if (!templatePath || !importsPath || !handlersPath || !outputPath) {
  console.error("Usage: render_plugin_module.ts --template FILE --imports FILE --handlers FILE --output FILE --name NAME --notes TEXT --surfaces TEXT")
  process.exit(1)
}

let template = readFileSync(templatePath, "utf8")
const replacements: Record<string, string> = {
  "{{PLUGIN_NAME}}": pluginName,
  "{{NOTES}}": notes,
  "{{SURFACES}}": surfaces,
  "{{IMPORTS}}": readFileSync(importsPath, "utf8"),
  "{{HANDLERS}}": readFileSync(handlersPath, "utf8").trimEnd(),
  "{{CONTEXT_SCRIPT}}": stringLiteralBody(contextScript),
  "{{ACTION_SCRIPT}}": stringLiteralBody(actionScript),
  "{{ACTION_LABEL}}": stringLiteralBody(actionLabel),
  "{{SERVICE_NAME}}": stringLiteralBody(serviceName),
}

for (const [key, value] of Object.entries(replacements)) {
  template = template.split(key).join(value)
}

writeFileSync(outputPath, `${template.trimEnd()}\n`, "utf8")

#!/usr/bin/env bun

import { existsSync, readdirSync } from "node:fs"
import { homedir } from "node:os"
import { resolve } from "node:path"
import { flagValue, hasFlag, readJsonObject } from "./opencode_json_utils.ts"

const pluginSuffixes = new Set([".ts", ".js", ".mjs", ".cjs", ".jsx", ".tsx"])

function chooseConfigPath(root: string, baseName: string): string {
  const jsonPath = resolve(root, `${baseName}.json`)
  const jsoncPath = resolve(root, `${baseName}.jsonc`)
  if (existsSync(jsonPath)) return jsonPath
  if (existsSync(jsoncPath)) return jsoncPath
  return jsonPath
}

function listPluginFiles(pluginDir: string, root = pluginDir): string[] {
  if (!existsSync(pluginDir)) return []
  const hits: string[] = []
  for (const entry of readdirSync(pluginDir, { withFileTypes: true })) {
    const fullPath = resolve(pluginDir, entry.name)
    if (entry.isDirectory()) {
      hits.push(...listPluginFiles(fullPath, root))
      continue
    }
    const suffix = entry.name.includes(".") ? `.${entry.name.split(".").pop()}` : ""
    if (entry.isFile() && pluginSuffixes.has(suffix)) {
      hits.push(fullPath.slice(root.length + 1))
    }
  }
  return hits.sort()
}

function inspectConfig(configRoot: string): [Record<string, unknown>, string[]] {
  const warnings: string[] = []
  const configFile = chooseConfigPath(configRoot, "opencode")
  let configData: Record<string, unknown> = {}
  if (existsSync(configFile)) {
    try {
      configData = readJsonObject(configFile)
      if (configFile.endsWith(".jsonc")) {
        warnings.push(`${configFile} uses JSONC comments; deterministic merges will rewrite normalized JSON.`)
      }
    } catch (error) {
      warnings.push(`Failed to parse ${configFile}: ${(error as Error).message}`)
    }
  }

  let pluginEntries = configData.plugin
  if (!Array.isArray(pluginEntries)) {
    if (pluginEntries !== undefined) warnings.push(`${configFile} has a non-array 'plugin' field; ignoring it.`)
    pluginEntries = []
  }

  return [
    {
      config_file: configFile,
      config_exists: existsSync(configFile),
      config_format: existsSync(configFile) ? configFile.split(".").pop() : "json",
      plugin_entries: pluginEntries,
      has_froggy_plugin: pluginEntries.includes("opencode-froggy"),
    },
    warnings,
  ]
}

function inspectScope(configRoot: string): Record<string, unknown> {
  const hookFile = resolve(configRoot, "hook", "hooks.md")
  const managedState = resolve(configRoot, "hook", ".managed", "manifest.json")
  const legacyPluginState = resolve(configRoot, "plugins", ".managed", "manifest.json")
  return {
    hook_file: hookFile,
    hook_exists: existsSync(hookFile),
    managed_state: resolve(configRoot, "hook", ".managed"),
    managed_state_exists: existsSync(managedState),
    legacy_plugin_state: resolve(configRoot, "plugins", ".managed"),
    legacy_plugin_state_exists: existsSync(legacyPluginState),
    local_plugin_files: listPluginFiles(resolve(configRoot, "plugins")),
  }
}

function isGitRepo(projectRoot: string): boolean {
  let current = resolve(projectRoot)
  while (true) {
    if (existsSync(resolve(current, ".git"))) return true
    const parent = resolve(current, "..")
    if (parent === current) return false
    current = parent
  }
}

const args = process.argv.slice(2)
const projectArg = flagValue(args, "--project")
if (!projectArg) {
  console.error("Usage: check_plugin_setup.ts --project DIR [--home DIR] [--json]")
  process.exit(1)
}

const projectRoot = resolve(projectArg)
const home = resolve(flagValue(args, "--home") ?? homedir())
const globalRoot = resolve(home, ".config/opencode")
const projectRuntimeRoot = resolve(projectRoot, ".opencode")

const [projectConfig, projectWarnings] = inspectConfig(projectRoot)
const [globalConfig, globalWarnings] = inspectConfig(globalRoot)
const projectState = inspectScope(projectRuntimeRoot)
const globalState = inspectScope(globalRoot)

const projectHasOpenCode =
  Boolean(projectConfig.config_exists) ||
  Boolean(projectState.hook_exists) ||
  Boolean(projectState.managed_state_exists) ||
  Boolean(projectState.legacy_plugin_state_exists) ||
  (Array.isArray(projectState.local_plugin_files) && projectState.local_plugin_files.length > 0)

const scopeRecommendation = isGitRepo(projectRoot) || projectHasOpenCode ? "project" : "global"

const result = {
  project_root: projectRoot,
  home,
  scope_recommendation: scopeRecommendation,
  deployment_recommendation: "opencode-froggy",
  recommended_hook_config: ".opencode/hook/hooks.md",
  recommended_config_target: "opencode.json",
  project: {
    ...projectConfig,
    ...projectState,
  },
  global: {
    ...globalConfig,
    ...globalState,
  },
  warnings: [...projectWarnings, ...globalWarnings],
}

console.log(JSON.stringify(result, null, hasFlag(args, "--json") ? 2 : 0))

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

function packageDependencies(path: string): Record<string, unknown> {
  if (!existsSync(path)) return {}
  try {
    const data = readJsonObject(path)
    const deps = data.dependencies
    return deps && typeof deps === "object" && !Array.isArray(deps) ? deps as Record<string, unknown> : {}
  } catch {
    return {}
  }
}

function inspectScope(configRoot: string): [Record<string, unknown>, string[]] {
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

  const pluginDir = resolve(configRoot, "plugins")
  const packageFile = resolve(configRoot, "package.json")
  return [
    {
      config_file: configFile,
      config_exists: existsSync(configFile),
      config_format: existsSync(configFile) ? configFile.split(".").pop() : "json",
      plugin_entries: pluginEntries,
      plugin_dir: pluginDir,
      local_plugin_files: listPluginFiles(pluginDir),
      package_file: packageFile,
      package_exists: existsSync(packageFile),
      package_dependencies: packageDependencies(packageFile),
    },
    warnings,
  ]
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

const [projectState, projectWarnings] = inspectScope(projectRoot)
const runtimePluginFiles = listPluginFiles(resolve(projectRuntimeRoot, "plugins"))
if (runtimePluginFiles.length > 0) {
  projectState.local_plugin_files = runtimePluginFiles
  projectState.plugin_dir = resolve(projectRuntimeRoot, "plugins")
}
projectState.package_file = resolve(projectRuntimeRoot, "package.json")
projectState.package_exists = existsSync(resolve(projectRuntimeRoot, "package.json"))
projectState.package_dependencies = packageDependencies(resolve(projectRuntimeRoot, "package.json"))

const [globalState, globalWarnings] = inspectScope(globalRoot)

const projectHasPlugins = Array.isArray(projectState.local_plugin_files) && projectState.local_plugin_files.length > 0
const scopeRecommendation =
  isGitRepo(projectRoot) || Boolean(projectState.config_exists) || projectHasPlugins || Boolean(projectState.package_exists)
    ? "project"
    : "global"
const deploymentRecommendation =
  (Array.isArray(projectState.plugin_entries) && projectState.plugin_entries.length > 0) ||
  (Array.isArray(globalState.plugin_entries) && globalState.plugin_entries.length > 0)
    ? "hybrid"
    : "local-files"

const result = {
  project_root: projectRoot,
  home,
  scope_recommendation: scopeRecommendation,
  deployment_recommendation: deploymentRecommendation,
  recommended_module_format: "ts",
  project: projectState,
  global: globalState,
  warnings: [...projectWarnings, ...globalWarnings],
}

console.log(JSON.stringify(result, null, hasFlag(args, "--json") ? 2 : 0))

#!/usr/bin/env bun

import { resolve } from "node:path"
import { flagValue, readJsonObject, writeJson } from "./opencode_json_utils.ts"

const args = process.argv.slice(2)
const packageFile = flagValue(args, "--package-file")
const dependenciesJson = flagValue(args, "--dependencies-json")

if (!packageFile || dependenciesJson === undefined) {
  console.error("Usage: merge_package_json.ts --package-file FILE --dependencies-json JSON_OBJECT")
  process.exit(1)
}

const packagePath = resolve(packageFile)
const data = readJsonObject(packagePath, {
  name: "opencode-config",
  private: true,
  type: "module",
  dependencies: {},
})

const requested = JSON.parse(dependenciesJson)
if (!requested || typeof requested !== "object" || Array.isArray(requested)) {
  throw new Error("--dependencies-json must be a JSON object")
}

const existing = data.dependencies && typeof data.dependencies === "object" && !Array.isArray(data.dependencies)
  ? data.dependencies as Record<string, unknown>
  : {}
const merged = { ...existing, ...requested }
const sortedDependencies = Object.fromEntries(Object.entries(merged).sort(([a], [b]) => a.localeCompare(b)))

data.name ??= "opencode-config"
data.private ??= true
data.type ??= "module"
data.dependencies = sortedDependencies
writeJson(packagePath, data)

console.log(JSON.stringify({ package_file: packagePath, dependencies: sortedDependencies }, null, 2))

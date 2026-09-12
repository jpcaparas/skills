#!/usr/bin/env bun

import { resolve } from "node:path"
import { flagValue, readJsonObject, writeJson } from "./opencode_json_utils.ts"

const args = process.argv.slice(2)
const configFile = flagValue(args, "--config-file")
const pluginIndex = args.indexOf("--plugins")

if (!configFile || pluginIndex === -1 || pluginIndex === args.length - 1) {
  console.error("Usage: merge_opencode_config.ts --config-file FILE --plugins plugin-a [plugin-b ...]")
  process.exit(1)
}

const plugins = args.slice(pluginIndex + 1).filter((value) => value && !value.startsWith("--"))
const configPath = resolve(configFile)
const data = readJsonObject(configPath, { $schema: "https://opencode.ai/config.json" })
const existing = Array.isArray(data.plugin) ? data.plugin.filter((item) => typeof item === "string") as string[] : []
const merged = [...existing]
for (const plugin of plugins) {
  if (!merged.includes(plugin)) merged.push(plugin)
}

data.plugin = merged
data.$schema ??= "https://opencode.ai/config.json"
writeJson(configPath, data)

console.log(JSON.stringify({ config_file: configPath, plugins: merged }, null, 2))

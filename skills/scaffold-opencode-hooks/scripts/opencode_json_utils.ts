#!/usr/bin/env bun

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname } from "node:path"

export function stripJsonc(text: string): string {
  let result = ""
  let i = 0
  let inString = false
  let stringChar = ""

  while (i < text.length) {
    const char = text[i]
    const next = text[i + 1] ?? ""

    if (inString) {
      result += char
      if (char === "\\" && i + 1 < text.length) {
        result += text[i + 1]
        i += 2
        continue
      }
      if (char === stringChar) inString = false
      i += 1
      continue
    }

    if (char === '"' || char === "'") {
      inString = true
      stringChar = char
      result += char
      i += 1
      continue
    }

    if (char === "/" && next === "/") {
      i += 2
      while (i < text.length && !"\r\n".includes(text[i])) i += 1
      continue
    }

    if (char === "/" && next === "*") {
      i += 2
      while (i + 1 < text.length && !(text[i] === "*" && text[i + 1] === "/")) i += 1
      i += 2
      continue
    }

    result += char
    i += 1
  }

  return result.replace(/,(\s*[}\]])/g, "$1")
}

export function readJsonObject(path: string, fallback: Record<string, unknown> = {}): Record<string, unknown> {
  if (!existsSync(path)) return { ...fallback }
  const data = JSON.parse(stripJsonc(readFileSync(path, "utf8")))
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error(`${path} did not contain a JSON object`)
  }
  return data as Record<string, unknown>
}

export function writeJson(path: string, data: unknown): void {
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, `${JSON.stringify(data, null, 2)}\n`, "utf8")
}

export function flagValue(args: string[], flag: string): string | undefined {
  const index = args.indexOf(flag)
  if (index === -1) return undefined
  const value = args[index + 1]
  if (!value || value.startsWith("--")) throw new Error(`${flag} requires a value`)
  return value
}

export function hasFlag(args: string[], flag: string): boolean {
  return args.includes(flag)
}

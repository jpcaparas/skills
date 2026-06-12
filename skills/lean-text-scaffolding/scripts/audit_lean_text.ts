#!/usr/bin/env bun

import { existsSync, readFileSync } from "node:fs"

type Severity = "error" | "warning"

interface Issue {
  file: string
  line: number
  severity: Severity
  rule: string
  message: string
  match: string
}

interface FileReport {
  file: string
  issues: Issue[]
}

interface Summary {
  files: number
  errors: number
  warnings: number
  passed: boolean
}

interface AuditReport {
  summary: Summary
  reports: FileReport[]
}

interface PatternRule {
  rule: string
  severity: Severity
  pattern: RegExp
  message: string
}

const placeholderRules: PatternRule[] = [
  {
    rule: "placeholder-lorem",
    severity: "error",
    pattern: /\blorem ipsum\b/gi,
    message: "Replace lorem ipsum with real, minimal copy or remove the text block.",
  },
  {
    rule: "placeholder-token",
    severity: "error",
    pattern: /\b(feature (one|two|three|\d+)|card title|short description|badge text|placeholder copy)\b/gi,
    message: "Replace scaffold placeholder tokens with specific text or remove the element.",
  },
  {
    rule: "stock-marketing",
    severity: "warning",
    pattern: /\b(everything you need|all-in-one|seamless workflows?|unlock your|supercharge|next-generation|revolutionary|cutting-edge|best-in-class|built for modern teams|transform the way you)\b/gi,
    message: "Stock marketing phrasing is usually filler in a scaffold; make it specific or remove it.",
  },
]

const standaloneLabelPattern =
  />\s*(Features|Benefits|Solutions|Platform|Overview|Why us|New|Introducing|Trusted by|Enterprise ready|Testimonials|FAQ)\s*</gi

const paragraphPattern = /<p\b[^>]*>([\s\S]*?)<\/p>/gi
const inputWithPlaceholderPattern = /<(input|textarea)\b(?=[^>]*\bplaceholder=)(?![^>]*\b(aria-label|aria-labelledby|id)=)[^>]*>/gi

function usage(): string {
  return [
    "Usage: bun scripts/audit_lean_text.ts [--json] [--allow-warnings] <file ...>",
    "",
    "Audits HTML, JSX, TSX, and similar source files for lean text scaffolding issues.",
  ].join("\n")
}

function lineNumber(content: string, index: number): number {
  let line = 1
  for (let i = 0; i < index; i += 1) {
    if (content.charCodeAt(i) === 10) line += 1
  }
  return line
}

function stripCodeNoise(content: string): string {
  return content
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "")
    .replace(/class(Name)?=(["'`])[\s\S]*?\2/g, "")
}

function textOnly(value: string): string {
  return value
    .replace(/<[^>]+>/g, " ")
    .replace(/\{[^}]*\}/g, " ")
    .replace(/\s+/g, " ")
    .trim()
}

function addPatternIssues(file: string, content: string, issues: Issue[], rules: PatternRule[]): void {
  for (const item of rules) {
    for (const match of content.matchAll(item.pattern)) {
      issues.push({
        file,
        line: lineNumber(content, match.index ?? 0),
        severity: item.severity,
        rule: item.rule,
        message: item.message,
        match: match[0],
      })
    }
  }
}

function addStandaloneLabelIssues(file: string, content: string, issues: Issue[]): void {
  for (const match of content.matchAll(standaloneLabelPattern)) {
    const index = match.index ?? 0
    const lineStart = content.lastIndexOf("\n", index) + 1
    const lineEnd = content.indexOf("\n", index)
    const line = content.slice(lineStart, lineEnd === -1 ? content.length : lineEnd)
    if (/<label\b/i.test(line)) continue
    issues.push({
      file,
      line: lineNumber(content, index),
      severity: "warning",
      rule: "decorative-label",
      message:
        "Decorative section labels and eyebrow text should be omitted unless they disambiguate real categories or the user asked for them.",
      match: match[1],
    })
  }
}

function addLongParagraphIssues(file: string, content: string, issues: Issue[]): void {
  for (const match of content.matchAll(paragraphPattern)) {
    const rawText = textOnly(match[1] ?? "")
    if (!rawText) continue
    const wordCount = rawText.split(/\s+/).length
    if (wordCount <= 32) continue
    issues.push({
      file,
      line: lineNumber(content, match.index ?? 0),
      severity: "warning",
      rule: "long-paragraph",
      message: "Paragraph copy in a scaffold is long; split, tighten, or remove unless detailed copy was requested.",
      match: `${wordCount} words`,
    })
  }
}

function addPlaceholderOnlyInputIssues(file: string, content: string, issues: Issue[]): void {
  for (const match of content.matchAll(inputWithPlaceholderPattern)) {
    issues.push({
      file,
      line: lineNumber(content, match.index ?? 0),
      severity: "error",
      rule: "placeholder-only-input",
      message: "Inputs with placeholders need a durable label, id-linked label, or accessible name.",
      match: match[0].slice(0, 120),
    })
  }
}

function auditFile(file: string): FileReport {
  const content = readFileSync(file, "utf-8")
  const cleaned = stripCodeNoise(content)
  const issues: Issue[] = []

  addPatternIssues(file, cleaned, issues, placeholderRules)
  addStandaloneLabelIssues(file, cleaned, issues)
  addLongParagraphIssues(file, cleaned, issues)
  addPlaceholderOnlyInputIssues(file, cleaned, issues)

  const decorativeCount = issues.filter((issue) => issue.rule === "decorative-label").length
  if (decorativeCount > 3) {
    issues.push({
      file,
      line: 1,
      severity: "error",
      rule: "label-density",
      message: "This file contains many decorative labels; remove label stacks unless explicitly requested.",
      match: `${decorativeCount} decorative labels`,
    })
  }

  return { file, issues }
}

function parseArgs(argv: string[]): { json: boolean; allowWarnings: boolean; files: string[] } {
  const files: string[] = []
  let json = false
  let allowWarnings = false
  for (const arg of argv) {
    if (arg === "--json") {
      json = true
      continue
    }
    if (arg === "--allow-warnings") {
      allowWarnings = true
      continue
    }
    files.push(arg)
  }
  return { json, allowWarnings, files }
}

function buildReport(files: string[], allowWarnings: boolean): AuditReport {
  const reports = files.map(auditFile)
  const issues = reports.flatMap((report) => report.issues)
  const errors = issues.filter((issue) => issue.severity === "error").length
  const warnings = issues.filter((issue) => issue.severity === "warning").length
  return {
    summary: {
      files: reports.length,
      errors,
      warnings,
      passed: errors === 0 && (allowWarnings || warnings === 0),
    },
    reports,
  }
}

function printHuman(report: AuditReport): void {
  for (const fileReport of report.reports) {
    if (fileReport.issues.length === 0) {
      console.log(`${fileReport.file}: ok`)
      continue
    }
    console.log(`${fileReport.file}: ${fileReport.issues.length} issue(s)`)
    for (const issue of fileReport.issues) {
      console.log(
        `  ${issue.line}: ${issue.severity.toUpperCase()} ${issue.rule}: ${issue.message} (${issue.match})`,
      )
    }
  }
  const status = report.summary.passed ? "PASS" : "FAIL"
  console.log(`${status}: ${report.summary.errors} error(s), ${report.summary.warnings} warning(s)`)
}

const args = parseArgs(process.argv.slice(2))
if (args.files.length === 0) {
  console.error(usage())
  process.exit(2)
}

for (const file of args.files) {
  if (!existsSync(file)) {
    console.error(`Missing file: ${file}`)
    process.exit(2)
  }
}

const report = buildReport(args.files, args.allowWarnings)
if (args.json) {
  console.log(JSON.stringify(report, null, 2))
} else {
  printHuman(report)
}
process.exit(report.summary.passed ? 0 : 1)

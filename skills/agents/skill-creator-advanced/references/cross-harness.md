# Cross-Harness Compatibility

Use this reference when a skill must work in more than one agent harness. Treat portability as a set of verified contracts, not as a property implied by the directory layout.

## Table of Contents

- [Portable Core](#portable-core)
- [Target Capability Record](#target-capability-record)
- [Capability Checklist](#capability-checklist)
- [Invocation Contract](#invocation-contract)
- [Keep Metadata Namespaces Separate](#keep-metadata-namespaces-separate)
- [Discovery and Installation](#discovery-and-installation)
- [Scripts and Evals](#scripts-and-evals)
- [Release Gate](#release-gate)

## Portable Core

For harnesses that implement the Agent Skills format, the conservative interchange unit is a directory containing `SKILL.md`:

```text
skill-name/
└── SKILL.md
```

```yaml
---
name: skill-name
description: "Create or improve the named outcome when the request matches this domain."
---
```

The shared format covers the entry file, its frontmatter, Markdown instructions, and relative references. It does not by itself guarantee:

- where a harness discovers the directory
- when or whether the body is loaded
- whether linked files are read automatically
- whether scripts, tools, or subagents are available
- whether UI manifests or invocation controls are honored
- whether an eval format has a runner

Keep relative references inside the skill directory. Keeping `SKILL.md` below 500 lines is a useful format recommendation, not proof that every harness will load or follow it correctly.

Supporting directories are earned artifacts. Add `references/`, `scripts/`, `assets/`, `agents/`, or `evals/` only when the target workflow and harness can use them.

## Target Capability Record

Record the primary documentation or installed behavior checked for every promised target. Product contracts change; refresh this table when releasing portability-sensitive changes.

| Target contract | Checked | Confirmed capability | Boundary not to infer |
|---|---|---|---|
| [Agent Skills format](https://agentskills.io/specification) | 2026-07-12 | `SKILL.md`, `name`, `description`, relative references, and the under-500-line recommendation for conforming harnesses | Discovery, invocation, script execution, and eval execution |
| [GitHub Copilot skills](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills) | 2026-07-12 | Repository roots include `.github/skills/`, `.claude/skills/`, and `.agents/skills/`; personal roots include `~/.copilot/skills/` and `~/.agents/skills/`; supporting scripts and resources are supported | Identical discovery precedence, tool access, or subagent behavior in other harnesses |
| [Gemini CLI skills](https://geminicli.com/docs/cli/creating-skills/) | 2026-07-12 | Documented roots include `.gemini/skills/` and `.agents/skills/` | Any requirement for an unrelated registry metadata namespace |
| [OpenCode skills](https://opencode.ai/docs/skills/#place-files) | 2026-07-12 | Documented project and user skill locations used by this package's placement helper | Identical precedence or behavior in another harness |
| This package's observed Codex environment and repository contract | 2026-07-12 | The local install uses `$CODEX_HOME/skills/` when configured or `~/.codex/skills/`; optional UI metadata uses `agents/openai.yaml` with an `interface` mapping | Universal Codex discovery paths, repo-local precedence, invocation semantics, or support outside the observed install |

Use exact version numbers or documentation links in release evidence when a compatibility promise matters. If a capability is undocumented and untested, mark it unknown and do not promise it.

## Capability Checklist

For each target harness, verify:

| Capability | Question to answer |
|---|---|
| Discovery | Which repository and user roots are documented, and what is their precedence? |
| Startup metadata | Which fields are scanned before the body loads? |
| Body loading | Is loading automatic, model-selected, or explicitly requested? |
| References | Can the harness follow relative files, and must `SKILL.md` route to them? |
| Automation | Which runtimes, tools, permissions, and network policies are available? |
| Subagents | Is delegation supported, and does it preserve the skill context? |
| Invocation controls | Are manual-only, user-invocable, or model-invocable controls documented? |
| UI metadata | Is there a separate manifest, and what exact schema owns it? |
| Evals | Is there a supported runner, or are evals only repository-local fixtures? |
| Effects | How are approvals, dry runs, credentials, and external writes handled? |

Do not use labels such as “full,” “partial,” or “supported” without naming the tested capability. A harness may read Markdown while rejecting scripts, or run scripts while ignoring a UI manifest.

## Invocation Contract

Choose the intended reachability before adding platform controls:

| Need | Cross-harness design |
|---|---|
| Agent should discover the skill | Put the defining action first in `description`; cover each semantic branch once |
| Human should invoke it explicitly | Use only a control documented for that target harness |
| Another skill needs the behavior | Verify that dependency invocation works; otherwise co-locate shared guidance or expose a human route |
| Several explicit entrypoints need orientation | Add a human-facing router and validate it as derived state |

The description is startup metadata only in harnesses that document scanning it. Test positive triggers and near misses on each promised target; text-only review cannot establish invocation behavior.

Distinguish dependencies:

- A **hard dependency** makes the result incorrect or nonfunctional when unavailable. Document detection and setup or stop safely.
- A **soft dependency** improves the result. Degrade gracefully when it is absent.

Manual-only flags, slash commands, and skill-to-skill invocation are harness contracts. Never copy them between platforms by analogy.

## Keep Metadata Namespaces Separate

These surfaces may coexist, but they do different jobs:

- `SKILL.md` frontmatter belongs to the selected skill format.
- `agents/openai.yaml` is a repository-specific Codex UI manifest.
- `metadata.json` is packaging or catalog metadata when repository policy defines it.
- owner-specific frontmatter extensions belong only to the contract that documents them.
- `evals/evals.json` is test data for a runner that explicitly supports its schema.

Do not move keys between these files, nest one owner's extension under another owner's namespace, or assume a registry field changes harness discovery.

### Codex UI manifest used by this repository

When this repository's packaging contract calls for Codex UI metadata, use the nested shape:

```yaml
# agents/openai.yaml
interface:
  display_name: "API Integration Helper"
  short_description: "Create and verify a safe API integration"
  default_prompt: "Help me create and verify a safe API integration."
```

Do not flatten the fields to the document root. The manifest is optional presentation metadata; it does not replace `SKILL.md` or establish discovery and invocation behavior. Validate it against the current repository or installed-harness schema before release.

For any other extension, copy the exact documented schema from its owner and record which harness, registry, or installer consumes it. Omit speculative metadata.

## Discovery and Installation

Repository layout, discovery roots, and installer behavior are separate contracts.

This repository publishes installable skills under:

```text
skills/<skill-name>/SKILL.md
```

Use the installed CLI's help and a non-mutating discovery command to verify what the current version sees. For the installer used by this repository:

```bash
npx --yes skills add . --list
```

Treat successful listing as evidence for that installer version and repository state only. It does not prove that a target harness will load, invoke, or execute the skill after installation. Verify the resolved destination and harness behavior separately.

## Scripts and Evals

Design automation for the documented target environment:

- Declare required runtimes, binaries, permissions, credentials, and network access.
- Resolve files relative to the skill or an explicit input, never a developer-specific absolute path.
- Prefer dependencies already guaranteed by the target; otherwise provide setup and failure guidance.
- Provide a non-interactive mode when an agent is expected to run the command.
- Use structured output only when a caller consumes a documented schema.
- Define exit codes according to the script's CLI contract. Use zero for documented success and nonzero codes for documented failure classes when that convention applies.
- Make help, dry-run, overwrite, and confirmation behavior explicit when the script can mutate state.
- Offer a manual fallback only when it can preserve correctness and safety.

Language and shell choices are dependencies, not universal defaults. If a Python script targets environments that document `python3`, an environment-based shebang can reduce path assumptions. If a Bash script is required, declare Bash rather than assuming every shell is compatible.

Eval files are portable as repository content, not automatically executable across harnesses. Before claiming a pass, confirm that:

1. the intended evaluator is installed and authenticated
2. the runner actually executed every scenario
3. trigger and near-miss outcomes came from the promised harness
4. assertion and process failures produce the documented result or exit status
5. all-zero, empty, skipped, or infrastructure-failed runs are rejected as invalid evidence

## Release Gate

Release a cross-harness claim only when:

- the portable core validates against the chosen format version
- every target has a dated capability record backed by primary documentation or an installed-behavior test
- discovery, invocation, references, automation, and effects are verified independently
- owner-specific metadata is isolated and schema-checked
- unsupported capabilities have a safe fallback or are excluded from the promise
- eval evidence is valid for the named runner and harness

## See Also

- `references/curation.md` — invocation ownership, routers, hard and soft dependencies, and lifecycle surfaces
- `references/anatomy.md` — portable core and earned support artifacts
- `references/testing.md` — target-harness invocation and portability evidence

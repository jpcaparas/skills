# Codex Mechanics

Use this reference for Codex-specific subagent behavior, configuration, and setup questions.

## Availability

The public Codex docs describe current releases as enabling subagent workflows by default. Subagent activity is surfaced in the Codex app and Codex CLI. Treat other surfaces as unsupported for this skill until official docs show the same subagent visibility and this skill is updated.

Codex does not spawn subagents automatically. The user must ask for subagents, parallel agents, delegation in parallel, one agent per point, or a similar explicit workflow.

## Built-In Agents

Codex documents these built-in agents:

| Agent | Use |
|---|---|
| `default` | General-purpose fallback |
| `worker` | Execution-focused implementation and fixes |
| `explorer` | Read-heavy codebase exploration |

Prefer the narrowest role that matches the task. Use explorers for specific codebase questions and workers for bounded execution with clear ownership.

## Managing Threads

In the CLI, `/agent` switches between active agent threads and lets the user inspect ongoing work. The user can also ask Codex to steer a running subagent, stop it, or close completed agent threads.

When many agents run, Codex waits until requested results are available and returns a consolidated response. The parent workflow is still responsible for final synthesis.

## Approvals And Sandbox

Subagents inherit the parent session's sandbox policy. Codex also reapplies live runtime overrides from the parent turn when spawning children, including interactive permission changes.

Important consequences:

- A child agent may fail when it needs fresh approval in a non-interactive flow.
- In interactive CLI sessions, approval requests can surface from inactive agent threads.
- Read-only or restricted parent settings should be treated as applying to children unless explicitly overridden by supported custom-agent config and current runtime policy.
- Do not ask subagents to read secrets or private data unless the main task already requires that data and the user authorized the access.

## Custom Agents

Custom agents are standalone TOML files under:

- `~/.codex/agents/` for personal agents.
- `.codex/agents/` for project-scoped agents.

Each custom agent file must define:

- `name`
- `description`
- `developer_instructions`

Optional fields inherit from the parent session when omitted. Public docs include examples such as:

- `nickname_candidates`
- `model`
- `model_reasoning_effort`
- `sandbox_mode`
- `mcp_servers`
- `skills.config`

The `name` field is the source of truth. Matching the filename to `name` is the simplest convention, but the filename is not authoritative.

### Model-Neutral Authoring

Do not bake a specific model version into reusable subagent policy. Prefer this order:

1. Omit `model` so the subagent inherits the parent session default.
2. If needed, describe the task need in the prompt: fast scan, deep review, high-risk reasoning, broad exploration, or low-cost triage.
3. Set `model_reasoning_effort` only when there is a clear quality, speed, or cost reason.
4. Pin a concrete model only when the user explicitly asks or the current project policy requires it.

## Global `[agents]` Settings

Global subagent settings live under `[agents]` in Codex configuration:

| Key | Purpose |
|---|---|
| `agents.max_threads` | Concurrent open agent thread cap |
| `agents.max_depth` | Maximum nesting depth for spawned agent threads |
| `agents.job_max_runtime_seconds` | Default timeout per worker for CSV-spawned jobs |

Keep depth shallow unless the user deliberately asks for recursive delegation. Deeper fan-out increases token use, latency, local resource consumption, and predictability risk.

## Conservative Preflight

Run `scripts/detect_codex_surface.py` when you need a local settings preflight. It can detect the Codex CLI, common config locations, and custom-agent directories. It cannot prove that the Codex app is the current surface.

Treat official docs and the current Codex CLI/App surface as stronger evidence than this helper script.

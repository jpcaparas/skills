# Claude Code Advisor Mechanics

This reference captures the current Claude Code advisor behavior that matters when writing agent instructions.

## Official Sources

- Claude Code advisor docs: https://code.claude.com/docs/en/advisor
- Claude Code settings docs: https://code.claude.com/docs/en/settings
- Claude Code environment variables: https://code.claude.com/docs/en/env-vars
- Claude API advisor tool docs: https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool

## Availability

The Claude Code advisor is experimental. The Claude Code docs state these requirements:

- Claude Code v2.1.98 or later.
- Anthropic API provider for Claude Code. The docs exclude Amazon Bedrock, Google Vertex AI, and Microsoft Foundry for Claude Code advisor use.
- A supported main model.
- A configured advisor model.

Fable advisor use needs Claude Code v2.1.170 or later and organization access.

## Enabling Signals

Claude Code can enable advisor in three ways:

| Method | Persistence | Notes |
|---|---|---|
| `/advisor` | Saves to user `advisorModel` | Can pick a model interactively or pass an alias such as `opus` |
| `advisorModel` setting | Persistent settings | Accepts aliases such as `opus`, `sonnet`, `fable`, or a full model ID |
| `claude --advisor MODEL` | Single launch | Takes precedence for that session and may not be visible in settings files |

The settings docs define `advisorModel` as unset when advisor is disabled. The advisor can also be disabled with `/advisor off` or `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1`.

## Settings Locations

Claude Code settings use these common scopes:

| Scope | Typical path |
|---|---|
| User | `~/.claude/settings.json` |
| Project | `.claude/settings.json` |
| Local project | `.claude/settings.local.json` |
| Managed Linux/WSL | `/etc/claude-code/managed-settings.json` |
| Managed macOS | `/Library/Application Support/ClaudeCode/managed-settings.json` |
| Managed Windows | `C:\Program Files\ClaudeCode\managed-settings.json` |

Settings precedence is managed settings, command-line arguments, local project, shared project, then user settings. Command-line `--advisor` and server-managed settings may not be visible to local filesystem checks.

## Model Pairing

The Claude Code docs state that the advisor must be at least as capable as the main model. The accepted aliases include `opus`, `sonnet`, and `fable`; full model IDs are also accepted. Claude Code validates the pairing before sending a request.

Important consequences:

- A saved advisor may exist but not attach if the main model does not support it.
- Organization `availableModels` allowlists can block a saved advisor model.
- Unknown main or advisor models prevent attachment.
- Subagents inherit the configured advisor, but pairing is checked against the subagent model.

## Call Timing

Claude decides when to call the advisor. The docs say it tends to consult before committing to an approach, when an error recurs, and before declaring a task done. The user can request consultation in a prompt, and skill instructions can create that same pressure, but there is no setting that forces every desired call.

This skill therefore uses mandatory language only for high-value categories, while still respecting no-advisor and no-reason gates.

## Transcript, Privacy, And Cost

The advisor receives the full conversation, including tool calls and results. Each advisor call consumes advisor-model tokens in addition to the main model's usage. The advisor model processes the full transcript for each call; its own read is not cached between calls.

Enabling or disabling advisor mid-session does not invalidate the main model prompt cache. Advisor guidance becomes part of the transcript and may be cached later as transcript content.

## Failure Modes

If the advisor is invalid, blocked, overloaded, rate-limited, or unavailable, Claude Code/API behavior is designed to continue without that advice rather than making the entire task fail. Treat advisor failures as a reason to increase local verification, not as permission to invent an advisor result.

Common skip reasons:

- No advisor model is set.
- Advisor tool disabled by environment.
- Main/advisor model pairing is invalid.
- Advisor model is outside organization allowlist.
- Provider does not support the advisor in Claude Code.
- Transcript is too long for the advisor model.

## Helper Script Limits

`scripts/detect_advisor_config.py` checks visible local settings and environment variables only. It cannot reliably detect:

- A session-only `claude --advisor MODEL` flag.
- Server-managed settings delivered after sign-in.
- Organization model allowlists.
- Whether Claude Code attached the advisor tool to the current model request.

Use the script as a conservative preflight. The current Claude Code tool list remains the source of truth for whether you can call the advisor now.

## See Also

- `references/advisor-policy.md`

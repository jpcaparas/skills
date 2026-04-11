#!/usr/bin/env bash
#
# pre_tool_use.sh
#
# Managed hook stub for Codex PreToolUse.
#
# Event purpose:
#   Gate or deny Bash commands before they run.
#
# Matcher notes:
#   Current Codex runtime only emits `Bash` here. Other matcher regexes parse, but they do not match anything useful today.
#
# Output contract:
#   Plain text stdout is ignored. JSON can deny with `hookSpecificOutput.permissionDecision = "deny"` or the legacy `decision: "block"` shape.
#
# Blocking / control notes:
#   Use `deny_pre_tool_use` or exit code `2` with a reason on stderr to block the Bash command before it runs.
#
# Replace the example logic below with project-specific behavior.
# Keep stdout empty unless you intentionally emit hook output.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
. "$SCRIPT_DIR/../lib/common.sh"

HOOK_INPUT="$(read_hook_input)"

# Common helpers:
#   hook_json FILTER [FALLBACK]
#   emit_additional_context EVENT MESSAGE
#   emit_system_message MESSAGE
#   deny_pre_tool_use REASON
#   block_with_reason REASON
#   exit_with_block_reason REASON
#
# Example:
#   CWD="$(hook_json '.cwd')"

COMMAND="$(hook_json '.tool_input.command' '')"

matches_command() {
    local pattern="$1"
    printf '%s\n' "$COMMAND" | grep -Eiq "$pattern"
}

if [ -z "$COMMAND" ]; then
    exit 0
fi

if matches_command '(^|[;&|[:space:]])git([[:space:]]+-C[[:space:]]+[^;&|[:space:]]+)?[[:space:]]+reset[[:space:]]+--hard([[:space:];&|]|$)'; then
    deny_pre_tool_use "Blocked 'git reset --hard'. Inspect the diff and use a non-destructive recovery command instead."
    exit 0
fi

if matches_command '(^|[;&|[:space:]])git([[:space:]]+-C[[:space:]]+[^;&|[:space:]]+)?[[:space:]]+checkout[[:space:]]+--([[:space:];&|]|$)'; then
    deny_pre_tool_use "Blocked 'git checkout --'. Reverting tracked files blindly is destructive in this repository."
    exit 0
fi

if matches_command '(^|[;&|[:space:]])git([[:space:]]+-C[[:space:]]+[^;&|[:space:]]+)?[[:space:]]+clean([[:space:]]+-[^[:space:]]*)*[[:space:]]+-[^[:space:]]*f'; then
    deny_pre_tool_use "Blocked 'git clean'. This repository prefers explicit cleanup over deleting untracked files wholesale."
    exit 0
fi

if matches_command '(^|[;&|[:space:]])(sudo[[:space:]]+)?rm([[:space:]]+-[^[:space:]]*)*[[:space:]]+-rf([[:space:]]+--)?[[:space:]]+(/|/\*|~|~/\*|\.|\.\.|\*)([[:space:];&|]|$)'; then
    deny_pre_tool_use "Blocked a broad 'rm -rf' target. Use a narrower command after reviewing exactly what should be removed."
    exit 0
fi

exit 0

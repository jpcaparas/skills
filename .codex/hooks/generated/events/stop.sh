#!/usr/bin/env bash
#
# stop.sh
#
# Managed hook stub for Codex Stop.
#
# Event purpose:
#   Run end-of-turn review or request one more Codex pass before the turn fully stops.
#
# Matcher notes:
#   Current runtime ignores `matcher` for this event.
#
# Output contract:
#   When exiting `0`, stdout must be JSON. `decision: "block"` continues Codex with your `reason` as a new continuation prompt.
#
# Blocking / control notes:
#   Treat `block` on `Stop` as 'continue and do one more pass', not as a normal reject decision.
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

if [ "$(hook_json '.stop_hook_active' 'false')" = "true" ]; then
    jq -n '{continue: true}'
    exit 0
fi

CWD="$(hook_json '.cwd' "$PWD")"
REPO_ROOT="$(repo_root_from_cwd "$CWD")"
cd "$REPO_ROOT"

if VALIDATION_OUTPUT="$(bash "$REPO_ROOT/scripts/agent-stop-checks.sh" "$REPO_ROOT" 2>&1)"; then
    jq -n '{continue: true}'
    exit 0
fi

VALIDATION_OUTPUT="$(printf '%s\n' "$VALIDATION_OUTPUT" | tail -n 200)"
REASON="$(cat <<EOF
Validation failed. Run \`bash scripts/agent-stop-checks.sh\`, fix the reported issues below, and stop again only after it passes. This includes README skill art cards, the Codex skills context-budget guard, and full repository validation.

${VALIDATION_OUTPUT}
EOF
)"

block_with_reason "$REASON"

exit 0

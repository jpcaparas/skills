#!/usr/bin/env bash
#
# user_prompt_submit.sh
#
# Managed hook stub for Codex UserPromptSubmit.
#
# Event purpose:
#   Inject context into user prompts or block a prompt before it is sent.
#
# Matcher notes:
#   Current runtime ignores `matcher` for this event.
#
# Output contract:
#   Plain text stdout is added as extra developer context. JSON can add context or block with `decision: "block"`.
#
# Blocking / control notes:
#   Use `block_with_reason` or exit code `2` with stderr when you need Codex to stop and ask for a clearer prompt.
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

# TODO: add project-specific logic here.

exit 0

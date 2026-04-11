#!/usr/bin/env bash
#
# post_tool_use.sh
#
# Managed hook stub for Codex PostToolUse.
#
# Event purpose:
#   React to Bash command results after the command has already run.
#
# Matcher notes:
#   Current Codex runtime only emits `Bash` here, and not every shell path is intercepted yet.
#
# Output contract:
#   Plain text stdout is ignored. JSON can add context, replace the feedback Codex sees next, or return `continue: false`.
#
# Blocking / control notes:
#   This event cannot undo command side effects. Treat `decision: "block"` here as feedback control, not as prevention.
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

case "$COMMAND" in
    *"skills/"*|*"SKILL.md"*|*"scripts/validate-all-skills.sh"*|*"npx --yes skills add . --list"*)
        MESSAGE="$(cat <<'EOF'
Repo reminder: SKILL.md remains the canonical source for each skill, while README.md, AGENTS.md, and metadata.json stay thin wrappers.
If you changed a specific skill, run:
  python3 skills/<skill-name>/scripts/validate.py skills/<skill-name>
  python3 skills/<skill-name>/scripts/test_skill.py skills/<skill-name>
Before finishing repository changes, also run:
  bash scripts/validate-all-skills.sh
EOF
)"
        emit_additional_context "PostToolUse" "$MESSAGE"
        ;;
esac

exit 0

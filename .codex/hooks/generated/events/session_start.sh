#!/usr/bin/env bash
#
# session_start.sh
#
# Managed hook stub for Codex SessionStart.
#
# Event purpose:
#   Bootstrap session context or run lightweight environment checks before Codex starts working.
#
# Matcher notes:
#   Use a matcher only for `startup` or `resume`. `*` and an empty matcher both mean match all.
#
# Output contract:
#   Plain text stdout is added as extra developer context. JSON can return `hookSpecificOutput.additionalContext`.
#
# Blocking / control notes:
#   There is no dedicated blocking shape for this event. Keep it lightweight and context-oriented.
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

SOURCE="$(hook_json '.source' 'startup')"
CWD="$(hook_json '.cwd' "$PWD")"
REPO_ROOT="$(repo_root_from_cwd "$CWD")"

MESSAGE="$(cat <<EOF
Skills repository reminder for ${SOURCE}:
- Installable skills live under skills/<skill-name>/ and SKILL.md is the canonical instruction file.
- README.md, AGENTS.md, and metadata.json beside a skill stay as thin packaging wrappers.
- Prefer repo-agnostic instructions unless the user explicitly needs machine-specific paths.
- If a skill ships scripts, validate with:
  python3 skills/<skill-name>/scripts/validate.py skills/<skill-name>
  python3 skills/<skill-name>/scripts/test_skill.py skills/<skill-name>
- Before ending a turn with repository changes, run:
  bash scripts/validate-all-skills.sh
- Current repo root: ${REPO_ROOT}
EOF
)"

emit_additional_context "SessionStart" "$MESSAGE"

exit 0

#!/usr/bin/env bash
#
# script.sh
#
# Canonical event script for WorktreeCreate.
#
# What this event is for:
#   Runs when a worktree is being created.
#
# Recommended starting style:
#   Usually sync because this event can replace the default worktree behavior.
#
# Ports/adapters layout:
#   - script.sh is the shared, editable project behavior for this lifecycle event.
#   - <harness>.sh files are thin protocol adapters invoked by harness config.
#   - <harness>.json files carry harness-specific plan data such as commands,
#     reusable scripts, matchers, and blocking preferences.
#
# How this script is organized:
#   1. main() reads the active harness JSON payload from stdin exactly once.
#   2. read_adapter_config() loads the active <harness>.json plan data.
#   3. run_hook_event() applies shared skip policy before custom or plan effects.
#   4. handle_event() contains the shared project-specific logic.
#   5. run_configured_scripts() and run_configured_commands() execute plan data.
#   6. Protocol-specific output helpers live in hooks/lib/<harness>.sh.
#
# Safe editing rule:
#   Start by editing handle_event(). Keep protocol-specific stdout/stderr logic
#   in hooks/lib/<harness>.sh so this script can serve every harness that maps
#   to this event.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

: "${AGENT_HOOK_HARNESS:?AGENT_HOOK_HARNESS must be set by the harness adapter}"
: "${AGENT_HOOK_EVENT:=WorktreeCreate}"

# shellcheck source=/dev/null
source "$HOOKS_ROOT/lib/agent-hook-runtime.sh"
# shellcheck source=/dev/null
source "$HOOKS_ROOT/lib/${AGENT_HOOK_HARNESS}.sh"

HOOK_INPUT=""
ADAPTER_CONFIG_JSON="{}"

handle_event() {
    # Project-specific logic belongs here.
    # Use config_scripts_json and config_commands_json for plan-managed
    # reusable behavior, then add any local event logic below those calls.
    if ! run_configured_scripts "$(config_scripts_json)"; then
        handle_project_command_failure "$AGENT_HOOK_EVENT" "$(configured_command_failure_message)"
        return $?
    fi

    if ! run_configured_commands "$(config_commands_json)"; then
        handle_project_command_failure "$AGENT_HOOK_EVENT" "$(configured_command_failure_message)"
        return $?
    fi

    # Useful helpers from hooks/lib/agent-hook-runtime.sh:
    #   hook_json FILTER [FALLBACK]
    #   config_value FILTER [FALLBACK]
    #   run_project_script LABEL SCRIPT_PATH ARGS_JSON [CWD]
    #   run_project_command LABEL COMMAND [CWD]
    #
    # Useful protocol helpers come from hooks/lib/${AGENT_HOOK_HARNESS}.sh.
    #
    # Keep stdout empty unless this hook intentionally sends JSON back to the
    # active harness. Plain logging should go to stderr.
    return 0
}

main() {
    HOOK_INPUT="$(read_hook_input)"
    readonly HOOK_INPUT

    ADAPTER_CONFIG_JSON="$(read_adapter_config "$SCRIPT_DIR/${AGENT_HOOK_HARNESS}.json")"
    readonly ADAPTER_CONFIG_JSON

    run_hook_event handle_event "$@"
}

main "$@"

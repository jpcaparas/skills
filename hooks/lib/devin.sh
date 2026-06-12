#!/usr/bin/env bash
set -euo pipefail

write_decision() {
    local decision="$1"
    local reason="${2:-}"
    require_jq
    if [ -n "$reason" ]; then
        jq -n --arg decision "$decision" --arg reason "$reason" '{decision: $decision, reason: $reason}'
    else
        jq -n --arg decision "$decision" '{decision: $decision}'
    fi
}

block_action() {
    local reason="$1"
    write_decision "block" "$reason"
    return 2
}

deny_action() {
    local reason="$1"
    write_decision "deny" "$reason"
    return 2
}

approve_action() {
    local reason="${1:-}"
    write_decision "approve" "$reason"
}

handle_project_command_failure() {
    local event_name="$1"
    local message="$2"
    local block_on_failure
    block_on_failure="$(config_block_on_failure)"

    if [ "$block_on_failure" = "true" ]; then
        block_action "$message"
        return 2
    fi

    printf '[devin-hook] %s configured command failed but block_on_failure=false.\n' "$event_name" >&2
    printf '%s\n' "$message" >&2
    return 1
}

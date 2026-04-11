#!/usr/bin/env bash
#
# common.sh
#
# Shared helper functions for generated Codex hook scripts.
#

set -euo pipefail

read_hook_input() {
    cat
}

hook_json() {
    local filter="$1"
    local fallback="${2:-__NO_FALLBACK__}"
    local result=""

    if [ "$fallback" = "__NO_FALLBACK__" ]; then
        printf '%s' "$HOOK_INPUT" | jq -er "$filter"
    else
        if result="$(printf '%s' "$HOOK_INPUT" | jq -er "$filter" 2>/dev/null)"; then
            printf '%s\n' "$result"
        else
            printf '%s\n' "$fallback"
        fi
    fi
}

emit_additional_context() {
    local event_name="$1"
    local message="$2"
    jq -n --arg event_name "$event_name" --arg message "$message" \
        '{hookSpecificOutput: {hookEventName: $event_name, additionalContext: $message}}'
}

emit_system_message() {
    local message="$1"
    jq -n --arg message "$message" '{systemMessage: $message}'
}

deny_pre_tool_use() {
    local reason="$1"
    jq -n --arg reason "$reason" \
        '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
}

block_with_reason() {
    local reason="$1"
    jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
}

exit_with_block_reason() {
    local reason="$1"
    printf '%s\n' "$reason" >&2
    exit 2
}

repo_root_from_cwd() {
    local cwd="${1:-}"

    if [ -z "$cwd" ]; then
        cwd="$(pwd -P)"
    fi

    git -C "$cwd" rev-parse --show-toplevel 2>/dev/null || printf '%s\n' "$cwd"
}

is_sail_up() {
    local repo_root="$1"
    local api_dir="$repo_root/apps/api"

    if [ ! -f "$api_dir/docker-compose.yml" ] || [ ! -f "$api_dir/.env" ]; then
        return 1
    fi

    if ! command -v docker >/dev/null 2>&1; then
        return 1
    fi

    docker compose \
        -f "$api_dir/docker-compose.yml" \
        --env-file "$api_dir/.env" \
        ps --status running --format '{{.Service}}' 2>/dev/null \
        | grep -q '^laravel\.test$'
}

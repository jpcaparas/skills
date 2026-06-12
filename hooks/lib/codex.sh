#!/usr/bin/env bash
set -euo pipefail

emit_additional_context() {
    local event_name="$1"
    local message="$2"
    require_jq
    jq -n --arg event_name "$event_name" --arg message "$message" \
        '{hookSpecificOutput: {hookEventName: $event_name, additionalContext: $message}}'
}

emit_system_message() {
    local message="$1"
    require_jq
    jq -n --arg message "$message" '{systemMessage: $message}'
}

deny_pre_tool_use() {
    local reason="$1"
    require_jq
    jq -n --arg reason "$reason" \
        '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
}

deny_permission_request() {
    local message="$1"
    require_jq
    jq -n --arg message "$message" \
        '{hookSpecificOutput: {hookEventName: "PermissionRequest", decision: {behavior: "deny", message: $message}}}'
}

block_with_reason() {
    local reason="$1"
    require_jq
    jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
}

stop_processing() {
    local reason="$1"
    require_jq
    jq -n --arg reason "$reason" '{continue: false, stopReason: $reason}'
}

exit_with_block_reason() {
    local reason="$1"
    printf '%s\n' "$reason" >&2
    exit 2
}

handle_project_command_failure() {
    local event_name="$1"
    local message="$2"

    case "$event_name" in
        PreToolUse)
            deny_pre_tool_use "$message"
            ;;
        PermissionRequest)
            deny_permission_request "$message"
            ;;
        PreCompact|PostCompact)
            stop_processing "$message"
            ;;
        Stop|SubagentStop|UserPromptSubmit|PostToolUse)
            block_with_reason "$message"
            ;;
        SessionStart|SubagentStart)
            emit_additional_context "$event_name" "$message"
            ;;
        *)
            printf '%s\n' "$message" >&2
            return 1
            ;;
    esac
}

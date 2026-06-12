#!/usr/bin/env bash
#
# Claude Code output adapter helpers.

set -euo pipefail

write_system_message() {
    local message="$1"
    require_jq
    jq -n --arg message "$message" '{systemMessage: $message}'
}

write_additional_context() {
    local message="$1"
    require_jq
    jq -n --arg message "$message" '{additionalContext: $message}'
}

write_block_decision() {
    local reason="$1"
    require_jq
    jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
}

stop_processing() {
    local reason="$1"
    require_jq
    jq -n --arg reason "$reason" '{continue: false, stopReason: $reason}'
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
        Stop|SubagentStop|TeammateIdle|TaskCreated|TaskCompleted|PostToolBatch|ConfigChange|Elicitation|ElicitationResult|UserPromptExpansion)
            write_block_decision "$message"
            ;;
        PreCompact)
            stop_processing "$message"
            ;;
        PostToolUse|PostToolUseFailure|SessionStart|Setup|Notification|MessageDisplay|SubagentStart|PostCompact|SessionEnd|CwdChanged|FileChanged|InstructionsLoaded|StopFailure|PermissionDenied|WorktreeRemove)
            write_system_message "$message"
            ;;
        *)
            printf '%s\n' "$message" >&2
            return 1
            ;;
    esac
}

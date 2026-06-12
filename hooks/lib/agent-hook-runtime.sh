#!/usr/bin/env bash
set -euo pipefail

require_jq() {
    if ! command -v jq >/dev/null 2>&1; then
        echo "jq is required by agent hook helpers." >&2
        return 1
    fi
}

read_hook_input() { cat; }

read_adapter_config() {
    local config_file="$1"
    require_jq
    if [ -f "$config_file" ]; then
        jq -c '.' "$config_file"
    else
        printf '{}\n'
    fi
}

hook_json() {
    local filter="$1"
    require_jq
    if [ "$#" -ge 2 ]; then
        local fallback="$2"
        printf '%s' "$HOOK_INPUT" | jq -er "$filter" 2>/dev/null || printf '%s\n' "$fallback"
    else
        printf '%s' "$HOOK_INPUT" | jq -er "$filter"
    fi
}

config_value() {
    local filter="$1"
    require_jq
    if [ "$#" -ge 2 ]; then
        local fallback="$2"
        printf '%s' "$ADAPTER_CONFIG_JSON" | jq -er "$filter" 2>/dev/null || printf '%s\n' "$fallback"
    else
        printf '%s' "$ADAPTER_CONFIG_JSON" | jq -er "$filter"
    fi
}

config_scripts_json() { config_value '.scripts // []' '[]'; }
config_commands_json() { config_value '.commands // []' '[]'; }
config_block_on_failure() { config_value '(.block_on_failure // false | tostring)' 'false'; }

hook_project_root() {
    case "${AGENT_HOOK_HARNESS:-}" in
        claude)
            if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then printf '%s\n' "$CLAUDE_PROJECT_DIR"; return 0; fi
            ;;
        devin)
            if [ -n "${DEVIN_PROJECT_DIR:-}" ]; then printf '%s\n' "$DEVIN_PROJECT_DIR"; return 0; fi
            ;;
    esac

    local payload_cwd
    payload_cwd="$(printf '%s' "$HOOK_INPUT" | jq -er '.cwd // empty' 2>/dev/null || true)"
    if [ -n "$payload_cwd" ]; then
        printf '%s\n' "$payload_cwd"
        return 0
    fi

    if git rev-parse --show-toplevel >/dev/null 2>&1; then
        git rev-parse --show-toplevel
        return 0
    fi

    pwd -P
}

hook_session_id() {
    local session_id
    session_id="$(printf '%s' "$HOOK_INPUT" | jq -er '.session_id // .sessionId // .conversation_id // .conversationId // empty' 2>/dev/null || true)"
    if [ -n "$session_id" ]; then
        printf '%s\n' "$session_id"
        return 0
    fi
    printf '%s-default\n' "${AGENT_HOOK_HARNESS:-agent}"
}

resolve_command_cwd() {
    local requested_cwd="${1:-.}"
    case "$requested_cwd" in
        ""|".") hook_project_root ;;
        /*) printf '%s\n' "$requested_cwd" ;;
        *) printf '%s/%s\n' "$(hook_project_root)" "$requested_cwd" ;;
    esac
}

COMMAND_FAILURE_SUMMARY=""

append_command_failure() {
    local label="$1"
    local command="$2"
    local status="$3"
    COMMAND_FAILURE_SUMMARY="${COMMAND_FAILURE_SUMMARY}- ${label}: exited with ${status} while running \`${command}\`
"
}

configured_command_failure_message() {
    printf 'One or more project hook commands failed.\n\n%s\nFix the failing command output, then retry the agent action.' "$COMMAND_FAILURE_SUMMARY"
}

run_project_command() {
    local label="$1"
    local command="$2"
    local cwd
    local project_root
    local session_id
    cwd="$(resolve_command_cwd "${3:-.}")"
    project_root="$(hook_project_root)"
    session_id="$(hook_session_id)"
    printf '[%s-hook] %s\n' "${AGENT_HOOK_HARNESS:-agent}" "$label" >&2
    printf '[%s-hook] cwd: %s\n' "${AGENT_HOOK_HARNESS:-agent}" "$cwd" >&2
    printf '[%s-hook] command: %s\n' "${AGENT_HOOK_HARNESS:-agent}" "$command" >&2
    (
        cd "$cwd"
        AGENT_HOOK_PROJECT_ROOT="$project_root" \
            AGENT_HOOK_SESSION_ID="$session_id" \
            /usr/bin/env bash -lc "$command"
    )
}

run_project_script() {
    local label="$1"
    local script_path="$2"
    local args_json="${3:-[]}"
    local cwd
    local project_root
    local resolved_script
    local session_id
    local -a script_args=()

    cwd="$(resolve_command_cwd "${4:-.}")"
    project_root="$(hook_project_root)"
    session_id="$(hook_session_id)"
    case "$script_path" in
        /*) resolved_script="$script_path" ;;
        *) resolved_script="$project_root/$script_path" ;;
    esac

    require_jq
    while IFS= read -r script_arg; do
        script_args+=("$script_arg")
    done < <(printf '%s' "$args_json" | jq -r '.[]?')

    if [ ! -f "$resolved_script" ]; then
        printf '[%s-hook] missing script: %s\n' "${AGENT_HOOK_HARNESS:-agent}" "$resolved_script" >&2
        return 127
    fi

    printf '[%s-hook] %s\n' "${AGENT_HOOK_HARNESS:-agent}" "$label" >&2
    printf '[%s-hook] cwd: %s\n' "${AGENT_HOOK_HARNESS:-agent}" "$cwd" >&2
    printf '[%s-hook] script: %s\n' "${AGENT_HOOK_HARNESS:-agent}" "$resolved_script" >&2
    if [ "${#script_args[@]}" -gt 0 ]; then
        (
            cd "$cwd"
            AGENT_HOOK_PROJECT_ROOT="$project_root" \
                AGENT_HOOK_SESSION_ID="$session_id" \
                /usr/bin/env bash "$resolved_script" "${script_args[@]}"
        )
    else
        (
            cd "$cwd"
            AGENT_HOOK_PROJECT_ROOT="$project_root" \
                AGENT_HOOK_SESSION_ID="$session_id" \
                /usr/bin/env bash "$resolved_script"
        )
    fi
}

run_configured_scripts() {
    local scripts_json="$1"
    local failed="false"
    require_jq
    if [ "$(printf '%s' "$scripts_json" | jq 'length')" -eq 0 ]; then return 0; fi
    while IFS= read -r script_item; do
        local label script_path script_args_json cwd status
        script_path="$(printf '%s' "$script_item" | jq -r '.path // .script // empty')"
        label="$(printf '%s' "$script_item" | jq -r '.label // .name // .path // .script')"
        script_args_json="$(printf '%s' "$script_item" | jq -c '.args // []')"
        cwd="$(printf '%s' "$script_item" | jq -r '.cwd // "."')"
        if [ -z "$script_path" ]; then
            append_command_failure "$label" "<missing script path>" 64
            failed="true"
            continue
        fi
        if run_project_script "$label" "$script_path" "$script_args_json" "$cwd"; then
            :
        else
            status="$?"
            append_command_failure "$label" "$script_path" "$status"
            failed="true"
        fi
    done < <(printf '%s' "$scripts_json" | jq -c '.[]')
    [ "$failed" = "false" ]
}

run_configured_commands() {
    local commands_json="$1"
    local failed="false"
    require_jq
    if [ "$(printf '%s' "$commands_json" | jq 'length')" -eq 0 ]; then return 0; fi
    while IFS= read -r command_item; do
        local label command cwd status
        label="$(printf '%s' "$command_item" | jq -r '.label // .name // .command')"
        command="$(printf '%s' "$command_item" | jq -r '.command')"
        cwd="$(printf '%s' "$command_item" | jq -r '.cwd // "."')"
        if run_project_command "$label" "$command" "$cwd"; then
            :
        else
            status="$?"
            append_command_failure "$label" "$command" "$status"
            failed="true"
        fi
    done < <(printf '%s' "$commands_json" | jq -c '.[]')
    [ "$failed" = "false" ]
}

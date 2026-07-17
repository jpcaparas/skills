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

config_collection_json() {
    local field="$1"
    require_jq
    # Preserve present-but-invalid values so the runner fails closed.
    printf '%s' "$ADAPTER_CONFIG_JSON" | jq -c --arg field "$field" '
        if type != "object" then error("adapter config must be an object")
        elif has($field) then .[$field]
        else []
        end
    '
}
config_scripts_json() { config_collection_json "scripts"; }
config_commands_json() { config_collection_json "commands"; }
config_block_on_failure() { config_value '(.block_on_failure // false | tostring)' 'false'; }
config_run_on_code_changes() { config_value '(.run_on_code_changes // false | tostring)' 'false'; }
config_code_change_extensions_json() { config_collection_json "code_change_extensions"; }

hook_stop_is_active() {
    [ "$(hook_json '(.stop_hook_active // false | tostring)' 'false')" = "true" ]
}

hook_has_code_changes() {
    local project_dir="$1"
    local extensions_json="${2:-[]}"
    local pattern
    local -a command_statuses=()
    require_jq
    if ! pattern="$(printf '%s' "$extensions_json" | jq -er 'map(ltrimstr(".")) | join("|")')"; then
        return 2
    fi
    [ -n "$pattern" ] || return 1
    git -C "$project_dir" rev-parse --show-toplevel >/dev/null 2>&1 || return 2

    # grep must consume the full stream. A quiet grep can close the pipe early
    # and make a successful Git producer look like a SIGPIPE failure.
    if {
        git -C "$project_dir" diff --cached --name-only 2>/dev/null &&
            git -C "$project_dir" diff --name-only 2>/dev/null &&
            git -C "$project_dir" ls-files --others --exclude-standard 2>/dev/null
    } | grep -Ei "\\.($pattern)$" >/dev/null; then
        command_statuses=("${PIPESTATUS[@]}")
    else
        # Capture both statuses before another command overwrites PIPESTATUS.
        command_statuses=("${PIPESTATUS[@]}")
    fi

    if [ "${command_statuses[0]}" -ne 0 ]; then return 2; fi
    case "${command_statuses[1]}" in
        0) return 0 ;;
        1) return 1 ;;
        *) return 2 ;;
    esac
}

hook_should_skip_event() {
    local code_change_extensions_json
    local code_change_status

    case "${AGENT_HOOK_EVENT:-}" in
        Stop|SubagentStop)
            if hook_stop_is_active; then
                return 0
            fi
            if [ "$(config_run_on_code_changes)" = "true" ]; then
                if ! code_change_extensions_json="$(config_code_change_extensions_json)" \
                    || ! validate_code_change_extensions_json "$code_change_extensions_json"; then
                    printf '[%s-hook] invalid code_change_extensions configuration: expected an array of non-empty strings.\n' \
                        "${AGENT_HOOK_HARNESS:-agent}" >&2
                    return 1
                fi
                if hook_has_code_changes "$(hook_project_root)" "$code_change_extensions_json"; then
                    :
                else
                    code_change_status="$?"
                    if [ "$code_change_status" -eq 1 ]; then
                        return 0
                    fi
                    printf '[%s-hook] unable to inspect code changes; running configured checks.\n' \
                        "${AGENT_HOOK_HARNESS:-agent}" >&2
                    return 1
                fi
            fi
            ;;
    esac
    return 1
}

validate_code_change_extensions_json() {
    local extensions_json="$1"

    printf '%s' "$extensions_json" | jq -e '
        if type != "array" then false
        else all(.[];
            if type != "string" then false
            else (ltrimstr(".") | length) > 0
            end
        )
        end
    ' >/dev/null 2>&1
}

preflight_configured_effects() {
    local scripts_json
    local commands_json

    if ! scripts_json="$(config_scripts_json 2>/dev/null)"; then
        record_invalid_configured_items "scripts"
        return 1
    fi
    if ! commands_json="$(config_commands_json 2>/dev/null)"; then
        record_invalid_configured_items "commands"
        return 1
    fi
    if ! validate_configured_items_json "scripts" "$scripts_json"; then
        return 1
    fi
    validate_configured_items_json "commands" "$commands_json"
}

run_hook_event() {
    local handler="$1"
    shift

    if hook_should_skip_event; then
        return 0
    fi
    if ! preflight_configured_effects; then
        handle_project_command_failure "$AGENT_HOOK_EVENT" "$(configured_command_failure_message)"
        return $?
    fi
    "$handler" "$@"
}

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

record_invalid_configured_items() {
    local kind="$1"
    local expected
    case "$kind" in
        scripts) expected="an array of objects with a non-empty path, optional string args, and an optional string cwd" ;;
        commands) expected="an array of objects with a non-empty command and an optional string cwd" ;;
        *) expected="a valid array" ;;
    esac
    printf '[%s-hook] invalid %s configuration: expected %s.\n' \
        "${AGENT_HOOK_HARNESS:-agent}" "$kind" "$expected" >&2
    append_command_failure "invalid $kind configuration" "<plan validation>" 64
}

validate_configured_items_json() {
    local kind="$1"
    local items_json="$2"
    local filter
    case "$kind" in
        scripts)
            filter='
                def valid_args:
                    if has("args") then
                        if (.args | type) != "array" then false
                        else all(.args[]; type == "string")
                        end
                    else true
                    end;
                def valid_cwd:
                    if has("cwd") then (.cwd | type) == "string" else true end;
                def valid_item:
                    if type != "object" then false
                    else
                        (.path? // .script? // null) as $path
                        | (if ($path | type) == "string" then ($path | length) > 0 else false end)
                        and valid_args
                        and valid_cwd
                    end;
                if type != "array" then false else all(.[]; valid_item) end
            '
            ;;
        commands)
            filter='
                def valid_cwd:
                    if has("cwd") then (.cwd | type) == "string" else true end;
                def valid_item:
                    if type != "object" then false
                    else
                        (.command? // null) as $command
                        | (if ($command | type) == "string" then ($command | length) > 0 else false end)
                        and valid_cwd
                    end;
                if type != "array" then false else all(.[]; valid_item) end
            '
            ;;
        *)
            record_invalid_configured_items "$kind"
            return 1
            ;;
    esac
    if printf '%s' "$items_json" | jq -e "$filter" >/dev/null 2>&1; then
        return 0
    fi
    record_invalid_configured_items "$kind"
    return 1
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
    local args_count
    local cwd
    local project_root
    local resolved_script
    local script_arg
    local script_arg_index
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
    if ! args_count="$(
        printf '%s' "$args_json" | jq -er '
            if type != "array" then error("script args must be an array")
            elif all(.[]; type == "string") then length
            else error("script args must contain only strings")
            end
        '
    )"; then
        printf '[%s-hook] invalid script args configuration: expected an array of strings.\n' \
            "${AGENT_HOOK_HARNESS:-agent}" >&2
        return 64
    fi
    for ((script_arg_index = 0; script_arg_index < args_count; script_arg_index += 1)); do
        if ! script_arg="$(
            printf '%s' "$args_json" | jq -er --argjson index "$script_arg_index" '.[$index]'
        )"; then
            printf '[%s-hook] failed to read validated script args.\n' \
                "${AGENT_HOOK_HARNESS:-agent}" >&2
            return 64
        fi
        script_args+=("$script_arg")
    done

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
    local script_items
    require_jq
    if ! validate_configured_items_json "scripts" "$scripts_json"; then return 1; fi
    # Capture the producer status before looping; process substitution hides it.
    if ! script_items="$(printf '%s' "$scripts_json" | jq -c '.[]')"; then
        record_invalid_configured_items "scripts"
        return 1
    fi
    if [ -z "$script_items" ]; then return 0; fi
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
    done <<< "$script_items"
    [ "$failed" = "false" ]
}

run_configured_commands() {
    local commands_json="$1"
    local command_items
    local failed="false"
    require_jq
    if ! validate_configured_items_json "commands" "$commands_json"; then return 1; fi
    if ! command_items="$(printf '%s' "$commands_json" | jq -c '.[]')"; then
        record_invalid_configured_items "commands"
        return 1
    fi
    if [ -z "$command_items" ]; then return 0; fi
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
    done <<< "$command_items"
    [ "$failed" = "false" ]
}

#!/usr/bin/env bash
#
# scaffold_hooks.sh
#
# Render or refresh a managed Devin CLI hook scaffold in a target project.
#
# This script is deterministic by design:
# - it always creates one managed bash stub per documented Devin lifecycle event
# - it only enables the events listed in the provided plan JSON
# - it only replaces previously managed hook commands in .devin/hooks.v1.json
# - it leaves unrelated custom hooks alone
#
# Usage:
#   ./scaffold_hooks.sh --project /path/to/project --plan /path/to/plan.json
#   ./scaffold_hooks.sh --project /path/to/project --plan /path/to/plan.json --mode overhaul
#

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  scaffold_hooks.sh --project DIR --plan FILE [--mode additive|overhaul] [--dry-run]

Options:
  --project DIR   Target project root.
  --plan FILE     Hook plan JSON.
  --mode MODE     Override the mode in the plan. Valid values: additive, overhaul.
  --dry-run       Validate inputs and print what would happen without writing files.
  -h, --help      Show this help text.
EOF
}

require_command() {
    local name="$1"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "Required command is missing: $name" >&2
        exit 1
    fi
}

validate_plan_item_collections() {
    local plan_file="$1"

    # Validate the complete collection before any jq iterator can turn a bad
    # scripts/commands value into an empty generated adapter configuration.
    if jq -e '
        def valid_args:
            if has("args") then
                if (.args | type) != "array" then false
                else all(.args[]; type == "string")
                end
            else true
            end;
        def valid_cwd:
            if has("cwd") then (.cwd | type) == "string" else true end;
        def valid_script:
            if type != "object" then false
            else
                (.path? // .script? // null) as $path
                | (if ($path | type) == "string" then ($path | length) > 0 else false end)
                and valid_args
                and valid_cwd
            end;
        def valid_command:
            if type != "object" then false
            else
                (.command? // null) as $command
                | (if ($command | type) == "string" then ($command | length) > 0 else false end)
                and valid_cwd
            end;
        def valid_event:
            if type != "object" then false
            elif has("scripts") and ((.scripts | type) != "array" or (all(.scripts[]; valid_script) | not)) then false
            elif has("commands") and ((.commands | type) != "array" or (all(.commands[]; valid_command) | not)) then false
            else true
            end;
        if type != "object" then false
        elif has("enabled_events") then
            if (.enabled_events | type) != "array" then false
            else all(.enabled_events[]; valid_event)
            end
        else true
        end
    ' "$plan_file" >/dev/null 2>&1; then
        return 0
    fi

    echo "Plan file has invalid scripts or commands configuration." >&2
    echo "Expected arrays of objects with non-empty paths/commands, string args, and string cwd values." >&2
    return 1
}

escape_for_sed() {
    printf '%s' "$1" | sed -e 's/[&|\\]/\\&/g'
}

event_dir_name() {
    local script_name="$1"
    script_name="${script_name%.sh}"
    printf '%s\n' "$script_name" | tr '_' '-'
}

write_adapter_script() {
    local harness="$1"
    local event_name="$2"
    local target="$3"

    cat > "$target" <<EOF
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
export AGENT_HOOK_HARNESS="$harness"
export AGENT_HOOK_EVENT="$event_name"

exec bash "\$SCRIPT_DIR/script.sh" "\$@"
EOF
    chmod +x "$target"
}

write_runtime_lib() {
    cat > "$LIB_DIR/agent-hook-runtime.sh" <<'EOF'
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
                    if [ "$code_change_status" -eq 1 ]; then return 0; fi
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
    if hook_should_skip_event; then return 0; fi
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
    cwd="$(resolve_command_cwd "${3:-.}")"
    printf '[%s-hook] %s\n' "${AGENT_HOOK_HARNESS:-agent}" "$label" >&2
    printf '[%s-hook] cwd: %s\n' "${AGENT_HOOK_HARNESS:-agent}" "$cwd" >&2
    printf '[%s-hook] command: %s\n' "${AGENT_HOOK_HARNESS:-agent}" "$command" >&2
    (cd "$cwd" && /usr/bin/env bash -lc "$command")
}

run_project_script() {
    local label="$1"
    local script_path="$2"
    local args_json="${3:-[]}"
    local args_count
    local cwd
    local resolved_script
    local script_arg
    local script_arg_index
    local -a script_args=()

    cwd="$(resolve_command_cwd "${4:-.}")"
    case "$script_path" in
        /*) resolved_script="$script_path" ;;
        *) resolved_script="$(hook_project_root)/$script_path" ;;
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
        (cd "$cwd" && /usr/bin/env bash "$resolved_script" "${script_args[@]}")
    else
        (cd "$cwd" && /usr/bin/env bash "$resolved_script")
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
EOF
    chmod +x "$LIB_DIR/agent-hook-runtime.sh"
}

write_devin_lib() {
    cat > "$LIB_DIR/devin.sh" <<'EOF'
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

# Devin strictly parses non-empty hook stdout as Claude-format JSON; plain
# text fails its effects evaluator and is silently dropped. Use this helper
# to inject context (for example from SessionStart) instead of printing text.
write_additional_context() {
    local event_name
    local message
    if [ "$#" -eq 1 ]; then
        event_name="${AGENT_HOOK_EVENT:-SessionStart}"
        message="$1"
    else
        event_name="$1"
        message="$2"
    fi

    require_jq
    jq -n --arg event "$event_name" --arg message "$message" \
        '{hookSpecificOutput: {hookEventName: $event, additionalContext: $message}}'
}

emit_additional_context() {
    write_additional_context "$@"
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
EOF
    chmod +x "$LIB_DIR/devin.sh"
}

PROJECT_ROOT=""
PLAN_FILE=""
MODE_OVERRIDE=""
DRY_RUN="false"

while [ $# -gt 0 ]; do
    case "$1" in
        --project)
            PROJECT_ROOT="$2"
            shift 2
            ;;
        --plan)
            PLAN_FILE="$2"
            shift 2
            ;;
        --mode)
            MODE_OVERRIDE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

if [ -z "$PROJECT_ROOT" ] || [ -z "$PLAN_FILE" ]; then
    usage >&2
    exit 1
fi

require_command jq

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
SCAFFOLD_ROOT="$(cd "$SKILL_ROOT/../.." && pwd -P)"
MANIFEST_SOURCE="$SKILL_ROOT/assets/hook-events.json"
EVENT_TEMPLATE="$SKILL_ROOT/templates/event-script.sh.tmpl"

PROJECT_ROOT="$(
    cd "$PROJECT_ROOT"
    pwd -P
)"
PLAN_FILE="$(
    cd "$(dirname "$PLAN_FILE")"
    printf '%s/%s\n' "$(pwd -P)" "$(basename "$PLAN_FILE")"
)"

if [ ! -f "$PLAN_FILE" ]; then
    echo "Plan file does not exist: $PLAN_FILE" >&2
    exit 1
fi

validate_plan_item_collections "$PLAN_FILE" || exit 1

MODE="$(jq -r '.mode // "additive"' "$PLAN_FILE")"
if [ -n "$MODE_OVERRIDE" ]; then
    MODE="$MODE_OVERRIDE"
fi

case "$MODE" in
    additive|overhaul)
        ;;
    *)
        echo "Mode must be additive or overhaul. Got: $MODE" >&2
        exit 1
        ;;
esac

HOOKS_TARGET_REL="$(jq -r '.hooks_target // ".devin/hooks.v1.json"' "$PLAN_FILE")"
MANAGED_ROOT_REL="$(jq -r '.managed_root // "hooks"' "$PLAN_FILE")"

case "$HOOKS_TARGET_REL" in
    .devin/hooks.v1.json)
        ;;
    *)
        echo "This scaffold writes only .devin/hooks.v1.json. Got: $HOOKS_TARGET_REL" >&2
        exit 1
        ;;
esac

MANAGED_ROOT_ABS="$PROJECT_ROOT/$MANAGED_ROOT_REL"
LIB_DIR="$MANAGED_ROOT_ABS/lib"
STATE_DIR="$MANAGED_ROOT_ABS/.state/devin"
HOOKS_FRAGMENT_FILE="$STATE_DIR/hooks.v1.json"
MANIFEST_TARGET_FILE="$STATE_DIR/manifest.json"
HOOKS_TARGET_ABS="$PROJECT_ROOT/$HOOKS_TARGET_REL"

detect_code_change_extensions() {
    if command -v python3 >/dev/null 2>&1 && [ -f "$SCAFFOLD_ROOT/scripts/detect_code_extensions.py" ]; then
        python3 "$SCAFFOLD_ROOT/scripts/detect_code_extensions.py" \
            --project "$PROJECT_ROOT" \
            --hooks-root "$MANAGED_ROOT_REL" 2>/dev/null \
            || printf '["js","jsx","ts","tsx","py","go","rs","java","php","rb","cs","sh"]\n'
    else
        printf '["js","jsx","ts","tsx","py","go","rs","java","php","rb","cs","sh"]\n'
    fi
}

CODE_CHANGE_EXTENSIONS_JSON="$(detect_code_change_extensions)"

UNKNOWN_EVENTS="$(
    jq -n \
        --slurpfile manifest "$MANIFEST_SOURCE" \
        --slurpfile plan "$PLAN_FILE" '
        ($manifest[0].events | map(.name)) as $known
        | ($plan[0].enabled_events // [])
        | map(select(.name as $event_name | (($known | index($event_name)) | not)) | .name)
        | .[]
        '
)"

if [ -n "$UNKNOWN_EVENTS" ]; then
    echo "Plan file contains unknown event names:" >&2
    printf '  - %s\n' $UNKNOWN_EVENTS >&2
    exit 1
fi

DUPLICATE_EVENTS="$(
    jq -r '.enabled_events[]?.name' "$PLAN_FILE" | LC_ALL=C sort | uniq -d
)"
if [ -n "$DUPLICATE_EVENTS" ]; then
    echo "Plan file contains duplicate enabled event names:" >&2
    printf '  - %s\n' $DUPLICATE_EVENTS >&2
    exit 1
fi

INVALID_COMMAND_EVENTS="$(
    jq -r '
        .enabled_events[]?
        | .name as $event_name
        | (.commands // [])[]?
        | (.command // null) as $command
        | select(if ($command | type) == "string" then ($command | length) == 0 else true end)
        | $event_name
    ' "$PLAN_FILE" | LC_ALL=C sort -u
)"
if [ -n "$INVALID_COMMAND_EVENTS" ]; then
    echo "Plan file contains command entries without a non-empty command string:" >&2
    printf '  - %s\n' $INVALID_COMMAND_EVENTS >&2
    exit 1
fi

INVALID_SCRIPT_EVENTS="$(
    jq -r '
        .enabled_events[]?
        | .name as $event_name
        | (.scripts // [])[]?
        | (.path // .script // null) as $script_path
        | select(if ($script_path | type) == "string" then ($script_path | length) == 0 else true end)
        | $event_name
    ' "$PLAN_FILE" | LC_ALL=C sort -u
)"
if [ -n "$INVALID_SCRIPT_EVENTS" ]; then
    echo "Plan file contains script entries without a non-empty path string:" >&2
    printf '  - %s\n' $INVALID_SCRIPT_EVENTS >&2
    exit 1
fi

if [ "$DRY_RUN" = "true" ]; then
    cat <<EOF
scaffold_hooks.sh dry run
  project root:  $PROJECT_ROOT
  plan file:     $PLAN_FILE
  mode:          $MODE
  hooks target:  $HOOKS_TARGET_REL
  hook root:     $MANAGED_ROOT_REL
EOF
    exit 0
fi

if ! MANIFEST_ROWS="$(
    jq -er '.events[] | [.name, .script_name, .description, .blocking_guidance] | @tsv' \
        "$MANIFEST_SOURCE"
)"; then
    echo "Failed to read complete Devin hook manifest rows." >&2
    exit 1
fi

mkdir -p "$PROJECT_ROOT/.devin" "$MANAGED_ROOT_ABS" "$LIB_DIR" "$STATE_DIR"

if [ "$MODE" = "overhaul" ]; then
    rm -rf "$STATE_DIR"
    find "$MANAGED_ROOT_ABS" -mindepth 2 -maxdepth 2 \( -name 'devin.sh' -o -name 'devin.json' \) -delete 2>/dev/null || true
    mkdir -p "$STATE_DIR"
fi

write_runtime_lib
write_devin_lib

while IFS=$'\t' read -r event_name script_name description blocking_guidance; do
    event_dir="$(event_dir_name "$script_name")"
    EVENT_DIR="$MANAGED_ROOT_ABS/$event_dir"
    TARGET_SCRIPT="$EVENT_DIR/script.sh"
    ADAPTER_SCRIPT="$EVENT_DIR/devin.sh"
    ADAPTER_CONFIG="$EVENT_DIR/devin.json"
    mkdir -p "$EVENT_DIR"

    if [ "$MODE" = "additive" ] && [ -f "$TARGET_SCRIPT" ]; then
        chmod +x "$TARGET_SCRIPT"
    else
        sed \
            -e "s|{{SCRIPT_NAME}}|script.sh|g" \
            -e "s|{{EVENT_NAME}}|$(escape_for_sed "$event_name")|g" \
            -e "s|{{EVENT_DESCRIPTION}}|$(escape_for_sed "$description")|g" \
            -e "s|{{BLOCKING_GUIDANCE}}|$(escape_for_sed "$blocking_guidance")|g" \
            "$EVENT_TEMPLATE" > "$TARGET_SCRIPT"

        chmod +x "$TARGET_SCRIPT"
    fi

    event_commands_json="$(
        jq -c --arg name "$event_name" '
            [
                .enabled_events[]?
                | select(.name == $name)
                | (.commands // [])[]?
                | {
                    label: (.label // .name // .command),
                    command: .command,
                    cwd: (.cwd // "."),
                    notes: (.notes // "")
                }
            ]
        ' "$PLAN_FILE"
    )"
    event_scripts_json="$(
        jq -c --arg name "$event_name" '
            [
                .enabled_events[]?
                | select(.name == $name)
                | (.scripts // [])[]?
                | {
                    label: (.label // .name // .path // .script),
                    path: (.path // .script),
                    args: (.args // []),
                    cwd: (.cwd // "."),
                    notes: (.notes // "")
                }
            ]
        ' "$PLAN_FILE"
    )"
    block_on_failure="$(
        jq -r --arg name "$event_name" '
            .enabled_events[]?
            | select(.name == $name)
            | (.block_on_failure // false | tostring)
        ' "$PLAN_FILE" | head -n 1
    )"
    [ -n "$block_on_failure" ] || block_on_failure="false"
    run_on_code_changes="$(
        jq -r --arg name "$event_name" '
            ([.enabled_events[]? | select(.name == $name)][0] // {}) as $event
            | ($event.run_on_code_changes // (if $name == "Stop" then true else false end) | tostring)
        ' "$PLAN_FILE"
    )"
    code_change_extensions_json="$(
        jq -c --arg name "$event_name" --argjson detected "$CODE_CHANGE_EXTENSIONS_JSON" '
            ([.enabled_events[]? | select(.name == $name)][0] // {}) as $event
            | ($event.code_change_extensions // .code_change_extensions // $detected)
        ' "$PLAN_FILE"
    )"

    write_adapter_script "devin" "$event_name" "$ADAPTER_SCRIPT"
    jq -n \
        --arg harness "devin" \
        --arg event "$event_name" \
        --argjson scripts "$event_scripts_json" \
        --argjson commands "$event_commands_json" \
        --argjson block_on_failure "$block_on_failure" \
        --argjson run_on_code_changes "$run_on_code_changes" \
        --argjson code_change_extensions "$code_change_extensions_json" \
        '{
            harness: $harness,
            event: $event,
            scripts: $scripts,
            commands: $commands,
            block_on_failure: $block_on_failure,
            run_on_code_changes: $run_on_code_changes,
            code_change_extensions: $code_change_extensions
        }' > "$ADAPTER_CONFIG"
done <<< "$MANIFEST_ROWS"

jq \
    --arg generated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg managed_root "$MANAGED_ROOT_REL" \
    --arg hooks_target "$HOOKS_TARGET_REL" \
    --arg mode "$MODE" \
    --slurpfile plan "$PLAN_FILE" \
    '
    . + {
        generated_at: $generated_at,
        hook_root: $managed_root,
        hooks_target: $hooks_target,
        mode: $mode,
        enabled_events: ($plan[0].enabled_events // [])
    }
    ' "$MANIFEST_SOURCE" > "$MANIFEST_TARGET_FILE"

jq \
    --slurpfile manifest "$MANIFEST_SOURCE" \
    --slurpfile plan "$PLAN_FILE" \
    --arg managed_root "$MANAGED_ROOT_REL" \
    '
    def event_dir($script_name): ($script_name | sub("\\.sh$"; "") | gsub("_"; "-"));
    ($manifest[0].events | map({(.name): .}) | add) as $event_map
    | ($plan[0].enabled_events // []) as $enabled
    | reduce $enabled[] as $item ({};
        ($event_map[$item.name]) as $event
        | .[$item.name] = (
            (.[$item.name] // [])
            + [
                (
                    {
                        hooks: [
                            (
                                {
                                    type: "command",
                                    command: ("bash \"$DEVIN_PROJECT_DIR/" + $managed_root + "/" + event_dir($event.script_name) + "/devin.sh\"")
                                }
                                + (if ($item | has("timeout")) then {timeout: $item.timeout} else {} end)
                            )
                        ]
                    }
                    + (if ($item | has("matcher")) then {matcher: ($item.matcher // "")} else {} end)
                )
            ]
        )
    )
    ' "$MANIFEST_SOURCE" > "$HOOKS_FRAGMENT_FILE"

"$SCRIPT_DIR/merge_hooks_file.sh" \
    --hooks-file "$HOOKS_TARGET_ABS" \
    --fragment-file "$HOOKS_FRAGMENT_FILE" \
    --managed-root "$MANAGED_ROOT_REL/" \
    --managed-suffix "/devin.sh"

"$SCRIPT_DIR/render_hooks_readme.sh" \
    --project "$PROJECT_ROOT" \
    --plan "$PLAN_FILE"

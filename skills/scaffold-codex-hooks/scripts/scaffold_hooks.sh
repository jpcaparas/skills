#!/usr/bin/env bash
#
# scaffold_hooks.sh
#
# Render or refresh a managed Codex hook scaffold in a target project.
#

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  scaffold_hooks.sh --project DIR --plan FILE [--mode additive|overhaul] [--ensure-feature project|user|off] [--home DIR] [--dry-run]
EOF
}

require_command() {
    local name="$1"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "Required command is missing: $name" >&2
        exit 1
    fi
}

escape_for_sed() {
    printf '%s' "$1" | sed -e 's/[&|\\]/\\&/g'
}

assert_live_git_root_substitution() {
    local command="$1"

    case "$command" in
        *'\$(git rev-parse --show-toplevel)'*)
            echo "Managed hook command escaped \$(git rev-parse --show-toplevel): $command" >&2
            exit 1
            ;;
    esac
}

build_hook_command() {
    local event_dir="$1"
    if [ "$IS_GIT_REPO" = "true" ]; then
        # Keep the command substitution live for hook execution time.
        printf "/usr/bin/env bash -lc 'exec \"\$(git rev-parse --show-toplevel)/%s/%s/codex.sh\"'\n" \
            "$MANAGED_ROOT_REL" "$event_dir"
    else
        printf "/usr/bin/env bash -lc 'exec \"%s/%s/codex.sh\"'\n" \
            "$MANAGED_ROOT_ABS" "$event_dir"
    fi
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

exec "\$SCRIPT_DIR/script.sh" "\$@"
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
    local cwd
    local resolved_script
    local -a script_args=()

    cwd="$(resolve_command_cwd "${4:-.}")"
    case "$script_path" in
        /*) resolved_script="$script_path" ;;
        *) resolved_script="$(hook_project_root)/$script_path" ;;
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
        (cd "$cwd" && /usr/bin/env bash "$resolved_script" "${script_args[@]}")
    else
        (cd "$cwd" && /usr/bin/env bash "$resolved_script")
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
EOF
    chmod +x "$LIB_DIR/agent-hook-runtime.sh"
}

write_codex_lib() {
    cat > "$LIB_DIR/codex.sh" <<'EOF'
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
EOF
    chmod +x "$LIB_DIR/codex.sh"
}

PROJECT_ROOT=""
PLAN_FILE=""
MODE_OVERRIDE=""
ENSURE_FEATURE_OVERRIDE=""
HOME_OVERRIDE=""
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
        --ensure-feature)
            ENSURE_FEATURE_OVERRIDE="$2"
            shift 2
            ;;
        --home)
            HOME_OVERRIDE="$2"
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
require_command git
require_command python3

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
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

MODE="$(jq -r '.mode // "additive"' "$PLAN_FILE")"
if [ -n "$MODE_OVERRIDE" ]; then
    MODE="$MODE_OVERRIDE"
fi
case "$MODE" in
    additive|overhaul) ;;
    *)
        echo "Mode must be additive or overhaul. Got: $MODE" >&2
        exit 1
        ;;
esac

ENSURE_FEATURE="$(jq -r '.feature_scope // "project"' "$PLAN_FILE")"
if [ -n "$ENSURE_FEATURE_OVERRIDE" ]; then
    ENSURE_FEATURE="$ENSURE_FEATURE_OVERRIDE"
fi
case "$ENSURE_FEATURE" in
    project|user|off) ;;
    *)
        echo "Feature scope must be project, user, or off. Got: $ENSURE_FEATURE" >&2
        exit 1
        ;;
esac

HOOKS_TARGET_REL="$(jq -r '.hooks_target // ".codex/hooks.json"' "$PLAN_FILE")"
MANAGED_ROOT_REL="$(jq -r '.managed_root // "hooks"' "$PLAN_FILE")"
MANAGED_ROOT_ABS="$PROJECT_ROOT/$MANAGED_ROOT_REL"
HOOKS_TARGET_ABS="$PROJECT_ROOT/$HOOKS_TARGET_REL"
LIB_DIR="$MANAGED_ROOT_ABS/lib"
STATE_DIR="$MANAGED_ROOT_ABS/.state/codex"
FRAGMENT_FILE="$STATE_DIR/hooks.json"
MANIFEST_TARGET_FILE="$STATE_DIR/manifest.json"

IS_GIT_REPO="false"
if git -C "$PROJECT_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
    IS_GIT_REPO="true"
fi

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

run_check_hooks_feature() {
    if [ -n "$HOME_OVERRIDE" ]; then
        python3 "$SCRIPT_DIR/check_hooks_feature.py" \
            --project "$PROJECT_ROOT" \
            --home "$HOME_OVERRIDE" \
            "$@"
    else
        python3 "$SCRIPT_DIR/check_hooks_feature.py" \
            --project "$PROJECT_ROOT" \
            "$@"
    fi
}

FEATURE_STATUS_JSON="$(
    run_check_hooks_feature --json 2>/dev/null || printf '{}\n'
)"
FEATURE_EFFECTIVE="$(printf '%s' "$FEATURE_STATUS_JSON" | jq -r '.effective // "unknown"')"
TEMP_FEATURE_STATUS="$(mktemp)"
TEMP_GROUPS_DIR=""
cleanup() {
    rm -f "$TEMP_FEATURE_STATUS"
    if [ -n "$TEMP_GROUPS_DIR" ] && [ -d "$TEMP_GROUPS_DIR" ]; then
        rm -rf "$TEMP_GROUPS_DIR"
    fi
}
trap cleanup EXIT
printf '%s\n' "$FEATURE_STATUS_JSON" > "$TEMP_FEATURE_STATUS"

if [ "$DRY_RUN" = "true" ]; then
    cat <<EOF
scaffold_hooks.sh dry run
  project root:    $PROJECT_ROOT
  plan file:       $PLAN_FILE
  mode:            $MODE
  hooks target:    $HOOKS_TARGET_REL
  hook root:       $MANAGED_ROOT_REL
  ensure feature:  $ENSURE_FEATURE
  feature active:  $FEATURE_EFFECTIVE
EOF
    if [ "$ENSURE_FEATURE" != "off" ] && [ "$FEATURE_EFFECTIVE" != "true" ]; then
        printf '  note: would enable hooks in %s scope\n' "$ENSURE_FEATURE"
    fi
    exit 0
fi

if [ "$ENSURE_FEATURE" != "off" ] && [ "$FEATURE_EFFECTIVE" != "true" ]; then
    run_check_hooks_feature \
        --enable \
        --scope "$ENSURE_FEATURE" \
        --json >/dev/null
    FEATURE_STATUS_JSON="$(
        run_check_hooks_feature --json 2>/dev/null || printf '{}\n'
    )"
    printf '%s\n' "$FEATURE_STATUS_JSON" > "$TEMP_FEATURE_STATUS"
fi

mkdir -p "$PROJECT_ROOT/.codex" "$MANAGED_ROOT_ABS" "$LIB_DIR" "$STATE_DIR"

if [ "$MODE" = "overhaul" ]; then
    rm -rf "$STATE_DIR"
    find "$MANAGED_ROOT_ABS" -mindepth 2 -maxdepth 2 \( -name 'codex.sh' -o -name 'codex.json' \) -delete 2>/dev/null || true
    mkdir -p "$STATE_DIR"
fi

write_runtime_lib
write_codex_lib

while IFS=$'\t' read -r event_name script_name description matcher_guidance output_guidance blocking_guidance; do
    event_dir="$(event_dir_name "$script_name")"
    event_dir_abs="$MANAGED_ROOT_ABS/$event_dir"
    target_script="$event_dir_abs/script.sh"
    adapter_script="$event_dir_abs/codex.sh"
    adapter_config="$event_dir_abs/codex.json"
    mkdir -p "$event_dir_abs"

    if [ "$MODE" = "additive" ] && [ -f "$target_script" ]; then
        chmod +x "$target_script"
    else
        sed \
            -e "s|{{SCRIPT_NAME}}|script.sh|g" \
            -e "s|{{EVENT_NAME}}|$(escape_for_sed "$event_name")|g" \
            -e "s|{{EVENT_DESCRIPTION}}|$(escape_for_sed "$description")|g" \
            -e "s|{{MATCHER_GUIDANCE}}|$(escape_for_sed "$matcher_guidance")|g" \
            -e "s|{{OUTPUT_GUIDANCE}}|$(escape_for_sed "$output_guidance")|g" \
            -e "s|{{BLOCKING_GUIDANCE}}|$(escape_for_sed "$blocking_guidance")|g" \
            "$EVENT_TEMPLATE" > "$target_script"

        chmod +x "$target_script"
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
    write_adapter_script "codex" "$event_name" "$adapter_script"
    jq -n \
        --arg harness "codex" \
        --arg event "$event_name" \
        --argjson scripts "$event_scripts_json" \
        --argjson commands "$event_commands_json" \
        '{
            harness: $harness,
            event: $event,
            scripts: $scripts,
            commands: $commands
        }' > "$adapter_config"
done < <(
    jq -r '.events[] | [.name, .script_name, .description, .matcher_guidance, .output_guidance, .blocking_guidance] | @tsv' \
        "$MANIFEST_SOURCE"
)

jq \
    --arg generated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg managed_root "$MANAGED_ROOT_REL" \
    --arg hooks_target "$HOOKS_TARGET_REL" \
    --arg mode "$MODE" \
    --arg feature_scope "$ENSURE_FEATURE" \
    --slurpfile feature_status "$TEMP_FEATURE_STATUS" \
    --slurpfile plan "$PLAN_FILE" \
    '
    . + {
        generated_at: $generated_at,
        hook_root: $managed_root,
        hooks_target: $hooks_target,
        mode: $mode,
        feature_scope: $feature_scope,
        feature_status: ($feature_status[0] // {}),
        enabled_events: ($plan[0].enabled_events // [])
    }
    ' "$MANIFEST_SOURCE" > "$MANIFEST_TARGET_FILE"

TEMP_GROUPS_DIR="$(mktemp -d)"

while IFS= read -r row; do
    event_name="$(printf '%s' "$row" | jq -r '.name')"
    script_name="$(printf '%s' "$row" | jq -r '.script_name')"
    event_dir="$(event_dir_name "$script_name")"
    matcher_supported="$(printf '%s' "$row" | jq -r '.matcher_supported')"
    matcher="$(printf '%s' "$row" | jq -r '.matcher')"
    timeout="$(printf '%s' "$row" | jq -r '.timeout')"
    status_message="$(printf '%s' "$row" | jq -r '.status_message')"
    command="$(build_hook_command "$event_dir")"
    assert_live_git_root_substitution "$command"
    effective_matcher="$matcher"
    if [ "$matcher_supported" != "true" ]; then
        effective_matcher=""
    fi
    jq -n \
        --arg event_name "$event_name" \
        --arg matcher "$effective_matcher" \
        --arg command "$command" \
        --arg status_message "$status_message" \
        --arg timeout "$timeout" \
        '
        {
            ($event_name): [
                ({
                    hooks: [
                        ({
                            type: "command",
                            command: $command,
                            timeout: ($timeout | tonumber)
                        } + (if $status_message == "" then {} else {statusMessage: $status_message} end))
                    ]
                } + (if $matcher == "" then {} else {matcher: $matcher} end))
            ]
        }
        ' > "$TEMP_GROUPS_DIR/$event_name.json"
done < <(
    jq -c -n \
        --slurpfile manifest "$MANIFEST_SOURCE" \
        --slurpfile plan "$PLAN_FILE" '
        ($manifest[0].events | map({(.name): .}) | add) as $event_map
        | ($plan[0].enabled_events // [])
        | .[]
        | ($event_map[.name]) as $event
        | {
            name: .name,
            script_name: $event.script_name,
            matcher_supported: $event.matcher_supported,
            matcher: (.matcher // ""),
            timeout: (.timeout // 600),
            status_message: (.status_message // "")
          }
        '
)

if compgen -G "$TEMP_GROUPS_DIR/*.json" >/dev/null; then
    jq -s '
        {
            hooks: (
                reduce .[] as $item ({};
                    reduce ($item | to_entries[]) as $entry (.;
                        .[$entry.key] = ((.[$entry.key] // []) + $entry.value)
                    )
                )
            )
        }
    ' "$TEMP_GROUPS_DIR"/*.json > "$FRAGMENT_FILE"
else
    printf '{ "hooks": {} }\n' > "$FRAGMENT_FILE"
fi

bash "$SCRIPT_DIR/merge_hooks_json.sh" \
    --hooks-file "$HOOKS_TARGET_ABS" \
    --fragment-file "$FRAGMENT_FILE" \
    --managed-root "$MANAGED_ROOT_REL/" \
    --managed-suffix "/codex.sh"

bash "$SCRIPT_DIR/render_hooks_readme.sh" \
    --project "$PROJECT_ROOT" \
    --plan "$PLAN_FILE"

cat <<EOF
scaffold_hooks.sh complete
  project root:    $PROJECT_ROOT
  hooks target:    $HOOKS_TARGET_REL
  hook root:       $MANAGED_ROOT_REL
  mode:            $MODE
  ensure feature:  $ENSURE_FEATURE
EOF

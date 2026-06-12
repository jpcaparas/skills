#!/usr/bin/env bash
#
# scaffold_hooks.sh
#
# Render or refresh a managed GitHub Copilot hook scaffold in a target project.

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

escape_for_sed() {
    printf '%s' "$1" | sed -e 's/[&|\\]/\\&/g'
}

escape_for_single_quotes() {
    printf '%s' "$1" | sed "s/'/'\\\\''/g"
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
    additive|overhaul)
        ;;
    *)
        echo "Mode must be additive or overhaul. Got: $MODE" >&2
        exit 1
        ;;
esac

HOOKS_TARGET_REL="$(jq -r '.hooks_target // ".github/hooks/copilot-hooks.json"' "$PLAN_FILE")"
MANAGED_ROOT_REL="$(jq -r '.managed_root // ".github/copilot/hooks/generated"' "$PLAN_FILE")"

case "$HOOKS_TARGET_REL" in
    .github/hooks/*.json)
        ;;
    *)
        echo "Repository hook target must stay under .github/hooks/*.json. Got: $HOOKS_TARGET_REL" >&2
        exit 1
        ;;
esac

case "$MANAGED_ROOT_REL" in
    .github/copilot/hooks/generated|.github/copilot/hooks/generated/*)
        ;;
    *)
        echo "Managed root must stay under .github/copilot/hooks/generated. Got: $MANAGED_ROOT_REL" >&2
        exit 1
        ;;
esac

MANAGED_ROOT_ABS="$PROJECT_ROOT/$MANAGED_ROOT_REL"
EVENTS_DIR="$MANAGED_ROOT_ABS/events"
LIB_DIR="$MANAGED_ROOT_ABS/lib"
HOOKS_FRAGMENT_FILE="$MANAGED_ROOT_ABS/hooks.generated.json"
MANIFEST_TARGET_FILE="$MANAGED_ROOT_ABS/manifest.json"
HOOKS_TARGET_ABS="$PROJECT_ROOT/$HOOKS_TARGET_REL"

UNKNOWN_EVENTS="$(
    jq -n \
        --slurpfile manifest "$MANIFEST_SOURCE" \
        --slurpfile plan "$PLAN_FILE" '
        ($manifest[0].events | map([.name] + (.aliases // [])) | add) as $known
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
  managed root:  $MANAGED_ROOT_REL
EOF
    exit 0
fi

mkdir -p "$PROJECT_ROOT/.github/hooks" "$PROJECT_ROOT/.github/copilot/hooks"

if [ "$MODE" = "overhaul" ] && [ -d "$MANAGED_ROOT_ABS" ]; then
    BACKUP_PATH="${MANAGED_ROOT_ABS}.bak.$(date +%Y%m%d%H%M%S)"
    mv "$MANAGED_ROOT_ABS" "$BACKUP_PATH"
fi

mkdir -p "$EVENTS_DIR" "$LIB_DIR"

cat > "$LIB_DIR/common.sh" <<'EOF'
#!/usr/bin/env bash
#
# common.sh
#
# Shared helper functions for generated GitHub Copilot hook scripts.

set -euo pipefail

require_jq() {
    if ! command -v jq >/dev/null 2>&1; then
        echo "jq is required by generated Copilot hook helpers." >&2
        return 1
    fi
}

read_hook_input() {
    cat
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

hook_tool_name() {
    hook_json '.toolName // .tool_name // ""' ""
}

hook_event_name() {
    hook_json '.hook_event_name // ""' ""
}

write_json() {
    require_jq
    jq -nc "$@"
}

deny_pre_tool_use() {
    local reason="$1"
    write_json --arg reason "$reason" '{permissionDecision:"deny", permissionDecisionReason:$reason}'
}

deny_permission_request() {
    local reason="$1"
    write_json --arg message "$reason" '{behavior:"deny", message:$message}'
}

block_agent_stop() {
    local reason="$1"
    write_json --arg reason "$reason" '{decision:"block", reason:$reason}'
}

add_context() {
    local message="$1"
    write_json --arg additionalContext "$message" '{additionalContext:$additionalContext}'
}

copilot_project_root() {
    if [ -n "${GITHUB_WORKSPACE:-}" ] && [ -d "$GITHUB_WORKSPACE" ]; then
        printf '%s\n' "$GITHUB_WORKSPACE"
        return 0
    fi

    local payload_cwd
    payload_cwd="$(hook_json '.cwd // empty' "" 2>/dev/null || true)"
    if [ -n "$payload_cwd" ] && [ -d "$payload_cwd" ]; then
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
        ""|".")
            copilot_project_root
            ;;
        /*)
            printf '%s\n' "$requested_cwd"
            ;;
        *)
            printf '%s/%s\n' "$(copilot_project_root)" "$requested_cwd"
            ;;
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

    printf '[copilot-hook] %s\n' "$label" >&2
    printf '[copilot-hook] cwd: %s\n' "$cwd" >&2
    printf '[copilot-hook] command: %s\n' "$command" >&2

    (
        cd "$cwd"
        /usr/bin/env bash -lc "$command"
    )
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
        /*)
            resolved_script="$script_path"
            ;;
        *)
            resolved_script="$(copilot_project_root)/$script_path"
            ;;
    esac

    require_jq
    while IFS= read -r script_arg; do
        script_args+=("$script_arg")
    done < <(printf '%s' "$args_json" | jq -r '.[]?')

    if [ ! -f "$resolved_script" ]; then
        printf '[copilot-hook] missing script: %s\n' "$resolved_script" >&2
        return 127
    fi

    printf '[copilot-hook] %s\n' "$label" >&2
    printf '[copilot-hook] cwd: %s\n' "$cwd" >&2
    printf '[copilot-hook] script: %s\n' "$resolved_script" >&2

    if [ "${#script_args[@]}" -gt 0 ]; then
        (
            cd "$cwd"
            /usr/bin/env bash "$resolved_script" "${script_args[@]}"
        )
    else
        (
            cd "$cwd"
            /usr/bin/env bash "$resolved_script"
        )
    fi
}

run_configured_scripts() {
    local scripts_json="$1"
    local failed="false"

    require_jq

    if [ "$(printf '%s' "$scripts_json" | jq 'length')" -eq 0 ]; then
        return 0
    fi

    while IFS= read -r script_item; do
        local label
        local script_path
        local script_args_json
        local cwd
        local status

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

    if [ "$(printf '%s' "$commands_json" | jq 'length')" -eq 0 ]; then
        return 0
    fi

    while IFS= read -r command_item; do
        local label
        local command
        local cwd
        local status

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

handle_configured_failure() {
    local event_name="$1"
    local block_on_failure="$2"
    local message="$3"

    if [ "$block_on_failure" != "true" ]; then
        printf '[copilot-hook] %s configured command failed but block_on_failure=false.\n' "$event_name" >&2
        printf '%s\n' "$message" >&2
        if [ "$event_name" = "preToolUse" ]; then
            printf '[copilot-hook] swallowing non-blocking preToolUse failure because command hooks are fail-closed.\n' >&2
            return 0
        fi
        return 1
    fi

    case "$event_name" in
        preToolUse)
            deny_pre_tool_use "$message"
            return 0
            ;;
        permissionRequest)
            deny_permission_request "$message"
            return 2
            ;;
        agentStop|subagentStop)
            block_agent_stop "$message"
            return 0
            ;;
        postToolUseFailure)
            add_context "$message"
            return 2
            ;;
        *)
            printf '%s\n' "$message" >&2
            return 1
            ;;
    esac
}
EOF
chmod +x "$LIB_DIR/common.sh"

while IFS=$'\t' read -r event_name script_name description; do
    TARGET_SCRIPT="$EVENTS_DIR/$script_name"

    if [ "$MODE" = "additive" ] && [ -f "$TARGET_SCRIPT" ]; then
        chmod +x "$TARGET_SCRIPT"
        continue
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

    sed \
        -e "s|{{SCRIPT_NAME}}|$(escape_for_sed "$script_name")|g" \
        -e "s|{{EVENT_NAME}}|$(escape_for_sed "$event_name")|g" \
        -e "s|{{EVENT_DESCRIPTION}}|$(escape_for_sed "$description")|g" \
        -e "s|{{BLOCK_ON_FAILURE}}|$(escape_for_sed "$block_on_failure")|g" \
        -e "s|{{PROJECT_SCRIPTS_JSON}}|$(escape_for_sed "$(escape_for_single_quotes "$event_scripts_json")")|g" \
        -e "s|{{PROJECT_COMMANDS_JSON}}|$(escape_for_sed "$(escape_for_single_quotes "$event_commands_json")")|g" \
        "$EVENT_TEMPLATE" > "$TARGET_SCRIPT"

    chmod +x "$TARGET_SCRIPT"
done < <(jq -r '.events[] | [.name, .script_name, .description] | @tsv' "$MANIFEST_SOURCE")

jq \
    --arg generated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg managed_root "$MANAGED_ROOT_REL" \
    --arg hooks_target "$HOOKS_TARGET_REL" \
    --arg mode "$MODE" \
    --slurpfile plan "$PLAN_FILE" \
    '
    . + {
        generated_at: $generated_at,
        managed_root: $managed_root,
        hooks_target: $hooks_target,
        mode: $mode,
        enabled_events: ($plan[0].enabled_events // [])
    }
    ' "$MANIFEST_SOURCE" > "$MANIFEST_TARGET_FILE"

jq -n \
    --slurpfile manifest "$MANIFEST_SOURCE" \
    --slurpfile plan "$PLAN_FILE" \
    --arg managed_root "$MANAGED_ROOT_REL" \
    '
    ($manifest[0].events
        | map(. as $event | ([.name] + (.aliases // []) | map({key: ., value: $event}))[])
        | from_entries) as $event_map
    | ($plan[0].enabled_events // []) as $enabled
    | reduce $enabled[] as $item ({version: 1, hooks: {}};
        ($event_map[$item.name]) as $event
        | .hooks[$item.name] = (
            (.hooks[$item.name] // [])
            + [
                (
                    {
                        type: "command",
                        bash: ("bash \"" + $managed_root + "/events/" + $event.script_name + "\""),
                        command: ("bash \"" + $managed_root + "/events/" + $event.script_name + "\""),
                        cwd: "."
                    }
                    + (if ($item | has("timeoutSec")) then {timeoutSec: $item.timeoutSec} elif ($item | has("timeout")) then {timeoutSec: $item.timeout} else {} end)
                    + (if ($item | has("matcher")) then {matcher: ($item.matcher // "")} else {} end)
                    + (if ($item | has("env")) then {env: ($item.env // {})} else {} end)
                )
            ]
        )
    )
    ' > "$HOOKS_FRAGMENT_FILE"

"$SCRIPT_DIR/merge_hooks_file.sh" \
    --hooks-file "$HOOKS_TARGET_ABS" \
    --fragment-file "$HOOKS_FRAGMENT_FILE" \
    --managed-root "$MANAGED_ROOT_REL"

"$SCRIPT_DIR/render_hooks_readme.sh" \
    --project "$PROJECT_ROOT" \
    --plan "$PLAN_FILE"

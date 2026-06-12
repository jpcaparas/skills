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
    (cd "$cwd" && /usr/bin/env bash "$resolved_script" "${script_args[@]}")
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

    write_adapter_script "devin" "$event_name" "$ADAPTER_SCRIPT"
    jq -n \
        --arg harness "devin" \
        --arg event "$event_name" \
        --argjson scripts "$event_scripts_json" \
        --argjson commands "$event_commands_json" \
        --argjson block_on_failure "$block_on_failure" \
        '{
            harness: $harness,
            event: $event,
            scripts: $scripts,
            commands: $commands,
            block_on_failure: $block_on_failure
        }' > "$ADAPTER_CONFIG"
done < <(jq -r '.events[] | [.name, .script_name, .description, .blocking_guidance] | @tsv' "$MANIFEST_SOURCE")

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

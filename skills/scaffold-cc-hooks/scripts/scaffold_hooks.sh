#!/usr/bin/env bash
#
# scaffold_hooks.sh
#
# Render or refresh a managed Claude Code hook scaffold in a target project.
#
# This script is deterministic by design:
# - it always creates one managed bash stub per official hook event
# - it only enables the events listed in the provided plan JSON
# - it only replaces previously managed hook handlers in the chosen settings file
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

SETTINGS_TARGET_REL="$(jq -r '.settings_target // ".claude/settings.json"' "$PLAN_FILE")"
MANAGED_ROOT_REL="$(jq -r '.managed_root // ".claude/hooks/generated"' "$PLAN_FILE")"
MANAGED_ROOT_ABS="$PROJECT_ROOT/$MANAGED_ROOT_REL"
EVENTS_DIR="$MANAGED_ROOT_ABS/events"
LIB_DIR="$MANAGED_ROOT_ABS/lib"
SETTINGS_FRAGMENT_FILE="$MANAGED_ROOT_ABS/settings.generated.json"
MANIFEST_TARGET_FILE="$MANAGED_ROOT_ABS/manifest.json"
SETTINGS_TARGET_ABS="$PROJECT_ROOT/$SETTINGS_TARGET_REL"

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

if [ "$DRY_RUN" = "true" ]; then
    cat <<EOF
scaffold_hooks.sh dry run
  project root:    $PROJECT_ROOT
  plan file:       $PLAN_FILE
  mode:            $MODE
  settings target: $SETTINGS_TARGET_REL
  managed root:    $MANAGED_ROOT_REL
EOF
    exit 0
fi

mkdir -p "$PROJECT_ROOT/.claude/hooks"

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
# Shared helper functions for generated Claude Code hook scripts.
#
# Keep this file small and explicit. Event scripts should be easy to read on
# their own; this file only holds repeated input, JSON, and output helpers.
#

set -euo pipefail

require_jq() {
    # Hook output helpers build JSON with jq so quoting stays correct.
    # Fail with a clear message instead of returning malformed JSON.
    if ! command -v jq >/dev/null 2>&1; then
        echo "jq is required by generated Claude Code hook helpers." >&2
        return 1
    fi
}

read_hook_input() {
    # Claude Code passes one JSON object to command hooks on stdin.
    # Read the whole payload once; event scripts store it in HOOK_INPUT.
    cat
}

hook_json() {
    # Read one value from HOOK_INPUT with jq.
    #
    # Arguments:
    #   $1 - jq filter, for example '.cwd'
    #   $2 - optional fallback printed when the filter is missing or null
    #
    # Examples:
    #   hook_json '.cwd' "$CLAUDE_PROJECT_DIR"
    #   hook_json '.tool.name'
    local filter="$1"
    require_jq

    if [ "$#" -ge 2 ]; then
        local fallback="$2"
        printf '%s' "$HOOK_INPUT" | jq -er "$filter" 2>/dev/null || printf '%s\n' "$fallback"
    else
        printf '%s' "$HOOK_INPUT" | jq -er "$filter"
    fi
}

write_system_message() {
    # Emit a systemMessage payload Claude Code can consume on the next turn.
    # Use this only when the hook should add visible guidance.
    local message="$1"
    require_jq
    jq -n --arg message "$message" '{systemMessage: $message}'
}

write_additional_context() {
    # Emit additionalContext text for the next Claude turn.
    # Use this for lightweight context that should not look like user text.
    local message="$1"
    require_jq
    jq -n --arg message "$message" '{additionalContext: $message}'
}

write_block_decision() {
    # Ask Claude Code to continue or block when the current event supports the
    # top-level decision/reason contract. Stop and SubagentStop use this shape
    # to keep the agent working.
    local reason="$1"
    require_jq
    jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
}

stop_processing() {
    # Stop the current hook flow when an event supports continue=false.
    local reason="$1"
    require_jq
    jq -n --arg reason "$reason" '{continue: false, stopReason: $reason}'
}

deny_pre_tool_use() {
    # Deny a PreToolUse event before the tool runs.
    local reason="$1"
    require_jq
    jq -n --arg reason "$reason" \
        '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
}

deny_permission_request() {
    # Deny a PermissionRequest event before the normal permission dialog.
    local message="$1"
    require_jq
    jq -n --arg message "$message" \
        '{hookSpecificOutput: {hookEventName: "PermissionRequest", decision: {behavior: "deny", message: $message}}}'
}

hook_project_root() {
    # Prefer Claude's project root, then the hook payload cwd, then the process
    # cwd. This keeps command execution language-agnostic and repo-local.
    if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
        printf '%s\n' "$CLAUDE_PROJECT_DIR"
        return 0
    fi

    local payload_cwd
    payload_cwd="$(printf '%s' "$HOOK_INPUT" | jq -er '.cwd // empty' 2>/dev/null || true)"
    if [ -n "$payload_cwd" ]; then
        printf '%s\n' "$payload_cwd"
        return 0
    fi

    pwd -P
}

resolve_command_cwd() {
    # Command cwd can be absolute or relative to the project root.
    local requested_cwd="${1:-.}"
    case "$requested_cwd" in
        ""|".")
            hook_project_root
            ;;
        /*)
            printf '%s\n' "$requested_cwd"
            ;;
        *)
            printf '%s/%s\n' "$(hook_project_root)" "$requested_cwd"
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
    # Run an existing repo command exactly as configured in the hook plan.
    # The command string is trusted project configuration, not user input from
    # the hook payload. Keep toolchain-specific details in the plan.
    local label="$1"
    local command="$2"
    local cwd
    cwd="$(resolve_command_cwd "${3:-.}")"

    printf '[hook] %s\n' "$label" >&2
    printf '[hook] cwd: %s\n' "$cwd" >&2
    printf '[hook] command: %s\n' "$command" >&2

    (
        cd "$cwd"
        /usr/bin/env bash -lc "$command"
    )
}

run_configured_commands() {
    # Execute command entries from an event plan:
    #   [{"label":"quality gate","command":"your repo command","cwd":"."}]
    #
    # This is deliberately language-agnostic. It can run package-manager,
    # framework, Make, Just, Taskfile, shell, or custom repo commands.
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

handle_project_command_failure() {
    # Convert failed project commands into the safest output shape for each
    # event. Events that cannot block get a system message or stderr instead.
    local event_name="$1"
    local message="$2"

    case "$event_name" in
        PreToolUse)
            deny_pre_tool_use "$message"
            ;;
        PermissionRequest)
            deny_permission_request "$message"
            ;;
        Stop|SubagentStop|TeammateIdle|TaskCreated|TaskCompleted|PostToolBatch|ConfigChange|Elicitation|ElicitationResult)
            write_block_decision "$message"
            ;;
        PreCompact)
            stop_processing "$message"
            ;;
        PostToolUse|PostToolUseFailure|SessionStart|Setup|Notification|SubagentStart|PostCompact|SessionEnd|CwdChanged|FileChanged|InstructionsLoaded|StopFailure|PermissionDenied|WorktreeRemove)
            write_system_message "$message"
            ;;
        *)
            printf '%s\n' "$message" >&2
            return 1
            ;;
    esac
}
EOF
chmod +x "$LIB_DIR/common.sh"

while IFS=$'\t' read -r event_name script_name description async_guidance; do
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

    sed \
        -e "s|{{SCRIPT_NAME}}|$(escape_for_sed "$script_name")|g" \
        -e "s|{{EVENT_NAME}}|$(escape_for_sed "$event_name")|g" \
        -e "s|{{EVENT_DESCRIPTION}}|$(escape_for_sed "$description")|g" \
        -e "s|{{ASYNC_GUIDANCE}}|$(escape_for_sed "$async_guidance")|g" \
        -e "s|{{PROJECT_COMMANDS_JSON}}|$(escape_for_sed "$event_commands_json")|g" \
        "$EVENT_TEMPLATE" > "$TARGET_SCRIPT"

    chmod +x "$TARGET_SCRIPT"
done < <(jq -r '.events[] | [.name, .script_name, .description, .async_guidance] | @tsv' "$MANIFEST_SOURCE")

jq \
    --arg generated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg managed_root "$MANAGED_ROOT_REL" \
    --arg settings_target "$SETTINGS_TARGET_REL" \
    --arg mode "$MODE" \
    --slurpfile plan "$PLAN_FILE" \
    '
    . + {
        generated_at: $generated_at,
        managed_root: $managed_root,
        settings_target: $settings_target,
        mode: $mode,
        enabled_events: ($plan[0].enabled_events // [])
    }
    ' "$MANIFEST_SOURCE" > "$MANIFEST_TARGET_FILE"

jq \
    --slurpfile manifest "$MANIFEST_SOURCE" \
    --slurpfile plan "$PLAN_FILE" \
    --arg managed_root "$MANAGED_ROOT_REL" \
    '
    ($manifest[0].events | map({(.name): .}) | add) as $event_map
    | ($plan[0].enabled_events // []) as $enabled
    | {
        hooks: (
            reduce $enabled[] as $item ({};
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
                                            command: ("\"$CLAUDE_PROJECT_DIR\"/" + $managed_root + "/events/" + $event.script_name)
                                        }
                                        + (if ($item | has("async")) then {async: $item.async} else {} end)
                                        + (if ($item | has("timeout")) then {timeout: $item.timeout} else {} end)
                                        + (if (($item.if // "") | length) > 0 then {if: $item.if} else {} end)
                                        + (if (($item.shell // "") | length) > 0 then {shell: $item.shell} else {} end)
                                    )
                                ]
                            }
                            + (
                                if ($event.supports_matcher and ($item | has("matcher"))) then
                                    {matcher: ($item.matcher // "")}
                                else
                                    {}
                                end
                            )
                        )
                    ]
                )
            )
        )
    }
    ' "$MANIFEST_SOURCE" > "$SETTINGS_FRAGMENT_FILE"

"$SCRIPT_DIR/merge_settings.sh" \
    --settings-file "$SETTINGS_TARGET_ABS" \
    --fragment-file "$SETTINGS_FRAGMENT_FILE" \
    --managed-root "$MANAGED_ROOT_REL"

"$SCRIPT_DIR/render_hooks_readme.sh" \
    --project "$PROJECT_ROOT" \
    --plan "$PLAN_FILE"

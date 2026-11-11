#!/usr/bin/env bash
#
# scaffold_hooks.sh
#
# Render or refresh a managed Devin CLI hook scaffold in a target project.
#
# This script is deterministic by design:
# - it scaffolds only the plan events that have scripts or commands
# - it removes managed files of events that no longer qualify
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

# Code lines only: comments, blank lines and the event-name default are the parts
# a hand edit or a regenerated header may legitimately change.
generated_code() {
    grep -Ev '^[[:space:]]*(#|$)' "$1" | grep -v 'AGENT_HOOK_EVENT:=' || true
}

# Removes what an earlier scaffold generated for events that no longer have
# behaviour: this harness's adapter, then the shared script.sh once no adapter
# uses it and it is still the untouched generated stub.
prune_stale_events() {
    local dir name
    for dir in "$MANAGED_ROOT_ABS"/*/; do
        [ -d "$dir" ] || continue
        name="$(basename "$dir")"
        case " $KEPT_DIRS " in *" $name "*) continue ;; esac
        [ "$name" != "lib" ] || continue
        if grep -qs 'AGENT_HOOK_HARNESS="devin"' "$dir/devin.sh"; then
            rm -f "$dir/devin.sh" "$dir/devin.json"
        fi
        if [ -z "$(find "$dir" -maxdepth 1 -name '*.sh' ! -name script.sh -print -quit)" ] \
            && [ -f "$dir/script.sh" ] \
            && [ "$(generated_code "$dir/script.sh")" = "$(generated_code "$EVENT_TEMPLATE")" ]; then
            rm -f "$dir/script.sh"
        fi
        rmdir "$dir" 2>/dev/null || true
    done
    if [ -z "$KEPT_DIRS" ]; then
        rm -rf "$STATE_DIR"
        rm -f "$LIB_DIR/devin.sh"
    fi
    if [ -z "$(find "$MANAGED_ROOT_ABS" -mindepth 2 -maxdepth 2 \( -name devin.sh -o -name codex.sh -o -name devin.sh \) -print -quit 2>/dev/null)" ]; then
        rm -f "$LIB_DIR/agent-hook-runtime.sh"
    fi
    rmdir "$LIB_DIR" 2>/dev/null || true
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
    cp "$SCAFFOLD_ROOT/assets/agent-hook-runtime.sh" "$LIB_DIR/agent-hook-runtime.sh"
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
KEPT_DIRS=""

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

source "$SCRIPT_DIR/scaffold_paths.sh"
validate_scaffold_path "$PROJECT_ROOT" "$HOOKS_TARGET_REL" hooks_target
validate_scaffold_path "$PROJECT_ROOT" "$MANAGED_ROOT_REL" managed_root tree

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
  events:        $(jq '[(.enabled_events // [])[] | select(((.scripts // []) + (.commands // [])) | length > 0)] | length' "$PLAN_FILE")
EOF
    exit 0
fi

# An event is scaffolded only when the plan gives it scripts or commands. Every
# later step reads this filtered plan, so a stub is never rendered or wired.
EFFECTIVE_PLAN="$(mktemp)"
EMPTY_FRAGMENT="$(mktemp)"
trap 'rm -f "$EFFECTIVE_PLAN" "$EMPTY_FRAGMENT"' EXIT
jq '.enabled_events = [(.enabled_events // [])[] | select(((.scripts // []) + (.commands // [])) | length > 0)]' \
    "$PLAN_FILE" > "$EFFECTIVE_PLAN"
PLAN_FILE="$EFFECTIVE_PLAN"

if ! MANIFEST_ROWS="$(
    jq -r --slurpfile plan "$PLAN_FILE" '
        ($plan[0].enabled_events | map(.name)) as $enabled
        | .events[]
        | select(.name as $name | $enabled | index($name))
        | [.name, .script_name]
        | @tsv
    ' "$MANIFEST_SOURCE"
)"; then
    echo "Failed to read complete Devin hook manifest rows." >&2
    exit 1
fi

if [ -z "$MANIFEST_ROWS" ]; then
    prune_stale_events
    if [ -f "$HOOKS_TARGET_ABS" ]; then
        printf '{}\n' > "$EMPTY_FRAGMENT"
        "$SCRIPT_DIR/merge_hooks_file.sh" \
            --hooks-file "$HOOKS_TARGET_ABS" \
            --fragment-file "$EMPTY_FRAGMENT" \
            --managed-root "$MANAGED_ROOT_REL/" \
            --managed-suffix "/devin.sh"
    fi
    echo "No plan event has scripts or commands; no Devin hooks were scaffolded." >&2
    exit 0
fi

mkdir -p "$PROJECT_ROOT/.devin" "$MANAGED_ROOT_ABS" "$LIB_DIR" "$STATE_DIR"

write_runtime_lib
write_devin_lib

while IFS=$'\t' read -r event_name script_name; do
    event_dir="$(event_dir_name "$script_name")"
    KEPT_DIRS="$KEPT_DIRS $event_dir"
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

prune_stale_events

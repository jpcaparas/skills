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

build_hook_command() {
    local script_name="$1"
    if [ "$IS_GIT_REPO" = "true" ]; then
        printf "/usr/bin/env bash -lc 'exec \"\\\$(git rev-parse --show-toplevel)/%s/events/%s\"'\n" \
            "$MANAGED_ROOT_REL" "$script_name"
    else
        printf "/usr/bin/env bash -lc 'exec \"%s/events/%s\"'\n" \
            "$MANAGED_ROOT_ABS" "$script_name"
    fi
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
MANAGED_ROOT_REL="$(jq -r '.managed_root // ".codex/hooks/generated"' "$PLAN_FILE")"
MANAGED_ROOT_ABS="$PROJECT_ROOT/$MANAGED_ROOT_REL"
HOOKS_TARGET_ABS="$PROJECT_ROOT/$HOOKS_TARGET_REL"
EVENTS_DIR="$MANAGED_ROOT_ABS/events"
LIB_DIR="$MANAGED_ROOT_ABS/lib"
FRAGMENT_FILE="$MANAGED_ROOT_ABS/hooks.generated.json"
MANIFEST_TARGET_FILE="$MANAGED_ROOT_ABS/manifest.json"

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

FEATURE_ARGS=()
if [ -n "$HOME_OVERRIDE" ]; then
    FEATURE_ARGS+=(--home "$HOME_OVERRIDE")
fi

FEATURE_STATUS_JSON="$(
    python3 "$SCRIPT_DIR/check_hooks_feature.py" \
        --project "$PROJECT_ROOT" \
        --json \
        "${FEATURE_ARGS[@]}" \
        2>/dev/null || printf '{}\n'
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
  managed root:    $MANAGED_ROOT_REL
  ensure feature:  $ENSURE_FEATURE
  feature active:  $FEATURE_EFFECTIVE
EOF
    if [ "$ENSURE_FEATURE" != "off" ] && [ "$FEATURE_EFFECTIVE" != "true" ]; then
        printf '  note: would enable codex_hooks in %s scope\n' "$ENSURE_FEATURE"
    fi
    exit 0
fi

if [ "$ENSURE_FEATURE" != "off" ] && [ "$FEATURE_EFFECTIVE" != "true" ]; then
    python3 "$SCRIPT_DIR/check_hooks_feature.py" \
        --project "$PROJECT_ROOT" \
        --enable \
        --scope "$ENSURE_FEATURE" \
        --json \
        "${FEATURE_ARGS[@]}" >/dev/null
    FEATURE_STATUS_JSON="$(
        python3 "$SCRIPT_DIR/check_hooks_feature.py" \
            --project "$PROJECT_ROOT" \
            --json \
            "${FEATURE_ARGS[@]}" \
            2>/dev/null || printf '{}\n'
    )"
    printf '%s\n' "$FEATURE_STATUS_JSON" > "$TEMP_FEATURE_STATUS"
fi

mkdir -p "$PROJECT_ROOT/.codex/hooks"

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
# Shared helper functions for generated Codex hook scripts.
#

set -euo pipefail

read_hook_input() {
    cat
}

hook_json() {
    local filter="$1"
    local fallback="${2:-__NO_FALLBACK__}"

    if [ "$fallback" = "__NO_FALLBACK__" ]; then
        printf '%s' "$HOOK_INPUT" | jq -er "$filter"
    else
        printf '%s' "$HOOK_INPUT" | jq -er "$filter" 2>/dev/null || printf '%s\n' "$fallback"
    fi
}

emit_additional_context() {
    local event_name="$1"
    local message="$2"
    jq -n --arg event_name "$event_name" --arg message "$message" \
        '{hookSpecificOutput: {hookEventName: $event_name, additionalContext: $message}}'
}

emit_system_message() {
    local message="$1"
    jq -n --arg message "$message" '{systemMessage: $message}'
}

deny_pre_tool_use() {
    local reason="$1"
    jq -n --arg reason "$reason" \
        '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
}

block_with_reason() {
    local reason="$1"
    jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
}

exit_with_block_reason() {
    local reason="$1"
    printf '%s\n' "$reason" >&2
    exit 2
}
EOF
chmod +x "$LIB_DIR/common.sh"

while IFS=$'\t' read -r event_name script_name description matcher_guidance output_guidance blocking_guidance; do
    target_script="$EVENTS_DIR/$script_name"

    if [ "$MODE" = "additive" ] && [ -f "$target_script" ]; then
        chmod +x "$target_script"
        continue
    fi

    sed \
        -e "s|{{SCRIPT_NAME}}|$(escape_for_sed "$script_name")|g" \
        -e "s|{{EVENT_NAME}}|$(escape_for_sed "$event_name")|g" \
        -e "s|{{EVENT_DESCRIPTION}}|$(escape_for_sed "$description")|g" \
        -e "s|{{MATCHER_GUIDANCE}}|$(escape_for_sed "$matcher_guidance")|g" \
        -e "s|{{OUTPUT_GUIDANCE}}|$(escape_for_sed "$output_guidance")|g" \
        -e "s|{{BLOCKING_GUIDANCE}}|$(escape_for_sed "$blocking_guidance")|g" \
        "$EVENT_TEMPLATE" > "$target_script"

    chmod +x "$target_script"
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
        managed_root: $managed_root,
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
    matcher_supported="$(printf '%s' "$row" | jq -r '.matcher_supported')"
    matcher="$(printf '%s' "$row" | jq -r '.matcher')"
    timeout="$(printf '%s' "$row" | jq -r '.timeout')"
    status_message="$(printf '%s' "$row" | jq -r '.status_message')"
    command="$(build_hook_command "$script_name")"
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
    --managed-root "$MANAGED_ROOT_REL"

bash "$SCRIPT_DIR/render_hooks_readme.sh" \
    --project "$PROJECT_ROOT" \
    --plan "$PLAN_FILE"

cat <<EOF
scaffold_hooks.sh complete
  project root:    $PROJECT_ROOT
  hooks target:    $HOOKS_TARGET_REL
  managed root:    $MANAGED_ROOT_REL
  mode:            $MODE
  ensure feature:  $ENSURE_FEATURE
EOF

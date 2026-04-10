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
# Keep this file small and boring. The goal is to make each event stub easier
# to extend, not to hide important behavior.
#

set -euo pipefail

read_hook_input() {
    # Claude Code passes JSON to command hooks on stdin.
    # Read the whole payload so each stub can inspect it later.
    cat
}

hook_json() {
    # Read a value from the hook JSON payload with jq.
    #
    # Arguments:
    #   1. jq filter
    #   2. optional fallback string
    local filter="$1"
    local fallback="${2:-}"

    if ! command -v jq >/dev/null 2>&1; then
        if [ -n "$fallback" ]; then
            printf '%s\n' "$fallback"
            return 0
        fi
        echo "jq is required to parse hook JSON." >&2
        return 1
    fi

    if [ -n "$fallback" ]; then
        printf '%s' "$HOOK_INPUT" | jq -er "$filter" 2>/dev/null || printf '%s\n' "$fallback"
    else
        printf '%s' "$HOOK_INPUT" | jq -er "$filter"
    fi
}

write_system_message() {
    # Return a systemMessage payload Claude Code can consume on the next turn.
    local message="$1"
    jq -n --arg message "$message" '{systemMessage: $message}'
}

write_additional_context() {
    # Return additionalContext text for the next Claude turn.
    local message="$1"
    jq -n --arg message "$message" '{additionalContext: $message}'
}
EOF
chmod +x "$LIB_DIR/common.sh"

while IFS=$'\t' read -r event_name script_name description async_guidance; do
    TARGET_SCRIPT="$EVENTS_DIR/$script_name"

    if [ "$MODE" = "additive" ] && [ -f "$TARGET_SCRIPT" ]; then
        chmod +x "$TARGET_SCRIPT"
        continue
    fi

    sed \
        -e "s|{{SCRIPT_NAME}}|$(escape_for_sed "$script_name")|g" \
        -e "s|{{EVENT_NAME}}|$(escape_for_sed "$event_name")|g" \
        -e "s|{{EVENT_DESCRIPTION}}|$(escape_for_sed "$description")|g" \
        -e "s|{{ASYNC_GUIDANCE}}|$(escape_for_sed "$async_guidance")|g" \
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
        hooks:
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
    }
    ' "$MANIFEST_SOURCE" > "$SETTINGS_FRAGMENT_FILE"

"$SCRIPT_DIR/merge_settings.sh" \
    --settings-file "$SETTINGS_TARGET_ABS" \
    --fragment-file "$SETTINGS_FRAGMENT_FILE" \
    --managed-root "$MANAGED_ROOT_REL"

"$SCRIPT_DIR/render_hooks_readme.sh" \
    --project "$PROJECT_ROOT" \
    --plan "$PLAN_FILE"

#!/usr/bin/env bash
#
# scaffold_hooks.sh
#
# Render or refresh the generated OpenCode plugin that runs the plan's scripts and
# commands. Only plan events that have scripts or commands are emitted; a plan
# without any writes no plugin. Managed output of the earlier opencode-froggy
# scaffold is removed.

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  scaffold_hooks.sh --project DIR --plan FILE [--mode additive|overhaul] [--home DIR] [--allow-global-targets] [--dry-run]
EOF
}

require_command() {
    local name="$1"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "Required command is missing: $name" >&2
        exit 1
    fi
}

resolve_target_path() {
    local value="$1"
    local project_root="$2"
    local home_root="$3"

    case "$value" in
        "~"*) printf '%s\n' "${home_root}${value#"~"}" ;;
        /*) printf '%s\n' "$value" ;;
        *) printf '%s\n' "$project_root/$value" ;;
    esac
}

remove_if_empty_dir() {
    local dir="$1"
    rmdir "$dir" 2>/dev/null || true
}

remove_legacy_opencode_event_dir() {
    local event_dir="$1"
    local dir="$PROJECT_ROOT/$HOOKS_ROOT_VALUE/$event_dir"
    local script="$dir/script.sh"
    local adapter="$dir/opencode.sh"

    [ -d "$dir" ] || return 0
    if [ -f "$adapter" ] && grep -q 'OPENCODE_HOOK_EVENT' "$adapter" \
        && { [ ! -f "$script" ] || grep -q '\[opencode-hook\] missing delegate' "$script"; }; then
        rm -f "$adapter" "$script"
        remove_if_empty_dir "$dir"
    fi
}

remove_legacy_dependency_artifacts() {
    local package_file="$PROJECT_ROOT/.opencode/package.json"
    [ -f "$package_file" ] || return 0

    if jq -e '
        ((.dependencies // {}) | keys) == ["@opencode-ai/plugin"]
        and ((.devDependencies // {}) | length == 0)
        and ((.peerDependencies // {}) | length == 0)
    ' "$package_file" >/dev/null 2>&1; then
        rm -f "$package_file"
        rm -f "$PROJECT_ROOT/.opencode/package-lock.json"
        rm -f "$PROJECT_ROOT/.opencode/bun.lock" "$PROJECT_ROOT/.opencode/bun.lockb"
        rm -rf "$PROJECT_ROOT/.opencode/node_modules"
    fi

    local gitignore="$PROJECT_ROOT/.opencode/.gitignore"
    if [ -f "$gitignore" ] && ! grep -qvE '^(node_modules|package\.json|package-lock\.json|bun\.lock|bun\.lockb|\.gitignore)?$' "$gitignore"; then
        rm -f "$gitignore"
    fi
}

cleanup_legacy_plugin_scaffold() {
    local legacy_state="$PROJECT_ROOT/.opencode/plugins/.managed"
    local legacy_manifest="$legacy_state/manifest.json"
    [ -f "$legacy_manifest" ] || return 0

    if ! jq -e '
        (.scaffold_hooks.skill_name == "scaffold-hooks" and .scaffold_hooks.harness == "opencode")
        or (
            (.deployment // "") == "local-files"
            and (.plugin_root // ".opencode/plugins") == ".opencode/plugins"
            and ((.managed_files // []) | type) == "array"
            and (
                ((.enabled_plugins // []) | map(select(
                    (.pattern // "") == "lifecycle-action"
                    or ((.context_script // "") | startswith("hooks/opencode-session-"))
                    or ((.action_script // "") | startswith("hooks/opencode-session-"))
                )) | length) > 0
            )
        )
    ' "$legacy_manifest" >/dev/null 2>&1; then
        return 0
    fi

    local legacy_plugin_root_value
    legacy_plugin_root_value="$(jq -r '.plugin_root // ".opencode/plugins"' "$legacy_manifest")"
    local legacy_plugin_root
    legacy_plugin_root="$(resolve_target_path "$legacy_plugin_root_value" "$PROJECT_ROOT" "$HOME_ROOT")"

    validate_scaffold_path "$PROJECT_ROOT" "$legacy_plugin_root_value" legacy_plugin_root tree
    local managed_files rel_path cleanup_path
    managed_files="$(jq -r '
        (.managed_files // [])
        | if type != "array" then error("managed_files must be an array")
          elif all(.[]; type == "string" and length > 0) then .[]
          else error("managed_files must contain non-empty paths") end
    ' "$legacy_manifest")"
    while IFS= read -r rel_path; do
        [ -n "$rel_path" ] || continue
        validate_scaffold_path "$legacy_plugin_root" "$rel_path" legacy_managed_file
    done <<< "$managed_files"
    for cleanup_path in .opencode/package.json .opencode/package-lock.json \
        .opencode/bun.lock .opencode/bun.lockb .opencode/node_modules .opencode/.gitignore; do
        validate_scaffold_path "$PROJECT_ROOT" "$cleanup_path" legacy_cleanup
    done
    if [ "$DRY_RUN" = "true" ]; then
        return 0
    fi

    while IFS= read -r rel_path; do
        [ -n "$rel_path" ] || continue
        rm -f "$legacy_plugin_root/$rel_path"
    done <<< "$managed_files"

    if [ -f "$legacy_plugin_root/README.md" ] && grep -q 'OpenCode Hooks' "$legacy_plugin_root/README.md"; then
        rm -f "$legacy_plugin_root/README.md"
    fi

    rm -rf "$legacy_state"
    remove_if_empty_dir "$legacy_plugin_root"
    remove_if_empty_dir "$PROJECT_ROOT/.opencode/plugins"

    remove_legacy_opencode_event_dir "opencode-session-created"
    remove_legacy_opencode_event_dir "opencode-session-idle"
    remove_legacy_dependency_artifacts
}


# Froggy-era output: the managed hooks.md block and the opencode-froggy plugin
# entry, removed only when the scaffold's own state proves it wrote them.
cleanup_froggy_scaffold() {
    local state="$CONFIG_DIR/hook/.managed"
    local hooks_file="$CONFIG_DIR/hook/hooks.md"
    local config_file="$FROGGY_CONFIG_FILE"
    local remaining tmp

    if [ -f "$hooks_file" ] && grep -q '# BEGIN scaffold-hooks managed opencode-froggy' "$hooks_file"; then
        [ "$DRY_RUN" = "true" ] && return 0
        tmp="$(mktemp)"
        sed '/# BEGIN scaffold-hooks managed opencode-froggy/,/# END scaffold-hooks managed opencode-froggy/d' "$hooks_file" > "$tmp"
        remaining="$(grep -vE '^(---|hooks:|# OpenCode Froggy Hooks|Managed by scaffold-hooks.*)?[[:space:]]*$' "$tmp" || true)"
        if [ -z "$remaining" ]; then
            rm -f "$hooks_file"
        else
            mv "$tmp" "$hooks_file"
        fi
        rm -f "$tmp"
        rmdir "$CONFIG_DIR/hook" 2>/dev/null || true
    fi

    if [ -f "$state/manifest.json" ]; then
        [ "$DRY_RUN" = "true" ] && return 0
        if [ -f "$config_file" ] && jq -e 'type == "object"' "$config_file" >/dev/null 2>&1; then
            tmp="$(mktemp)"
            jq '
                if (.plugin | type) == "array" then
                    .plugin |= map(select(. != "opencode-froggy"))
                    | if (.plugin | length) == 0 then del(.plugin) else . end
                else . end
                | if (keys - ["$schema"]) == [] then empty else . end
            ' "$config_file" > "$tmp"
            if [ -s "$tmp" ]; then mv "$tmp" "$config_file"; else rm -f "$tmp" "$config_file"; fi
        fi
        rm -rf "$state"
        rmdir "$CONFIG_DIR/hook" 2>/dev/null || true
    fi
}

PROJECT_ROOT=""
PLAN_FILE=""
MODE_OVERRIDE=""
HOME_OVERRIDE=""
DRY_RUN="false"
ALLOW_GLOBAL_TARGETS="false"

while [ $# -gt 0 ]; do
    case "$1" in
        --project) PROJECT_ROOT="$2"; shift 2 ;;
        --plan) PLAN_FILE="$2"; shift 2 ;;
        --mode) MODE_OVERRIDE="$2"; shift 2 ;;
        --home) HOME_OVERRIDE="$2"; shift 2 ;;
        --allow-global-targets) ALLOW_GLOBAL_TARGETS="true"; shift ;;
        --dry-run) DRY_RUN="true"; shift ;;
        -h|--help) usage; exit 0 ;;
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
UNIVERSAL_SKILL_ROOT="$(cd "$SKILL_ROOT/../.." && pwd -P)"
MANIFEST_SOURCE="$SKILL_ROOT/assets/hook-events.json"
PLUGIN_TEMPLATE="$SKILL_ROOT/templates/plugin.ts.tmpl"
GENERATED_MARKER="// Generated by scaffold-hooks."

PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd -P)"
PLAN_FILE="$(cd "$(dirname "$PLAN_FILE")" && printf '%s/%s\n' "$(pwd -P)" "$(basename "$PLAN_FILE")")"

if [ ! -f "$PLAN_FILE" ]; then
    echo "Plan file does not exist: $PLAN_FILE" >&2
    exit 1
fi

MODE="$(jq -r '.mode // "additive"' "$PLAN_FILE")"
[ -z "$MODE_OVERRIDE" ] || MODE="$MODE_OVERRIDE"
case "$MODE" in
    additive|overhaul) ;;
    *)
        echo "Mode must be additive or overhaul. Got: $MODE" >&2
        exit 1
        ;;
esac

SCOPE="$(jq -r '.scope // "project"' "$PLAN_FILE")"
case "$SCOPE" in
    project|global) ;;
    *)
        echo "Scope must be project or global. Got: $SCOPE" >&2
        exit 1
        ;;
esac

# Malformed events fail before any write, whether or not they would be emitted.
if ! jq -e --slurpfile manifest "$MANIFEST_SOURCE" '
    def valid_args: if has("args") then ((.args | type) == "array" and all(.args[]; type == "string")) else true end;
    def valid_cwd: if has("cwd") then (.cwd | type) == "string" else true end;
    def nonempty: type == "string" and length > 0;
    def valid_script: type == "object" and ((.path? // .script? // null) | nonempty) and valid_args and valid_cwd;
    def valid_command: type == "object" and ((.command? // null) | nonempty) and valid_cwd;
    def valid_event:
        type == "object"
        and (.name as $name | $manifest[0].events | map(.name) | index($name) != null)
        and (if has("scripts") then ((.scripts | type) == "array" and all(.scripts[]; valid_script)) else true end)
        and (if has("commands") then ((.commands | type) == "array" and all(.commands[]; valid_command)) else true end);
    type == "object"
    and (if has("enabled_events") then ((.enabled_events | type) == "array" and all(.enabled_events[]; valid_event)
        and ((.enabled_events | map(.name) | unique | length) == (.enabled_events | length))) else true end)
' "$PLAN_FILE" >/dev/null 2>&1; then
    echo "Plan file has invalid events, scripts or commands configuration." >&2
    echo "Expected event names from assets/hook-events.json, each used once, with arrays of objects holding non-empty paths/commands, string args and string cwd values." >&2
    exit 1
fi

HOME_ROOT="${HOME_OVERRIDE:-$HOME}"
source "$SCRIPT_DIR/scaffold_paths.sh"
HOOKS_ROOT_VALUE="$(jq -r '.hooks_root // "hooks"' "$PLAN_FILE")"
validate_scaffold_path "$PROJECT_ROOT" "$HOOKS_ROOT_VALUE" hooks_root tree
PLUGIN_TARGET_VALUE="$(jq -r '.plugin_target // empty' "$PLAN_FILE")"
if [ "$SCOPE" = "global" ]; then
    CONFIG_DIR="$HOME_ROOT/.config/opencode"
    FROGGY_CONFIG_FILE="$CONFIG_DIR/opencode.json"
    [ -n "$PLUGIN_TARGET_VALUE" ] || PLUGIN_TARGET_VALUE="~/.config/opencode/plugins/scaffold-hooks.ts"
else
    CONFIG_DIR="$PROJECT_ROOT/.opencode"
    FROGGY_CONFIG_FILE="$PROJECT_ROOT/opencode.json"
    [ -n "$PLUGIN_TARGET_VALUE" ] || PLUGIN_TARGET_VALUE=".opencode/plugins/scaffold-hooks.ts"
fi
PLUGIN_TARGET_ABS="$(resolve_target_path "$PLUGIN_TARGET_VALUE" "$PROJECT_ROOT" "$HOME_ROOT")"

if [ "$SCOPE" = "global" ]; then
    if [ "$ALLOW_GLOBAL_TARGETS" != "true" ]; then
        echo "Global scope requires explicit --allow-global-targets authorization." >&2
        exit 1
    fi
    case "$PLUGIN_TARGET_ABS" in
        "$HOME_ROOT/.config/opencode/"*) ;;
        *) echo "Unsafe scaffold path: global targets must stay under ~/.config/opencode/." >&2; exit 1 ;;
    esac
    validate_scaffold_path "$HOME_ROOT" "${PLUGIN_TARGET_ABS#"$HOME_ROOT/"}" plugin_target
    validate_scaffold_path "$HOME_ROOT" .config/opencode/opencode.json froggy_config
    validate_scaffold_path "$HOME_ROOT" .config/opencode/hook froggy_state tree
else
    validate_scaffold_path "$PROJECT_ROOT" "$PLUGIN_TARGET_VALUE" plugin_target
    validate_scaffold_path "$PROJECT_ROOT" opencode.json froggy_config
    validate_scaffold_path "$PROJECT_ROOT" .opencode/hook froggy_state tree
fi
validate_scaffold_path "$PROJECT_ROOT" .opencode/plugins/.managed legacy_state tree
# Validate every manifest-controlled removal before creating output.
DRY_RUN=true cleanup_legacy_plugin_scaffold

detect_code_change_extensions() {
    python3 "$UNIVERSAL_SKILL_ROOT/scripts/detect_code_extensions.py" --project "$PROJECT_ROOT" --hooks-root hooks 2>/dev/null \
        || printf '["js","jsx","ts","tsx","py","go","rs","java","php","rb","cs","sh"]\n'
}

# An event is emitted only when the plan gives it scripts or commands.
EVENTS_JSON="$(
    jq -c --argjson detected "$(detect_code_change_extensions)" '
        [(.enabled_events // [])[]
            | select(((.scripts // []) + (.commands // [])) | length > 0)
            | {name, matcher, timeout, scripts: (.scripts // []), commands: (.commands // []), run_on_code_changes, code_change_extensions: (.code_change_extensions // $detected)}
            | with_entries(select(.value != null))]
    ' "$PLAN_FILE"
)"
EVENT_COUNT="$(printf '%s' "$EVENTS_JSON" | jq 'length')"

if [ "$DRY_RUN" = "true" ]; then
    cat <<EOF
scaffold_hooks.sh dry run
  project root:   $PROJECT_ROOT
  scope:          $SCOPE
  mode:           $MODE
  plugin target:  $PLUGIN_TARGET_VALUE
  events:         $EVENT_COUNT
EOF
    exit 0
fi

if [ -f "$PLUGIN_TARGET_ABS" ] && ! head -n 1 "$PLUGIN_TARGET_ABS" | grep -qF "$GENERATED_MARKER"; then
    echo "Refusing to overwrite $PLUGIN_TARGET_VALUE: it was not generated by scaffold-hooks." >&2
    exit 1
fi

cleanup_legacy_plugin_scaffold
cleanup_froggy_scaffold

if [ "$EVENT_COUNT" -eq 0 ]; then
    rm -f "$PLUGIN_TARGET_ABS"
    rmdir "$(dirname "$PLUGIN_TARGET_ABS")" "$CONFIG_DIR" 2>/dev/null || true
    echo "No plan event has scripts or commands; no OpenCode plugin was scaffolded." >&2
    exit 0
fi

PLACEHOLDER_LINE="$(grep -n '@@PLAN@@' "$PLUGIN_TEMPLATE" | cut -d: -f1)"
mkdir -p "$(dirname "$PLUGIN_TARGET_ABS")"
{
    head -n "$((PLACEHOLDER_LINE - 1))" "$PLUGIN_TEMPLATE"
    printf 'const PLAN: { events: PlanEvent[] } = %s\n' "$(jq -nc --argjson events "$EVENTS_JSON" '{events: $events}')"
    tail -n "+$((PLACEHOLDER_LINE + 1))" "$PLUGIN_TEMPLATE"
} > "$PLUGIN_TARGET_ABS"

cat <<EOF
scaffold_hooks.sh complete
  project root:   $PROJECT_ROOT
  scope:          $SCOPE
  plugin:         $PLUGIN_TARGET_VALUE
  events:         $(printf '%s' "$EVENTS_JSON" | jq -r 'map(.name) | join(",")')
EOF

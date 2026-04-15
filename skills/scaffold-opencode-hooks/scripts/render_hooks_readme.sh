#!/usr/bin/env bash
#
# render_hooks_readme.sh
#
# Rebuild .opencode/plugins/README.md from the managed manifest and current plan.
#

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  render_hooks_readme.sh --project DIR --plan FILE [--home DIR]
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

PROJECT_ROOT=""
PLAN_FILE=""
HOME_OVERRIDE=""

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
        --home)
            HOME_OVERRIDE="$2"
            shift 2
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

PROJECT_ROOT="$(
    cd "$PROJECT_ROOT"
    pwd -P
)"
PLAN_FILE="$(
    cd "$(dirname "$PLAN_FILE")"
    printf '%s/%s\n' "$(pwd -P)" "$(basename "$PLAN_FILE")"
)"

HOME_ROOT="${HOME_OVERRIDE:-$HOME}"
SCOPE="$(jq -r '.scope // "project"' "$PLAN_FILE")"
PLUGIN_ROOT_VALUE="$(jq -r '.plugin_root // empty' "$PLAN_FILE")"
MANAGED_STATE_VALUE="$(jq -r '.managed_state_dir // empty' "$PLAN_FILE")"
CONFIG_TARGET_VALUE="$(jq -r '.config_target // empty' "$PLAN_FILE")"
PACKAGE_TARGET_VALUE="$(jq -r '.package_target // empty' "$PLAN_FILE")"

if [ -z "$PLUGIN_ROOT_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        PLUGIN_ROOT_VALUE="~/.config/opencode/plugins"
    else
        PLUGIN_ROOT_VALUE=".opencode/plugins"
    fi
fi
if [ -z "$MANAGED_STATE_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        MANAGED_STATE_VALUE="~/.config/opencode/plugins/.managed"
    else
        MANAGED_STATE_VALUE=".opencode/plugins/.managed"
    fi
fi
if [ -z "$CONFIG_TARGET_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        CONFIG_TARGET_VALUE="~/.config/opencode/opencode.json"
    else
        CONFIG_TARGET_VALUE="opencode.json"
    fi
fi
if [ -z "$PACKAGE_TARGET_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        PACKAGE_TARGET_VALUE="~/.config/opencode/package.json"
    else
        PACKAGE_TARGET_VALUE=".opencode/package.json"
    fi
fi

PLUGIN_ROOT_ABS="$(resolve_target_path "$PLUGIN_ROOT_VALUE" "$PROJECT_ROOT" "$HOME_ROOT")"
MANAGED_STATE_ABS="$(resolve_target_path "$MANAGED_STATE_VALUE" "$PROJECT_ROOT" "$HOME_ROOT")"
README_FILE="$PLUGIN_ROOT_ABS/README.md"
MANIFEST_FILE="$MANAGED_STATE_ABS/manifest.json"

if [ ! -f "$MANIFEST_FILE" ]; then
    echo "Manifest file does not exist: $MANIFEST_FILE" >&2
    exit 1
fi

mkdir -p "$(dirname "$README_FILE")"

{
    printf '# OpenCode Hooks\n\n'
    printf 'Managed OpenCode plugin scaffold for this target.\n\n'
    printf '## Managed Paths\n\n'
    printf -- '- plugin root: `%s`\n' "$PLUGIN_ROOT_VALUE"
    printf -- '- managed state: `%s`\n' "$MANAGED_STATE_VALUE"
    printf -- '- config target: `%s`\n' "$CONFIG_TARGET_VALUE"
    printf -- '- package target: `%s`\n' "$PACKAGE_TARGET_VALUE"
    printf '\n'

    printf '## Notes\n\n'
    printf -- '- OpenCode hooks are implemented as plugins, not a separate hook config file.\n'
    printf -- '- Only the enabled managed plugin modules live in the active plugin directory.\n'
    printf -- '- The managed state directory keeps the full surface catalog as `.txt` stubs so dormant handlers do not load at runtime.\n'
    printf -- '- Project-local plugins do not replace global plugins; OpenCode loads all configured sources in sequence.\n\n'

    printf '## Active Managed Plugins\n\n'
    printf '| Plugin | File | Surfaces | Notes |\n'
    printf '|--------|------|----------|-------|\n'
    jq -r '
        (.enabled_plugins // [])
        | .[]
        | [
            .name,
            .filename,
            ((.surfaces // []) | join(", ")),
            (.notes // "")
          ]
        | @tsv
    ' "$MANIFEST_FILE" | while IFS=$'\t' read -r name file surfaces notes; do
        printf '| `%s` | `%s` | `%s` | %s |\n' "$name" "$file" "$surfaces" "$notes"
    done
    printf '\n'

    printf '## Hook Surface Map\n\n'
    printf '| Surface | Active | Kind | Stub | Guidance |\n'
    printf '|---------|--------|------|------|----------|\n'
    jq -r '
        ((.enabled_plugins // []) | map(.surfaces // []) | add // []) as $active
        | ((.special_surfaces // []) + (.events // []))[]
        as $surface
        | [
            $surface.name,
            (if ($active | index($surface.name)) then "yes" else "no" end),
            $surface.kind,
            $surface.stub_file,
            $surface.guidance
          ]
        | @tsv
    ' "$MANIFEST_FILE" | while IFS=$'\t' read -r name active kind stub guidance; do
        printf '| `%s` | %s | `%s` | `%s` | %s |\n' \
            "$name" "$active" "$kind" "$stub" "$guidance"
    done
    printf '\n'

    printf '## Sources\n\n'
    jq -r '.verified_with.official_docs[]' "$MANIFEST_FILE" | while IFS= read -r url; do
        printf -- '- %s\n' "$url"
    done
    jq -r '.verified_with.secondary_sources[]' "$MANIFEST_FILE" | while IFS= read -r url; do
        printf -- '- %s\n' "$url"
    done
} > "$README_FILE"

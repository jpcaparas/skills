#!/usr/bin/env bash
#
# render_hooks_readme.sh
#
# Build a readable README for a target project's .claude/hooks directory.
#
# The README is generated from:
# - the current event manifest
# - the current hook plan
#
# Usage:
#   ./render_hooks_readme.sh --project /path/to/project --plan /path/to/plan.json
#

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  render_hooks_readme.sh --project DIR --plan FILE [--output FILE]

Options:
  --project DIR   Target project root.
  --plan FILE     Hook plan JSON used for the scaffold.
  --output FILE   Override the README output path.
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

PROJECT_ROOT=""
PLAN_FILE=""
OUTPUT_FILE=""

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
        --output)
            OUTPUT_FILE="$2"
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"

MANAGED_ROOT_REL="$(jq -r '.managed_root // ".claude/hooks/generated"' "$PLAN_FILE")"
SETTINGS_TARGET_REL="$(jq -r '.settings_target // ".claude/settings.json"' "$PLAN_FILE")"
MANIFEST_FILE="$PROJECT_ROOT/$MANAGED_ROOT_REL/manifest.json"

if [ ! -f "$MANIFEST_FILE" ]; then
    MANIFEST_FILE="$SKILL_ROOT/assets/hook-events.json"
fi

if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_FILE="$PROJECT_ROOT/.claude/hooks/README.md"
fi

mkdir -p "$(dirname "$OUTPUT_FILE")"

{
    echo "# Claude Code Hooks"
    echo
    echo "This folder contains the Claude Code hook scaffold for this project."
    echo
    echo "## Managed Layer"
    echo
    echo "- Settings target: \`$SETTINGS_TARGET_REL\`"
    echo "- Managed hook root: \`$MANAGED_ROOT_REL\`"
    echo "- Every current official Claude Code hook event has a bash stub in the managed event folder."
    echo "- Only events listed in the current plan are wired into the settings file."
    echo "- Re-run the scaffold after re-checking the live official Claude Code hook docs."
    echo
    echo "## Event Map"
    echo
    echo "| Event | Enabled | Async When Enabled | Managed Script | Purpose |"
    echo "|------|---------|--------------------|----------------|---------|"

    while IFS=$'\t' read -r event_name script_name description; do
        enabled="No"
        async_value="n/a"

        if jq -e --arg name "$event_name" '.enabled_events[]? | select(.name == $name)' "$PLAN_FILE" >/dev/null; then
            enabled="Yes"
            async_value="$(
                jq -r --arg name "$event_name" '
                    .enabled_events[]?
                    | select(.name == $name)
                    | if has("async") then (.async | tostring) else "false" end
                ' "$PLAN_FILE" | head -n 1
            )"
        fi

        printf '| `%s` | %s | %s | `%s/events/%s` | %s |\n' \
            "$event_name" \
            "$enabled" \
            "$async_value" \
            "$MANAGED_ROOT_REL" \
            "$script_name" \
            "$description"
    done < <(jq -r '.events[] | [.name, .script_name, .description] | @tsv' "$MANIFEST_FILE")

    echo
    echo "## Notes"
    echo
    echo "- Use sync hooks for blocking gates, permission decisions, and environment changes that must land before the next action."
    echo "- Use async hooks for logging, notifications, metrics, and background test or formatting work that should not slow Claude down."
    echo "- Keep unrelated custom hooks outside the managed folder if you do not want future scaffold refreshes to replace them."
} > "$OUTPUT_FILE"


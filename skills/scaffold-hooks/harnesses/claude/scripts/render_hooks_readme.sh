#!/usr/bin/env bash
#
# render_hooks_readme.sh
#
# Build a readable README for a target project's shared hooks directory.
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

MANAGED_ROOT_REL="$(jq -r '.managed_root // "hooks"' "$PLAN_FILE")"
SETTINGS_TARGET_REL="$(jq -r '.settings_target // ".claude/settings.json"' "$PLAN_FILE")"
MANIFEST_FILE="$PROJECT_ROOT/$MANAGED_ROOT_REL/.state/claude/manifest.json"

if [ ! -f "$MANIFEST_FILE" ]; then
    MANIFEST_FILE="$SKILL_ROOT/assets/hook-events.json"
fi

if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_FILE="$PROJECT_ROOT/$MANAGED_ROOT_REL/README.md"
fi

mkdir -p "$(dirname "$OUTPUT_FILE")"

{
    echo "# Claude Code Hooks"
    echo
    echo "This folder contains shared repo-owned hook logic plus Claude Code adapters for this project."
    echo
    echo "## Managed Layer"
    echo
    echo "- Settings target: \`$SETTINGS_TARGET_REL\`"
    echo "- Hook root: \`$MANAGED_ROOT_REL\`"
    echo "- Harness state: \`$MANAGED_ROOT_REL/.state/claude\`"
    echo "- Every current official Claude Code hook event has a shared \`script.sh\` under \`$MANAGED_ROOT_REL/<event>/\`."
    echo "- Claude Code invokes \`$MANAGED_ROOT_REL/<event>/claude.sh\`, which loads \`claude.json\` for plan data."
    echo "- Only events listed in the current plan are wired into the settings file."
    echo "- Re-run the scaffold after re-checking the live official Claude Code hook docs."
    echo
    echo "## Event Map"
    echo
    echo "| Event | Enabled | Async When Enabled | Plan Scripts | Plan Commands | Shared Script | Claude Adapter | Purpose |"
    echo "|------|---------|--------------------|--------------|---------------|---------------|----------------|---------|"

    while IFS=$'\t' read -r event_name script_name description; do
        enabled="No"
        async_value="n/a"
        script_labels="none"
        command_labels="none"

        if jq -e --arg name "$event_name" '.enabled_events[]? | select(.name == $name)' "$PLAN_FILE" >/dev/null; then
            enabled="Yes"
            async_value="$(
                jq -r --arg name "$event_name" '
                    .enabled_events[]?
                    | select(.name == $name)
                    | if has("async") then (.async | tostring) else "false" end
                ' "$PLAN_FILE" | head -n 1
            )"
            command_labels="$(
                jq -r --arg name "$event_name" '
                    [
                        .enabled_events[]?
                        | select(.name == $name)
                        | (.commands // [])[]?
                        | (.label // .name // .command)
                    ]
                    | if length == 0 then "none" else join("<br>") end
                ' "$PLAN_FILE" | sed 's/|/\\|/g'
            )"
            script_labels="$(
                jq -r --arg name "$event_name" '
                    [
                        .enabled_events[]?
                        | select(.name == $name)
                        | (.scripts // [])[]?
                        | (.label // .name // .path // .script)
                    ]
                    | if length == 0 then "none" else join("<br>") end
                ' "$PLAN_FILE" | sed 's/|/\\|/g'
            )"
        fi

        event_dir="${script_name%.sh}"
        event_dir="$(printf '%s' "$event_dir" | tr '_' '-')"

        printf '| `%s` | %s | %s | %s | %s | `%s/%s/script.sh` | `%s/%s/claude.sh` | %s |\n' \
            "$event_name" \
            "$enabled" \
            "$async_value" \
            "$script_labels" \
            "$command_labels" \
            "$MANAGED_ROOT_REL" \
            "$event_dir" \
            "$MANAGED_ROOT_REL" \
            "$event_dir" \
            "$description"
    done < <(jq -r '.events[] | [.name, .script_name, .description] | @tsv' "$MANIFEST_FILE")

    echo
    echo "## Notes"
    echo
    echo "- Use sync hooks for blocking gates, permission decisions, and environment changes that must land before the next action."
    echo "- Use async hooks for logging, notifications, metrics, and background test or formatting work that should not slow Claude down."
    echo "- Put reusable project behavior in repo-owned scripts and reference it through the plan's \`scripts\` array."
    echo "- Put existing repo commands in the plan's \`commands\` array instead of hard-coding a language or package manager into generated bash."
    echo "- Keep shared behavior in \`script.sh\`; keep Claude-specific output handling in \`hooks/lib/claude.sh\`."
    echo "- Keep unrelated custom hooks outside this adapter path if you do not want future scaffold refreshes to replace them."
} > "$OUTPUT_FILE"

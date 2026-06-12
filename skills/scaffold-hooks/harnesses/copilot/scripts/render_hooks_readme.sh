#!/usr/bin/env bash
#
# render_hooks_readme.sh
#
# Build a readable README for a target project's .github/copilot/hooks folder.

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

MANAGED_ROOT_REL="$(jq -r '.managed_root // ".github/copilot/hooks/generated"' "$PLAN_FILE")"
HOOKS_TARGET_REL="$(jq -r '.hooks_target // ".github/hooks/copilot-hooks.json"' "$PLAN_FILE")"
MANIFEST_FILE="$PROJECT_ROOT/$MANAGED_ROOT_REL/manifest.json"

if [ ! -f "$MANIFEST_FILE" ]; then
    MANIFEST_FILE="$SKILL_ROOT/assets/hook-events.json"
fi

if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_FILE="$PROJECT_ROOT/.github/copilot/hooks/README.md"
fi

mkdir -p "$(dirname "$OUTPUT_FILE")"

{
    echo "# GitHub Copilot Hooks"
    echo
    echo "This folder contains the GitHub Copilot hook scaffold for this project."
    echo
    echo "## Managed Layer"
    echo
    echo "- Hooks target: \`$HOOKS_TARGET_REL\`"
    echo "- Managed hook root: \`$MANAGED_ROOT_REL\`"
    echo "- Every documented Copilot hook event has a bash stub in the managed event folder."
    echo "- Only events listed in the current plan are wired into \`$HOOKS_TARGET_REL\`."
    echo "- Repository hooks in \`.github/hooks/*.json\` are shared by Copilot cloud agent and Copilot CLI."
    echo "- Restart Copilot CLI after hook config changes."
    echo
    echo "## Event Map"
    echo
    echo "| Event | Enabled | Matcher | Blocks On Failure | Cloud Agent | Plan Scripts | Plan Commands | Managed Script | Purpose |"
    echo "|------|---------|---------|-------------------|-------------|--------------|---------------|----------------|---------|"

    while IFS=$'\t' read -r event_name aliases script_name description cloud_agent; do
        enabled="No"
        matcher_value="n/a"
        blocks_value="n/a"
        script_labels="none"
        command_labels="none"

        if jq -e --arg name "$event_name" --arg aliases "$aliases" '
            .enabled_events[]? as $event
            | select($event.name == $name or (($aliases | split(",")) | index($event.name)))
        ' "$PLAN_FILE" >/dev/null; then
            enabled="Yes"
            matcher_value="$(
                jq -r --arg name "$event_name" --arg aliases "$aliases" '
                    .enabled_events[]? as $event
                    | select($event.name == $name or (($aliases | split(",")) | index($event.name)))
                    | ($event.matcher // "")
                ' "$PLAN_FILE" | head -n 1 | sed 's/|/\\|/g'
            )"
            [ -n "$matcher_value" ] || matcher_value="all"
            blocks_value="$(
                jq -r --arg name "$event_name" --arg aliases "$aliases" '
                    .enabled_events[]? as $event
                    | select($event.name == $name or (($aliases | split(",")) | index($event.name)))
                    | ($event.block_on_failure // false | tostring)
                ' "$PLAN_FILE" | head -n 1
            )"
            command_labels="$(
                jq -r --arg name "$event_name" --arg aliases "$aliases" '
                    [
                        .enabled_events[]? as $event
                        | select($event.name == $name or (($aliases | split(",")) | index($event.name)))
                        | ($event.commands // [])[]?
                        | (.label // .name // .command)
                    ]
                    | if length == 0 then "none" else join("<br>") end
                ' "$PLAN_FILE" | sed 's/|/\\|/g'
            )"
            script_labels="$(
                jq -r --arg name "$event_name" --arg aliases "$aliases" '
                    [
                        .enabled_events[]? as $event
                        | select($event.name == $name or (($aliases | split(",")) | index($event.name)))
                        | ($event.scripts // [])[]?
                        | (.label // .name // .path // .script)
                    ]
                    | if length == 0 then "none" else join("<br>") end
                ' "$PLAN_FILE" | sed 's/|/\\|/g'
            )"
        fi

        printf '| `%s` | %s | `%s` | %s | %s | %s | %s | `%s/events/%s` | %s |\n' \
            "$event_name" \
            "$enabled" \
            "$matcher_value" \
            "$blocks_value" \
            "$cloud_agent" \
            "$script_labels" \
            "$command_labels" \
            "$MANAGED_ROOT_REL" \
            "$script_name" \
            "$description"
    done < <(jq -r '.events[] | [.name, ((.aliases // []) | join(",")), .script_name, .description, .cloud_agent] | @tsv' "$MANIFEST_FILE")

    echo
    echo "## Notes"
    echo
    echo "- Use stdout JSON for intentional \`preToolUse\` decisions."
    echo "- Use exit code \`2\` only where Copilot documents event-specific behavior, especially CLI-only \`permissionRequest\` denies."
    echo "- Put reusable project behavior in repo-owned scripts and reference it through the plan's \`scripts\` array."
    echo "- Put existing repo commands in the plan's \`commands\` array instead of hard-coding a language or package manager into generated bash."
    echo "- Keep unrelated custom hooks outside the managed command path if you do not want future scaffold refreshes to replace them."
    echo "- Cloud agent loads repository hook files from \`.github/hooks/*.json\`; it does not load local user-level hooks."
} > "$OUTPUT_FILE"

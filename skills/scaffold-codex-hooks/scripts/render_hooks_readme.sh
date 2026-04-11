#!/usr/bin/env bash
#
# render_hooks_readme.sh
#
# Rebuild .codex/hooks/README.md from the managed manifest and current plan.
#

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  render_hooks_readme.sh --project DIR --plan FILE
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

MANAGED_ROOT_REL="$(jq -r '.managed_root // ".codex/hooks/generated"' "$PLAN_FILE")"
HOOKS_TARGET_REL="$(jq -r '.hooks_target // ".codex/hooks.json"' "$PLAN_FILE")"
FEATURE_SCOPE="$(jq -r '.feature_scope // "project"' "$PLAN_FILE")"
README_FILE="$PROJECT_ROOT/.codex/hooks/README.md"
MANIFEST_FILE="$PROJECT_ROOT/$MANAGED_ROOT_REL/manifest.json"

if [ ! -f "$MANIFEST_FILE" ]; then
    echo "Manifest file does not exist: $MANIFEST_FILE" >&2
    exit 1
fi

mkdir -p "$(dirname "$README_FILE")"

{
    printf '# Codex Hooks\n\n'
    printf 'Managed Codex hook scaffold for this project.\n\n'
    printf '## Managed Paths\n\n'
    printf -- '- `hooks.json`: `%s`\n' "$HOOKS_TARGET_REL"
    printf -- '- managed root: `%s`\n' "$MANAGED_ROOT_REL"
    if [ "$FEATURE_SCOPE" = "project" ]; then
        printf -- '- feature scope: project (`.codex/config.toml`)\n'
    elif [ "$FEATURE_SCOPE" = "user" ]; then
        printf -- '- feature scope: user (`~/.codex/config.toml`)\n'
    else
        printf -- '- feature scope: off (no automatic enablement)\n'
    fi
    printf '\n'

    printf '## Notes\n\n'
    printf -- '- Current Codex runtime only supports command hooks in practice today.\n'
    printf -- '- `PreToolUse` and `PostToolUse` currently match Bash-only traffic.\n'
    printf -- '- Project-local hooks run alongside any active user-global `~/.codex/hooks.json` handlers.\n'
    printf -- '- Re-run the scaffold when the official docs or schemas change.\n\n'

    printf '## Event Map\n\n'
    printf '| Event | Enabled | Matcher | Timeout | Script | Notes |\n'
    printf '|------|---------|---------|---------|--------|-------|\n'

    jq -r '
        (.enabled_events // []) as $enabled
        | ($enabled | map({(.name): .}) | add) as $enabled_map
        | .events[]
        | [
            .name,
            (if $enabled_map[.name] then "yes" else "no" end),
            ($enabled_map[.name].matcher // (if .matcher_supported then "*" else "ignored" end)),
            (if $enabled_map[.name] then (($enabled_map[.name].timeout // 600) | tostring) else "—" end),
            (.script_name),
            ($enabled_map[.name].notes // .description)
          ]
        | @tsv
    ' "$MANIFEST_FILE" | while IFS=$'\t' read -r event enabled matcher timeout script_name notes; do
        printf '| `%s` | %s | `%s` | `%s` | `%s` | %s |\n' \
            "$event" "$enabled" "$matcher" "$timeout" "$script_name" "$notes"
    done

    printf '\n'
    printf '## Sources\n\n'
    jq -r '.verified_with.official_docs[]' "$MANIFEST_FILE" | while IFS= read -r url; do
        printf -- '- %s\n' "$url"
    done
    jq -r '.verified_with.schemas[]' "$MANIFEST_FILE" | head -n 1 | while IFS= read -r url; do
        printf -- '- %s\n' "$url"
    done
} > "$README_FILE"

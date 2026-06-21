#!/usr/bin/env bash
#
# render_hooks_readme.sh
#
# Rebuild .opencode/hook/README.md from the managed manifest and current plan.
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
HOOK_CONFIG_VALUE="$(jq -r '.hook_config_target // empty' "$PLAN_FILE")"
MANAGED_STATE_VALUE="$(jq -r '.managed_state_dir // empty' "$PLAN_FILE")"
CONFIG_TARGET_VALUE="$(jq -r '.config_target // empty' "$PLAN_FILE")"

if [ -z "$HOOK_CONFIG_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        HOOK_CONFIG_VALUE="~/.config/opencode/hook/hooks.md"
    else
        HOOK_CONFIG_VALUE=".opencode/hook/hooks.md"
    fi
fi
if [ -z "$MANAGED_STATE_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        MANAGED_STATE_VALUE="~/.config/opencode/hook/.managed"
    else
        MANAGED_STATE_VALUE=".opencode/hook/.managed"
    fi
fi
if [ -z "$CONFIG_TARGET_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        CONFIG_TARGET_VALUE="~/.config/opencode/opencode.json"
    else
        CONFIG_TARGET_VALUE="opencode.json"
    fi
fi

HOOK_CONFIG_ABS="$(resolve_target_path "$HOOK_CONFIG_VALUE" "$PROJECT_ROOT" "$HOME_ROOT")"
MANAGED_STATE_ABS="$(resolve_target_path "$MANAGED_STATE_VALUE" "$PROJECT_ROOT" "$HOME_ROOT")"
README_FILE="$(dirname "$HOOK_CONFIG_ABS")/README.md"
MANIFEST_FILE="$MANAGED_STATE_ABS/manifest.json"

if [ ! -f "$MANIFEST_FILE" ]; then
    echo "Manifest file does not exist: $MANIFEST_FILE" >&2
    exit 1
fi

mkdir -p "$(dirname "$README_FILE")"

{
    printf '# OpenCode Froggy Hooks\n\n'
    if [ "$SCOPE" = "global" ]; then
        printf 'Global OpenCode hook configuration managed by `scaffold-hooks` through `opencode-froggy`.\n\n'
    else
        printf 'Project-local OpenCode hook configuration managed by `scaffold-hooks` through `opencode-froggy`.\n\n'
    fi

    printf '## Managed Paths\n\n'
    printf -- '- OpenCode config: `%s`\n' "$CONFIG_TARGET_VALUE"
    printf -- '- Froggy hook config: `%s`\n' "$HOOK_CONFIG_VALUE"
    printf -- '- Managed state: `%s`\n\n' "$MANAGED_STATE_VALUE"

    printf '## Active Hooks\n\n'
    printf '| Event | Conditions | Actions | Notes |\n'
    printf '|-------|------------|---------|-------|\n'
    jq -r '
        (.hooks // [])
        | .[]
        | [
            .event,
            ((.conditions // []) | join(", ")),
            ((.actions // []) | map(keys[0]) | join(", ")),
            (.notes // "")
          ]
        | @tsv
    ' "$MANIFEST_FILE" | while IFS=$'\t' read -r event conditions actions notes; do
        printf '| `%s` | %s | `%s` | %s |\n' "$event" "${conditions:-none}" "$actions" "$notes"
    done
    printf '\n'

    printf '## Notes\n\n'
    printf -- '- `opencode.json` loads `opencode-froggy`; hook behavior lives in `hooks.md`.\n'
    printf -- '- Froggy merges global hooks first, then project hooks.\n'
    printf -- '- Bash actions receive `OPENCODE_PROJECT_DIR`, `OPENCODE_SESSION_ID`, and JSON context on stdin.\n'
    printf -- '- `tool.before.*` and `tool.before.<name>` bash actions can block by exiting `2` and writing the reason to stderr.\n'
    printf -- '- Exit code controls success, failure, or blocking; stderr is for diagnostics and block reasons, not successful status messages.\n'
    printf -- '- The old scaffold-owned `.opencode/plugins/*.ts` lifecycle adapter is intentionally removed during migration.\n\n'

    printf '## Sources\n\n'
    jq -r '.verified_with.official_docs[]' "$MANIFEST_FILE" | while IFS= read -r url; do
        printf -- '- %s\n' "$url"
    done
    jq -r '.verified_with.froggy_sources[]' "$MANIFEST_FILE" | while IFS= read -r url; do
        printf -- '- %s\n' "$url"
    done
} > "$README_FILE"

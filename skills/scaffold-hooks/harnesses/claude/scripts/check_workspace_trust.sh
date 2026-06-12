#!/usr/bin/env bash
#
# check_workspace_trust.sh
#
# Inspect or enable Claude Code workspace trust for a single project path.
#
# Usage:
#   ./check_workspace_trust.sh /path/to/project
#   ./check_workspace_trust.sh /path/to/project --json
#   ./check_workspace_trust.sh /path/to/project --enable
#   ./check_workspace_trust.sh /path/to/project --config /path/to/.claude.json
#

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  check_workspace_trust.sh <project-path> [--json] [--enable] [--config FILE]

Options:
  --json          Print machine-readable JSON.
  --enable        Set hasTrustDialogAccepted=true for the exact project path.
  --config FILE   Override the Claude Code config file path. Default: ~/.claude.json
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

PROJECT_PATH=""
CONFIG_PATH="$HOME/.claude.json"
JSON_OUTPUT="false"
ENABLE_TRUST="false"

while [ $# -gt 0 ]; do
    case "$1" in
        --json)
            JSON_OUTPUT="true"
            shift
            ;;
        --enable)
            ENABLE_TRUST="true"
            shift
            ;;
        --config)
            if [ $# -lt 2 ]; then
                echo "--config requires a file path." >&2
                exit 1
            fi
            CONFIG_PATH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            if [ -n "$PROJECT_PATH" ]; then
                echo "Unexpected extra argument: $1" >&2
                exit 1
            fi
            PROJECT_PATH="$1"
            shift
            ;;
    esac
done

if [ -z "$PROJECT_PATH" ]; then
    usage >&2
    exit 1
fi

if [ ! -d "$PROJECT_PATH" ]; then
    echo "Project path is not a directory: $PROJECT_PATH" >&2
    exit 1
fi

require_command jq

PROJECT_PATH="$(
    cd "$PROJECT_PATH"
    pwd -P
)"

CONFIG_PATH="$(
    cd "$(dirname "$CONFIG_PATH")" 2>/dev/null && printf '%s/%s\n' "$(pwd -P)" "$(basename "$CONFIG_PATH")" \
        || printf '%s\n' "$CONFIG_PATH"
)"

load_config_json() {
    if [ ! -e "$CONFIG_PATH" ]; then
        printf '{}\n'
        return 0
    fi

    if [ ! -f "$CONFIG_PATH" ]; then
        echo "Claude config path is not a file: $CONFIG_PATH" >&2
        exit 1
    fi

    jq -e '.' "$CONFIG_PATH" >/dev/null
    cat "$CONFIG_PATH"
}

write_config_json() {
    local new_json="$1"
    local config_dir
    local tmp_file

    config_dir="$(dirname "$CONFIG_PATH")"
    mkdir -p "$config_dir"
    tmp_file="$(mktemp "$config_dir/.claude.json.tmp.XXXXXX")"
    printf '%s\n' "$new_json" > "$tmp_file"
    mv "$tmp_file" "$CONFIG_PATH"
}

CONFIG_EXISTS="false"
if [ -e "$CONFIG_PATH" ]; then
    CONFIG_EXISTS="true"
fi

CONFIG_JSON="$(load_config_json)"

if [ "$ENABLE_TRUST" = "true" ]; then
    CONFIG_JSON="$(
        printf '%s' "$CONFIG_JSON" | jq --arg project "$PROJECT_PATH" '
            . = (if type == "object" then . else {} end)
            | .projects = ((.projects // {}) | if type == "object" then . else {} end)
            | .projects[$project] = ((.projects[$project] // {}) | if type == "object" then . else {} end)
            | .projects[$project].hasTrustDialogAccepted = true
        '
    )"
    write_config_json "$CONFIG_JSON"
    CONFIG_EXISTS="true"
fi

STATUS_JSON="$(
    jq -n \
        --argjson config "$(printf '%s' "$CONFIG_JSON")" \
        --arg project "$PROJECT_PATH" \
        --arg config_path "$CONFIG_PATH" \
        --argjson config_exists "$CONFIG_EXISTS" \
        --argjson changed "$ENABLE_TRUST" '
        def root_object:
            $config | if type == "object" then . else {} end;

        def projects_object:
            (root_object.projects // {}) | if type == "object" then . else {} end;

        (projects_object) as $projects
        | ($projects[$project] // null) as $entry
        | {
            project_path: $project,
            claude_config_path: $config_path,
            config_exists: $config_exists,
            project_entry_exists: ($entry != null),
            hasTrustDialogAccepted: (
                if ($entry | type) == "object" then ($entry.hasTrustDialogAccepted // false)
                else false
                end
            )
        }
        | .status = (
            if .hasTrustDialogAccepted then
                "trusted"
            elif .project_entry_exists then
                "untrusted"
            elif .config_exists then
                "not-configured"
            else
                "config-missing"
            end
        )
        | .changed = $changed
    '
)"

if [ "$JSON_OUTPUT" = "true" ]; then
    printf '%s\n' "$STATUS_JSON"
    exit 0
fi

STATUS="$(printf '%s' "$STATUS_JSON" | jq -r '.status')"
TRUST_ACCEPTED="$(printf '%s' "$STATUS_JSON" | jq -r '.hasTrustDialogAccepted')"

cat <<EOF
project: $PROJECT_PATH
config: $CONFIG_PATH
status: $STATUS
hasTrustDialogAccepted: $TRUST_ACCEPTED
EOF

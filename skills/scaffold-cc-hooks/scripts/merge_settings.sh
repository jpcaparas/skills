#!/usr/bin/env bash
#
# merge_settings.sh
#
# Merge a generated Claude Code hook fragment into a settings file.
#
# The merge is intentionally conservative:
# - remove only previously managed command hooks whose command path contains the
#   managed root path
# - preserve unrelated custom hooks
# - append the new managed hooks from the generated fragment
#
# Usage:
#   ./merge_settings.sh \
#     --settings-file /repo/.claude/settings.json \
#     --fragment-file /repo/.claude/hooks/generated/settings.generated.json \
#     --managed-root .claude/hooks/generated
#

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  merge_settings.sh --settings-file FILE --fragment-file FILE --managed-root PATH

Options:
  --settings-file FILE  Claude Code settings file to update.
  --fragment-file FILE  Generated settings fragment to merge in.
  --managed-root PATH   Managed hook root path relative to the project root.
  -h, --help            Show this help text.
EOF
}

require_command() {
    local name="$1"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "Required command is missing: $name" >&2
        exit 1
    fi
}

SETTINGS_FILE=""
FRAGMENT_FILE=""
MANAGED_ROOT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --settings-file)
            SETTINGS_FILE="$2"
            shift 2
            ;;
        --fragment-file)
            FRAGMENT_FILE="$2"
            shift 2
            ;;
        --managed-root)
            MANAGED_ROOT="$2"
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

if [ -z "$SETTINGS_FILE" ] || [ -z "$FRAGMENT_FILE" ] || [ -z "$MANAGED_ROOT" ]; then
    usage >&2
    exit 1
fi

require_command jq

if [ ! -f "$FRAGMENT_FILE" ]; then
    echo "Fragment file does not exist: $FRAGMENT_FILE" >&2
    exit 1
fi

mkdir -p "$(dirname "$SETTINGS_FILE")"

TEMP_INPUT="$(mktemp)"
TEMP_OUTPUT="$(mktemp)"
trap 'rm -f "$TEMP_INPUT" "$TEMP_OUTPUT"' EXIT

if [ -f "$SETTINGS_FILE" ]; then
    cp "$SETTINGS_FILE" "$TEMP_INPUT"
else
    printf '{}\n' > "$TEMP_INPUT"
fi

jq \
    --arg managed_root "$MANAGED_ROOT" \
    --slurpfile fragment "$FRAGMENT_FILE" \
    '
    def strip_managed_groups($managed_root):
        ((.hooks // {}) | with_entries(
            .value |= (
                map(
                    .hooks |= map(
                        select(
                            (.type != "command")
                            or (((.command // "") | contains($managed_root)) | not)
                        )
                    )
                )
                | map(select((.hooks | length) > 0))
            )
        ));

    def append_generated_groups($generated):
        reduce (($generated.hooks // {}) | to_entries[]) as $entry ((.hooks // {});
            .[$entry.key] = ((.[$entry.key] // []) + $entry.value)
        );

    . as $settings
    | ($fragment[0] // {}) as $generated
    | $settings
    | .hooks = strip_managed_groups($managed_root)
    | .hooks = append_generated_groups($generated)
    ' "$TEMP_INPUT" > "$TEMP_OUTPUT"

mv "$TEMP_OUTPUT" "$SETTINGS_FILE"


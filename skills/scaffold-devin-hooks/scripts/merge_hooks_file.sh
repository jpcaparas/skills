#!/usr/bin/env bash
#
# merge_hooks_file.sh
#
# Merge a generated Devin hook fragment into .devin/hooks.v1.json.
#
# The merge is intentionally conservative:
# - remove only previously managed command hooks whose command path contains the
#   managed root path
# - preserve unrelated custom hooks
# - append the new managed hooks from the generated fragment
#
# Usage:
#   ./merge_hooks_file.sh \
#     --hooks-file /repo/.devin/hooks.v1.json \
#     --fragment-file /repo/hooks/.state/devin/hooks.v1.json \
#     --managed-root hooks/ \
#     --managed-suffix /devin.sh
#

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  merge_hooks_file.sh --hooks-file FILE --fragment-file FILE --managed-root PATH [--managed-suffix NAME]

Options:
  --hooks-file FILE     Devin .devin/hooks.v1.json file to update.
  --fragment-file FILE  Managed hooks fragment to merge in.
  --managed-root PATH   Managed hook root path relative to the project root.
  --managed-suffix NAME Optional suffix that must also appear in managed commands.
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

HOOKS_FILE=""
FRAGMENT_FILE=""
MANAGED_ROOT=""
MANAGED_SUFFIX=""

while [ $# -gt 0 ]; do
    case "$1" in
        --hooks-file)
            HOOKS_FILE="$2"
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
        --managed-suffix)
            MANAGED_SUFFIX="$2"
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

if [ -z "$HOOKS_FILE" ] || [ -z "$FRAGMENT_FILE" ] || [ -z "$MANAGED_ROOT" ]; then
    usage >&2
    exit 1
fi

require_command jq

if [ ! -f "$FRAGMENT_FILE" ]; then
    echo "Fragment file does not exist: $FRAGMENT_FILE" >&2
    exit 1
fi

mkdir -p "$(dirname "$HOOKS_FILE")"

TEMP_INPUT="$(mktemp)"
TEMP_OUTPUT="$(mktemp)"
trap 'rm -f "$TEMP_INPUT" "$TEMP_OUTPUT"' EXIT

if [ -f "$HOOKS_FILE" ]; then
    cp "$HOOKS_FILE" "$TEMP_INPUT"
else
    printf '{}\n' > "$TEMP_INPUT"
fi

jq \
    --arg managed_root "$MANAGED_ROOT" \
    --arg managed_suffix "$MANAGED_SUFFIX" \
    --slurpfile fragment "$FRAGMENT_FILE" \
    '
    def is_managed_command($managed_root; $managed_suffix):
        ((.command // "") | contains($managed_root))
        and (($managed_suffix | length) == 0 or ((.command // "") | contains($managed_suffix)));

    def strip_managed_groups($managed_root; $managed_suffix):
        with_entries(
            .value |= (
                map(
                    .hooks = (
                        (.hooks // [])
                        | map(
                            select(
                                (.type != "command")
                                or (is_managed_command($managed_root; $managed_suffix) | not)
                            )
                        )
                    )
                )
                | map(select((.hooks | length) > 0))
            )
        )
        | with_entries(select((.value | length) > 0));

    def append_generated_groups($generated):
        reduce (($generated // {}) | to_entries[]) as $entry (.;
            .[$entry.key] = ((.[$entry.key] // []) + $entry.value)
        );

    . as $hooks_file
    | ($fragment[0] // {}) as $generated
    | $hooks_file
    | strip_managed_groups($managed_root; $managed_suffix)
    | append_generated_groups($generated)
    ' "$TEMP_INPUT" > "$TEMP_OUTPUT"

mv "$TEMP_OUTPUT" "$HOOKS_FILE"

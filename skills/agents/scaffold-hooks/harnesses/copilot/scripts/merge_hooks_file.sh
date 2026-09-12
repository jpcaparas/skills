#!/usr/bin/env bash
#
# merge_hooks_file.sh
#
# Merge a generated GitHub Copilot hook fragment into .github/hooks/*.json.

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  merge_hooks_file.sh --hooks-file FILE --fragment-file FILE --managed-root PATH

Options:
  --hooks-file FILE     Copilot hook JSON file to update.
  --fragment-file FILE  Generated hooks fragment to merge in.
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

HOOKS_FILE=""
FRAGMENT_FILE=""
MANAGED_ROOT=""

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
    printf '{"version":1,"hooks":{}}\n' > "$TEMP_INPUT"
fi

jq \
    --arg managed_root "$MANAGED_ROOT" \
    --slurpfile fragment "$FRAGMENT_FILE" \
    '
    def is_managed($managed_root):
        (((.bash // "") | contains($managed_root))
        or ((.command // "") | contains($managed_root))
        or ((.powershell // "") | contains($managed_root)));

    def strip_managed($managed_root):
        .hooks = (
            (.hooks // {})
            | with_entries(
                .value = [
                    (.value // [])[]?
                    | select(is_managed($managed_root) | not)
                ]
            )
            | with_entries(select((.value | length) > 0))
        );

    def append_generated($generated_hooks):
        reduce (($generated_hooks // {}) | to_entries[]) as $entry (.;
            .hooks[$entry.key] = ((.hooks[$entry.key] // []) + $entry.value)
        );

    . as $existing
    | ($fragment[0] // {"version": 1, "hooks": {}}) as $generated
    | $existing
    | .version = 1
    | .hooks = (.hooks // {})
    | strip_managed($managed_root)
    | append_generated($generated.hooks)
    ' "$TEMP_INPUT" > "$TEMP_OUTPUT"

mv "$TEMP_OUTPUT" "$HOOKS_FILE"

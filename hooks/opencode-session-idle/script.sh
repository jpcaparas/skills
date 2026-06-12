#!/usr/bin/env bash
set -euo pipefail

export AGENT_HOOK_HARNESS="${AGENT_HOOK_HARNESS:-opencode}"
export AGENT_HOOK_EVENT="${AGENT_HOOK_EVENT:-Stop}"

PROJECT_ROOT="${OPENCODE_PROJECT_DIR:-}"
if [ -z "$PROJECT_ROOT" ]; then
    if git rev-parse --show-toplevel >/dev/null 2>&1; then
        PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    else
        PROJECT_ROOT="$(pwd -P)"
    fi
fi

DELEGATE="$PROJECT_ROOT/scripts/agent-stop-checks.sh"
if [ ! -f "$DELEGATE" ]; then
    printf '[opencode-hook] missing delegate: %s\n' "$DELEGATE" >&2
    exit 127
fi

exec /usr/bin/env bash "$DELEGATE" "$@"

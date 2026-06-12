#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${OPENCODE_PROJECT_DIR:-}"
if [ -z "$PROJECT_ROOT" ]; then
    if git rev-parse --show-toplevel >/dev/null 2>&1; then
        PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    else
        PROJECT_ROOT="$(pwd -P)"
    fi
fi

DELEGATE="$PROJECT_ROOT/scripts/agent-session-context.sh"
if [ ! -f "$DELEGATE" ]; then
    printf '[opencode-hook] missing delegate: %s\n' "$DELEGATE" >&2
    exit 127
fi

export AGENT_HOOK_HARNESS="${AGENT_HOOK_HARNESS:-opencode}"
export AGENT_HOOK_PROJECT_ROOT="${AGENT_HOOK_PROJECT_ROOT:-$PROJECT_ROOT}"
export AGENT_HOOK_SESSION_ID="${AGENT_HOOK_SESSION_ID:-opencode-default}"

exec /usr/bin/env bash "$DELEGATE" "$@"

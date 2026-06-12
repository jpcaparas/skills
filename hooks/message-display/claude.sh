#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AGENT_HOOK_HARNESS="claude"
export AGENT_HOOK_EVENT="MessageDisplay"

exec "$SCRIPT_DIR/script.sh" "$@"

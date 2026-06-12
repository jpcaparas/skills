#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AGENT_HOOK_HARNESS="codex"
export AGENT_HOOK_EVENT="Stop"

exec "$SCRIPT_DIR/script.sh" "$@"

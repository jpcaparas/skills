#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AGENT_HOOK_HARNESS="devin"
export AGENT_HOOK_EVENT="UserPromptSubmit"

exec "$SCRIPT_DIR/script.sh" "$@"

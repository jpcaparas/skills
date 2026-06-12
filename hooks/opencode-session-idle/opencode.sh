#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export OPENCODE_HOOK_EVENT="opencode-session-idle"

exec "$SCRIPT_DIR/script.sh" "$@"

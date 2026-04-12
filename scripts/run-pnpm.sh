#!/usr/bin/env sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

cd "$REPO_ROOT"

# Prefer Corepack when available so the packageManager field controls the pnpm
# version. GUI Git clients often inherit a PATH that can see npm/node but not a
# user-installed pnpm shim, so fall back to npm exec with the pinned version.
if command -v corepack >/dev/null 2>&1; then
    exec corepack pnpm "$@"
fi

if command -v pnpm >/dev/null 2>&1; then
    exec pnpm "$@"
fi

if command -v npm >/dev/null 2>&1; then
    package_manager="$(node -p "require('./package.json').packageManager" 2>/dev/null || true)"
    case "$package_manager" in
        pnpm@*)
            exec npm exec --yes "$package_manager" -- "$@"
            ;;
    esac
fi

echo "Unable to find pnpm, corepack, or npm for this repository." >&2
exit 127

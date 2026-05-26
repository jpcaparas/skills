#!/usr/bin/env bash
#
# Shared stop-check pipeline for local agent hooks.
#
# Codex, OpenCode, Git hooks, and manual runs can call this same script instead
# of duplicating validation behavior. It exits 0 when stopping is safe and exits
# 2 when the agent should continue and repair the reported issue.
#

set -euo pipefail

unset GREP_OPTIONS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ "${1:-}" != "" ]; then
    if resolved_root="$(git -C "$1" rev-parse --show-toplevel 2>/dev/null)"; then
        REPO_ROOT="$resolved_root"
    fi
fi

cd "$REPO_ROOT"

has_invisible_skill_files() {
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        source_line="$(git check-ignore -v -- "$file" 2>/dev/null || true)"
        source_file="${source_line%%:*}"
        if [[ "$source_file" == /* ]] || [[ "$source_file" == *".git/info/exclude" ]]; then
            return 0
        fi
    done < <(git ls-files --others --ignored --exclude-standard skills 2>/dev/null)
    return 1
}

if [ "${SKILLS_AGENT_STOP_FORCE:-0}" != "1" ] \
    && [ -z "$(git status --porcelain 2>/dev/null)" ] \
    && ! has_invisible_skill_files \
    && upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)" \
    && ahead_count="$(git rev-list --count "${upstream_ref}..HEAD" 2>/dev/null)" \
    && [ "$ahead_count" = "0" ]; then
    echo "No local or unpushed repository changes detected; skipping stop validation."
    exit 0
fi

set +e
bash "$REPO_ROOT/scripts/validate-all-skills.sh"
status=$?
set -e

if [ "$status" -eq 0 ]; then
    exit 0
fi

exit 2

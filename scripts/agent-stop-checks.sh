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

sanitize_hook_id() {
    printf '%s' "$1" | LC_ALL=C tr -c 'A-Za-z0-9_.-' '_'
}

external_ignored_skill_files() {
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        source_line="$(git check-ignore -v -- "$file" 2>/dev/null || true)"
        source_file="${source_line%%:*}"
        if [[ "$source_file" == /* ]] || [[ "$source_file" == *".git/info/exclude" ]]; then
            printf '%s\n' "$file"
        fi
    done < <(git ls-files --others --ignored --exclude-standard skills 2>/dev/null)
}

repo_snapshot_hash() {
    {
        git rev-parse HEAD 2>/dev/null || true
        git status --porcelain=v1 --untracked-files=all 2>/dev/null || true
        external_ignored_skill_files
        if upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"; then
            printf 'upstream:%s\n' "$upstream_ref"
            git rev-list --count "${upstream_ref}..HEAD" 2>/dev/null || true
        fi
    } | shasum -a 256 | awk '{print $1}'
}

session_baseline_file() {
    local git_dir
    git_dir="$(git rev-parse --git-dir)"
    printf '%s/%s-%s.env\n' \
        "$git_dir/agent-hooks/session-baselines" \
        "$(sanitize_hook_id "${AGENT_HOOK_HARNESS:-agent}")" \
        "$(sanitize_hook_id "${AGENT_HOOK_SESSION_ID:-default}")"
}

if [ "${SKILLS_AGENT_STOP_FORCE:-0}" != "1" ] && [ -n "${AGENT_HOOK_HARNESS:-}" ]; then
    baseline_file="$(session_baseline_file)"
    if [ ! -f "$baseline_file" ]; then
        echo "No agent session baseline found; skipping stop validation for unchanged first turn." >&2
        exit 0
    fi

    # shellcheck source=/dev/null
    source "$baseline_file"
    current_snapshot="$(repo_snapshot_hash)"
    if [ "${snapshot:-}" = "$current_snapshot" ]; then
        echo "No repository changes detected since this agent session started; skipping stop validation." >&2
        exit 0
    fi
fi

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
    echo "No local or unpushed repository changes detected; skipping stop validation." >&2
    exit 0
fi

set +e
if [ -n "${AGENT_HOOK_HARNESS:-}" ]; then
    bash "$REPO_ROOT/scripts/validate-all-skills.sh" >&2
else
    bash "$REPO_ROOT/scripts/validate-all-skills.sh"
fi
status=$?
set -e

if [ "$status" -eq 0 ]; then
    exit 0
fi

exit 2

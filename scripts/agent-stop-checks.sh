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

hook_log() {
    if [ -n "${AGENT_HOOK_HARNESS:-}" ]; then
        printf '%s\n' "$*" >&2
    else
        printf '%s\n' "$*"
    fi
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

untracked_and_external_skill_file_hashes() {
    {
        git ls-files --others --exclude-standard -z 2>/dev/null
        external_ignored_skill_files | while IFS= read -r file; do
            printf '%s\0' "$file"
        done
    } | LC_ALL=C sort -zu | while IFS= read -r -d '' file; do
        printf 'file:%s\n' "$file"
        shasum -a 256 -- "$file"
    done
}

repo_snapshot_hash() {
    {
        git rev-parse HEAD 2>/dev/null || true
        git status --porcelain=v1 --untracked-files=all 2>/dev/null || true
        git diff --binary --no-ext-diff HEAD -- 2>/dev/null || true
        untracked_and_external_skill_file_hashes
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

validation_cache_file() {
    local git_dir
    git_dir="$(git rev-parse --git-dir)"
    printf '%s/agent-hooks/last-successful-stop.env\n' "$git_dir"
}

cached_validation_snapshot() {
    local cache_file
    cache_file="$(validation_cache_file)"
    if [ -f "$cache_file" ]; then
        sed -n 's/^snapshot=\([0-9a-f][0-9a-f]*\)$/\1/p' "$cache_file" | head -n 1
    fi
}

record_validated_snapshot() {
    local snapshot_value="$1"
    local cache_file cache_dir temporary_file
    cache_file="$(validation_cache_file)"
    cache_dir="$(dirname "$cache_file")"
    temporary_file="${cache_file}.tmp.$$"
    mkdir -p "$cache_dir"
    {
        printf 'snapshot=%s\n' "$snapshot_value"
        printf 'validated_at=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    } >"$temporary_file"
    mv "$temporary_file" "$cache_file"
}

if [ "${SKILLS_AGENT_STOP_FORCE:-0}" != "1" ] && [ -n "${AGENT_HOOK_HARNESS:-}" ]; then
    baseline_file="$(session_baseline_file)"
    if [ ! -f "$baseline_file" ]; then
        hook_log "No agent session baseline found; skipping stop validation for unchanged first turn."
        exit 0
    fi

    # shellcheck source=/dev/null
    source "$baseline_file"
    current_snapshot="$(repo_snapshot_hash)"
    if [ "${snapshot:-}" = "$current_snapshot" ]; then
        hook_log "No repository changes detected since this agent session started; skipping stop validation."
        exit 0
    fi
fi

validation_snapshot="${current_snapshot:-$(repo_snapshot_hash)}"
if [ "${SKILLS_AGENT_STOP_FORCE:-0}" != "1" ] \
    && [ "$(cached_validation_snapshot)" = "$validation_snapshot" ]; then
    hook_log "Repository snapshot already passed stop validation; skipping repeated checks."
    exit 0
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
    hook_log "No local or unpushed repository changes detected; skipping stop validation."
    exit 0
fi

set +e
if [ -n "${AGENT_HOOK_HARNESS:-}" ]; then
    SKILLS_VALIDATE_ALLOW_UNTRACKED_SKILL_WORKTREE=1 \
        bash "$REPO_ROOT/scripts/validate-all-skills.sh" >&2
else
    bash "$REPO_ROOT/scripts/validate-all-skills.sh"
fi
status=$?
set -e

if [ "$status" -eq 0 ]; then
    post_validation_snapshot="$(repo_snapshot_hash)"
    if [ "$post_validation_snapshot" != "$validation_snapshot" ]; then
        hook_log "Repository changed while stop validation was running; retry against the new snapshot."
        exit 2
    fi
    record_validated_snapshot "$validation_snapshot"
    exit 0
fi

exit 2

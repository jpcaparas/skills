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
# shellcheck source=/dev/null
source "$SCRIPT_DIR/agent-repo-snapshot.sh"

if [ "${1:-}" != "" ]; then
    if resolved_root="$(git -C "$1" rev-parse --show-toplevel 2>/dev/null)"; then
        REPO_ROOT="$resolved_root"
    fi
fi

cd "$REPO_ROOT"

sanitize_hook_id() {
    printf '%s' "$1" | LC_ALL=C tr -c 'A-Za-z0-9_.-' '_'
}

absolute_git_dir() {
    git -C "$REPO_ROOT" rev-parse --absolute-git-dir
}

atomic_replace_file() {
    local source_file="$1"
    local target_file="$2"
    local mv_help

    # GNU mv needs -T and BSD mv needs -h to replace a destination symlink
    # itself instead of treating a symlink-to-directory as the destination.
    mv_help="$(mv --help 2>&1 || true)"
    if [[ "$mv_help" == *"--no-target-directory"* ]]; then
        mv -fT "$source_file" "$target_file"
    else
        mv -f -h "$source_file" "$target_file"
    fi
}

hook_log() {
    if [ -n "${AGENT_HOOK_HARNESS:-}" ]; then
        printf '%s\n' "$*" >&2
    else
        printf '%s\n' "$*"
    fi
}

capture_repository_snapshot() {
    local snapshot_value
    if ! snapshot_value="$(agent_repo_snapshot_hash "$REPO_ROOT")" \
        || ! [[ "$snapshot_value" =~ ^[0-9a-f]{64}$ ]]; then
        return 1
    fi
    printf '%s\n' "$snapshot_value"
}

block_on_snapshot_failure() {
    hook_log "Unable to capture a complete repository snapshot; stop validation cannot proceed safely."
    exit 2
}

session_baseline_file() {
    local git_dir
    git_dir="$(absolute_git_dir)"
    printf '%s/%s-%s.env\n' \
        "$git_dir/agent-hooks/session-baselines" \
        "$(sanitize_hook_id "${AGENT_HOOK_HARNESS:-agent}")" \
        "$(sanitize_hook_id "${AGENT_HOOK_SESSION_ID:-default}")"
}

validation_cache_file() {
    local git_dir
    git_dir="$(absolute_git_dir)"
    printf '%s/agent-hooks/last-successful-stop.env\n' "$git_dir"
}

session_baseline_snapshot() {
    local baseline_file="$1"
    local baseline_dir agent_hooks_dir
    local line snapshot_value=""
    local snapshot_count=0
    local recorded_at_count=0
    baseline_dir="$(dirname "$baseline_file")"
    agent_hooks_dir="$(dirname "$baseline_dir")"

    # Baselines are data, never shell. Reject symlinks and extract one exact
    # SHA-256 record plus the optional UTC timestamp written by SessionStart.
    if [ -L "$agent_hooks_dir" ] \
        || [ -L "$baseline_dir" ] \
        || [ ! -f "$baseline_file" ] \
        || [ -L "$baseline_file" ]; then
        return 1
    fi
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^snapshot=([0-9a-f]{64})$ ]]; then
            snapshot_value="${BASH_REMATCH[1]}"
            snapshot_count=$((snapshot_count + 1))
        elif [[ "$line" =~ ^recorded_at=[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]]; then
            recorded_at_count=$((recorded_at_count + 1))
        else
            return 1
        fi
    done <"$baseline_file"

    if [ "$snapshot_count" -ne 1 ] || [ "$recorded_at_count" -gt 1 ]; then
        return 1
    fi
    printf '%s\n' "$snapshot_value"
}

cached_validation_snapshot() {
    local cache_file cache_dir
    local line snapshot_value=""
    local snapshot_count=0
    local validated_at_count=0
    cache_file="$(validation_cache_file)"
    cache_dir="$(dirname "$cache_file")"

    if [ -L "$cache_dir" ] || [ ! -f "$cache_file" ] || [ -L "$cache_file" ]; then
        return 1
    fi
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^snapshot=([0-9a-f]{64})$ ]]; then
            snapshot_value="${BASH_REMATCH[1]}"
            snapshot_count=$((snapshot_count + 1))
        elif [[ "$line" =~ ^validated_at=[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]]; then
            validated_at_count=$((validated_at_count + 1))
        else
            return 1
        fi
    done <"$cache_file"

    if [ "$snapshot_count" -ne 1 ] || [ "$validated_at_count" -gt 1 ]; then
        return 1
    fi
    printf '%s\n' "$snapshot_value"
}

record_validated_snapshot() {
    local snapshot_value="$1"
    local cache_file cache_dir temporary_file
    cache_file="$(validation_cache_file)"
    cache_dir="$(dirname "$cache_file")"

    if [ -L "$cache_dir" ]; then
        printf 'Refusing symlinked agent hook cache directory: %s\n' "$cache_dir" >&2
        return 1
    fi
    mkdir -p "$cache_dir"
    if [ -L "$cache_dir" ]; then
        printf 'Refusing symlinked agent hook cache directory: %s\n' "$cache_dir" >&2
        return 1
    fi
    if [ -d "$cache_file" ] && [ ! -L "$cache_file" ]; then
        printf 'Refusing directory at validation cache file path: %s\n' "$cache_file" >&2
        return 1
    fi
    temporary_file="$(mktemp "${cache_file}.tmp.XXXXXX")"
    if ! {
        printf 'snapshot=%s\n' "$snapshot_value"
        printf 'validated_at=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    } >"$temporary_file"; then
        rm -f "$temporary_file"
        return 1
    fi
    chmod 600 "$temporary_file"
    if ! atomic_replace_file "$temporary_file" "$cache_file"; then
        rm -f "$temporary_file"
        return 1
    fi
}

if [ "${SKILLS_AGENT_STOP_FORCE:-0}" != "1" ] && [ -n "${AGENT_HOOK_HARNESS:-}" ]; then
    baseline_file="$(session_baseline_file)"
    if [ ! -e "$baseline_file" ] && [ ! -L "$baseline_file" ]; then
        hook_log "No agent session baseline found; running stop validation instead of skipping."
    elif baseline_snapshot="$(session_baseline_snapshot "$baseline_file")"; then
        current_snapshot="$(capture_repository_snapshot)" \
            || block_on_snapshot_failure
        if [ "$baseline_snapshot" = "$current_snapshot" ]; then
            hook_log "No repository changes detected since this agent session started; skipping stop validation."
            exit 0
        fi
    else
        hook_log "Session baseline is invalid or unsafe; running stop validation instead of skipping."
    fi
fi

if [ -n "${current_snapshot:-}" ]; then
    validation_snapshot="$current_snapshot"
else
    validation_snapshot="$(capture_repository_snapshot)" \
        || block_on_snapshot_failure
fi
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
    post_validation_snapshot="$(capture_repository_snapshot)" \
        || block_on_snapshot_failure
    if [ "$post_validation_snapshot" != "$validation_snapshot" ]; then
        hook_log "Repository changed while stop validation was running; retry against the new snapshot."
        exit 2
    fi
    if ! record_validated_snapshot "$validation_snapshot"; then
        hook_log "Unable to record the validated repository snapshot safely; retry after repairing hook state storage."
        exit 2
    fi
    exit 0
fi

exit 2

#!/usr/bin/env bash
#
# Lightweight session context shared by local agent hook adapters.

set -euo pipefail

REPO_ROOT="${AGENT_HOOK_PROJECT_ROOT:-}"
if [ -z "$REPO_ROOT" ] && git rev-parse --show-toplevel >/dev/null 2>&1; then
    REPO_ROOT="$(git rev-parse --show-toplevel)"
fi

sanitize_hook_id() {
    printf '%s' "$1" | LC_ALL=C tr -c 'A-Za-z0-9_.-' '_'
}

session_baseline_file() {
    local git_dir
    git_dir="$(git -C "$REPO_ROOT" rev-parse --git-dir)"
    mkdir -p "$git_dir/agent-hooks/session-baselines"
    printf '%s/%s-%s.env\n' \
        "$git_dir/agent-hooks/session-baselines" \
        "$(sanitize_hook_id "${AGENT_HOOK_HARNESS:-agent}")" \
        "$(sanitize_hook_id "${AGENT_HOOK_SESSION_ID:-default}")"
}

external_ignored_skill_files() {
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        source_line="$(git -C "$REPO_ROOT" check-ignore -v -- "$file" 2>/dev/null || true)"
        source_file="${source_line%%:*}"
        if [[ "$source_file" == /* ]] || [[ "$source_file" == *".git/info/exclude" ]]; then
            printf '%s\n' "$file"
        fi
    done < <(git -C "$REPO_ROOT" ls-files --others --ignored --exclude-standard skills 2>/dev/null)
}

repo_snapshot_hash() {
    {
        git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || true
        git -C "$REPO_ROOT" status --porcelain=v1 --untracked-files=all 2>/dev/null || true
        external_ignored_skill_files
        if upstream_ref="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"; then
            printf 'upstream:%s\n' "$upstream_ref"
            git -C "$REPO_ROOT" rev-list --count "${upstream_ref}..HEAD" 2>/dev/null || true
        fi
    } | shasum -a 256 | awk '{print $1}'
}

if [ -n "$REPO_ROOT" ] && git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    baseline_file="$(session_baseline_file)"
    {
        printf 'snapshot=%q\n' "$(repo_snapshot_hash)"
        printf 'recorded_at=%q\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    } >"$baseline_file"
fi

if [ -z "${AGENT_HOOK_HARNESS:-}" ] || [ "${AGENT_HOOK_HARNESS:-}" = "opencode" ]; then
    cat <<'EOF'
This repository is the public source for installable agent skills.
Keep installable skills under skills/<skill-name>/, keep SKILL.md canonical,
and run bash scripts/validate-all-skills.sh before finishing repository changes.
EOF
fi

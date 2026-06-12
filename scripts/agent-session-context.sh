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

session_context() {
    cat <<'EOF'
This repository is the public source for installable agent skills.

Repository constraints:
- Put every installable skill in skills/<skill-name>/.
- Keep SKILL.md as the canonical instruction file; README.md, AGENTS.md, and metadata.json beside a skill are thin packaging wrappers.
- Treat the root README.md as a public/generated catalog. Do not move agent working agreements or long-lived repository policy into it; keep those in AGENTS.md, SKILL.md, references, validators, or this session-start hook.
- Prefer repo-agnostic instructions. Do not hard-code one workspace or machine path unless the user explicitly requires it.
- Keep skills portable across macOS, Ubuntu, and Windows where practical. Prefer cross-platform language/runtime APIs, quote paths, avoid GNU-only shell flags unless guarded, document unavoidable POSIX shell assumptions, and keep Windows fallbacks explicit when a workflow can reasonably support them.
- Prefer strongly typed implementations. When adding Node-based code, prefer TypeScript over JavaScript unless the surrounding skill already requires plain JS.
- Keep hook architecture simple: shared project behavior belongs in hooks/<event>/script.sh or repo-owned scripts, while harness adapters only translate protocol. Do not duplicate the same validation logic across .claude, .codex, .devin, and .opencode.
- When a skill creates other skills, detect whether the best destination is repo-local or global before writing files.
- Add or update deterministic validators for repeated rules instead of relying only on prose instructions.
- Rely on the stop hook for repository-wide validation; run focused checks earlier only when they help with active debugging.
EOF
}

emit_session_context() {
    local message="$1"
    case "${AGENT_HOOK_HARNESS:-}" in
        codex)
            jq -n --arg message "$message" \
                '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $message}}'
            ;;
        devin)
            # Devin CLI strictly parses hook stdout as Claude-format JSON;
            # plain text fails its effects evaluator and the context is dropped.
            jq -n --arg message "$message" \
                '{systemMessage: "Loaded skills repository session context.", hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $message}}'
            ;;
        claude)
            jq -n --arg message "$message" '{additionalContext: $message}'
            ;;
        *)
            printf '%s\n' "$message"
            ;;
    esac
}

emit_session_context "$(session_context)"

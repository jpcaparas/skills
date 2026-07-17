#!/usr/bin/env bash
#
# Lightweight session context shared by local agent hook adapters.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/agent-repo-snapshot.sh"

REPO_ROOT="${AGENT_HOOK_PROJECT_ROOT:-}"
if [ -z "$REPO_ROOT" ] && git rev-parse --show-toplevel >/dev/null 2>&1; then
    REPO_ROOT="$(git rev-parse --show-toplevel)"
fi

sanitize_hook_id() {
    printf '%s' "$1" | LC_ALL=C tr -c 'A-Za-z0-9_.-' '_'
}

absolute_git_dir() {
    git -C "$REPO_ROOT" rev-parse --absolute-git-dir
}

session_baseline_file() {
    local git_dir
    git_dir="$(absolute_git_dir)"
    printf '%s/%s-%s.env\n' \
        "$git_dir/agent-hooks/session-baselines" \
        "$(sanitize_hook_id "${AGENT_HOOK_HARNESS:-agent}")" \
        "$(sanitize_hook_id "${AGENT_HOOK_SESSION_ID:-default}")"
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

record_session_baseline() {
    local snapshot_value="$1"
    local baseline_file baseline_dir agent_hooks_dir temporary_file
    baseline_file="$(session_baseline_file)"
    baseline_dir="$(dirname "$baseline_file")"
    agent_hooks_dir="$(dirname "$baseline_dir")"

    # Refuse redirected state directories, then replace the final path with a
    # same-directory rename so an existing baseline symlink is never followed.
    if [ -L "$agent_hooks_dir" ] || [ -L "$baseline_dir" ]; then
        printf 'Refusing symlinked agent hook state path: %s\n' "$baseline_dir" >&2
        return 1
    fi
    mkdir -p "$baseline_dir"
    if [ -L "$agent_hooks_dir" ] || [ -L "$baseline_dir" ]; then
        printf 'Refusing symlinked agent hook state path: %s\n' "$baseline_dir" >&2
        return 1
    fi
    if [ -d "$baseline_file" ] && [ ! -L "$baseline_file" ]; then
        printf 'Refusing directory at session baseline file path: %s\n' "$baseline_file" >&2
        return 1
    fi
    temporary_file="$(mktemp "${baseline_file}.tmp.XXXXXX")"
    if ! {
        printf 'snapshot=%s\n' "$snapshot_value"
        printf 'recorded_at=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    } >"$temporary_file"; then
        rm -f "$temporary_file"
        return 1
    fi
    chmod 600 "$temporary_file"
    if ! atomic_replace_file "$temporary_file" "$baseline_file"; then
        rm -f "$temporary_file"
        return 1
    fi
}

if [ -n "$REPO_ROOT" ] && git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    if ! session_snapshot="$(agent_repo_snapshot_hash "$REPO_ROOT")" \
        || ! [[ "$session_snapshot" =~ ^[0-9a-f]{64}$ ]]; then
        printf 'Unable to capture a complete repository snapshot; session baseline was not recorded.\n' >&2
        exit 1
    fi
    record_session_baseline "$session_snapshot"
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

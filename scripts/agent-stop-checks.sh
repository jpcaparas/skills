#!/usr/bin/env bash
#
# Stop gate shared by every agent harness. Exit 0 lets the agent finish; exit 2
# sends it back to work with the end of the validation log as the reason.
#
# Usage: agent-stop-checks.sh [claude|codex|devin|opencode|amp]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
harness="${1:-}"

# These harnesses pipe the hook event as JSON, and set stop_hook_active once
# this gate has already sent the agent back. Blocking a second time would loop
# forever on a failure the agent cannot fix.
case "$harness" in
    claude | codex | devin)
        if [ "$(jq -r '.stop_hook_active // false' 2>/dev/null)" = "true" ]; then
            exit 0
        fi
        ;;
esac

# Nothing to validate: CI already covers a clean tree that matches its upstream.
if [ -z "$(git status --porcelain)" ] \
    && upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)" \
    && [ "$(git rev-list --count "${upstream}..HEAD")" = "0" ]; then
    exit 0
fi

log="$(mktemp "${TMPDIR:-/tmp}/skills-stop-checks.XXXXXX")"
if SKILLS_VALIDATE_ALLOW_UNTRACKED_SKILL_WORKTREE=1 \
    bash scripts/validate-all-skills.sh >"$log" 2>&1; then
    rm -f "$log"
    exit 0
fi

reason="Repository validation failed. Fix it before finishing; rerun with \`pnpm validate\`.
Full log: ${log}

$(tail -n 40 "$log")"
printf '%s\n' "$reason" >&2
# Devin reads its block decision from stdout; the others read stderr.
if [ "$harness" = "devin" ]; then
    jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
fi
exit 2

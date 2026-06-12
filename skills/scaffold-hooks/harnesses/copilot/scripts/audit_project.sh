#!/usr/bin/env bash
#
# audit_project.sh
#
# Build a compact profile of a project before choosing GitHub Copilot hooks.

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  audit_project.sh /path/to/project

Prints a compact, human-readable project audit for Copilot hook planning.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
fi

PROJECT_ROOT="${1:-.}"
PROJECT_ROOT="$(
    cd "$PROJECT_ROOT"
    pwd -P
)"

section() {
    printf '\n## %s\n' "$1"
}

list_existing() {
    local pattern="$1"
    if command -v rg >/dev/null 2>&1; then
        rg --files "$PROJECT_ROOT" 2>/dev/null | rg "$pattern" | sed "s|^$PROJECT_ROOT/||" | LC_ALL=C sort
    else
        find "$PROJECT_ROOT" -type f | sed "s|^$PROJECT_ROOT/||" | grep -E "$pattern" | LC_ALL=C sort || true
    fi
}

printf '# Copilot Hook Project Audit\n'
printf 'project_root: %s\n' "$PROJECT_ROOT"

section "Repository"
if git -C "$PROJECT_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
    printf 'git_root: %s\n' "$(git -C "$PROJECT_ROOT" rev-parse --show-toplevel)"
    printf 'branch: %s\n' "$(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null || true)"
else
    printf 'git_root: not detected\n'
fi

section "Likely Project Shape"
for file in \
    package.json pnpm-workspace.yaml yarn.lock package-lock.json pnpm-lock.yaml turbo.json \
    Makefile justfile Taskfile.yml pyproject.toml requirements.txt go.mod Cargo.toml \
    AGENTS.md README.md .github/workflows/copilot-setup-steps.yml
do
    if [ -e "$PROJECT_ROOT/$file" ]; then
        printf '%s\n' "$file"
    fi
done

section "Existing Copilot Hooks And Settings"
list_existing '^\.github/hooks/.*\.json$|^\.github/copilot/settings(\.local)?\.json$|^\.github/copilot/'

section "Cross-Tool Hook Context"
list_existing '^\.claude/settings(\.local)?\.json$|^\.codex/hooks\.json$|^\.devin/hooks\.v1\.json$|^\.opencode/'

section "Reusable Automation Candidates"
list_existing '^(scripts|bin|tools|\.github/scripts)/'

section "Sensitive Or High-Impact Paths"
list_existing '(^|/)(\.env|\.env\..*|.*secret.*|.*credential.*|migrations|infra|terraform|pulumi|deploy|generated|dist|build)(/|$)' | head -200

section "Suggested Next Read"
printf '%s\n' 'Read references/project-analysis.md, then choose enabled events in a hook plan JSON.'

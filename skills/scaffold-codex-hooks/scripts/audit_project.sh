#!/usr/bin/env bash
#
# audit_project.sh
#
# Inspect a target project and report Codex-hook-relevant facts as JSON.
#

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  audit_project.sh <project-path> [--output FILE]
EOF
}

require_command() {
    local name="$1"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "Required command is missing: $name" >&2
        exit 1
    fi
}

collect_globs_json() {
    local root="$1"
    shift

    (
        cd "$root"
        for pattern in "$@"; do
            rg --files --hidden -g "$pattern" 2>/dev/null || true
        done | LC_ALL=C sort -u | jq -R . | jq -s .
    )
}

PROJECT_PATH=""
OUTPUT_FILE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            if [ -n "$PROJECT_PATH" ]; then
                echo "Unexpected extra argument: $1" >&2
                exit 1
            fi
            PROJECT_PATH="$1"
            shift
            ;;
    esac
done

if [ -z "$PROJECT_PATH" ]; then
    usage >&2
    exit 1
fi

require_command jq
require_command git
require_command rg
require_command python3

PROJECT_ROOT="$(
    cd "$PROJECT_PATH"
    pwd -P
)"

REPO_ROOT="$PROJECT_ROOT"
IS_GIT_REPO="false"
if git -C "$PROJECT_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
    REPO_ROOT="$(git -C "$PROJECT_ROOT" rev-parse --show-toplevel)"
    IS_GIT_REPO="true"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

marker_files_json="$(
    collect_globs_json "$REPO_ROOT" \
        'package.json' \
        'pnpm-workspace.yaml' \
        'turbo.json' \
        'nx.json' \
        'bun.lock' \
        'bun.lockb' \
        'package-lock.json' \
        'yarn.lock' \
        'Cargo.toml' \
        'go.mod' \
        'pyproject.toml' \
        'requirements.txt' \
        'Pipfile' \
        'poetry.lock' \
        'Gemfile' \
        'composer.json' \
        'justfile' \
        'Makefile' \
        'Taskfile.yml' \
        '.envrc'
)"

codex_files_json="$(
    collect_globs_json "$REPO_ROOT" \
        '.codex/config.toml' \
        '.codex/hooks.json' \
        '.codex/hooks/**'
)"

git_hook_files_json="$(
    collect_globs_json "$REPO_ROOT" \
        '.husky/**' \
        'lefthook.yml' \
        'lefthook.yaml' \
        '.githooks/**'
)"

instruction_files_json="$(
    collect_globs_json "$REPO_ROOT" \
        'AGENTS.md' \
        'README*'
)"

protected_candidates_json="$(
    collect_globs_json "$REPO_ROOT" \
        '.env' \
        '.env.*' \
        '*.lock' \
        'package-lock.json' \
        'pnpm-lock.yaml' \
        'yarn.lock' \
        'bun.lock' \
        'bun.lockb' \
        'migrations/**' \
        'infra/**'
)"

package_scripts_json="$(
    PACKAGE_LIST="$(collect_globs_json "$REPO_ROOT" 'package.json')"
    if [ "$PACKAGE_LIST" = "[]" ]; then
        printf '[]\n'
    else
        printf '%s' "$PACKAGE_LIST" | jq -r '.[]' | while IFS= read -r rel_path; do
            jq -c --arg rel_path "$rel_path" '
                {
                    path: $rel_path,
                    scripts: ((.scripts // {}) | keys | sort)
                }
            ' "$REPO_ROOT/$rel_path"
        done | jq -s .
    fi
)"

workspace_kinds_json="$(
    jq -n \
        --argjson markers "$marker_files_json" '
        [
            if ($markers | index("pnpm-workspace.yaml")) then "pnpm-workspace" else empty end,
            if ($markers | index("turbo.json")) then "turborepo" else empty end,
            if ($markers | index("nx.json")) then "nx" else empty end,
            if ($markers | index("Cargo.toml")) then "cargo-workspace-or-package" else empty end,
            if ($markers | index("package.json")) then "node-package" else empty end
        ] | unique
        '
)"

languages_json="$(
    jq -n \
        --argjson markers "$marker_files_json" '
        [
            if (($markers | index("package.json")) or ($markers | index("pnpm-workspace.yaml")) or ($markers | index("turbo.json")) or ($markers | index("nx.json"))) then "javascript-typescript" else empty end,
            if (($markers | index("pyproject.toml")) or ($markers | index("requirements.txt")) or ($markers | index("Pipfile"))) then "python" else empty end,
            if ($markers | index("Cargo.toml")) then "rust" else empty end,
            if ($markers | index("go.mod")) then "go" else empty end,
            if ($markers | index("Gemfile")) then "ruby" else empty end,
            if ($markers | index("composer.json")) then "php" else empty end
        ] | unique
        '
)"

PACKAGE_JSON_COUNT="$(printf '%s' "$package_scripts_json" | jq 'length')"
MONOREPO="false"
if [ "$PACKAGE_JSON_COUNT" -gt 1 ] || [ "$(printf '%s' "$workspace_kinds_json" | jq 'length')" -gt 1 ]; then
    MONOREPO="true"
fi

MANAGED_ROOT=""
if [ -f "$REPO_ROOT/.codex/hooks/generated/manifest.json" ]; then
    MANAGED_ROOT=".codex/hooks/generated"
fi

FEATURE_STATUS_JSON="$(
    python3 "$SCRIPT_DIR/check_hooks_feature.py" --project "$REPO_ROOT" --json 2>/dev/null || printf '{}\n'
)"

RECOMMENDED_FEATURE_SCOPE="user"
if [ "$IS_GIT_REPO" = "true" ]; then
    RECOMMENDED_FEATURE_SCOPE="project"
fi
if printf '%s' "$codex_files_json" | jq -e '. | index(".codex/config.toml")' >/dev/null; then
    RECOMMENDED_FEATURE_SCOPE="project"
fi

RESULT_JSON="$(
    jq -n \
        --arg project_root "$PROJECT_ROOT" \
        --arg repo_root "$REPO_ROOT" \
        --arg recommended_hooks_target ".codex/hooks.json" \
        --arg recommended_managed_root ".codex/hooks/generated" \
        --arg existing_managed_root "$MANAGED_ROOT" \
        --arg recommended_feature_scope "$RECOMMENDED_FEATURE_SCOPE" \
        --argjson is_git_repo "$IS_GIT_REPO" \
        --argjson marker_files "$marker_files_json" \
        --argjson codex_files "$codex_files_json" \
        --argjson git_hook_files "$git_hook_files_json" \
        --argjson instruction_files "$instruction_files_json" \
        --argjson protected_candidates "$protected_candidates_json" \
        --argjson package_scripts "$package_scripts_json" \
        --argjson workspace_kinds "$workspace_kinds_json" \
        --argjson languages "$languages_json" \
        --argjson monorepo "$MONOREPO" \
        --argjson feature_status "$FEATURE_STATUS_JSON" '
        {
            project_root: $project_root,
            repo_root: $repo_root,
            is_git_repo: $is_git_repo,
            monorepo: $monorepo,
            marker_files: $marker_files,
            workspace_kinds: $workspace_kinds,
            languages: $languages,
            package_scripts: $package_scripts,
            codex: {
                files: $codex_files,
                feature_status: $feature_status,
                recommended_hooks_target: $recommended_hooks_target,
                recommended_managed_root: $recommended_managed_root,
                existing_managed_hook_root: (if $existing_managed_root == "" then null else $existing_managed_root end),
                recommended_feature_scope: $recommended_feature_scope
            },
            instructions: $instruction_files,
            git_hooks: $git_hook_files,
            protected_candidates: $protected_candidates
        }
        '
)"

if [ -n "$OUTPUT_FILE" ]; then
    printf '%s\n' "$RESULT_JSON" > "$OUTPUT_FILE"
fi

printf '%s\n' "$RESULT_JSON"

#!/usr/bin/env bash
#
# audit_project.sh
#
# Inspect a target project and report hook-relevant facts as JSON.
#
# This script is intentionally deterministic. It does not decide policy.
# It only reports real signals from the repository so the calling agent can
# choose a hook plan with context.
#
# Usage:
#   ./audit_project.sh /path/to/project
#   ./audit_project.sh /path/to/project --output /tmp/project-profile.json
#

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  audit_project.sh <project-path> [--output FILE]

Options:
  --output FILE   Write the JSON profile to FILE instead of stdout.
  -h, --help      Show this help text.
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

    local cmd=(rg --files "$root")
    local pattern=""
    for pattern in "$@"; do
        cmd+=(-g "$pattern")
    done

    (
        "${cmd[@]}" 2>/dev/null || true
    ) | LC_ALL=C sort | sed "s#^$root/##" | jq -R -s 'split("\n") | map(select(length > 0))'
}

json_array_from_lines() {
    jq -R -s 'split("\n") | map(select(length > 0))'
}

discover_repo_root() {
    local target="$1"
    if git -C "$target" rev-parse --show-toplevel >/dev/null 2>&1; then
        git -C "$target" rev-parse --show-toplevel
    else
        (
            cd "$target"
            pwd -P
        )
    fi
}

make_relative() {
    local absolute_path="$1"
    printf '%s\n' "${absolute_path#"$REPO_ROOT"/}"
}

TARGET_PATH=""
OUTPUT_FILE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --output)
            if [ $# -lt 2 ]; then
                echo "--output requires a file path." >&2
                exit 1
            fi
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            if [ -n "$TARGET_PATH" ]; then
                echo "Unexpected extra argument: $1" >&2
                exit 1
            fi
            TARGET_PATH="$1"
            shift
            ;;
    esac
done

if [ -z "$TARGET_PATH" ]; then
    usage >&2
    exit 1
fi

if [ ! -d "$TARGET_PATH" ]; then
    echo "Project path is not a directory: $TARGET_PATH" >&2
    exit 1
fi

require_command git
require_command jq
require_command rg

TARGET_PATH="$(
    cd "$TARGET_PATH"
    pwd -P
)"
IS_GIT_REPO="false"
if git -C "$TARGET_PATH" rev-parse --show-toplevel >/dev/null 2>&1; then
    IS_GIT_REPO="true"
fi
REPO_ROOT="$(discover_repo_root "$TARGET_PATH")"
TIMESTAMP_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

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
        'pnpm-lock.yaml' \
        'tsconfig.json' \
        'pyproject.toml' \
        'requirements*.txt' \
        'poetry.lock' \
        'go.mod' \
        'Cargo.toml' \
        'Gemfile' \
        'composer.json' \
        'pom.xml' \
        'build.gradle' \
        'build.gradle.kts' \
        'Makefile' \
        'justfile' \
        'Taskfile.yml' \
        'Taskfile.yaml' \
        '.env' \
        '.env.*' \
        '.envrc' \
        'mise.toml'
)"

claude_settings_json="$(
    collect_globs_json "$REPO_ROOT" \
        '.claude/settings.json' \
        '.claude/settings.local.json'
)"

claude_rules_json="$(
    collect_globs_json "$REPO_ROOT" \
        'CLAUDE.md' \
        '.claude/rules/*.md'
)"

claude_hook_files_json="$(
    collect_globs_json "$REPO_ROOT" \
        '.claude/hooks/**'
)"

git_hook_files_json="$(
    collect_globs_json "$REPO_ROOT" \
        '.husky/**' \
        'lefthook.yml' \
        'lefthook.yaml' \
        '.githooks/**'
)"

automation_files_json="$(
    collect_globs_json "$REPO_ROOT" \
        '.github/workflows/*' \
        '.gitlab-ci.yml' \
        '.circleci/config.yml' \
        'azure-pipelines.yml'
)"

protected_candidates_json="$(
    collect_globs_json "$REPO_ROOT" \
        '.env' \
        '.env.*' \
        '.envrc' \
        '*.pem' \
        '*.key' \
        'package-lock.json' \
        'pnpm-lock.yaml' \
        'yarn.lock' \
        'bun.lock' \
        'bun.lockb' \
        'Cargo.lock' \
        'poetry.lock' \
        'composer.lock' \
        'go.sum' \
        '*.tfstate' \
        '*.tfstate.*'
)"

package_scripts_json="$(
    PACKAGE_LIST="$(collect_globs_json "$REPO_ROOT" 'package.json')"
    if [ "$(printf '%s' "$PACKAGE_LIST" | jq 'length')" -eq 0 ]; then
        printf '[]\n'
    else
        while IFS= read -r package_path; do
            [ -n "$package_path" ] || continue
            package_file="$REPO_ROOT/$package_path"
            jq -c --arg path "$package_path" '
                {
                    path: $path,
                    scripts: ((.scripts // {}) | keys | sort)
                }
            ' "$package_file"
        done < <(printf '%s' "$PACKAGE_LIST" | jq -r '.[]') | jq -s '.'
    fi
)"

workspace_kinds_json="$(
    jq -n \
        --argjson markers "$marker_files_json" \
        '
        [
            if ($markers | index("pnpm-workspace.yaml")) then "pnpm-workspace" else empty end,
            if ($markers | index("turbo.json")) then "turborepo" else empty end,
            if ($markers | index("nx.json")) then "nx" else empty end,
            if ($markers | index("package.json")) then "node-package" else empty end,
            if ($markers | index("pyproject.toml")) then "python-project" else empty end,
            if ($markers | index("go.mod")) then "go-module" else empty end,
            if ($markers | index("Cargo.toml")) then "cargo-workspace-or-crate" else empty end
        ] | unique
        '
)"

languages_json="$(
    jq -n \
        --argjson markers "$marker_files_json" \
        '
        [
            if (($markers | index("package.json")) or ($markers | index("tsconfig.json"))) then "javascript-typescript" else empty end,
            if ($markers | index("pyproject.toml")) then "python" else empty end,
            if ($markers | index("go.mod")) then "go" else empty end,
            if ($markers | index("Cargo.toml")) then "rust" else empty end,
            if ($markers | index("Gemfile")) then "ruby" else empty end,
            if ($markers | index("composer.json")) then "php" else empty end,
            if (($markers | index("pom.xml")) or ($markers | index("build.gradle")) or ($markers | index("build.gradle.kts"))) then "jvm" else empty end
        ] | unique
        '
)"

PACKAGE_JSON_COUNT="$(printf '%s' "$package_scripts_json" | jq 'length')"
MONOREPO="false"
if [ "$PACKAGE_JSON_COUNT" -gt 1 ] || [ "$(printf '%s' "$workspace_kinds_json" | jq 'length')" -gt 1 ]; then
    MONOREPO="true"
fi

RECOMMENDED_SETTINGS_TARGET=".claude/settings.json"
if printf '%s' "$claude_settings_json" | jq -e '. | index(".claude/settings.json")' >/dev/null; then
    RECOMMENDED_SETTINGS_TARGET=".claude/settings.json"
elif printf '%s' "$claude_settings_json" | jq -e '. | index(".claude/settings.local.json")' >/dev/null; then
    RECOMMENDED_SETTINGS_TARGET=".claude/settings.local.json"
fi

MANAGED_ROOT=""
if [ -f "$REPO_ROOT/.claude/hooks/generated/manifest.json" ]; then
    MANAGED_ROOT=".claude/hooks/generated"
fi

RESULT_JSON="$(
    jq -n \
        --arg generated_at "$TIMESTAMP_UTC" \
        --arg target_path "$TARGET_PATH" \
        --arg repo_root "$REPO_ROOT" \
        --arg recommended_settings_target "$RECOMMENDED_SETTINGS_TARGET" \
        --arg managed_root "$MANAGED_ROOT" \
        --argjson is_git_repo "$IS_GIT_REPO" \
        --argjson marker_files "$marker_files_json" \
        --argjson claude_settings "$claude_settings_json" \
        --argjson claude_rules "$claude_rules_json" \
        --argjson claude_hook_files "$claude_hook_files_json" \
        --argjson git_hook_files "$git_hook_files_json" \
        --argjson automation_files "$automation_files_json" \
        --argjson protected_candidates "$protected_candidates_json" \
        --argjson package_scripts "$package_scripts_json" \
        --argjson workspace_kinds "$workspace_kinds_json" \
        --argjson languages "$languages_json" \
        --argjson monorepo "$MONOREPO" \
        '
        {
            generated_at: $generated_at,
            target_path: $target_path,
            repo_root: $repo_root,
            is_git_repo: $is_git_repo,
            monorepo: $monorepo,
            recommended_settings_target: $recommended_settings_target,
            existing_managed_hook_root: (if $managed_root == "" then null else $managed_root end),
            workspace_kinds: $workspace_kinds,
            languages: $languages,
            marker_files: $marker_files,
            package_scripts: $package_scripts,
            claude: {
                settings_files: $claude_settings,
                rules_and_memory_files: $claude_rules,
                hook_files: $claude_hook_files
            },
            git_hooks: $git_hook_files,
            automation_files: $automation_files,
            protected_candidates: $protected_candidates
        }
        '
)"

if [ -n "$OUTPUT_FILE" ]; then
    mkdir -p "$(dirname "$OUTPUT_FILE")"
    printf '%s\n' "$RESULT_JSON" > "$OUTPUT_FILE"
else
    printf '%s\n' "$RESULT_JSON"
fi

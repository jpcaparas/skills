#!/usr/bin/env bash
#
# audit_project.sh
#
# Inspect a target repository and report Copilot-cloud-agent-environment facts as JSON.
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

collect_rg_matches_json() {
    local root="$1"
    shift

    (
        cd "$root"
        rg -n --hidden "$@" 2>/dev/null | jq -R . | jq -s .
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

CURRENT_BRANCH=""
DEFAULT_BRANCH=""
if [ "$IS_GIT_REPO" = "true" ]; then
    CURRENT_BRANCH="$(git -C "$REPO_ROOT" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
    DEFAULT_BRANCH="$(
        git -C "$REPO_ROOT" symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null \
            | sed 's#^refs/remotes/origin/##' || true
    )"
fi

marker_files_json="$(
    collect_globs_json "$REPO_ROOT" \
        'package.json' \
        'pnpm-workspace.yaml' \
        'package-lock.json' \
        'pnpm-lock.yaml' \
        'yarn.lock' \
        'bun.lock' \
        'bun.lockb' \
        'pyproject.toml' \
        'requirements.txt' \
        'Pipfile' \
        'poetry.lock' \
        'go.mod' \
        'Cargo.toml' \
        'Gemfile' \
        'pom.xml' \
        'build.gradle' \
        'build.gradle.kts' \
        '*.sln' \
        '*.csproj' \
        'Directory.Build.props' \
        'global.json' \
        '.nvmrc' \
        '.node-version' \
        '.python-version' \
        '.ruby-version' \
        '.java-version'
)"

workflow_files_json="$(
    collect_globs_json "$REPO_ROOT" \
        '.github/workflows/*.yml' \
        '.github/workflows/*.yaml'
)"

copilot_files_json="$(
    collect_globs_json "$REPO_ROOT" \
        '.github/workflows/copilot-setup-steps.yml' \
        '.github/workflows/copilot-setup-steps.yaml' \
        '.github/copilot-instructions.md' \
        '.github/instructions/**/*.instructions.md' \
        'AGENTS.md' \
        'CLAUDE.md' \
        'GEMINI.md'
)"

container_files_json="$(
    collect_globs_json "$REPO_ROOT" \
        '.devcontainer/**' \
        'Dockerfile' \
        'Dockerfile.*' \
        'docker-compose.yml' \
        'docker-compose.yaml' \
        'docker-compose.*.yml' \
        'docker-compose.*.yaml' \
        'compose.yml' \
        'compose.yaml' \
        'compose.*.yml' \
        'compose.*.yaml'
)"

registry_files_json="$(
    collect_globs_json "$REPO_ROOT" \
        '.npmrc' \
        '.yarnrc.yml' \
        'pip.conf' \
        '.pypirc' \
        'poetry.toml' \
        '.cargo/config.toml' \
        'nuget.config' \
        'settings.xml'
)"

toolchain_files_json="$(
    collect_globs_json "$REPO_ROOT" \
        '.nvmrc' \
        '.node-version' \
        '.python-version' \
        '.ruby-version' \
        '.java-version' \
        'global.json' \
        'go.mod'
)"

windows_markers_json="$(
    collect_globs_json "$REPO_ROOT" \
        '*.sln' \
        '*.csproj' \
        'Directory.Build.props' \
        'Directory.Build.targets' \
        'global.json'
)"

package_json_details_json="$(
    PACKAGE_LIST="$(collect_globs_json "$REPO_ROOT" 'package.json')"
    if [ "$PACKAGE_LIST" = "[]" ]; then
        printf '[]\n'
    else
        printf '%s' "$PACKAGE_LIST" | jq -r '.[]' | while IFS= read -r rel_path; do
            jq -c --arg rel_path "$rel_path" '
                {
                    path: $rel_path,
                    scripts: ((.scripts // {}) | keys | sort),
                    packageManager: (.packageManager // null),
                    engines: (.engines // {})
                }
            ' "$REPO_ROOT/$rel_path"
        done | jq -s .
    fi
)"

make_targets_json="$(
    if [ -f "$REPO_ROOT/Makefile" ]; then
        rg -n '^[A-Za-z0-9_.-]+:' "$REPO_ROOT/Makefile" \
            | sed -E 's#^[0-9]+:##; s#:.*$##' \
            | grep -v '^\.' \
            | LC_ALL=C sort -u \
            | jq -R . | jq -s .
    else
        printf '[]\n'
    fi
)"

runner_mentions_json="$(
    if [ "$workflow_files_json" = "[]" ]; then
        printf '[]\n'
    else
        collect_rg_matches_json "$REPO_ROOT" 'self-hosted|windows-|ubuntu-|arc-|runs-on:' .github/workflows
    fi
)"

LFS_DETECTED="false"
if [ -f "$REPO_ROOT/.gitattributes" ] && rg -n 'filter=lfs' "$REPO_ROOT/.gitattributes" >/dev/null 2>&1; then
    LFS_DETECTED="true"
fi

LANGUAGES_JSON="$(
    jq -n --argjson markers "$marker_files_json" '
        [
            if (
                ($markers | index("package.json")) or
                ($markers | index("pnpm-workspace.yaml")) or
                ($markers | index("package-lock.json")) or
                ($markers | index("pnpm-lock.yaml")) or
                ($markers | index("yarn.lock")) or
                ($markers | index("bun.lock")) or
                ($markers | index("bun.lockb"))
            ) then "javascript-typescript" else empty end,
            if (
                ($markers | index("pyproject.toml")) or
                ($markers | index("requirements.txt")) or
                ($markers | index("Pipfile")) or
                ($markers | index("poetry.lock"))
            ) then "python" else empty end,
            if ($markers | index("go.mod")) then "go" else empty end,
            if ($markers | index("Cargo.toml")) then "rust" else empty end,
            if ($markers | index("Gemfile")) then "ruby" else empty end,
            if (($markers | index("pom.xml")) or ($markers | index("build.gradle")) or ($markers | index("build.gradle.kts"))) then "jvm" else empty end,
            if (($markers | map(select(test("\\.sln$|\\.csproj$|global\\.json$|Directory\\.Build\\.props$"))) | length) > 0) then "dotnet" else empty end
        ] | unique
    '
)"

PACKAGE_MANAGERS_JSON="$(
    jq -n \
        --argjson markers "$marker_files_json" \
        --argjson packages "$package_json_details_json" '
        [
            if ($markers | index("package-lock.json")) then "npm" else empty end,
            if ($markers | index("pnpm-lock.yaml")) then "pnpm" else empty end,
            if ($markers | index("yarn.lock")) then "yarn" else empty end,
            if (($markers | index("bun.lock")) or ($markers | index("bun.lockb"))) then "bun" else empty end,
            ($packages[]?.packageManager // empty | split("@")[0])
        ] | map(select(length > 0)) | unique
    '
)"

PACKAGE_JSON_COUNT="$(printf '%s' "$package_json_details_json" | jq 'length')"
MONOREPO="false"
if [ "$PACKAGE_JSON_COUNT" -gt 1 ] || printf '%s' "$marker_files_json" | jq -e '. | index("pnpm-workspace.yaml")' >/dev/null; then
    MONOREPO="true"
fi

RESULT_JSON="$(
    jq -n \
        --arg project_root "$PROJECT_ROOT" \
        --arg repo_root "$REPO_ROOT" \
        --arg current_branch "$CURRENT_BRANCH" \
        --arg default_branch "$DEFAULT_BRANCH" \
        --argjson is_git_repo "$IS_GIT_REPO" \
        --argjson monorepo "$MONOREPO" \
        --argjson marker_files "$marker_files_json" \
        --argjson workflow_files "$workflow_files_json" \
        --argjson copilot_files "$copilot_files_json" \
        --argjson container_files "$container_files_json" \
        --argjson registry_files "$registry_files_json" \
        --argjson toolchain_files "$toolchain_files_json" \
        --argjson windows_markers "$windows_markers_json" \
        --argjson package_json_details "$package_json_details_json" \
        --argjson make_targets "$make_targets_json" \
        --argjson runner_mentions "$runner_mentions_json" \
        --argjson lfs_detected "$LFS_DETECTED" \
        --argjson languages "$LANGUAGES_JSON" \
        --argjson package_managers "$PACKAGE_MANAGERS_JSON" '
        {
            project_root: $project_root,
            repo_root: $repo_root,
            is_git_repo: $is_git_repo,
            current_branch: (if $current_branch == "" then null else $current_branch end),
            default_branch: (if $default_branch == "" then null else $default_branch end),
            monorepo: $monorepo,
            marker_files: $marker_files,
            workflow_files: $workflow_files,
            copilot: {
                workflow_files: ($copilot_files | map(select(test("^\\.github/workflows/copilot-setup-steps\\.(yml|yaml)$")))),
                custom_instruction_files: ($copilot_files | map(select(test("^\\.github/copilot-instructions\\.md$|^\\.github/instructions/|^AGENTS\\.md$|^CLAUDE\\.md$|^GEMINI\\.md$")))),
                has_custom_instructions: (($copilot_files | map(select(test("^\\.github/copilot-instructions\\.md$|^\\.github/instructions/|^AGENTS\\.md$|^CLAUDE\\.md$|^GEMINI\\.md$"))) | length) > 0)
            },
            languages: $languages,
            package_managers: $package_managers,
            package_jsons: $package_json_details,
            make_targets: $make_targets,
            lfs_detected: $lfs_detected,
            container_files: $container_files,
            registry_files: $registry_files,
            toolchain_files: $toolchain_files,
            windows_markers: $windows_markers,
            runner_mentions: $runner_mentions
        }
    '
)"

if [ -n "$OUTPUT_FILE" ]; then
    printf '%s\n' "$RESULT_JSON" > "$OUTPUT_FILE"
else
    printf '%s\n' "$RESULT_JSON"
fi

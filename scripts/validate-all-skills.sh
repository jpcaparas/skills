#!/usr/bin/env bash
#
# validate-all-skills.sh
#
# Run the same validation that the Validate Skills GitHub Actions workflow
# runs, so anything that would break CI gets caught locally first.
#
# This script is the shared source of truth between:
#   1. .github/workflows/validate-skills.yml
#   2. hooks/stop/claude.sh
#   3. hooks/stop/codex.sh
#   4. hooks/stop/devin.sh
#   5. OpenCode Froggy hooks in .opencode/hook/hooks.md
#   6. .husky/pre-push through the package-level validate script
#
# If you change a step here, all callers pick it up.
# For an explicit local Ubuntu/macOS GitHub Actions preflight, use
# scripts/validate-ci-with-act.sh. Do not call it from this script: act invokes
# this canonical validator, so doing so would recurse.
#
# Steps:
#   1. Confirm GitHub Actions, pre-push, and agent stop hooks still route to
#      this canonical validator.
#   2. Confirm README.md lists every installable skill and includes the
#      expected skills.sh install commands.
#   3. Confirm every README skill section has a constrained 16-bit art card
#      stored in that skill's folder.
#   4. For every skills/<name>/ that has a SKILL.md, run validate.py and
#      test_skill.py.
#   5. Confirm skills.sh discovery still works and does not emit Codex
#      skills context-budget warnings.
#
# Usage:
#   bash scripts/validate-all-skills.sh
#

set -euo pipefail

# Some local shells still export the removed GNU grep GREP_OPTIONS variable.
# BSD grep on macOS treats values such as --color=auto as an error, which
# creates noisy environment-specific validation output.
unset GREP_OPTIONS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

resolve_validation_executable() {
    local request="$1"
    local executable_dir resolved

    if [[ "$request" == */* ]]; then
        executable_dir="$(cd "$(dirname "$request")" 2>/dev/null && pwd -P)" || return 1
        resolved="$executable_dir/$(basename "$request")"
        [ -x "$resolved" ] || return 1
        printf '%s\n' "$resolved"
        return 0
    fi

    command -v "$request" 2>/dev/null
}

validation_python_request="${SKILLS_VALIDATION_PYTHON:-}"
if [ -z "$validation_python_request" ] && [ -x "$REPO_ROOT/.venv/bin/python3" ]; then
    validation_python_request="$REPO_ROOT/.venv/bin/python3"
fi
if [ -z "$validation_python_request" ]; then
    validation_python_request="python3"
fi
VALIDATION_PYTHON="$(resolve_validation_executable "$validation_python_request" || true)"

if [ -z "$VALIDATION_PYTHON" ] \
    || ! "$VALIDATION_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
    {
        echo "ERROR: native validation requires Python 3.11 or newer."
        echo "Create the repository .venv with a compatible interpreter; see TESTING.md."
    } >&2
    exit 1
fi

if ! "$VALIDATION_PYTHON" -c 'import openpyxl, yaml' >/dev/null 2>&1; then
    {
        echo "ERROR: native validation requires the pinned Python packages."
        echo "Install them with: $VALIDATION_PYTHON -m pip install -r requirements-validation.txt"
    } >&2
    exit 1
fi

readonly VALIDATION_PYTHON

validation_bun_request="${SKILLS_VALIDATION_BUN:-}"
if [ -z "$validation_bun_request" ]; then
    validation_bun_request="$(command -v bun 2>/dev/null || true)"
fi
if [ -z "$validation_bun_request" ]; then
    standard_bun="${BUN_INSTALL:-${HOME:-}/.bun}/bin/bun"
    if [ -x "$standard_bun" ]; then
        validation_bun_request="$standard_bun"
    fi
fi
VALIDATION_BUN="$(resolve_validation_executable "$validation_bun_request" || true)"
if [ -z "$VALIDATION_BUN" ] || ! "$VALIDATION_BUN" --version >/dev/null 2>&1; then
    {
        echo "ERROR: native validation requires Bun for the scaffold-hooks probes."
        echo "Install Bun and ensure bun is on PATH; see TESTING.md."
    } >&2
    exit 1
fi

readonly VALIDATION_BUN

validation_npx_request="${SKILLS_VALIDATION_NPX:-}"
if [ -z "$validation_npx_request" ]; then
    validation_npx_request="$(command -v npx 2>/dev/null || true)"
fi
VALIDATION_NPX="$(resolve_validation_executable "$validation_npx_request" || true)"
validation_npx_dir="$(dirname "${VALIDATION_NPX:-.}")"
validation_node_request="${SKILLS_VALIDATION_NODE:-}"
if [ -z "$validation_node_request" ] && [ -x "$validation_npx_dir/node" ]; then
    validation_node_request="$validation_npx_dir/node"
fi
if [ -z "$validation_node_request" ]; then
    validation_node_request="$(command -v node 2>/dev/null || true)"
fi
VALIDATION_NODE="$(resolve_validation_executable "$validation_node_request" || true)"
validation_node_dir="$(dirname "${VALIDATION_NODE:-.}")"
if [ -z "$VALIDATION_NPX" ] || [ -z "$VALIDATION_NODE" ] \
    || ! PATH="$validation_node_dir:$validation_npx_dir:$PATH" \
        "$VALIDATION_NPX" --version >/dev/null 2>&1; then
    {
        echo "ERROR: native validation requires npx for the skills discovery probe."
        echo "Install Node.js with npm/npx and ensure npx is on PATH; see TESTING.md."
    } >&2
    exit 1
fi

readonly VALIDATION_NODE VALIDATION_NPX

# Present one collision-proof command directory to every child. Prepending the
# Bun or Node installation directories directly could shadow the selected
# Python (or each other) when those runtimes share a package-manager prefix.
validation_tool_bin="$(mktemp -d "${TMPDIR:-/tmp}/skills-validation-tools.XXXXXX")"
cleanup_validation_tool_bin() {
    local command_name
    for command_name in python python3 bun node npx; do
        if [ -e "$validation_tool_bin/$command_name" ] || [ -L "$validation_tool_bin/$command_name" ]; then
            unlink "$validation_tool_bin/$command_name"
        fi
    done
    rmdir "$validation_tool_bin"
}
trap cleanup_validation_tool_bin EXIT

ln -s "$VALIDATION_PYTHON" "$validation_tool_bin/python"
ln -s "$VALIDATION_PYTHON" "$validation_tool_bin/python3"
ln -s "$VALIDATION_BUN" "$validation_tool_bin/bun"
ln -s "$VALIDATION_NODE" "$validation_tool_bin/node"
ln -s "$VALIDATION_NPX" "$validation_tool_bin/npx"
export PATH="$validation_tool_bin:$PATH"

echo "Checking local and CI validation entrypoint parity"
"$VALIDATION_PYTHON" scripts/test-validation-entrypoint-parity.py
"$VALIDATION_PYTHON" scripts/check-validation-entrypoint-parity.py

echo "Checking the local act matrix wrapper"
bash scripts/test-validate-ci-with-act.sh

echo "Checking stop-validation snapshot caching"
bash scripts/test-agent-stop-checks.sh

echo "Checking README skill coverage"
"$VALIDATION_PYTHON" scripts/test-shared-validator-regressions.py
"$VALIDATION_PYTHON" scripts/validate-readme-skills.py
"$VALIDATION_PYTHON" scripts/validate-skill-art.py
"$VALIDATION_PYTHON" scripts/check-skill-description-budget.py

while IFS= read -r skill; do
    echo "Validating ${skill}"
    "$VALIDATION_PYTHON" "${skill}/scripts/validate.py" "${skill}" < /dev/null
    "$VALIDATION_PYTHON" "${skill}/scripts/test_skill.py" "${skill}" < /dev/null
done < <(find skills -mindepth 1 -maxdepth 1 -type d -exec test -f "{}/SKILL.md" ';' -print | LC_ALL=C sort)

echo "Checking for leaked builder-only placement metadata"
if grep -n -E '^## Recommended Destination$' skills/*/SKILL.md; then
    echo "ERROR: remove builder-only placement sections from shipped SKILL.md files" >&2
    exit 1
fi

# Cross-check: files under skills/ that a fresh CI checkout will NOT see.
# This catches two classes of footgun that each skill's own validate.py
# cannot detect, because validate.py only inspects the working tree:
#
#   1. A required file is hidden from git by the user's global gitignore
#      or $GIT_DIR/info/exclude. Local validation passes (the file is on
#      disk) but CI fails on a fresh checkout (the file was never pushed).
#      This is exactly how `skills/better-writing/AGENTS.md` broke CI.
#
#   2. A new file was created under skills/<name>/ but never `git add`ed.
#      Same symptom: present locally, missing on CI.
#
# Files ignored by an in-tree .gitignore (relative path) are legitimate
# exclusions — e.g. `__pycache__/` — and are not flagged.
if git rev-parse --git-dir >/dev/null 2>&1; then
    echo "Checking for skill files invisible to a fresh CI checkout"

    invisible_hits=()

    # (1) On-disk files hidden by an external ignore source.
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        source_line="$(git check-ignore -v -- "$file" 2>/dev/null || true)"
        source_file="${source_line%%:*}"
        if [[ "$source_file" == /* ]] || [[ "$source_file" == *".git/info/exclude" ]]; then
            invisible_hits+=("${file} (ignored by ${source_file})")
        fi
    done < <(git ls-files --others --ignored --exclude-standard skills 2>/dev/null)

    # (2) On-disk files that are simply untracked (user forgot to git add).
    # Agent stop hooks validate an in-progress working tree before the agent's
    # final answer, so new skill files may be intentionally untracked at that
    # point. Keep manual/CI validation strict, but let hook-mode validation
    # validate the files on disk without forcing the agent to stage them.
    if [ "${SKILLS_VALIDATE_ALLOW_UNTRACKED_SKILL_WORKTREE:-0}" != "1" ]; then
        while IFS= read -r file; do
            [ -z "$file" ] && continue
            invisible_hits+=("${file} (untracked — run 'git add')")
        done < <(git ls-files --others --exclude-standard skills 2>/dev/null)
    fi

    if [ "${#invisible_hits[@]}" -gt 0 ]; then
        {
            echo
            echo "ERROR: skill files are invisible to a fresh CI checkout:"
            printf '  - %s\n' "${invisible_hits[@]}"
            echo
            echo "A local 'git status' may still look clean if the file is hidden by"
            echo "your global gitignore. Fix by committing the file (after adding a"
            echo "negation to .gitignore if needed), or remove it from the working tree."
        } >&2
        exit 1
    fi
fi

echo "Checking skills.sh discovery and Codex skills context budget"
bash scripts/test-codex-skills-context-budget.sh
bash scripts/check-codex-skills-context-budget.sh

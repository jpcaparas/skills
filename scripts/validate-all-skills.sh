#!/usr/bin/env bash
#
# The one validation entrypoint. GitHub Actions, the pre-push hook, and the
# agent stop gate (scripts/agent-stop-checks.sh) all run this script, so a
# check added here applies everywhere.
#
# It checks what breaks installs and hosts: the skill inventory, package
# integrity, the README catalogue and cards, each skill's own tests, and the
# Codex context budget. It does not lint how a skill words its instructions.
#
# Usage: pnpm validate

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
        echo "Create the repository .venv with a compatible interpreter; see the Validation section in AGENTS.md."
    } >&2
    exit 1
fi

if ! "$VALIDATION_PYTHON" -c 'import PIL, openpyxl, playwright.async_api, yaml' >/dev/null 2>&1; then
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
        echo "ERROR: native validation requires Bun."
        echo "Install Bun and ensure bun is on PATH; see the Validation section in AGENTS.md."
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
        echo "Install Node.js with npm/npx and ensure npx is on PATH; see the Validation section in AGENTS.md."
    } >&2
    exit 1
fi

readonly VALIDATION_NODE VALIDATION_NPX

# Present the selected tools to every child as one command directory.
# Prepending their installation directories could shadow each other when
# runtimes share a package-manager prefix. Python gets a wrapper, not a
# symlink: an interpreter reached through a symlink loses its virtualenv.
source scripts/executable-temp-dir.sh
validation_tool_bin="$(create_executable_temp_dir "$REPO_ROOT" "skills-validation-tools")"
trap 'cleanup_executable_temp_dir "$validation_tool_bin"' EXIT

for command_name in python python3; do
    printf '#!/usr/bin/env bash\nexec %q "$@"\n' "$VALIDATION_PYTHON" \
        >"$validation_tool_bin/$command_name"
    chmod +x "$validation_tool_bin/$command_name"
done
ln -s "$VALIDATION_BUN" "$validation_tool_bin/bun"
ln -s "$VALIDATION_NODE" "$validation_tool_bin/node"
ln -s "$VALIDATION_NPX" "$validation_tool_bin/npx"
export PATH="$validation_tool_bin:$PATH"

echo "Checking repository tooling"
bash scripts/test-executable-temp-dir.sh
bash scripts/test-orb-lifecycle.sh
bun scripts/test-repository-hooks.ts
python3 scripts/test-agent-stop-checks.py
python3 scripts/test-skill-catalog.py
python3 scripts/test-shared-validator-regressions.py

echo "Checking skill packages, README catalogue and cards"
python3 scripts/validate-skills.py
python3 scripts/validate-readme-skills.py
python3 scripts/validate-skill-art.py

# Resolve the complete inventory before running any package. A failing reader
# in process substitution would otherwise let Bash silently skip every skill.
skill_inventory="$(python3 scripts/skill_catalog.py --skills-root skills)"
while IFS= read -r skill; do
    compgen -G "${skill}/scripts/test_*.py" >/dev/null || continue
    echo "Testing ${skill}"
    python3 -m unittest discover -s "${skill}/scripts" -p 'test_*.py' </dev/null
done <<<"$skill_inventory"

# A file that exists locally but never reaches a fresh checkout passes here and
# fails in CI. Two causes: a user-global gitignore (or .git/info/exclude) hides
# it, or it was never staged. The agent stop gate validates work in progress,
# so it allows untracked files.
if git rev-parse --git-dir >/dev/null 2>&1; then
    echo "Checking for skill files a fresh checkout would not contain"
    invisible_files=()

    while IFS= read -r file; do
        [ -n "$file" ] || continue
        ignore_source="$(git check-ignore -v -- "$file" 2>/dev/null || true)"
        ignore_source="${ignore_source%%:*}"
        if [[ "$ignore_source" == /* ]] || [[ "$ignore_source" == *".git/info/exclude" ]]; then
            invisible_files+=("${file} (ignored by ${ignore_source})")
        fi
    done < <(git ls-files --others --ignored --exclude-standard skills)

    if [ "${SKILLS_VALIDATE_ALLOW_UNTRACKED_SKILL_WORKTREE:-0}" != "1" ]; then
        while IFS= read -r file; do
            [ -n "$file" ] || continue
            invisible_files+=("${file} (untracked; run 'git add')")
        done < <(git ls-files --others --exclude-standard skills)
    fi

    if [ "${#invisible_files[@]}" -gt 0 ]; then
        {
            echo "ERROR: skill files exist locally but would be missing from a fresh checkout:"
            printf '  - %s\n' "${invisible_files[@]}"
        } >&2
        exit 1
    fi
fi

echo "Checking skills.sh discovery and Codex skills context budget"
bash scripts/test-codex-skills-context-budget.sh
bash scripts/check-codex-skills-context-budget.sh

echo "All validation checks passed."

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
# For a containerized Ubuntu GitHub Actions preflight before pushing, use
# scripts/validate-ci-with-act.sh, which wraps this workflow through act.
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

echo "Checking local and CI validation entrypoint parity"
python3 scripts/check-validation-entrypoint-parity.py

echo "Checking stop-validation snapshot caching"
bash scripts/test-agent-stop-checks.sh

echo "Checking README skill coverage"
python3 scripts/validate-readme-skills.py
python3 scripts/validate-skill-art.py
python3 scripts/check-skill-description-budget.py

while IFS= read -r skill; do
    echo "Validating ${skill}"
    python3 "${skill}/scripts/validate.py" "${skill}" < /dev/null
    python3 "${skill}/scripts/test_skill.py" "${skill}" < /dev/null
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
bash scripts/check-codex-skills-context-budget.sh

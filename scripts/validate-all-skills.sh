#!/usr/bin/env bash
#
# validate-all-skills.sh
#
# Run the same validation that the Validate Skills GitHub Actions workflow
# runs, so anything that would break CI gets caught locally first.
#
# This script is the shared source of truth between:
#   1. .github/workflows/validate-skills.yml
#   2. .claude/hooks/generated/events/stop.sh
#
# If you change a step here, both callers pick it up.
#
# Steps:
#   1. Confirm README.md lists every installable skill and includes the
#      expected skills.sh install commands.
#   2. For every skills/<name>/ that has a SKILL.md, run validate.py and
#      test_skill.py.
#   3. Confirm skills.sh discovery still works via `npx --yes skills add .
#      --list`.
#
# Usage:
#   bash scripts/validate-all-skills.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "Checking README skill coverage"
python3 scripts/validate-readme-skills.py

while IFS= read -r skill; do
    echo "Validating ${skill}"
    python3 "${skill}/scripts/validate.py" "${skill}"
    python3 "${skill}/scripts/test_skill.py" "${skill}"
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
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        invisible_hits+=("${file} (untracked — run 'git add')")
    done < <(git ls-files --others --exclude-standard skills 2>/dev/null)

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

echo "Checking skills.sh discovery"
npx --yes skills add . --list

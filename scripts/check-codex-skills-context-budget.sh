#!/usr/bin/env bash
#
# check-codex-skills-context-budget.sh
#
# Verify local skill discovery returns every on-disk skill exactly once and
# does not emit Codex skills context-budget warnings. Codex keeps only the
# initial skill name, description, and path in prompt context, so omissions or
# shortening warnings are packaging failures that must be fixed before stopping
# work.
#
# Usage:
#   bash scripts/check-codex-skills-context-budget.sh
#
# Tests may set both variables below to validate a captured CLI fixture without
# invoking npx:
#   SKILLS_DISCOVERY_OUTPUT_FILE=/path/to/output.txt
#   SKILLS_DISCOVERY_SKILLS_ROOT=/path/to/skills
#

set -euo pipefail

# Keep this script stable on macOS shells that inherited GNU-only grep options.
unset GREP_OPTIONS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

SKILLS_ROOT="${SKILLS_DISCOVERY_SKILLS_ROOT:-$REPO_ROOT/skills}"
DISCOVERY_FIXTURE="${SKILLS_DISCOVERY_OUTPUT_FILE:-}"

OUTPUT_FILE="$(mktemp)"
PLAIN_FILE="$(mktemp)"
EXPECTED_NAMES_FILE="$(mktemp)"
DISCOVERED_NAMES_FILE="$(mktemp)"
DISCOVERED_UNIQUE_FILE="$(mktemp)"
DUPLICATE_NAMES_FILE="$(mktemp)"
MISSING_NAMES_FILE="$(mktemp)"
UNEXPECTED_NAMES_FILE="$(mktemp)"
trap 'rm -f "$OUTPUT_FILE" "$PLAIN_FILE" "$EXPECTED_NAMES_FILE" "$DISCOVERED_NAMES_FILE" "$DISCOVERED_UNIQUE_FILE" "$DUPLICATE_NAMES_FILE" "$MISSING_NAMES_FILE" "$UNEXPECTED_NAMES_FILE"' EXIT

if [ -n "$DISCOVERY_FIXTURE" ]; then
    if [ ! -f "$DISCOVERY_FIXTURE" ]; then
        echo "ERROR: discovery output fixture not found: $DISCOVERY_FIXTURE" >&2
        exit 1
    fi
    cp "$DISCOVERY_FIXTURE" "$OUTPUT_FILE"
else
    if ! npx --yes skills add . --list >"$OUTPUT_FILE" 2>&1; then
        cat "$OUTPUT_FILE" >&2
        exit 1
    fi
fi

perl -pe 's/\e\[[0-9;?]*[ -\/]*[@-~]//g' "$OUTPUT_FILE" >"$PLAIN_FILE"

if grep -Eiq 'Skill descriptions were shortened|2% skills context budget|Disable unused skills or plugins|skills were omitted|some skills may be omitted' "$PLAIN_FILE"; then
    cat "$PLAIN_FILE" >&2
    {
        echo
        echo "ERROR: Codex skills context-budget warning detected."
        echo
        echo "Codex starts with each skill's name, description, and path in context."
        echo "When the available skills list exceeds the skills budget, Codex shortens"
        echo "descriptions first and may eventually omit skills from the initial list."
        echo
        echo "Fix by keeping canonical SKILL.md descriptions concise and front-loaded."
        echo "For local-only pressure from unrelated installed capabilities, disable"
        echo "unused skills or plugins in ~/.codex/config.toml and restart Codex."
    } >&2
    exit 1
fi

# The skills CLI prints one ungrouped skill name on a tree line with four
# spaces. Descriptions use deeper indentation, so a single-word description
# cannot be mistaken for a discovered name. Accept two to four spaces to retain
# compatibility with the CLI's well-known-source rendering.
LC_ALL=C sed -n -E 's/^│ {2,4}([a-z0-9][a-z0-9-]*)$/\1/p' "$PLAIN_FILE" \
    | LC_ALL=C sort >"$DISCOVERED_NAMES_FILE"
LC_ALL=C uniq "$DISCOVERED_NAMES_FILE" >"$DISCOVERED_UNIQUE_FILE"
LC_ALL=C uniq -d "$DISCOVERED_NAMES_FILE" >"$DUPLICATE_NAMES_FILE"

if [ ! -d "$SKILLS_ROOT" ]; then
    echo "ERROR: skills root not found: $SKILLS_ROOT" >&2
    exit 1
fi

SYMLINKED_SKILL_MD="$({
    find "$SKILLS_ROOT" -mindepth 2 -maxdepth 2 -type l -name SKILL.md -print -quit
} 2>/dev/null)"
if [ -n "$SYMLINKED_SKILL_MD" ]; then
    echo "ERROR: installable SKILL.md must not be a symlink: $SYMLINKED_SKILL_MD" >&2
    exit 1
fi

# Keep expected discovery aligned with the repository-wide validator: only
# direct child directories containing a regular SKILL.md are installable.
while IFS= read -r skill_dir; do
    printf '%s\n' "${skill_dir##*/}"
done < <(
    find "$SKILLS_ROOT" -mindepth 1 -maxdepth 1 -type d \
        -exec test -f "{}/SKILL.md" ';' \
        -exec test ! -L "{}/SKILL.md" ';' -print \
        | LC_ALL=C sort
) >"$EXPECTED_NAMES_FILE"

if [ ! -s "$EXPECTED_NAMES_FILE" ]; then
    echo "ERROR: no installable skills found under $SKILLS_ROOT" >&2
    exit 1
fi

LC_ALL=C comm -23 "$EXPECTED_NAMES_FILE" "$DISCOVERED_UNIQUE_FILE" >"$MISSING_NAMES_FILE"
LC_ALL=C comm -13 "$EXPECTED_NAMES_FILE" "$DISCOVERED_UNIQUE_FILE" >"$UNEXPECTED_NAMES_FILE"

discovery_failed=0
if [ ! -s "$DISCOVERED_NAMES_FILE" ]; then
    echo "ERROR: skills discovery output contained no parseable skill names." >&2
    discovery_failed=1
fi
if [ -s "$DUPLICATE_NAMES_FILE" ]; then
    echo "ERROR: duplicate skill names in discovery output:" >&2
    sed 's/^/  - /' "$DUPLICATE_NAMES_FILE" >&2
    discovery_failed=1
fi
if [ -s "$MISSING_NAMES_FILE" ]; then
    echo "ERROR: on-disk skills missing from discovery output:" >&2
    sed 's/^/  - /' "$MISSING_NAMES_FILE" >&2
    discovery_failed=1
fi
if [ -s "$UNEXPECTED_NAMES_FILE" ]; then
    echo "ERROR: unexpected skill names in discovery output:" >&2
    sed 's/^/  - /' "$UNEXPECTED_NAMES_FILE" >&2
    discovery_failed=1
fi
if [ "$discovery_failed" -ne 0 ]; then
    exit 1
fi

cat "$OUTPUT_FILE"

#!/usr/bin/env bash
#
# check-codex-skills-context-budget.sh
#
# Verify local skill discovery does not emit Codex skills context-budget
# warnings. Codex keeps only the initial skill name, description, and path in
# prompt context, so this repository treats any budget warning as a packaging
# failure that must be fixed before stopping work.
#
# Usage:
#   bash scripts/check-codex-skills-context-budget.sh
#

set -euo pipefail

# Keep this script stable on macOS shells that inherited GNU-only grep options.
unset GREP_OPTIONS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

OUTPUT_FILE="$(mktemp)"
PLAIN_FILE="$(mktemp)"
trap 'rm -f "$OUTPUT_FILE" "$PLAIN_FILE"' EXIT

discovery_command=()
if [ "${SKILLS_VALIDATE_OFFLINE:-0}" = "1" ]; then
    if skills_path="$(command -v skills 2>/dev/null)" && [ -n "$skills_path" ]; then
        discovery_command=("$skills_path")
    elif [ -n "${HOME:-}" ]; then
        cached_skills=""
        for candidate in "$HOME"/.npm/_npx/*/node_modules/.bin/skills; do
            [ -x "$candidate" ] || continue
            if [ -z "$cached_skills" ] || [ "$candidate" -nt "$cached_skills" ]; then
                cached_skills="$candidate"
            fi
        done
        if [ -n "$cached_skills" ]; then
            discovery_command=("$cached_skills")
        fi
    fi

    if [ "${#discovery_command[@]}" -eq 0 ]; then
        echo "SKIP: skills discovery CLI is not installed or cached for offline validation."
        exit 0
    fi
else
    discovery_command=(npx --yes skills)
fi

if ! "${discovery_command[@]}" add . --list >"$OUTPUT_FILE" 2>&1; then
    if [ "${SKILLS_VALIDATE_OFFLINE:-0}" = "1" ]; then
        echo "SKIP: cached skills discovery CLI is not executable in this hook sandbox."
        exit 0
    fi
    cat "$OUTPUT_FILE" >&2
    exit 1
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

cat "$OUTPUT_FILE"

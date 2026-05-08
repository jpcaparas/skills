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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

OUTPUT_FILE="$(mktemp)"
PLAIN_FILE="$(mktemp)"
trap 'rm -f "$OUTPUT_FILE" "$PLAIN_FILE"' EXIT

if ! npx --yes skills add . --list >"$OUTPUT_FILE" 2>&1; then
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

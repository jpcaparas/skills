#!/usr/bin/env bash
#
# scaffold.sh — Create a new skill directory with all fixtures.
#
# Usage:
#   ./scaffold.sh <skill-name> [blueprint-type]
#   ./scaffold.sh <skill-name> [blueprint-type] --output-root /path/to/skills
#   ./scaffold.sh <skill-name> [blueprint-type] --dry-run
#
# Blueprint types: api-wrapper, cli-tool, progressive-docs
# If no blueprint is given, creates a minimal SKILL.md with frontmatter placeholder.
#
# Examples:
#   ./scaffold.sh stripe-api api-wrapper
#   ./scaffold.sh my-tool cli-tool
#   ./scaffold.sh aws-reference progressive-docs
#   ./scaffold.sh quick-util
#   ./scaffold.sh ffmpeg-helper cli-tool --output-root ~/.codex/skills
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_CREATOR_DIR="$(dirname "$SCRIPT_DIR")"
TEMPLATES_DIR="$SKILL_CREATOR_DIR/templates"
OUTPUT_ROOT=""
DRY_RUN=0

usage() {
    echo "Usage: $0 <skill-name> [blueprint-type] [--output-root DIR] [--dry-run]"
    echo ""
    echo "Blueprint types: api-wrapper, cli-tool, progressive-docs"
    echo "If no blueprint is given, creates a minimal skill."
}

# --- Argument parsing ---

POSITIONAL=()
while [ $# -gt 0 ]; do
    case "$1" in
        --output-root)
            if [ $# -lt 2 ]; then
                echo "Error: --output-root requires a directory path."
                exit 1
            fi
            OUTPUT_ROOT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done

set -- "${POSITIONAL[@]}"

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    usage
    exit 1
fi

SKILL_NAME="$1"
BLUEPRINT="${2:-minimal}"

# --- Validate skill name ---

if ! echo "$SKILL_NAME" | grep -qE '^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'; then
    echo "Error: skill name must be lowercase letters, digits, and hyphens only."
    echo "  - Must start and end with a letter or digit"
    echo "  - No consecutive hyphens"
    echo "  Got: '$SKILL_NAME'"
    exit 1
fi

if [ ${#SKILL_NAME} -lt 1 ] || [ ${#SKILL_NAME} -gt 64 ]; then
    echo "Error: skill name must be 1-64 characters. Got: ${#SKILL_NAME}"
    exit 1
fi

# --- Validate blueprint type ---

case "$BLUEPRINT" in
    api-wrapper|cli-tool|progressive-docs|minimal)
        ;;
    *)
        echo "Error: unknown blueprint type '$BLUEPRINT'"
        echo "Valid types: api-wrapper, cli-tool, progressive-docs"
        exit 1
        ;;
esac

# --- Determine output directory ---

if [ -z "$OUTPUT_ROOT" ]; then
    python3 "$SCRIPT_DIR/infer_destination.py" --format text --skill-name "$SKILL_NAME"
    OUTPUT_ROOT="$(python3 "$SCRIPT_DIR/infer_destination.py" --format path)"
else
    OUTPUT_ROOT="${OUTPUT_ROOT/#\~/$HOME}"
fi

mkdir -p "$OUTPUT_ROOT"
OUTPUT_ROOT="$(cd "$OUTPUT_ROOT" && pwd -P)"
OUTPUT_DIR="$OUTPUT_ROOT/$SKILL_NAME"

if [ -d "$OUTPUT_DIR" ]; then
    echo "Error: directory '$OUTPUT_DIR' already exists."
    exit 1
fi

echo "Creating skill: $SKILL_NAME (blueprint: $BLUEPRINT)"
echo "Root: $OUTPUT_ROOT"
echo "Location: $OUTPUT_DIR"

if [ "$DRY_RUN" -eq 1 ]; then
    echo ""
    echo "Dry run only. No files created."
    exit 0
fi

# --- Create directory structure ---

mkdir -p "$OUTPUT_DIR"/{references,scripts,templates,evals,assets,agents}

# --- Add .gitkeep to all directories ---

for dir in scripts templates assets agents; do
    touch "$OUTPUT_DIR/$dir/.gitkeep"
done

# --- Create evals stub ---

cat > "$OUTPUT_DIR/evals/evals.json" << EVALEOF
{
  "skill_name": "$SKILL_NAME",
  "created_by": "skill-creator-advanced",
  "evals": []
}
EVALEOF

# --- Create SKILL.md based on blueprint ---

case "$BLUEPRINT" in
    api-wrapper)
        if [ -f "$TEMPLATES_DIR/api-wrapper/SKILL.md" ]; then
            sed "s/{{SKILL_NAME}}/$SKILL_NAME/g" "$TEMPLATES_DIR/api-wrapper/SKILL.md" > "$OUTPUT_DIR/SKILL.md"
            # Copy reference templates if they exist
            for ref in api.md patterns.md configuration.md gotchas.md; do
                if [ -f "$TEMPLATES_DIR/api-wrapper/references/$ref" ]; then
                    sed "s/{{SKILL_NAME}}/$SKILL_NAME/g" "$TEMPLATES_DIR/api-wrapper/references/$ref" > "$OUTPUT_DIR/references/$ref"
                fi
            done
        else
            echo "Warning: api-wrapper template not found at $TEMPLATES_DIR/api-wrapper/SKILL.md"
            echo "Creating minimal SKILL.md instead."
            BLUEPRINT="minimal"
        fi
        ;;

    cli-tool)
        if [ -f "$TEMPLATES_DIR/cli-tool/SKILL.md" ]; then
            sed "s/{{SKILL_NAME}}/$SKILL_NAME/g" "$TEMPLATES_DIR/cli-tool/SKILL.md" > "$OUTPUT_DIR/SKILL.md"
            for ref in commands.md patterns.md configuration.md gotchas.md; do
                if [ -f "$TEMPLATES_DIR/cli-tool/references/$ref" ]; then
                    sed "s/{{SKILL_NAME}}/$SKILL_NAME/g" "$TEMPLATES_DIR/cli-tool/references/$ref" > "$OUTPUT_DIR/references/$ref"
                fi
            done
        else
            echo "Warning: cli-tool template not found at $TEMPLATES_DIR/cli-tool/SKILL.md"
            echo "Creating minimal SKILL.md instead."
            BLUEPRINT="minimal"
        fi
        ;;

    progressive-docs)
        if [ -f "$TEMPLATES_DIR/progressive-docs/SKILL.md" ]; then
            sed "s/{{SKILL_NAME}}/$SKILL_NAME/g" "$TEMPLATES_DIR/progressive-docs/SKILL.md" > "$OUTPUT_DIR/SKILL.md"
            for ref in shared.md; do
                if [ -f "$TEMPLATES_DIR/progressive-docs/references/$ref" ]; then
                    sed "s/{{SKILL_NAME}}/$SKILL_NAME/g" "$TEMPLATES_DIR/progressive-docs/references/$ref" > "$OUTPUT_DIR/references/$ref"
                fi
            done
        else
            echo "Warning: progressive-docs template not found at $TEMPLATES_DIR/progressive-docs/SKILL.md"
            echo "Creating minimal SKILL.md instead."
            BLUEPRINT="minimal"
        fi
        ;;
esac

# Minimal fallback (also the default)
if [ "$BLUEPRINT" = "minimal" ]; then
    cat > "$OUTPUT_DIR/SKILL.md" << SKILLEOF
---
name: $SKILL_NAME
description: "TODO: Describe what this skill does and when to trigger it."
---

# ${SKILL_NAME}

TODO: One-line summary of what this skill does.

## Quick Reference

| Operation | How |
|-----------|-----|
| TODO | TODO |

## Decision Tree

What do you need to do?

- TODO: First option -> references/TODO.md
- TODO: Second option -> references/TODO.md

## Gotchas

1. TODO: First non-obvious pitfall
2. TODO: Second non-obvious pitfall
3. TODO: Third non-obvious pitfall

## Reading Guide

| Task | Read |
|------|------|
| TODO | references/TODO.md |
SKILLEOF

    # Add a placeholder reference
    touch "$OUTPUT_DIR/references/.gitkeep"
fi

# --- Remove .gitkeep from directories that now have files ---

for dir in references evals; do
    if [ "$(ls -A "$OUTPUT_DIR/$dir" | grep -v .gitkeep | head -1)" ]; then
        rm -f "$OUTPUT_DIR/$dir/.gitkeep"
    fi
done

# --- Summary ---

echo ""
echo "Skill created successfully:"
echo ""
find "$OUTPUT_DIR" -type f | sort | while read -r f; do
    echo "  ${f#$OUTPUT_DIR/}"
done
echo ""
echo "Next steps:"
echo "  1. Edit SKILL.md to fill in placeholders"
echo "  2. Add reference files to references/"
echo "  3. Add test cases to evals/evals.json"
echo "  4. Run: python3 $SKILL_CREATOR_DIR/scripts/validate.py $OUTPUT_DIR"

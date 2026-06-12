#!/usr/bin/env bash
#
# scaffold_all_hooks.sh
#
# Compose the bundled Claude Code, Codex, GitHub Copilot, Devin CLI, and
# OpenCode harness scaffolders (harnesses/<name>/) into one shared repo-owned
# hooks/ tree (Copilot and OpenCode keep their own documented config surfaces).

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  scaffold_all_hooks.sh --project DIR [--plan FILE] [--mode additive|overhaul] [--harnesses LIST] [--ensure-codex-feature project|user|off] [--home DIR] [--cleanup-legacy true|false] [--dry-run]

Options:
  --project DIR                  Target project root.
  --plan FILE                    Universal scaffold-hooks plan. Defaults to templates/hook-plan.example.json.
  --mode MODE                    additive or overhaul. Overrides plan mode.
  --harnesses LIST               Comma-separated subset: claude,codex,copilot,devin,opencode.
  --ensure-codex-feature SCOPE   Override Codex feature enablement scope.
  --home DIR                     Home directory override for Codex/OpenCode helper scripts.
  --cleanup-legacy true|false    Remove legacy managed generated folders after migration. Default from plan, then true.
  --dry-run                      Print intended child operations without writing files.
  -h, --help                     Show this help text.
EOF
}

require_command() {
    local name="$1"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "Required command is missing: $name" >&2
        exit 1
    fi
}

json_string_array_from_csv() {
    local csv="$1"
    jq -nc --arg csv "$csv" '
        $csv
        | split(",")
        | map(gsub("^\\s+|\\s+$"; ""))
        | map(select(length > 0))
    '
}

contains_harness() {
    local harness="$1"
    printf '%s' "$HARNESS_LIST_JSON" | jq -e --arg harness "$harness" 'index($harness) != null' >/dev/null
}

validate_harnesses() {
    local unknown
    unknown="$(
        printf '%s' "$HARNESS_LIST_JSON" \
            | jq -r '.[] | select(. != "claude" and . != "codex" and . != "copilot" and . != "devin" and . != "opencode")'
    )"
    if [ -n "$unknown" ]; then
        echo "Unknown harness name(s):" >&2
        printf '  - %s\n' $unknown >&2
        exit 1
    fi
}

resolve_project() {
    local project="$1"
    if [ ! -d "$project" ]; then
        echo "Project directory does not exist: $project" >&2
        exit 1
    fi
    (cd "$project" && pwd -P)
}

normalize_plan_path() {
    local plan="$1"
    if [ ! -f "$plan" ]; then
        echo "Plan file does not exist: $plan" >&2
        exit 1
    fi
    (cd "$(dirname "$plan")" && printf '%s/%s\n' "$(pwd -P)" "$(basename "$plan")")
}

strip_legacy_nested_hooks_file() {
    local file="$1"
    [ -f "$file" ] || return 0

    local tmp
    tmp="$(mktemp)"
    jq --argjson roots "$LEGACY_ROOTS_JSON" '
        def legacy_command:
            (.type == "command")
            and ((.command // "") as $command | any($roots[]; $command | contains(.)));

        (.hooks // {}) as $hooks
        | .hooks = (
            $hooks
            | with_entries(
                .value |= (
                    map(
                        .hooks = ((.hooks // []) | map(select(legacy_command | not)))
                    )
                    | map(select((.hooks | length) > 0))
                )
            )
            | with_entries(select((.value | length) > 0))
        )
    ' "$file" > "$tmp"
    mv "$tmp" "$file"
}

strip_legacy_devin_hooks_file() {
    local file="$1"
    [ -f "$file" ] || return 0

    local tmp
    tmp="$(mktemp)"
    jq --argjson roots "$LEGACY_ROOTS_JSON" '
        def legacy_command:
            (.type == "command")
            and ((.command // "") as $command | any($roots[]; $command | contains(.)));

        if type == "object" then
            with_entries(
                .value |= (
                    map(
                        .hooks = ((.hooks // []) | map(select(legacy_command | not)))
                    )
                    | map(select((.hooks | length) > 0))
                )
            )
            | with_entries(select((.value | length) > 0))
        else
            {}
        end
    ' "$file" > "$tmp"
    mv "$tmp" "$file"
}

strip_legacy_config_entries() {
    strip_legacy_nested_hooks_file "$PROJECT_ROOT/.claude/settings.json"
    strip_legacy_nested_hooks_file "$PROJECT_ROOT/.codex/hooks.json"
    strip_legacy_devin_hooks_file "$PROJECT_ROOT/.devin/hooks.v1.json"
}

cleanup_legacy_managed_roots() {
    local base
    for base in ".claude/hooks" ".codex/hooks" ".devin/hooks"; do
        local generated="$PROJECT_ROOT/$base/generated"
        if [ -f "$generated/manifest.json" ]; then
            rm -rf "$generated"
            rm -f "$PROJECT_ROOT/$base/README.md" "$PROJECT_ROOT/$base/plan.json"
            rmdir "$PROJECT_ROOT/$base" 2>/dev/null || true
        fi
    done
}

cleanup_harness_state() {
    local harness="$1"
    local hooks_root_abs="$PROJECT_ROOT/$HOOKS_ROOT"

    case "$harness" in
        claude|codex|devin)
            rm -rf "$hooks_root_abs/.state/$harness"
            if [ -d "$hooks_root_abs" ]; then
                find "$hooks_root_abs" -mindepth 2 -maxdepth 2 \
                    \( -name "$harness.sh" -o -name "$harness.json" \) \
                    -delete 2>/dev/null || true
            fi
            ;;
        opencode|copilot)
            # OpenCode and Copilot harness scaffolders own their managed cleanup
            # (.opencode/plugins/.managed and .github/copilot/hooks/generated).
            ;;
    esac
}

fallback_plan_for_harness() {
    local harness="$1"
    case "$harness" in
        claude)
            if [ -f "$PROJECT_ROOT/.claude/hooks/plan.json" ]; then
                printf '%s\n' "$PROJECT_ROOT/.claude/hooks/plan.json"
            else
                printf '%s\n' "$HARNESSES_ROOT/claude/templates/hook-plan.example.json"
            fi
            ;;
        codex)
            if [ -f "$PROJECT_ROOT/.codex/hooks/plan.json" ]; then
                printf '%s\n' "$PROJECT_ROOT/.codex/hooks/plan.json"
            else
                printf '%s\n' "$HARNESSES_ROOT/codex/templates/hook-plan.example.json"
            fi
            ;;
        devin)
            if [ -f "$PROJECT_ROOT/.devin/hooks/plan.json" ]; then
                printf '%s\n' "$PROJECT_ROOT/.devin/hooks/plan.json"
            else
                printf '%s\n' "$HARNESSES_ROOT/devin/templates/hook-plan.example.json"
            fi
            ;;
        opencode)
            printf '%s\n' "$HARNESSES_ROOT/opencode/templates/hook-plan.example.json"
            ;;
        copilot)
            printf '%s\n' "$HARNESSES_ROOT/copilot/templates/hook-plan.example.json"
            ;;
    esac
}

build_child_plan() {
    local harness="$1"
    local output="$2"
    local fallback
    local child_mode="additive"

    fallback="$(fallback_plan_for_harness "$harness")"
    if [ "$harness" = "opencode" ] || [ "$harness" = "copilot" ]; then
        child_mode="$MODE"
    fi

    jq -n \
        --slurpfile universal "$PLAN_FILE" \
        --slurpfile fallback "$fallback" \
        --arg harness "$harness" \
        --arg mode "$child_mode" \
        --arg hooks_root "$HOOKS_ROOT" '
        (($universal[0].plans[$harness] // null) // $fallback[0]) as $plan
        | $plan
        | .mode = $mode
        | if $harness == "opencode" then
            .hooks_root = $hooks_root
          elif $harness == "copilot" then
            .
          else
            .managed_root = $hooks_root
          end
        | if $harness == "claude" then
            .settings_target = (.settings_target // ".claude/settings.json")
          elif $harness == "codex" then
            .hooks_target = (.hooks_target // ".codex/hooks.json")
          elif $harness == "devin" then
            .hooks_target = (.hooks_target // ".devin/hooks.v1.json")
          elif $harness == "copilot" then
            .hooks_target = (.hooks_target // ".github/hooks/copilot-hooks.json")
          else
            .
          end
    ' > "$output"
}

run_child_scaffold() {
    local harness="$1"
    local plan="$2"

    case "$harness" in
        claude)
            local args=(--project "$PROJECT_ROOT" --plan "$plan")
            if [ "$DRY_RUN" = "true" ]; then
                args+=(--dry-run)
            fi
            bash "$HARNESSES_ROOT/claude/scripts/scaffold_hooks.sh" "${args[@]}"
            ;;
        codex)
            local args=(--project "$PROJECT_ROOT" --plan "$plan")
            if [ -n "$ENSURE_CODEX_FEATURE" ]; then
                args+=(--ensure-feature "$ENSURE_CODEX_FEATURE")
            fi
            if [ -n "$HOME_OVERRIDE" ]; then
                args+=(--home "$HOME_OVERRIDE")
            fi
            if [ "$DRY_RUN" = "true" ]; then
                args+=(--dry-run)
            fi
            bash "$HARNESSES_ROOT/codex/scripts/scaffold_hooks.sh" "${args[@]}"
            ;;
        devin)
            local args=(--project "$PROJECT_ROOT" --plan "$plan")
            if [ "$DRY_RUN" = "true" ]; then
                args+=(--dry-run)
            fi
            bash "$HARNESSES_ROOT/devin/scripts/scaffold_hooks.sh" "${args[@]}"
            ;;
        copilot)
            local args=(--project "$PROJECT_ROOT" --plan "$plan")
            if [ "$DRY_RUN" = "true" ]; then
                args+=(--dry-run)
            fi
            bash "$HARNESSES_ROOT/copilot/scripts/scaffold_hooks.sh" "${args[@]}"
            ;;
        opencode)
            local args=(--project "$PROJECT_ROOT" --plan "$plan")
            if [ -n "$HOME_OVERRIDE" ]; then
                args+=(--home "$HOME_OVERRIDE")
            fi
            if [ "$DRY_RUN" = "true" ]; then
                args+=(--dry-run)
            fi
            bash "$HARNESSES_ROOT/opencode/scripts/scaffold_hooks.sh" "${args[@]}"
            ;;
    esac
}

write_universal_readme() {
    local hooks_root_abs="$PROJECT_ROOT/$HOOKS_ROOT"
    local readme="$hooks_root_abs/README.md"
    mkdir -p "$hooks_root_abs"

    {
        printf '# Agent Hooks\n\n'
        printf 'Shared repo-owned hook behavior for Claude Code, Codex, Devin CLI, OpenCode, and GitHub Copilot.\n\n'
        printf '## Layout\n\n'
        printf -- '- `hooks/<event>/script.sh` is the shared editable behavior for an event.\n'
        printf -- '- `hooks/<event>/<harness>.sh` is a thin adapter invoked by that harness config.\n'
        printf -- '- `hooks/<event>/<harness>.json` stores scripts and commands from the plan.\n'
        printf -- '- `hooks/lib/` stores shared runtime helpers and harness output helpers.\n'
        printf -- '- `hooks/.state/<harness>/` stores generated config fragments and manifests.\n\n'
        printf '## Harness Config\n\n'
        if contains_harness claude; then
            printf -- '- Claude Code: `.claude/settings.json`\n'
        fi
        if contains_harness codex; then
            printf -- '- Codex: `.codex/hooks.json`\n'
        fi
        if contains_harness devin; then
            printf -- '- Devin CLI: `.devin/hooks.v1.json`\n'
        fi
        if contains_harness opencode; then
            printf -- '- OpenCode: `.opencode/plugins/*.ts`, delegating to `hooks/opencode-session-*`\n'
        fi
        if contains_harness copilot; then
            printf -- '- GitHub Copilot: `.github/hooks/copilot-hooks.json`, generated events under `.github/copilot/hooks/generated/`\n'
        fi
        printf '\n## Event Adapters\n\n'
        if find "$hooks_root_abs" -mindepth 2 -maxdepth 2 -type f \( -name '*.sh' -o -name '*.json' \) >/dev/null 2>&1; then
            find "$hooks_root_abs" -mindepth 2 -maxdepth 2 -type f \
                \( -name '*.sh' -o -name '*.json' \) \
                ! -path '*/lib/*' \
                ! -path '*/.state/*' \
                | sed "s|^$PROJECT_ROOT/||" \
                | LC_ALL=C sort \
                | while IFS= read -r rel_path; do
                    printf -- '- `%s`\n' "$rel_path"
                done
        fi
        printf '\n## Maintenance\n\n'
        printf 'Re-run `/scaffold-hooks` or `scripts/scaffold_all_hooks.sh` from the installed skill to refresh harness adapters. Keep project-specific policy in repo-owned scripts and call those scripts from the plan.\n'
    } > "$readme"
}

write_universal_manifest() {
    local state_dir="$PROJECT_ROOT/$HOOKS_ROOT/.state/scaffold-hooks"
    mkdir -p "$state_dir"
    jq -n \
        --arg generated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --arg mode "$MODE" \
        --arg hooks_root "$HOOKS_ROOT" \
        --argjson harnesses "$HARNESS_LIST_JSON" \
        --argjson cleanup_legacy "$CLEANUP_LEGACY" \
        --argjson legacy_roots "$LEGACY_ROOTS_JSON" \
        --slurpfile plan "$PLAN_FILE" \
        '{
            generated_at: $generated_at,
            mode: $mode,
            hooks_root: $hooks_root,
            harnesses: $harnesses,
            cleanup_legacy: $cleanup_legacy,
            legacy_roots: $legacy_roots,
            plan: $plan[0]
        }' > "$state_dir/manifest.json"
}

verify_no_legacy_commands() {
    local failures=()
    if contains_harness claude && [ -f "$PROJECT_ROOT/.claude/settings.json" ] \
        && grep -qE '\.claude/hooks/generated|\.codex/hooks/generated|\.devin/hooks/generated' "$PROJECT_ROOT/.claude/settings.json"; then
        failures+=(".claude/settings.json still references a legacy generated hook root")
    fi
    if contains_harness codex && [ -f "$PROJECT_ROOT/.codex/hooks.json" ] \
        && grep -qE '\.claude/hooks/generated|\.codex/hooks/generated|\.devin/hooks/generated' "$PROJECT_ROOT/.codex/hooks.json"; then
        failures+=(".codex/hooks.json still references a legacy generated hook root")
    fi
    if contains_harness devin && [ -f "$PROJECT_ROOT/.devin/hooks.v1.json" ] \
        && grep -qE '\.claude/hooks/generated|\.codex/hooks/generated|\.devin/hooks/generated' "$PROJECT_ROOT/.devin/hooks.v1.json"; then
        failures+=(".devin/hooks.v1.json still references a legacy generated hook root")
    fi

    if [ "${#failures[@]}" -gt 0 ]; then
        printf 'scaffold_all_hooks.sh detected hook config collisions:\n' >&2
        printf '  - %s\n' "${failures[@]}" >&2
        exit 1
    fi
}

PROJECT_ROOT=""
PLAN_FILE=""
MODE_OVERRIDE=""
HARNESSES_OVERRIDE=""
ENSURE_CODEX_FEATURE=""
HOME_OVERRIDE=""
CLEANUP_LEGACY_OVERRIDE=""
DRY_RUN="false"

while [ $# -gt 0 ]; do
    case "$1" in
        --project)
            PROJECT_ROOT="$2"
            shift 2
            ;;
        --plan)
            PLAN_FILE="$2"
            shift 2
            ;;
        --mode)
            MODE_OVERRIDE="$2"
            shift 2
            ;;
        --harnesses)
            HARNESSES_OVERRIDE="$2"
            shift 2
            ;;
        --ensure-codex-feature)
            ENSURE_CODEX_FEATURE="$2"
            shift 2
            ;;
        --home)
            HOME_OVERRIDE="$2"
            shift 2
            ;;
        --cleanup-legacy)
            CLEANUP_LEGACY_OVERRIDE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

if [ -z "$PROJECT_ROOT" ]; then
    usage >&2
    exit 1
fi

require_command jq
require_command bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
HARNESSES_ROOT="$SKILL_ROOT/harnesses"
DEFAULT_PLAN="$SKILL_ROOT/templates/hook-plan.example.json"

PROJECT_ROOT="$(resolve_project "$PROJECT_ROOT")"
PLAN_FILE="$(normalize_plan_path "${PLAN_FILE:-$DEFAULT_PLAN}")"

MODE="$(jq -r '.mode // "additive"' "$PLAN_FILE")"
if [ -n "$MODE_OVERRIDE" ]; then
    MODE="$MODE_OVERRIDE"
fi
case "$MODE" in
    additive|overhaul) ;;
    *)
        echo "Mode must be additive or overhaul. Got: $MODE" >&2
        exit 1
        ;;
esac

HOOKS_ROOT="$(jq -r '.hooks_root // "hooks"' "$PLAN_FILE")"
if [ -z "$HOOKS_ROOT" ] || [ "$HOOKS_ROOT" = "." ] || [[ "$HOOKS_ROOT" = /* ]] || [[ "$HOOKS_ROOT" == *".."* ]]; then
    echo "hooks_root must be a safe project-relative path. Got: $HOOKS_ROOT" >&2
    exit 1
fi

if [ -n "$HARNESSES_OVERRIDE" ]; then
    HARNESS_LIST_JSON="$(json_string_array_from_csv "$HARNESSES_OVERRIDE")"
else
    HARNESS_LIST_JSON="$(jq -c '.harnesses // ["claude", "codex", "copilot", "devin", "opencode"]' "$PLAN_FILE")"
fi
validate_harnesses

CLEANUP_LEGACY="$(jq -r '.cleanup_legacy // true' "$PLAN_FILE")"
if [ -n "$CLEANUP_LEGACY_OVERRIDE" ]; then
    CLEANUP_LEGACY="$CLEANUP_LEGACY_OVERRIDE"
fi
case "$CLEANUP_LEGACY" in
    true|false) ;;
    *)
        echo "cleanup_legacy must be true or false. Got: $CLEANUP_LEGACY" >&2
        exit 1
        ;;
esac

LEGACY_ROOTS_JSON='[".claude/hooks/generated", ".codex/hooks/generated", ".devin/hooks/generated"]'

if contains_harness codex; then
    require_command git
    require_command python3
fi
if contains_harness opencode; then
    require_command bun
fi

TEMP_DIR="$(mktemp -d)"
cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

if [ "$DRY_RUN" != "true" ]; then
    strip_legacy_config_entries
fi

for harness in claude codex devin opencode copilot; do
    if ! contains_harness "$harness"; then
        continue
    fi

    child_plan="$TEMP_DIR/$harness-plan.json"
    build_child_plan "$harness" "$child_plan"

    if [ "$MODE" = "overhaul" ] && [ "$DRY_RUN" != "true" ]; then
        cleanup_harness_state "$harness"
    fi

    run_child_scaffold "$harness" "$child_plan"
done

if [ "$DRY_RUN" = "true" ]; then
    cat <<EOF
scaffold_all_hooks.sh dry run complete
  project root:    $PROJECT_ROOT
  plan file:       $PLAN_FILE
  mode:            $MODE
  hooks root:      $HOOKS_ROOT
  harnesses:       $(printf '%s' "$HARNESS_LIST_JSON" | jq -r 'join(",")')
  cleanup legacy:  $CLEANUP_LEGACY
EOF
    exit 0
fi

if [ "$CLEANUP_LEGACY" = "true" ]; then
    cleanup_legacy_managed_roots
fi

write_universal_readme
write_universal_manifest
verify_no_legacy_commands

cat <<EOF
scaffold_all_hooks.sh complete
  project root:    $PROJECT_ROOT
  plan file:       $PLAN_FILE
  mode:            $MODE
  hooks root:      $HOOKS_ROOT
  harnesses:       $(printf '%s' "$HARNESS_LIST_JSON" | jq -r 'join(",")')
  cleanup legacy:  $CLEANUP_LEGACY
EOF

#!/usr/bin/env bash
#
# scaffold_hooks.sh
#
# Install the opencode-froggy plugin and render its hooks.md configuration.
#

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  scaffold_hooks.sh --project DIR --plan FILE [--mode additive|overhaul] [--home DIR] [--dry-run]
EOF
}

require_command() {
    local name="$1"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "Required command is missing: $name" >&2
        exit 1
    fi
}

sha256_file() {
    local file="$1"
    if [ ! -f "$file" ]; then
        printf ''
        return 0
    fi
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$file" | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$file" | awk '{print $1}'
    elif command -v openssl >/dev/null 2>&1; then
        openssl dgst -sha256 "$file" | awk '{print $NF}'
    else
        printf ''
    fi
}

git_source_field() {
    local root="$1"
    local field="$2"
    case "$field" in
        repository)
            git -C "$root" config --get remote.origin.url 2>/dev/null || true
            ;;
        commit)
            git -C "$root" rev-parse HEAD 2>/dev/null || true
            ;;
        dirty)
            if git -C "$root" rev-parse --show-toplevel >/dev/null 2>&1; then
                if [ -n "$(git -C "$root" status --short -- . 2>/dev/null)" ]; then
                    printf 'true'
                else
                    printf 'false'
                fi
            else
                printf 'null'
            fi
            ;;
    esac
}

resolve_target_path() {
    local value="$1"
    local project_root="$2"
    local home_root="$3"

    case "$value" in
        "~"*) printf '%s\n' "${home_root}${value#"~"}" ;;
        /*) printf '%s\n' "$value" ;;
        *) printf '%s\n' "$project_root/$value" ;;
    esac
}

remove_if_empty_dir() {
    local dir="$1"
    rmdir "$dir" 2>/dev/null || true
}

remove_legacy_opencode_event_dir() {
    local event_dir="$1"
    local dir="$PROJECT_ROOT/$HOOKS_ROOT_VALUE/$event_dir"
    local script="$dir/script.sh"
    local adapter="$dir/opencode.sh"

    [ -d "$dir" ] || return 0
    if [ -f "$adapter" ] && grep -q 'OPENCODE_HOOK_EVENT' "$adapter" \
        && { [ ! -f "$script" ] || grep -q '\[opencode-hook\] missing delegate' "$script"; }; then
        rm -f "$adapter" "$script"
        remove_if_empty_dir "$dir"
    fi
}

remove_legacy_dependency_artifacts() {
    local package_file="$PROJECT_ROOT/.opencode/package.json"
    [ -f "$package_file" ] || return 0

    if jq -e '
        ((.dependencies // {}) | keys) == ["@opencode-ai/plugin"]
        and ((.devDependencies // {}) | length == 0)
        and ((.peerDependencies // {}) | length == 0)
    ' "$package_file" >/dev/null 2>&1; then
        rm -f "$package_file"
        rm -f "$PROJECT_ROOT/.opencode/package-lock.json"
        rm -f "$PROJECT_ROOT/.opencode/bun.lock" "$PROJECT_ROOT/.opencode/bun.lockb"
        rm -rf "$PROJECT_ROOT/.opencode/node_modules"
    fi

    local gitignore="$PROJECT_ROOT/.opencode/.gitignore"
    if [ -f "$gitignore" ] && ! grep -qvE '^(node_modules|package\.json|package-lock\.json|bun\.lock|bun\.lockb|\.gitignore)?$' "$gitignore"; then
        rm -f "$gitignore"
    fi
}

cleanup_legacy_plugin_scaffold() {
    local legacy_state="$PROJECT_ROOT/.opencode/plugins/.managed"
    local legacy_manifest="$legacy_state/manifest.json"
    [ -f "$legacy_manifest" ] || return 0

    if ! jq -e '
        (.scaffold_hooks.skill_name == "scaffold-hooks" and .scaffold_hooks.harness == "opencode")
        or (
            (.deployment // "") == "local-files"
            and (.plugin_root // ".opencode/plugins") == ".opencode/plugins"
            and ((.managed_files // []) | type) == "array"
            and (
                ((.enabled_plugins // []) | map(select(
                    (.pattern // "") == "lifecycle-action"
                    or ((.context_script // "") | startswith("hooks/opencode-session-"))
                    or ((.action_script // "") | startswith("hooks/opencode-session-"))
                )) | length) > 0
            )
        )
    ' "$legacy_manifest" >/dev/null 2>&1; then
        return 0
    fi

    local legacy_plugin_root_value
    legacy_plugin_root_value="$(jq -r '.plugin_root // ".opencode/plugins"' "$legacy_manifest")"
    local legacy_plugin_root
    legacy_plugin_root="$(resolve_target_path "$legacy_plugin_root_value" "$PROJECT_ROOT" "$HOME_ROOT")"

    while IFS= read -r rel_path; do
        [ -n "$rel_path" ] || continue
        rm -f "$legacy_plugin_root/$rel_path"
    done < <(jq -r '.managed_files[]? // empty' "$legacy_manifest")

    if [ -f "$legacy_plugin_root/README.md" ] && grep -q 'OpenCode Hooks' "$legacy_plugin_root/README.md"; then
        rm -f "$legacy_plugin_root/README.md"
    fi

    rm -rf "$legacy_state"
    remove_if_empty_dir "$legacy_plugin_root"
    remove_if_empty_dir "$PROJECT_ROOT/.opencode/plugins"

    remove_legacy_opencode_event_dir "opencode-session-created"
    remove_legacy_opencode_event_dir "opencode-session-idle"
    remove_legacy_dependency_artifacts
}

PROJECT_ROOT=""
PLAN_FILE=""
MODE_OVERRIDE=""
HOME_OVERRIDE=""
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
        --home)
            HOME_OVERRIDE="$2"
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

if [ -z "$PROJECT_ROOT" ] || [ -z "$PLAN_FILE" ]; then
    usage >&2
    exit 1
fi

require_command jq
require_command bun

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
UNIVERSAL_SKILL_ROOT="$(cd "$SKILL_ROOT/../.." && pwd -P)"
MANIFEST_SOURCE="$SKILL_ROOT/assets/hook-events.json"

PROJECT_ROOT="$(
    cd "$PROJECT_ROOT"
    pwd -P
)"
PLAN_FILE="$(
    cd "$(dirname "$PLAN_FILE")"
    printf '%s/%s\n' "$(pwd -P)" "$(basename "$PLAN_FILE")"
)"

if [ ! -f "$PLAN_FILE" ]; then
    echo "Plan file does not exist: $PLAN_FILE" >&2
    exit 1
fi

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

SCOPE="$(jq -r '.scope // "project"' "$PLAN_FILE")"
case "$SCOPE" in
    project|global) ;;
    *)
        echo "Scope must be project or global. Got: $SCOPE" >&2
        exit 1
        ;;
esac

PLUGIN_NAME="$(jq -r '.plugin_name // "opencode-froggy"' "$PLAN_FILE")"
if [ "$PLUGIN_NAME" != "opencode-froggy" ]; then
    echo "The OpenCode scaffold is Froggy-backed and only supports plugin_name=opencode-froggy. Got: $PLUGIN_NAME" >&2
    exit 1
fi

HOME_ROOT="${HOME_OVERRIDE:-$HOME}"
CONFIG_TARGET_VALUE="$(jq -r '.config_target // empty' "$PLAN_FILE")"
HOOK_CONFIG_VALUE="$(jq -r '.hook_config_target // empty' "$PLAN_FILE")"
MANAGED_STATE_VALUE="$(jq -r '.managed_state_dir // empty' "$PLAN_FILE")"
HOOKS_ROOT_VALUE="$(jq -r '.hooks_root // "hooks"' "$PLAN_FILE")"

if [ -z "$CONFIG_TARGET_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        CONFIG_TARGET_VALUE="~/.config/opencode/opencode.json"
    else
        CONFIG_TARGET_VALUE="opencode.json"
    fi
fi
if [ -z "$HOOK_CONFIG_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        HOOK_CONFIG_VALUE="~/.config/opencode/hook/hooks.md"
    else
        HOOK_CONFIG_VALUE=".opencode/hook/hooks.md"
    fi
fi
if [ -z "$MANAGED_STATE_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        MANAGED_STATE_VALUE="~/.config/opencode/hook/.managed"
    else
        MANAGED_STATE_VALUE=".opencode/hook/.managed"
    fi
fi

CONFIG_TARGET_ABS="$(resolve_target_path "$CONFIG_TARGET_VALUE" "$PROJECT_ROOT" "$HOME_ROOT")"
HOOK_CONFIG_ABS="$(resolve_target_path "$HOOK_CONFIG_VALUE" "$PROJECT_ROOT" "$HOME_ROOT")"
MANAGED_STATE_ABS="$(resolve_target_path "$MANAGED_STATE_VALUE" "$PROJECT_ROOT" "$HOME_ROOT")"
MANIFEST_TARGET_FILE="$MANAGED_STATE_ABS/manifest.json"
PLAN_SNAPSHOT_FILE="$MANAGED_STATE_ABS/plan.snapshot.json"

HOOKS_JSON="$(jq -c '.hooks // []' "$PLAN_FILE")"
if [ "$(printf '%s' "$HOOKS_JSON" | jq 'length')" -eq 0 ]; then
    echo "Plan file must define at least one Froggy hook in .hooks." >&2
    exit 1
fi

SETUP_ARGS=(--project "$PROJECT_ROOT" --json)
if [ -n "$HOME_OVERRIDE" ]; then
    SETUP_ARGS+=(--home "$HOME_OVERRIDE")
fi
SETUP_STATUS_JSON="$(bun "$SCRIPT_DIR/check_plugin_setup.ts" "${SETUP_ARGS[@]}")"

if [ "$DRY_RUN" = "true" ]; then
    cat <<EOF
scaffold_hooks.sh dry run
  project root:       $PROJECT_ROOT
  scope:              $SCOPE
  mode:               $MODE
  plugin:             $PLUGIN_NAME
  config target:      $CONFIG_TARGET_VALUE
  hook config target: $HOOK_CONFIG_VALUE
  managed state:      $MANAGED_STATE_VALUE
  hooks:              $(printf '%s' "$HOOKS_JSON" | jq 'length')
  legacy cleanup:     $([ -f "$PROJECT_ROOT/.opencode/plugins/.managed/manifest.json" ] && printf 'detected' || printf 'not-detected')
EOF
    exit 0
fi

mkdir -p "$MANAGED_STATE_ABS"

cleanup_legacy_plugin_scaffold

bun "$SCRIPT_DIR/merge_opencode_config.ts" \
    --config-file "$CONFIG_TARGET_ABS" \
    --plugins "$PLUGIN_NAME" >/dev/null

bun "$SCRIPT_DIR/render_froggy_hooks.ts" \
    --hooks-file "$HOOK_CONFIG_ABS" \
    --hooks-json "$HOOKS_JSON" \
    --mode "$MODE" \
    --managed-id "scaffold-hooks/opencode-froggy" >/dev/null

jq '.' "$PLAN_FILE" > "$PLAN_SNAPSHOT_FILE"

SKILL_VERSION="$(jq -r '.version // "unknown"' "$UNIVERSAL_SKILL_ROOT/metadata.json" 2>/dev/null || printf 'unknown')"
SOURCE_REPOSITORY="$(git_source_field "$UNIVERSAL_SKILL_ROOT" repository)"
SOURCE_COMMIT="$(git_source_field "$UNIVERSAL_SKILL_ROOT" commit)"
SOURCE_DIRTY="$(git_source_field "$UNIVERSAL_SKILL_ROOT" dirty)"
PLAN_SHA256="$(sha256_file "$PLAN_FILE")"
GENERATOR_SHA256="$(sha256_file "$SCRIPT_DIR/scaffold_hooks.sh")"
RENDERER_SHA256="$(sha256_file "$SCRIPT_DIR/render_froggy_hooks.ts")"
EVENT_MANIFEST_SHA256="$(sha256_file "$MANIFEST_SOURCE")"
HOOK_CONFIG_SHA256="$(sha256_file "$HOOK_CONFIG_ABS")"
CONFIG_SHA256="$(sha256_file "$CONFIG_TARGET_ABS")"

jq -n \
    --arg generated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg scope "$SCOPE" \
    --arg mode "$MODE" \
    --arg skill_version "$SKILL_VERSION" \
    --arg source_repository "$SOURCE_REPOSITORY" \
    --arg source_commit "$SOURCE_COMMIT" \
    --argjson source_dirty "$SOURCE_DIRTY" \
    --arg plan_sha256 "$PLAN_SHA256" \
    --arg generator_sha256 "$GENERATOR_SHA256" \
    --arg renderer_sha256 "$RENDERER_SHA256" \
    --arg event_manifest_sha256 "$EVENT_MANIFEST_SHA256" \
    --arg plugin_name "$PLUGIN_NAME" \
    --arg config_target "$CONFIG_TARGET_VALUE" \
    --arg hook_config_target "$HOOK_CONFIG_VALUE" \
    --arg managed_state_dir "$MANAGED_STATE_VALUE" \
    --arg config_sha256 "$CONFIG_SHA256" \
    --arg hook_config_sha256 "$HOOK_CONFIG_SHA256" \
    --argjson setup_status "$SETUP_STATUS_JSON" \
    --argjson hooks "$HOOKS_JSON" \
    --slurpfile source "$MANIFEST_SOURCE" \
    --slurpfile plan "$PLAN_FILE" '
    $source[0] + {
        generated_at: $generated_at,
        scaffold_hooks: {
            schema_version: 2,
            skill_name: "scaffold-hooks",
            harness: "opencode",
            integration: "opencode-froggy",
            skill_version: $skill_version,
            source: {
                repository: (if $source_repository == "" then null else $source_repository end),
                commit: (if $source_commit == "" then null else $source_commit end),
                dirty: $source_dirty
            },
            generator: {
                path: "harnesses/opencode/scripts/scaffold_hooks.sh",
                sha256: (if $generator_sha256 == "" then null else $generator_sha256 end)
            },
            renderer: {
                path: "harnesses/opencode/scripts/render_froggy_hooks.ts",
                sha256: (if $renderer_sha256 == "" then null else $renderer_sha256 end)
            },
            plan_sha256: (if $plan_sha256 == "" then null else $plan_sha256 end),
            event_manifest_sha256: (if $event_manifest_sha256 == "" then null else $event_manifest_sha256 end)
        },
        scope: $scope,
        mode: $mode,
        plugin_name: $plugin_name,
        config_target: $config_target,
        hook_config_target: $hook_config_target,
        managed_state_dir: $managed_state_dir,
        hooks: $hooks,
        managed_files: [$hook_config_target],
        managed_file_hashes: {
            ($hook_config_target): (if $hook_config_sha256 == "" then null else $hook_config_sha256 end)
        },
        merged_config_hashes: {
            ($config_target): (if $config_sha256 == "" then null else $config_sha256 end)
        },
        setup_status: $setup_status,
        plan: $plan[0]
    }
    ' > "$MANIFEST_TARGET_FILE"

bash "$SCRIPT_DIR/render_hooks_readme.sh" \
    --project "$PROJECT_ROOT" \
    --plan "$PLAN_FILE" \
    ${HOME_OVERRIDE:+--home "$HOME_OVERRIDE"}

cat <<EOF
scaffold_hooks.sh complete
  project root:       $PROJECT_ROOT
  scope:              $SCOPE
  mode:               $MODE
  plugin:             $PLUGIN_NAME
  config target:      $CONFIG_TARGET_VALUE
  hook config target: $HOOK_CONFIG_VALUE
  managed state:      $MANAGED_STATE_VALUE
EOF

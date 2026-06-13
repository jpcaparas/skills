#!/usr/bin/env bash
#
# scaffold_hooks.sh
#
# Render or refresh a managed OpenCode plugin scaffold in a target project.
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

json_object_from_hash_lines() {
    local file="$1"
    if [ ! -s "$file" ]; then
        printf '{}'
        return 0
    fi
    jq -s '
        map(select((.filename // "") != "" and (.sha256 // "") != ""))
        | map({key: .filename, value: .sha256})
        | from_entries
    ' "$file"
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

normalize_filename() {
    local filename="$1"
    case "$filename" in
        *.ts) printf '%s\n' "$filename" ;;
        *.js|*.mjs|*.cjs|*.jsx|*.tsx) printf '%s.ts\n' "${filename%.*}" ;;
        *) printf '%s.ts\n' "$filename" ;;
    esac
}

previous_manifest_has_file() {
    local filename="$1"
    [ -f "$MANIFEST_TARGET_FILE" ] || return 1
    jq -e --arg filename "$filename" '(.managed_files // []) | index($filename) != null' "$MANIFEST_TARGET_FILE" >/dev/null 2>&1
}

previous_manifest_hash() {
    local filename="$1"
    local field="$2"
    [ -f "$MANIFEST_TARGET_FILE" ] || return 0
    jq -r --arg filename "$filename" --arg field "$field" '.[$field][$filename] // empty' "$MANIFEST_TARGET_FILE" 2>/dev/null || true
}

has_managed_header() {
    local file="$1"
    [ -f "$file" ] || return 1
    grep -q "Managed by scaffold-hooks" "$file"
}

backup_existing_plugin() {
    local filename="$1"
    local target_path="$2"
    [ -f "$target_path" ] || return 0
    local backup_dir="$MANAGED_STATE_ABS/backups/$(date -u +%Y%m%d%H%M%S)"
    mkdir -p "$backup_dir"
    cp "$target_path" "$backup_dir/$filename"
}

write_opencode_event_scripts() {
    local hooks_root_abs="$1"
    local event_dir="$2"
    local delegate_script="$3"
    local mode="$4"
    local event_root="$hooks_root_abs/$event_dir"
    local script_path="$event_root/script.sh"
    local adapter_path="$event_root/opencode.sh"

    mkdir -p "$event_root"

    if [ "$mode" != "additive" ] || [ ! -f "$script_path" ]; then
        cat > "$script_path" <<EOF
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="\${OPENCODE_PROJECT_DIR:-}"
if [ -z "\$PROJECT_ROOT" ]; then
    if git rev-parse --show-toplevel >/dev/null 2>&1; then
        PROJECT_ROOT="\$(git rev-parse --show-toplevel)"
    else
        PROJECT_ROOT="\$(pwd -P)"
    fi
fi

DELEGATE="\$PROJECT_ROOT/$delegate_script"
if [ ! -f "\$DELEGATE" ]; then
    printf '[opencode-hook] missing delegate: %s\n' "\$DELEGATE" >&2
    exit 127
fi

exec /usr/bin/env bash "\$DELEGATE" "\$@"
EOF
        chmod +x "$script_path"
    fi

    cat > "$adapter_path" <<EOF
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
export OPENCODE_HOOK_EVENT="$event_dir"

exec "\$SCRIPT_DIR/script.sh" "\$@"
EOF
    chmod +x "$adapter_path"
}

render_handler_block() {
    local surface="$1"
    case "$surface" in
        event)
            cat <<'EOF'
    event: (() => {
      const childSessionIDs = new Set()

      return async ({ event }) => {
        const sessionID = event.properties?.info?.id ?? event.properties?.sessionID
        if (event.type === "session.created") {
          const parentID = event.properties?.info?.parentID
          if (sessionID && typeof parentID === "string" && parentID.length > 0) childSessionIDs.add(sessionID)
          return
        }
        if (event.type === "session.deleted") {
          if (sessionID) childSessionIDs.delete(sessionID)
          return
        }
        if (event.type !== "session.idle" || !sessionID || childSessionIDs.has(sessionID)) return

        await showToast(client, "info", "Background hook work started")
        // TODO: coordinate post-turn validation, notifications, or idle-triggered follow-up here.
        await showToast(client, "success", "Background hook work completed")
      }
    })(),
EOF
            ;;
        tool)
            cat <<'EOF'
    tool: {
      example: tool({
        description: "Describe what this custom OpenCode tool does",
        args: {},
        async execute(args, context) {
          void args
          void context
          return "TODO: implement tool behavior"
        },
      }),
    },
EOF
            ;;
        shell.env)
            cat <<'EOF'
    "shell.env": async (input, output) => {
      output.env.PROJECT_ROOT = input.cwd
      // TODO: add project-specific environment variables here.
    },
EOF
            ;;
        tool.execute.before)
            cat <<'EOF'
    "tool.execute.before": async (input, output) => {
      // TODO: inspect input.tool and either rewrite output.args or throw to deny the action.
      if (input.tool === "read" && output.args.filePath?.includes(".env")) {
        throw new Error("Do not read .env files")
      }
    },
EOF
            ;;
        tool.execute.after)
            cat <<'EOF'
    "tool.execute.after": async (input) => {
      // TODO: track edit tools or capture output for post-turn validation.
      if (input.tool === "write" || input.tool === "edit") {
        // Record that the agent changed files this turn.
        await showToast(client, "info", "Post-action hook work started")
      }
    },
EOF
            ;;
        experimental.session.compacting)
            cat <<'EOF'
    "experimental.session.compacting": async (input, output) => {
      void input
      output.context.push("## TODO\nAdd domain-specific context that should survive compaction.")
      // Or replace the entire prompt with output.prompt = "...";
    },
EOF
            ;;
        *)
            cat <<EOF
    "${surface}": async (input, output) => {
      void input
      void output
      // TODO: call showToast(client, "info" | "success" | "warning" | "error", "...") when this hook does meaningful background work.
      // TODO: implement logic for ${surface}.
    },
EOF
            ;;
    esac
}

stub_snippet_for_surface() {
    local surface="$1"
    case "$surface" in
        event)
            cat <<'EOF'
event: (() => {
  const childSessionIDs = new Set()

  return async ({ event }) => {
    const sessionID = event.properties?.info?.id ?? event.properties?.sessionID
    if (event.type === "session.created") {
      const parentID = event.properties?.info?.parentID
      if (sessionID && typeof parentID === "string" && parentID.length > 0) childSessionIDs.add(sessionID)
      return
    }
    if (event.type === "session.deleted") {
      if (sessionID) childSessionIDs.delete(sessionID)
      return
    }
    if (event.type !== "session.idle" || !sessionID || childSessionIDs.has(sessionID)) return

    await showToast(client, "info", "Background hook work started")
    // TODO: run post-turn validation or notifications here.
    await showToast(client, "success", "Background hook work completed")
  }
})(),
EOF
            ;;
        tool)
            cat <<'EOF'
tool: {
  example: tool({
    description: "Describe what this custom OpenCode tool does",
    args: {},
    async execute(args, context) {
      return "TODO"
    },
  }),
},
EOF
            ;;
        *)
            cat <<EOF
"${surface}": async (input, output) => {
  // TODO: use client.tui.showToast through a best-effort helper when this hook performs meaningful background work.
  // TODO: implement logic for ${surface}.
},
EOF
            ;;
    esac
}

write_surface_stub() {
    local surface="$1"
    local category="$2"
    local kind="$3"
    local description="$4"
    local guidance="$5"
    local target="$6"

    {
        printf 'Surface: %s\n' "$surface"
        printf 'Category: %s\n' "$category"
        printf 'Kind: %s\n' "$kind"
        printf 'Description: %s\n' "$description"
        printf 'Guidance: %s\n\n' "$guidance"
        printf 'Example snippet:\n\n'
        stub_snippet_for_surface "$surface"
    } > "$target"
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
TS_TEMPLATE="$SKILL_ROOT/templates/plugin-module.ts.tmpl"
LIFECYCLE_TEMPLATE="$SKILL_ROOT/templates/lifecycle-action-plugin.ts.tmpl"

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

DEPLOYMENT="$(jq -r '.deployment // "local-files"' "$PLAN_FILE")"
case "$DEPLOYMENT" in
    local-files|hybrid) ;;
    *)
        echo "Deployment must be local-files or hybrid. Got: $DEPLOYMENT" >&2
        exit 1
        ;;
esac

SURFACE_CATALOG="$(jq -r '.surface_catalog // false' "$PLAN_FILE")"
case "$SURFACE_CATALOG" in
    true|false) ;;
    *)
        echo "surface_catalog must be true or false. Got: $SURFACE_CATALOG" >&2
        exit 1
        ;;
esac

MODULE_FORMAT="$(jq -r '.module_format // "ts"' "$PLAN_FILE")"
case "$MODULE_FORMAT" in
    ts) ;;
    *)
        echo "module_format must be ts. OpenCode supports JavaScript, but this managed scaffold is TypeScript-only. Got: $MODULE_FORMAT" >&2
        exit 1
        ;;
esac

HOME_ROOT="${HOME_OVERRIDE:-$HOME}"
PLUGIN_ROOT_VALUE="$(jq -r '.plugin_root // empty' "$PLAN_FILE")"
MANAGED_STATE_VALUE="$(jq -r '.managed_state_dir // empty' "$PLAN_FILE")"
CONFIG_TARGET_VALUE="$(jq -r '.config_target // empty' "$PLAN_FILE")"
PACKAGE_TARGET_VALUE="$(jq -r '.package_target // empty' "$PLAN_FILE")"
HOOKS_ROOT_VALUE="$(jq -r '.hooks_root // "hooks"' "$PLAN_FILE")"

if [ -z "$PLUGIN_ROOT_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        PLUGIN_ROOT_VALUE="~/.config/opencode/plugins"
    else
        PLUGIN_ROOT_VALUE=".opencode/plugins"
    fi
fi
if [ -z "$MANAGED_STATE_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        MANAGED_STATE_VALUE="~/.config/opencode/plugins/.managed"
    else
        MANAGED_STATE_VALUE=".opencode/plugins/.managed"
    fi
fi
if [ -z "$CONFIG_TARGET_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        CONFIG_TARGET_VALUE="~/.config/opencode/opencode.json"
    else
        CONFIG_TARGET_VALUE="opencode.json"
    fi
fi
if [ -z "$PACKAGE_TARGET_VALUE" ]; then
    if [ "$SCOPE" = "global" ]; then
        PACKAGE_TARGET_VALUE="~/.config/opencode/package.json"
    else
        PACKAGE_TARGET_VALUE=".opencode/package.json"
    fi
fi

PLUGIN_ROOT_ABS="$(resolve_target_path "$PLUGIN_ROOT_VALUE" "$PROJECT_ROOT" "$HOME_ROOT")"
MANAGED_STATE_ABS="$(resolve_target_path "$MANAGED_STATE_VALUE" "$PROJECT_ROOT" "$HOME_ROOT")"
CONFIG_TARGET_ABS="$(resolve_target_path "$CONFIG_TARGET_VALUE" "$PROJECT_ROOT" "$HOME_ROOT")"
PACKAGE_TARGET_ABS="$(resolve_target_path "$PACKAGE_TARGET_VALUE" "$PROJECT_ROOT" "$HOME_ROOT")"
HOOKS_ROOT_ABS="$(resolve_target_path "$HOOKS_ROOT_VALUE" "$PROJECT_ROOT" "$HOME_ROOT")"
SURFACES_DIR="$MANAGED_STATE_ABS/surfaces"
MANIFEST_TARGET_FILE="$MANAGED_STATE_ABS/manifest.json"
PLAN_SNAPSHOT_FILE="$MANAGED_STATE_ABS/plan.snapshot.json"

KNOWN_SURFACES="$(
    jq -n --slurpfile manifest "$MANIFEST_SOURCE" '
        (($manifest[0].special_surfaces // []) + ($manifest[0].events // []))
        | map(.name)
        | unique
    '
)"

UNKNOWN_SURFACES="$(
    jq -n \
        --argjson known "$KNOWN_SURFACES" \
        --slurpfile plan "$PLAN_FILE" '
        ($plan[0].enabled_plugins // [])
        | map(.surfaces // [])
        | add
        | unique
        | map(select(($known | index(.)) | not))
        | .[]
    '
)"
if [ -n "$UNKNOWN_SURFACES" ]; then
    echo "Plan file contains unknown surface names:" >&2
    printf '  - %s\n' $UNKNOWN_SURFACES >&2
    exit 1
fi

DUPLICATE_FILENAMES="$(
    jq -r '.enabled_plugins[]?.filename // empty' "$PLAN_FILE" \
        | while IFS= read -r filename; do normalize_filename "$filename"; done \
        | LC_ALL=C sort \
        | uniq -d
)"
if [ -n "$DUPLICATE_FILENAMES" ]; then
    echo "Plan file contains duplicate enabled plugin filenames:" >&2
    printf '  - %s\n' $DUPLICATE_FILENAMES >&2
    exit 1
fi

SETUP_ARGS=(--project "$PROJECT_ROOT" --json)
if [ -n "$HOME_OVERRIDE" ]; then
    SETUP_ARGS+=(--home "$HOME_OVERRIDE")
fi
SETUP_STATUS_JSON="$(
    bun "$SCRIPT_DIR/check_plugin_setup.ts" "${SETUP_ARGS[@]}"
)"

PACKAGE_DEPS_JSON="$(jq -c '.package_dependencies // {}' "$PLAN_FILE")"
NEEDS_TOOL_HELPER="$(
    jq -r '
        [
          .enabled_plugins[]?.surfaces[]?
        ] | if index("tool") == null then "false" else "true" end
    ' "$PLAN_FILE"
)"
if [ "$NEEDS_TOOL_HELPER" = "true" ]; then
    PACKAGE_DEPS_JSON="$(
        jq -nc \
            --argjson existing "$PACKAGE_DEPS_JSON" \
            --arg version "$(jq -r '.recommended_dependency_versions["@opencode-ai/plugin"]' "$MANIFEST_SOURCE")" '
            $existing + {"@opencode-ai/plugin": $version}
        '
    )"
fi

NPM_PLUGIN_ARGS=()
while IFS= read -r plugin; do
    [ -n "$plugin" ] || continue
    NPM_PLUGIN_ARGS+=("$plugin")
done < <(jq -r '.npm_plugins[]? // empty' "$PLAN_FILE")

ENABLED_PLUGIN_COUNT="$(jq '.enabled_plugins | length' "$PLAN_FILE")"

if [ "$DRY_RUN" = "true" ]; then
    cat <<EOF
scaffold_hooks.sh dry run
  project root:    $PROJECT_ROOT
  scope:           $SCOPE
  deployment:      $DEPLOYMENT
  mode:            $MODE
  module format:   $MODULE_FORMAT
  plugin root:     $PLUGIN_ROOT_VALUE
  hook root:       $HOOKS_ROOT_VALUE
  managed state:   $MANAGED_STATE_VALUE
  config target:   $CONFIG_TARGET_VALUE
  package target:  $PACKAGE_TARGET_VALUE
EOF
    printf '  enabled plugins: %s\n' "$ENABLED_PLUGIN_COUNT"
    printf '  npm plugins:     %s\n' "$(jq '.npm_plugins | length' "$PLAN_FILE")"
    printf '  package deps:    %s\n' "$(printf '%s' "$PACKAGE_DEPS_JSON" | jq 'length')"
    exit 0
fi

mkdir -p "$PLUGIN_ROOT_ABS" "$HOOKS_ROOT_ABS"

if [ "$MODE" = "overhaul" ] && [ -f "$MANIFEST_TARGET_FILE" ]; then
    BACKUP_PATH="${MANAGED_STATE_ABS}.bak.$(date +%Y%m%d%H%M%S)"
    mkdir -p "$(dirname "$BACKUP_PATH")"
    cp -R "$MANAGED_STATE_ABS" "$BACKUP_PATH"
    while IFS= read -r rel_path; do
        [ -n "$rel_path" ] || continue
        rm -f "$PLUGIN_ROOT_ABS/$rel_path"
    done < <(jq -r '.managed_files[]? // empty' "$MANIFEST_TARGET_FILE")
    rm -rf "$MANAGED_STATE_ABS"
fi

mkdir -p "$MANAGED_STATE_ABS"

if [ "$SURFACE_CATALOG" = "true" ]; then
    mkdir -p "$SURFACES_DIR"

    while IFS=$'\t' read -r surface stub_file category kind description guidance; do
        write_surface_stub \
            "$surface" \
            "$category" \
            "$kind" \
            "$description" \
            "$guidance" \
            "$SURFACES_DIR/$stub_file"
    done < <(
        jq -r '
            ((.special_surfaces // []) + (.events // []))
            | .[]
            | [.name, .stub_file, .category, .kind, .description, .guidance]
            | @tsv
        ' "$MANIFEST_SOURCE"
    )
else
    rm -rf "$SURFACES_DIR"
fi

TEMP_MANAGED_FILES="$(mktemp)"
TEMP_ENABLED_PLUGINS="$(mktemp)"
TEMP_MANAGED_HASHES="$(mktemp)"
TEMP_PRESERVED_HASHES="$(mktemp)"
cleanup() {
    rm -f "$TEMP_MANAGED_FILES" "$TEMP_ENABLED_PLUGINS" "$TEMP_MANAGED_HASHES" "$TEMP_PRESERVED_HASHES"
}
trap cleanup EXIT

while IFS= read -r row; do
    name="$(printf '%s' "$row" | jq -r '.name')"
    notes="$(printf '%s' "$row" | jq -r '.notes // ""')"
    pattern="$(printf '%s' "$row" | jq -r '.pattern // "surface-handlers"')"
    filename_raw="$(printf '%s' "$row" | jq -r '.filename')"
    filename="$(normalize_filename "$filename_raw")"
    target_path="$PLUGIN_ROOT_ABS/$filename"
    surfaces_json="$(printf '%s' "$row" | jq -c '.surfaces // []')"
    context_script="$(printf '%s' "$row" | jq -r --arg root "$HOOKS_ROOT_VALUE" '.context_script // ($root + "/opencode-session-created/opencode.sh")')"
    action_script="$(printf '%s' "$row" | jq -r --arg root "$HOOKS_ROOT_VALUE" '.action_script // ($root + "/opencode-session-idle/opencode.sh")')"

    if [ "$(printf '%s' "$surfaces_json" | jq 'length')" -eq 0 ]; then
        echo "Enabled plugin '$name' has no surfaces." >&2
        exit 1
    fi

    if [ "$pattern" = "lifecycle-action" ]; then
        context_delegate="$(printf '%s' "$row" | jq -r '.context_delegate_script // "scripts/agent-session-context.sh"')"
        action_delegate="$(printf '%s' "$row" | jq -r '.action_delegate_script // "scripts/validate-project.sh"')"
        write_opencode_event_scripts "$HOOKS_ROOT_ABS" "opencode-session-created" "$context_delegate" "$MODE"
        write_opencode_event_scripts "$HOOKS_ROOT_ABS" "opencode-session-idle" "$action_delegate" "$MODE"
    fi

    if [ "$MODE" = "additive" ] && [ -f "$target_path" ]; then
        current_hash="$(sha256_file "$target_path")"
        previous_managed_hash="$(previous_manifest_hash "$filename" "managed_file_hashes")"
        previous_preserved_hash="$(previous_manifest_hash "$filename" "preserved_file_hashes")"

        if [ -n "$previous_preserved_hash" ]; then
            printf '%s\n' "$filename" >> "$TEMP_MANAGED_FILES"
            jq -nc --arg filename "$filename" --arg sha256 "$current_hash" \
                '{filename: $filename, sha256: $sha256}' >> "$TEMP_PRESERVED_HASHES"
            printf '%s\n' "$(printf '%s' "$row" | jq -c --arg filename "$filename" '. + {filename: $filename, preserved: true}')" >> "$TEMP_ENABLED_PLUGINS"
            continue
        fi

        if [ -n "$previous_managed_hash" ] && [ "$current_hash" != "$previous_managed_hash" ]; then
            printf '%s\n' "$filename" >> "$TEMP_MANAGED_FILES"
            jq -nc --arg filename "$filename" --arg sha256 "$current_hash" \
                '{filename: $filename, sha256: $sha256}' >> "$TEMP_PRESERVED_HASHES"
            printf '%s\n' "$(printf '%s' "$row" | jq -c --arg filename "$filename" '. + {filename: $filename, preserved: true}')" >> "$TEMP_ENABLED_PLUGINS"
            continue
        fi

        if [ -z "$previous_managed_hash" ]; then
            if previous_manifest_has_file "$filename" && has_managed_header "$target_path"; then
                backup_existing_plugin "$filename" "$target_path"
            else
                printf '%s\n' "$filename" >> "$TEMP_MANAGED_FILES"
                jq -nc --arg filename "$filename" --arg sha256 "$current_hash" \
                    '{filename: $filename, sha256: $sha256}' >> "$TEMP_PRESERVED_HASHES"
                printf '%s\n' "$(printf '%s' "$row" | jq -c --arg filename "$filename" '. + {filename: $filename, preserved: true}')" >> "$TEMP_ENABLED_PLUGINS"
                continue
            fi
        fi
    fi

    handlers_file="$(mktemp)"
    imports_file="$(mktemp)"
    {
        printf ''
    } > "$handlers_file"
    {
        if [ "$pattern" != "lifecycle-action" ] && printf '%s' "$surfaces_json" | jq -e 'index("tool")' >/dev/null; then
            printf 'import { type Plugin, tool } from "@opencode-ai/plugin"\n\n'
        fi
    } > "$imports_file"

    if [ "$pattern" != "lifecycle-action" ]; then
        while IFS= read -r surface; do
            render_handler_block "$surface" >> "$handlers_file"
            printf '\n' >> "$handlers_file"
        done < <(printf '%s' "$surfaces_json" | jq -r '.[]')
    fi

    template_path="$TS_TEMPLATE"
    if [ "$pattern" = "lifecycle-action" ]; then
        template_path="$LIFECYCLE_TEMPLATE"
    fi

    bun "$SCRIPT_DIR/render_plugin_module.ts" \
        --template "$template_path" \
        --imports "$imports_file" \
        --handlers "$handlers_file" \
        --output "$target_path" \
        --name "$name" \
        --notes "$notes" \
        --surfaces "$(printf '%s' "$surfaces_json" | jq -r 'join(", ")')" \
        --context-script "$context_script" \
        --action-script "$action_script" \
        --action-label "$(printf '%s' "$row" | jq -r '.action_label // "Project validation"')" \
        --service-name "$(printf '%s' "$row" | jq -r '.service // "opencode-lifecycle-hooks"')"

    rm -f "$handlers_file" "$imports_file"

    printf '%s\n' "$filename" >> "$TEMP_MANAGED_FILES"
    jq -nc --arg filename "$filename" --arg sha256 "$(sha256_file "$target_path")" \
        '{filename: $filename, sha256: $sha256}' >> "$TEMP_MANAGED_HASHES"
    printf '%s\n' "$(printf '%s' "$row" | jq -c --arg filename "$filename" '. + {filename: $filename}')" >> "$TEMP_ENABLED_PLUGINS"
done < <(jq -c '.enabled_plugins[]? // empty' "$PLAN_FILE")

PACKAGE_DEPS_COUNT="$(printf '%s' "$PACKAGE_DEPS_JSON" | jq 'length')"
if [ "$PACKAGE_DEPS_COUNT" -gt 0 ]; then
    bun "$SCRIPT_DIR/merge_package_json.ts" \
        --package-file "$PACKAGE_TARGET_ABS" \
        --dependencies-json "$PACKAGE_DEPS_JSON" >/dev/null
fi

if [ "${#NPM_PLUGIN_ARGS[@]}" -gt 0 ]; then
    bun "$SCRIPT_DIR/merge_opencode_config.ts" \
        --config-file "$CONFIG_TARGET_ABS" \
        --plugins "${NPM_PLUGIN_ARGS[@]}" >/dev/null
fi

jq '.' "$PLAN_FILE" > "$PLAN_SNAPSHOT_FILE"

SKILL_VERSION="$(jq -r '.version // "unknown"' "$UNIVERSAL_SKILL_ROOT/metadata.json" 2>/dev/null || printf 'unknown')"
SOURCE_REPOSITORY="$(git_source_field "$UNIVERSAL_SKILL_ROOT" repository)"
SOURCE_COMMIT="$(git_source_field "$UNIVERSAL_SKILL_ROOT" commit)"
SOURCE_DIRTY="$(git_source_field "$UNIVERSAL_SKILL_ROOT" dirty)"
PLAN_SHA256="$(sha256_file "$PLAN_FILE")"
GENERATOR_SHA256="$(sha256_file "$SCRIPT_DIR/scaffold_hooks.sh")"
TEMPLATE_SHA256="$(sha256_file "$LIFECYCLE_TEMPLATE")"
PLUGIN_TEMPLATE_SHA256="$(sha256_file "$TS_TEMPLATE")"
EVENT_MANIFEST_SHA256="$(sha256_file "$MANIFEST_SOURCE")"
MANAGED_FILE_HASHES_JSON="$(json_object_from_hash_lines "$TEMP_MANAGED_HASHES")"
PRESERVED_FILE_HASHES_JSON="$(json_object_from_hash_lines "$TEMP_PRESERVED_HASHES")"

jq -n \
    --arg generated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg scope "$SCOPE" \
    --arg deployment "$DEPLOYMENT" \
    --arg mode "$MODE" \
    --arg module_format "$MODULE_FORMAT" \
    --arg skill_version "$SKILL_VERSION" \
    --arg source_repository "$SOURCE_REPOSITORY" \
    --arg source_commit "$SOURCE_COMMIT" \
    --argjson source_dirty "$SOURCE_DIRTY" \
    --arg plan_sha256 "$PLAN_SHA256" \
    --arg generator_sha256 "$GENERATOR_SHA256" \
    --arg lifecycle_template_sha256 "$TEMPLATE_SHA256" \
    --arg plugin_template_sha256 "$PLUGIN_TEMPLATE_SHA256" \
    --arg event_manifest_sha256 "$EVENT_MANIFEST_SHA256" \
    --argjson surface_catalog "$SURFACE_CATALOG" \
    --arg plugin_root "$PLUGIN_ROOT_VALUE" \
    --arg hooks_root "$HOOKS_ROOT_VALUE" \
    --arg managed_state_dir "$MANAGED_STATE_VALUE" \
    --arg config_target "$CONFIG_TARGET_VALUE" \
    --arg package_target "$PACKAGE_TARGET_VALUE" \
    --argjson package_dependencies "$PACKAGE_DEPS_JSON" \
    --argjson setup_status "$SETUP_STATUS_JSON" \
    --argjson enabled_plugins "$(jq -s '.' "$TEMP_ENABLED_PLUGINS")" \
    --argjson managed_files "$(jq -R . < "$TEMP_MANAGED_FILES" | jq -s '.')" \
    --argjson managed_file_hashes "$MANAGED_FILE_HASHES_JSON" \
    --argjson preserved_file_hashes "$PRESERVED_FILE_HASHES_JSON" \
    --slurpfile source "$MANIFEST_SOURCE" '
    $source[0] + {
        generated_at: $generated_at,
        scaffold_hooks: {
            schema_version: 1,
            skill_name: "scaffold-hooks",
            harness: "opencode",
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
            plan_sha256: (if $plan_sha256 == "" then null else $plan_sha256 end),
            event_manifest_sha256: (if $event_manifest_sha256 == "" then null else $event_manifest_sha256 end),
            templates: {
                "lifecycle-action-plugin.ts.tmpl": (if $lifecycle_template_sha256 == "" then null else $lifecycle_template_sha256 end),
                "plugin-module.ts.tmpl": (if $plugin_template_sha256 == "" then null else $plugin_template_sha256 end)
            }
        },
        scope: $scope,
        deployment: $deployment,
        mode: $mode,
        module_format: $module_format,
        surface_catalog: $surface_catalog,
        plugin_root: $plugin_root,
        hooks_root: $hooks_root,
        managed_state_dir: $managed_state_dir,
        config_target: $config_target,
        package_target: $package_target,
        package_dependencies: $package_dependencies,
        enabled_plugins: $enabled_plugins,
        managed_files: $managed_files,
        managed_file_hashes: $managed_file_hashes,
        preserved_file_hashes: $preserved_file_hashes,
        setup_status: $setup_status
    }
    ' > "$MANIFEST_TARGET_FILE"

bash "$SCRIPT_DIR/render_hooks_readme.sh" \
    --project "$PROJECT_ROOT" \
    --plan "$PLAN_FILE" \
    ${HOME_OVERRIDE:+--home "$HOME_OVERRIDE"}

cat <<EOF
scaffold_hooks.sh complete
  project root:    $PROJECT_ROOT
  scope:           $SCOPE
  deployment:      $DEPLOYMENT
  plugin root:     $PLUGIN_ROOT_VALUE
  hook root:       $HOOKS_ROOT_VALUE
  managed state:   $MANAGED_STATE_VALUE
  mode:            $MODE
EOF

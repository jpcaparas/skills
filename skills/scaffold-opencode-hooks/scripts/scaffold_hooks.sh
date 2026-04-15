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
    local module_format="$2"
    case "$filename" in
        *.js|*.ts|*.mjs|*.cjs|*.jsx|*.tsx) printf '%s\n' "$filename" ;;
        *) printf '%s.%s\n' "$filename" "$module_format" ;;
    esac
}

render_handler_block() {
    local surface="$1"
    case "$surface" in
        event)
            cat <<'EOF'
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        // TODO: coordinate post-turn validation, notifications, or idle-triggered follow-up here.
      }
    },
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
event: async ({ event }) => {
  if (event.type === "session.idle") {
    // TODO: run post-turn validation or notifications here.
  }
},
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
require_command python3

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
MANIFEST_SOURCE="$SKILL_ROOT/assets/hook-events.json"
JS_TEMPLATE="$SKILL_ROOT/templates/plugin-module.js.tmpl"
TS_TEMPLATE="$SKILL_ROOT/templates/plugin-module.ts.tmpl"

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

MODULE_FORMAT="$(jq -r '.module_format // "js"' "$PLAN_FILE")"
case "$MODULE_FORMAT" in
    js|ts) ;;
    *)
        echo "module_format must be js or ts. Got: $MODULE_FORMAT" >&2
        exit 1
        ;;
esac

HOME_ROOT="${HOME_OVERRIDE:-$HOME}"
PLUGIN_ROOT_VALUE="$(jq -r '.plugin_root // empty' "$PLAN_FILE")"
MANAGED_STATE_VALUE="$(jq -r '.managed_state_dir // empty' "$PLAN_FILE")"
CONFIG_TARGET_VALUE="$(jq -r '.config_target // empty' "$PLAN_FILE")"
PACKAGE_TARGET_VALUE="$(jq -r '.package_target // empty' "$PLAN_FILE")"

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
        | while IFS= read -r filename; do normalize_filename "$filename" "$MODULE_FORMAT"; done \
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
    python3 "$SCRIPT_DIR/check_plugin_setup.py" "${SETUP_ARGS[@]}"
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
  managed state:   $MANAGED_STATE_VALUE
  config target:   $CONFIG_TARGET_VALUE
  package target:  $PACKAGE_TARGET_VALUE
EOF
    printf '  enabled plugins: %s\n' "$ENABLED_PLUGIN_COUNT"
    printf '  npm plugins:     %s\n' "$(jq '.npm_plugins | length' "$PLAN_FILE")"
    printf '  package deps:    %s\n' "$(printf '%s' "$PACKAGE_DEPS_JSON" | jq 'length')"
    exit 0
fi

mkdir -p "$PLUGIN_ROOT_ABS"

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

TEMP_MANAGED_FILES="$(mktemp)"
TEMP_ENABLED_PLUGINS="$(mktemp)"
cleanup() {
    rm -f "$TEMP_MANAGED_FILES" "$TEMP_ENABLED_PLUGINS"
}
trap cleanup EXIT

while IFS= read -r row; do
    name="$(printf '%s' "$row" | jq -r '.name')"
    notes="$(printf '%s' "$row" | jq -r '.notes // ""')"
    filename_raw="$(printf '%s' "$row" | jq -r '.filename')"
    filename="$(normalize_filename "$filename_raw" "$MODULE_FORMAT")"
    target_path="$PLUGIN_ROOT_ABS/$filename"
    surfaces_json="$(printf '%s' "$row" | jq -c '.surfaces // []')"

    if [ "$(printf '%s' "$surfaces_json" | jq 'length')" -eq 0 ]; then
        echo "Enabled plugin '$name' has no surfaces." >&2
        exit 1
    fi

    if [ "$MODE" = "additive" ] && [ -f "$target_path" ]; then
        printf '%s\n' "$filename" >> "$TEMP_MANAGED_FILES"
        printf '%s\n' "$(printf '%s' "$row" | jq -c --arg filename "$filename" '. + {filename: $filename}')" >> "$TEMP_ENABLED_PLUGINS"
        continue
    fi

    handlers_file="$(mktemp)"
    imports_file="$(mktemp)"
    {
        printf ''
    } > "$handlers_file"
    {
        if printf '%s' "$surfaces_json" | jq -e 'index("tool")' >/dev/null; then
            printf 'import { tool } from "@opencode-ai/plugin"\n\n'
        fi
    } > "$imports_file"

    while IFS= read -r surface; do
        render_handler_block "$surface" >> "$handlers_file"
        printf '\n' >> "$handlers_file"
    done < <(printf '%s' "$surfaces_json" | jq -r '.[]')

    template_path="$JS_TEMPLATE"
    if [ "$MODULE_FORMAT" = "ts" ]; then
        template_path="$TS_TEMPLATE"
    fi

    PLUGIN_NAME="$name" \
    PLUGIN_NOTES="$notes" \
    PLUGIN_SURFACES="$(printf '%s' "$surfaces_json" | jq -r 'join(", ")')" \
    python3 - "$template_path" "$imports_file" "$handlers_file" <<'PY' > "$target_path"
from pathlib import Path
import os
import sys

template = Path(sys.argv[1]).read_text(encoding="utf-8")
imports = Path(sys.argv[2]).read_text(encoding="utf-8")
handlers = Path(sys.argv[3]).read_text(encoding="utf-8").rstrip()
values = {
    "{{PLUGIN_NAME}}": os.environ["PLUGIN_NAME"],
    "{{NOTES}}": os.environ["PLUGIN_NOTES"],
    "{{SURFACES}}": os.environ["PLUGIN_SURFACES"],
    "{{IMPORTS}}": imports,
    "{{HANDLERS}}": handlers,
}
for key, value in values.items():
    template = template.replace(key, value)
print(template.rstrip() + "\n")
PY

    rm -f "$handlers_file" "$imports_file"

    printf '%s\n' "$filename" >> "$TEMP_MANAGED_FILES"
    printf '%s\n' "$(printf '%s' "$row" | jq -c --arg filename "$filename" '. + {filename: $filename}')" >> "$TEMP_ENABLED_PLUGINS"
done < <(jq -c '.enabled_plugins[]? // empty' "$PLAN_FILE")

if [ "$ENABLED_PLUGIN_COUNT" -gt 0 ]; then
    python3 "$SCRIPT_DIR/merge_package_json.py" \
        --package-file "$PACKAGE_TARGET_ABS" \
        --dependencies-json "$PACKAGE_DEPS_JSON" >/dev/null
fi

if [ "${#NPM_PLUGIN_ARGS[@]}" -gt 0 ]; then
    python3 "$SCRIPT_DIR/merge_opencode_config.py" \
        --config-file "$CONFIG_TARGET_ABS" \
        --plugins "${NPM_PLUGIN_ARGS[@]}" >/dev/null
fi

python3 - <<'PY' "$PLAN_FILE" "$PLAN_SNAPSHOT_FILE"
import json
import sys
from pathlib import Path

plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
Path(sys.argv[2]).write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
PY

jq -n \
    --arg generated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg scope "$SCOPE" \
    --arg deployment "$DEPLOYMENT" \
    --arg mode "$MODE" \
    --arg module_format "$MODULE_FORMAT" \
    --arg plugin_root "$PLUGIN_ROOT_VALUE" \
    --arg managed_state_dir "$MANAGED_STATE_VALUE" \
    --arg config_target "$CONFIG_TARGET_VALUE" \
    --arg package_target "$PACKAGE_TARGET_VALUE" \
    --argjson package_dependencies "$PACKAGE_DEPS_JSON" \
    --argjson setup_status "$SETUP_STATUS_JSON" \
    --argjson enabled_plugins "$(jq -s '.' "$TEMP_ENABLED_PLUGINS")" \
    --argjson managed_files "$(jq -R . < "$TEMP_MANAGED_FILES" | jq -s '.')" \
    --slurpfile source "$MANIFEST_SOURCE" '
    $source[0] + {
        generated_at: $generated_at,
        scope: $scope,
        deployment: $deployment,
        mode: $mode,
        module_format: $module_format,
        plugin_root: $plugin_root,
        managed_state_dir: $managed_state_dir,
        config_target: $config_target,
        package_target: $package_target,
        package_dependencies: $package_dependencies,
        enabled_plugins: $enabled_plugins,
        managed_files: $managed_files,
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
  managed state:   $MANAGED_STATE_VALUE
  mode:            $MODE
EOF

#!/usr/bin/env bash
#
# Run the Validate Skills GitHub Actions matrix through nektos/act.
#
# Ubuntu executes in a pinned Linux container. macOS executes directly on an
# Apple Silicon Mac through act's self-hosted mode; act cannot emulate macOS in
# Docker. The hosted GitHub Actions matrix remains the authoritative CI gate.
#
# Usage:
#   bash scripts/validate-ci-with-act.sh --matrix
#   bash scripts/validate-ci-with-act.sh --ubuntu
#   bash scripts/validate-ci-with-act.sh --macos
#   bash scripts/validate-ci-with-act.sh --list
#

set -euo pipefail

unset GREP_OPTIONS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

event="${SKILLS_ACT_EVENT:-pull_request}"
workflow="${SKILLS_ACT_WORKFLOW:-.github/workflows/validate-skills.yml}"
job="${SKILLS_ACT_JOB:-validate}"
mode="${SKILLS_ACT_OS:-all}"
image="${SKILLS_ACT_IMAGE:-ghcr.io/catthehacker/ubuntu@sha256:2362bb12b0c61438d334b9ed3686809981796a864ab89d93b5ee657652774eb7}"
arch="${SKILLS_ACT_ARCH:-linux/amd64}"
pull="${SKILLS_ACT_PULL:-true}"
offline="${SKILLS_ACT_OFFLINE:-false}"
list_only=0
mode_option=""
extra_args=()

usage() {
    cat <<'USAGE'
validate-ci-with-act.sh

Run the local Ubuntu/macOS validation matrix through nektos/act.

Usage:
  bash scripts/validate-ci-with-act.sh --matrix
  bash scripts/validate-ci-with-act.sh --ubuntu
  bash scripts/validate-ci-with-act.sh --macos
  bash scripts/validate-ci-with-act.sh --list

Modes:
  --matrix  Run Ubuntu in Docker and macOS on this Apple Silicon Mac (default).
  --ubuntu  Run only the ubuntu-24.04 container leg.
  --macos   Run only the macos-15 host leg; requires Apple Silicon macOS.
  --list    List the selected workflow without requiring Docker.

Environment:
  SKILLS_ACT_EVENT=pull_request
  SKILLS_ACT_WORKFLOW=.github/workflows/validate-skills.yml
  SKILLS_ACT_JOB=validate
  SKILLS_ACT_OS=all|ubuntu-24.04|macos-15
  SKILLS_ACT_IMAGE=<pinned Ubuntu image reference>
  SKILLS_ACT_ARCH=linux/amd64
  SKILLS_ACT_PULL=true|false
  SKILLS_ACT_OFFLINE=true|false
  SKILLS_ACT_MACOS_PYTHON=/path/to/python3.11-or-newer
  SKILLS_ACT_MACOS_NODE=/path/to/node
  SKILLS_ACT_MACOS_NPM=/path/to/npm
  SKILLS_ACT_MACOS_NPX=/path/to/npx
  SKILLS_ACT_MACOS_BUN=/path/to/bun

Logging arguments after -- may be passed to act: -v, --verbose, -q, --quiet,
--json, and --log-prefix-job-id.
USAGE
}

fail_usage() {
    echo "ERROR: $1" >&2
    exit 64
}

select_mode() {
    local requested="$1"
    local option="$2"

    if [ -n "$mode_option" ] && [ "$mode_option" != "$option" ]; then
        fail_usage "choose exactly one of --matrix, --ubuntu, or --macos"
    fi
    mode="$requested"
    mode_option="$option"
}

is_allowed_act_argument() {
    case "$1" in
        -v|--verbose|-q|--quiet|--json|--log-prefix-job-id)
            return 0
            ;;
    esac
    return 1
}

check_home_act_configuration() {
    local config_path
    local config_status

    if [ -z "${HOME:-}" ]; then
        echo "ERROR: HOME must be set so act configuration can be checked safely." >&2
        exit 64
    fi

    config_path="$HOME/.actrc"
    if [ ! -e "$config_path" ] && [ ! -L "$config_path" ]; then
        return
    fi
    if [ ! -f "$config_path" ] || [ ! -r "$config_path" ]; then
        echo "ERROR: act config is not a readable regular file: $config_path" >&2
        exit 64
    fi

    config_status=0
    grep -Eq '^[[:space:]]*[^#[:space:]]' "$config_path" || config_status=$?
    case "$config_status" in
        0)
            {
                echo "ERROR: HOME-level act arguments are disabled for deterministic matrix validation:"
                echo "  $config_path"
                echo "Temporarily move the config aside, then rerun this command."
            } >&2
            exit 64
            ;;
        1)
            ;;
        *)
            echo "ERROR: could not inspect act config safely: $config_path" >&2
            exit 64
            ;;
    esac
}

initialize_act_runtime() {
    act_runtime_root="$(mktemp -d "${TMPDIR:-/tmp}/skills-act-config.XXXXXX")"
    act_runtime_root="$(cd "$act_runtime_root" && pwd -P)"
    act_config_home="$act_runtime_root/config"
    act_invocation_dir="$act_runtime_root/invocation"
    mkdir -p "$act_config_home" "$act_invocation_dir"
}

cleanup_act_runtime() {
    if [ -z "${act_runtime_root:-}" ] || [ ! -d "$act_runtime_root" ]; then
        return
    fi
    case "$act_runtime_root" in
        */skills-act-config.??????)
            rm -rf -- "$act_runtime_root"
            ;;
        *)
            echo "WARNING: refusing to remove unexpected act runtime path: $act_runtime_root" >&2
            ;;
    esac
}

invoke_act() {
    (
        cd "$act_invocation_dir"
        XDG_CONFIG_HOME="$act_config_home" command act "$@"
    )
}

check_act_version() {
    local version_output
    local version
    local version_core
    local major
    local remainder
    local minor
    local patch

    if ! version_output="$(invoke_act --version 2>&1)"; then
        echo "ERROR: could not determine the installed act version." >&2
        exit 127
    fi

    version="${version_output##* }"
    version="${version#v}"
    version_core="${version%%[-+]*}"
    major="${version_core%%.*}"
    remainder="${version_core#*.}"
    minor="${remainder%%.*}"
    patch="${remainder#*.}"

    if [ "$remainder" = "$version_core" ] || [ "$patch" = "$remainder" ] || [[ "$patch" == *.* ]]; then
        echo "ERROR: could not parse act version from: $version_output" >&2
        exit 64
    fi
    for component in "$major" "$minor" "$patch"; do
        case "$component" in
            ''|*[!0-9]*)
                echo "ERROR: could not parse act version from: $version_output" >&2
                exit 64
                ;;
        esac
    done

    if [ "$major" -eq 0 ] && { [ "$minor" -lt 2 ] || { [ "$minor" -eq 2 ] && [ "$patch" -lt 89 ]; }; }; then
        {
            echo "ERROR: act v0.2.89 or later is required; found v$version_core."
            echo "Older releases can run the macOS matrix leg in a Linux container."
        } >&2
        exit 64
    fi
}

resolve_executable() {
    local request="$1"
    local executable_dir resolved

    if [[ "$request" == */* ]]; then
        executable_dir="$(cd "$(dirname "$request")" 2>/dev/null && pwd -P)" || return 1
        resolved="$executable_dir/$(basename "$request")"
        [ -x "$resolved" ] || return 1
        printf '%s\n' "$resolved"
        return 0
    fi

    command -v "$request" 2>/dev/null
}

resolve_macos_validation_python() {
    local explicit_request="${SKILLS_ACT_MACOS_PYTHON:-}"
    local candidate resolved
    local candidates=(python3 python3.11 python3.12 python3.13 python3.14 python3.15)

    if [ -n "$explicit_request" ]; then
        resolved="$(resolve_executable "$explicit_request" || true)"
        if [ -z "$resolved" ] \
            || ! "$resolved" -c 'import sys, venv; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
                >/dev/null 2>&1; then
            echo "ERROR: SKILLS_ACT_MACOS_PYTHON must select Python 3.11 or newer with venv support." >&2
            exit 64
        fi
        MACOS_VALIDATION_PYTHON="$resolved"
        return
    fi

    for candidate in "${candidates[@]}"; do
        resolved="$(resolve_executable "$candidate" || true)"
        if [ -n "$resolved" ] \
            && "$resolved" -c 'import sys, venv; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
                >/dev/null 2>&1; then
            MACOS_VALIDATION_PYTHON="$resolved"
            return
        fi
    done

    {
        echo "ERROR: the macOS act leg requires host Python 3.11 or newer with venv support."
        echo "Set SKILLS_ACT_MACOS_PYTHON to a compatible interpreter."
    } >&2
    exit 127
}

resolve_macos_node_toolchain() {
    local request="${SKILLS_ACT_MACOS_NODE:-node}"
    local node_dir npm_dir npx_dir npm_request npx_request version

    MACOS_VALIDATION_NODE="$(resolve_executable "$request" || true)"
    version="$("${MACOS_VALIDATION_NODE:-false}" --version 2>/dev/null || true)"
    if [ -z "$MACOS_VALIDATION_NODE" ] || [ -z "$version" ]; then
        echo "ERROR: SKILLS_ACT_MACOS_NODE must select a working Node.js runtime." >&2
        exit 64
    fi

    node_dir="$(dirname "$MACOS_VALIDATION_NODE")"
    npm_request="${SKILLS_ACT_MACOS_NPM:-}"
    if [ -z "$npm_request" ] && [ -x "$node_dir/npm" ]; then
        npm_request="$node_dir/npm"
    fi
    if [ -z "$npm_request" ]; then
        npm_request="npm"
    fi
    npx_request="${SKILLS_ACT_MACOS_NPX:-}"
    if [ -z "$npx_request" ] && [ -x "$node_dir/npx" ]; then
        npx_request="$node_dir/npx"
    fi
    if [ -z "$npx_request" ]; then
        npx_request="npx"
    fi
    MACOS_VALIDATION_NPM="$(resolve_executable "$npm_request" || true)"
    MACOS_VALIDATION_NPX="$(resolve_executable "$npx_request" || true)"
    npm_dir="$(dirname "${MACOS_VALIDATION_NPM:-.}")"
    npx_dir="$(dirname "${MACOS_VALIDATION_NPX:-.}")"
    if [ ! -x "$MACOS_VALIDATION_NPM" ] || [ ! -x "$MACOS_VALIDATION_NPX" ] \
        || ! PATH="$node_dir:$npm_dir:$npx_dir:$PATH" "$MACOS_VALIDATION_NPM" --version >/dev/null 2>&1 \
        || ! PATH="$node_dir:$npm_dir:$npx_dir:$PATH" "$MACOS_VALIDATION_NPX" --version >/dev/null 2>&1; then
        echo "ERROR: the macOS act leg requires working npm and npx commands for the selected Node.js runtime." >&2
        exit 64
    fi
}

resolve_macos_bun() {
    local request="${SKILLS_ACT_MACOS_BUN:-bun}"
    local version

    MACOS_VALIDATION_BUN="$(resolve_executable "$request" || true)"
    version="$("${MACOS_VALIDATION_BUN:-false}" --version 2>/dev/null || true)"
    if [ -z "$MACOS_VALIDATION_BUN" ] || [ -z "$version" ]; then
        echo "ERROR: SKILLS_ACT_MACOS_BUN must select a working Bun runtime." >&2
        exit 64
    fi
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --matrix|--all)
            select_mode "all" "--matrix"
            ;;
        --ubuntu)
            select_mode "ubuntu-24.04" "--ubuntu"
            ;;
        --macos)
            select_mode "macos-15" "--macos"
            ;;
        --list|-l)
            list_only=1
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --)
            shift
            extra_args+=("$@")
            break
            ;;
        *)
            extra_args+=("$1")
            ;;
    esac
    shift
done

if [ "${#extra_args[@]}" -gt 0 ]; then
    for extra_arg in "${extra_args[@]}"; do
        if ! is_allowed_act_argument "$extra_arg"; then
            fail_usage "act argument '$extra_arg' is not allowed by this wrapper"
        fi
    done
fi

case "$mode" in
    all|matrix)
        mode="all"
        ;;
    ubuntu|ubuntu-24.04)
        mode="ubuntu-24.04"
        ;;
    macos|macos-15)
        mode="macos-15"
        ;;
    *)
        fail_usage "SKILLS_ACT_OS must be all, ubuntu-24.04, or macos-15; got '$mode'"
        ;;
esac

case "$pull" in
    true|1)
        pull_enabled=1
        ;;
    false|0)
        pull_enabled=0
        ;;
    *)
        fail_usage "SKILLS_ACT_PULL must be true, false, 1, or 0; got '$pull'"
        ;;
esac

case "$offline" in
    true|1)
        offline_enabled=1
        ;;
    false|0)
        offline_enabled=0
        ;;
    *)
        fail_usage "SKILLS_ACT_OFFLINE must be true, false, 1, or 0; got '$offline'"
        ;;
esac

if [ ! -f "$workflow" ]; then
    echo "ERROR: workflow file not found: $workflow" >&2
    exit 1
fi

if ! command -v act >/dev/null 2>&1; then
    {
        echo "ERROR: act is not installed."
        echo "Install nektos/act v0.2.89 or later before running this preflight."
    } >&2
    exit 127
fi

check_home_act_configuration
initialize_act_runtime
trap cleanup_act_runtime EXIT
check_act_version

if [ "$list_only" -eq 1 ]; then
    list_cmd=(
        -C "$REPO_ROOT"
        -W "$workflow"
        --list
        --strict
        --container-architecture "$arch"
        -P "ubuntu-24.04=$image"
        -P "macos-15=-self-hosted"
        --env-file /dev/null
        --input-file /dev/null
        --secret-file /dev/null
        --var-file /dev/null
        --secret "GITHUB_TOKEN="
    )
    if [ "${#extra_args[@]}" -gt 0 ]; then
        list_cmd+=("${extra_args[@]}")
    fi
    invoke_act "${list_cmd[@]}"
    exit $?
fi

needs_ubuntu=0
needs_macos=0
case "$mode" in
    all)
        needs_ubuntu=1
        needs_macos=1
        ;;
    ubuntu-24.04)
        needs_ubuntu=1
        ;;
    macos-15)
        needs_macos=1
        ;;
esac

if [ "$needs_macos" -eq 1 ]; then
    host_os="$(uname -s)"
    host_arch="$(uname -m)"
    if [ "$host_os" != "Darwin" ] || [ "$host_arch" != "arm64" ]; then
        {
            echo "ERROR: the macos-15 act leg requires an Apple Silicon macOS host."
            echo "Detected: ${host_os}/${host_arch}. Run --ubuntu here and use GitHub Actions for macOS."
        } >&2
        exit 64
    fi

    for command_name in git rg http; do
        if ! command -v "$command_name" >/dev/null 2>&1; then
            echo "ERROR: the macOS host leg requires '$command_name' on PATH." >&2
            exit 127
        fi
    done
    resolve_macos_validation_python
    resolve_macos_node_toolchain
    resolve_macos_bun
fi

if [ "$needs_ubuntu" -eq 1 ]; then
    if ! command -v docker >/dev/null 2>&1; then
        echo "ERROR: Docker is required for the Ubuntu act leg." >&2
        exit 127
    fi
    if ! docker info >/dev/null 2>&1; then
        echo "ERROR: Docker is not running; start Docker before running the Ubuntu act leg." >&2
        exit 1
    fi
fi

run_act_leg() {
    local matrix_os="$1"
    local cmd=(
        "$event"
        -C "$REPO_ROOT"
        -W "$workflow"
        -j "$job"
        --matrix "os:$matrix_os"
        --strict
        --concurrent-jobs 1
    )

    case "$matrix_os" in
        ubuntu-24.04)
            cmd+=(
                --container-architecture "$arch"
                -P "ubuntu-24.04=$image"
            )
            ;;
        macos-15)
            cmd+=(-P "macos-15=-self-hosted")
            cmd+=(
                --env "SKILLS_ACT_MACOS_PYTHON=$MACOS_VALIDATION_PYTHON"
                --env "SKILLS_ACT_MACOS_NODE=$MACOS_VALIDATION_NODE"
                --env "SKILLS_ACT_MACOS_NPM=$MACOS_VALIDATION_NPM"
                --env "SKILLS_ACT_MACOS_NPX=$MACOS_VALIDATION_NPX"
                --env "SKILLS_ACT_MACOS_BUN=$MACOS_VALIDATION_BUN"
            )
            ;;
    esac

    if [ "$pull_enabled" -eq 0 ] || [ "$offline_enabled" -eq 1 ]; then
        cmd+=(--pull=false)
    fi
    if [ "$offline_enabled" -eq 1 ]; then
        cmd+=(--action-offline-mode)
    fi
    if [ "${#extra_args[@]}" -gt 0 ]; then
        cmd+=("${extra_args[@]}")
    fi

    # Fail closed: run real jobs in disposable workspaces, ignore default
    # dotenv/secret files, and prevent act from importing a GitHub token.
    cmd+=(
        --bind=false
        --no-skip-checkout=false
        --use-gitignore=true
        --reuse=false
        --rm
        --container-daemon-socket -
        --dryrun=false
        --graph=false
        --list=false
        --validate=false
        --watch=false
        --detect-event=false
        --bug-report=false
        --man-page=false
        --list-options=false
        --env-file /dev/null
        --input-file /dev/null
        --secret-file /dev/null
        --var-file /dev/null
        --secret "GITHUB_TOKEN="
        --env "AUDIFY_RUN_LIVE_TESTS=0"
    )
    invoke_act "${cmd[@]}"
}

case "$mode" in
    all)
        matrix_status=0
        run_act_leg ubuntu-24.04 || matrix_status=$?
        run_act_leg macos-15 || {
            leg_status=$?
            if [ "$matrix_status" -eq 0 ]; then
                matrix_status="$leg_status"
            fi
        }
        exit "$matrix_status"
        ;;
    ubuntu-24.04|macos-15)
        run_act_leg "$mode"
        ;;
esac

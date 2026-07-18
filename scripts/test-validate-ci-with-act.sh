#!/usr/bin/env bash
# Regression tests for the local nektos/act matrix wrapper.

set -euo pipefail

unset GREP_OPTIONS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_WRAPPER="$SCRIPT_DIR/validate-ci-with-act.sh"
TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/validate-ci-with-act-test.XXXXXX")"
TEST_ROOT="$(cd "$TEST_ROOT" && pwd -P)"
trap 'rm -rf "$TEST_ROOT"' EXIT

FIXTURE_ROOT="$TEST_ROOT/repo"
FAKE_BIN="$TEST_ROOT/bin"
ACT_CALL_LOG="$TEST_ROOT/act-calls.log"
ACT_CALL_COUNT_FILE="$TEST_ROOT/act-call-count"
DOCKER_CALL_LOG="$TEST_ROOT/docker-calls.log"
RUN_STDOUT="$TEST_ROOT/stdout.log"
RUN_STDERR="$TEST_ROOT/stderr.log"
TEST_HOME="$TEST_ROOT/home"
TEST_XDG_CONFIG_HOME="$TEST_ROOT/user-config"
PINNED_IMAGE="ghcr.io/catthehacker/ubuntu@sha256:2362bb12b0c61438d334b9ed3686809981796a864ab89d93b5ee657652774eb7"

mkdir -p "$FIXTURE_ROOT/scripts" "$FIXTURE_ROOT/.github/workflows" "$FAKE_BIN" "$TEST_HOME" "$TEST_XDG_CONFIG_HOME/act"
cp "$SOURCE_WRAPPER" "$FIXTURE_ROOT/scripts/validate-ci-with-act.sh"
printf '%s\n' 'name: Fixture' > "$FIXTURE_ROOT/.github/workflows/validate-skills.yml"
printf '%s\n' '--dryrun' > "$TEST_XDG_CONFIG_HOME/act/actrc"
for utility in basename dirname grep mkdir mktemp rm; do
    ln -s "$(command -v "$utility")" "$FAKE_BIN/$utility"
done

write_fake_act() {
    cat > "$FAKE_BIN/act" <<'FAKE_ACT'
#!/bin/bash
set -u
if [ "${1:-}" = "--version" ]; then
    printf '%s\n' "${FAKE_ACT_VERSION:-act version 0.2.89}"
    exit 0
fi
{
    printf '%s\n' '<call>'
    printf '<pwd=%s>\n' "$PWD"
    printf '<xdg=%s>\n' "${XDG_CONFIG_HOME:-}"
    printf '%s\n' "$@"
    printf '%s\n' '</call>'
} >> "${ACT_CALL_LOG:?ACT_CALL_LOG must be set}"
call_number=0
if [ -s "${ACT_CALL_COUNT_FILE:?ACT_CALL_COUNT_FILE must be set}" ]; then
    read -r call_number < "$ACT_CALL_COUNT_FILE"
fi
call_number=$((call_number + 1))
printf '%s\n' "$call_number" > "$ACT_CALL_COUNT_FILE"
case "$call_number" in
    1)
        exit "${FAKE_ACT_STATUS_1:-${FAKE_ACT_STATUS:-0}}"
        ;;
    2)
        exit "${FAKE_ACT_STATUS_2:-${FAKE_ACT_STATUS:-0}}"
        ;;
    *)
        exit "${FAKE_ACT_STATUS:-0}"
        ;;
esac
FAKE_ACT
    chmod +x "$FAKE_BIN/act"
}

write_fake_docker() {
    cat > "$FAKE_BIN/docker" <<'FAKE_DOCKER'
#!/bin/bash
set -u
printf '%s\n' "$*" >> "${DOCKER_CALL_LOG:?DOCKER_CALL_LOG must be set}"
if [ "${1:-}" = "info" ]; then
    exit "${FAKE_DOCKER_STATUS:-0}"
fi
exit 0
FAKE_DOCKER
    chmod +x "$FAKE_BIN/docker"
}

write_fake_uname() {
    cat > "$FAKE_BIN/uname" <<'FAKE_UNAME'
#!/bin/bash
set -u
case "${1:-}" in
    -s)
        printf '%s\n' "${FAKE_UNAME_S:-Darwin}"
        ;;
    -m)
        printf '%s\n' "${FAKE_UNAME_M:-arm64}"
        ;;
    *)
        printf '%s %s\n' "${FAKE_UNAME_S:-Darwin}" "${FAKE_UNAME_M:-arm64}"
        ;;
esac
FAKE_UNAME
    chmod +x "$FAKE_BIN/uname"
}

write_fake_host_command() {
    local command_name="$1"
    cat > "$FAKE_BIN/$command_name" <<'FAKE_COMMAND'
#!/bin/bash
exit 0
FAKE_COMMAND
    chmod +x "$FAKE_BIN/$command_name"
}

write_fake_node() {
    cat > "$FAKE_BIN/node" <<'FAKE_NODE'
#!/bin/bash
set -u
if [ "${1:-}" = "--version" ]; then
    if [ "${FAKE_NODE_STATUS:-0}" -ne 0 ]; then
        exit "$FAKE_NODE_STATUS"
    fi
    printf '%s\n' "${FAKE_NODE_VERSION:-v26.3.0}"
fi
exit 0
FAKE_NODE
    chmod +x "$FAKE_BIN/node"
}

write_fake_bun() {
    cat > "$FAKE_BIN/bun" <<'FAKE_BUN'
#!/bin/bash
set -u
if [ "${1:-}" = "--version" ]; then
    if [ "${FAKE_BUN_STATUS:-0}" -ne 0 ]; then
        exit "$FAKE_BUN_STATUS"
    fi
    printf '%s\n' "${FAKE_BUN_VERSION:-1.3.11}"
fi
exit 0
FAKE_BUN
    chmod +x "$FAKE_BIN/bun"
}

write_fake_python() {
    local command_name="$1"
    local status_variable="$2"
    cat > "$FAKE_BIN/$command_name" <<FAKE_PYTHON
#!/bin/bash
set -u
if [ "\${1:-}" = "-c" ]; then
    exit "\${$status_variable:-0}"
fi
exit 0
FAKE_PYTHON
    chmod +x "$FAKE_BIN/$command_name"
}

write_fake_act
write_fake_docker
write_fake_uname
for host_command in git npm npx rg http; do
    write_fake_host_command "$host_command"
done
write_fake_node
write_fake_bun
write_fake_python python3 FAKE_PYTHON3_STATUS
write_fake_python python3.11 FAKE_PYTHON311_STATUS

run_wrapper() {
    local environment=(
        env -i
        "PATH=$FAKE_BIN"
        "HOME=$TEST_HOME"
        "TMPDIR=${TMPDIR:-/tmp}"
        "XDG_CONFIG_HOME=$TEST_XDG_CONFIG_HOME"
        "ACT_CALL_LOG=$ACT_CALL_LOG"
        "ACT_CALL_COUNT_FILE=$ACT_CALL_COUNT_FILE"
        "DOCKER_CALL_LOG=$DOCKER_CALL_LOG"
        "FAKE_ACT_VERSION=${FAKE_ACT_VERSION:-act version 0.2.89}"
        "FAKE_ACT_STATUS=${FAKE_ACT_STATUS:-0}"
        "FAKE_ACT_STATUS_1=${FAKE_ACT_STATUS_1:-}"
        "FAKE_ACT_STATUS_2=${FAKE_ACT_STATUS_2:-}"
        "FAKE_DOCKER_STATUS=${FAKE_DOCKER_STATUS:-0}"
        "FAKE_UNAME_S=${FAKE_UNAME_S:-Darwin}"
        "FAKE_UNAME_M=${FAKE_UNAME_M:-arm64}"
        "FAKE_PYTHON3_STATUS=${FAKE_PYTHON3_STATUS:-0}"
        "FAKE_PYTHON311_STATUS=${FAKE_PYTHON311_STATUS:-0}"
        "FAKE_NODE_STATUS=${FAKE_NODE_STATUS:-0}"
        "FAKE_NODE_VERSION=${FAKE_NODE_VERSION:-v26.3.0}"
        "FAKE_BUN_STATUS=${FAKE_BUN_STATUS:-0}"
        "FAKE_BUN_VERSION=${FAKE_BUN_VERSION:-1.3.11}"
    )

    if [ -n "${TEST_ACT_OS+x}" ]; then
        environment+=("SKILLS_ACT_OS=$TEST_ACT_OS")
    fi
    if [ -n "${TEST_PULL+x}" ]; then
        environment+=("SKILLS_ACT_PULL=$TEST_PULL")
    fi
    if [ -n "${TEST_OFFLINE+x}" ]; then
        environment+=("SKILLS_ACT_OFFLINE=$TEST_OFFLINE")
    fi
    if [ -n "${TEST_WORKFLOW+x}" ]; then
        environment+=("SKILLS_ACT_WORKFLOW=$TEST_WORKFLOW")
    fi
    if [ -n "${TEST_MACOS_PYTHON+x}" ]; then
        environment+=("SKILLS_ACT_MACOS_PYTHON=$TEST_MACOS_PYTHON")
    fi
    if [ -n "${TEST_MACOS_NODE+x}" ]; then
        environment+=("SKILLS_ACT_MACOS_NODE=$TEST_MACOS_NODE")
    fi
    if [ -n "${TEST_MACOS_BUN+x}" ]; then
        environment+=("SKILLS_ACT_MACOS_BUN=$TEST_MACOS_BUN")
    fi

    : > "$ACT_CALL_LOG"
    printf '%s\n' '0' > "$ACT_CALL_COUNT_FILE"
    : > "$DOCKER_CALL_LOG"
    : > "$RUN_STDOUT"
    : > "$RUN_STDERR"
    RUN_STATUS=0
    "${environment[@]}" /bin/bash "$FIXTURE_ROOT/scripts/validate-ci-with-act.sh" "$@" \
        > "$RUN_STDOUT" 2> "$RUN_STDERR" || RUN_STATUS=$?
}

fail() {
    echo "FAIL: $1" >&2
    if [ -s "$RUN_STDERR" ]; then
        sed 's/^/  stderr: /' "$RUN_STDERR" >&2
    fi
    exit 1
}

assert_status() {
    local expected="$1"
    local scenario="$2"
    if [ "$RUN_STATUS" -ne "$expected" ]; then
        fail "$scenario: expected status $expected, got $RUN_STATUS"
    fi
}

assert_line() {
    local file="$1"
    local expected="$2"
    local scenario="$3"
    if ! grep -Fqx -- "$expected" "$file"; then
        fail "$scenario: expected exact log line '$expected'"
    fi
}

assert_no_line() {
    local file="$1"
    local unexpected="$2"
    local scenario="$3"
    if grep -Fqx -- "$unexpected" "$file"; then
        fail "$scenario: unexpected exact log line '$unexpected'"
    fi
}

assert_line_count() {
    local file="$1"
    local expected_line="$2"
    local expected_count="$3"
    local scenario="$4"
    local actual_count
    actual_count="$(grep -Fxc -- "$expected_line" "$file" || true)"
    if [ "$actual_count" -ne "$expected_count" ]; then
        fail "$scenario: expected '$expected_line' $expected_count time(s), got $actual_count"
    fi
}

assert_call_line() {
    local call_number="$1"
    local expected="$2"
    local scenario="$3"
    if ! awk -v target="$call_number" '
        $0 == "<call>" { call += 1 }
        call == target { print }
        $0 == "</call>" && call == target { exit }
    ' "$ACT_CALL_LOG" | grep -Fqx -- "$expected"; then
        fail "$scenario: call $call_number must contain '$expected'"
    fi
}

assert_call_has_no_line() {
    local call_number="$1"
    local unexpected="$2"
    local scenario="$3"
    if awk -v target="$call_number" '
        $0 == "<call>" { call += 1 }
        call == target { print }
        $0 == "</call>" && call == target { exit }
    ' "$ACT_CALL_LOG" | grep -Fqx -- "$unexpected"; then
        fail "$scenario: call $call_number must not contain '$unexpected'"
    fi
}

assert_stderr_contains() {
    local expected="$1"
    local scenario="$2"
    if ! grep -Fq -- "$expected" "$RUN_STDERR"; then
        fail "$scenario: expected stderr to contain '$expected'"
    fi
}

assert_empty() {
    local file="$1"
    local scenario="$2"
    if [ -s "$file" ]; then
        fail "$scenario: expected $file to be empty"
    fi
}

run_wrapper
assert_status 0 "default matrix"
assert_line_count "$ACT_CALL_LOG" "<call>" 2 "one invocation per matrix leg"
assert_no_line "$ACT_CALL_LOG" "<xdg=$TEST_XDG_CONFIG_HOME>" "isolated XDG act config"
if ! grep -Eq '^<pwd=.*/skills-act-config\.[^/]+/invocation>$' "$ACT_CALL_LOG"; then
    fail "isolated invocation directory: expected temporary act working directory"
fi
assert_line_count "$ACT_CALL_LOG" "pull_request" 2 "default matrix event"
assert_line_count "$ACT_CALL_LOG" ".github/workflows/validate-skills.yml" 2 "default workflow"
assert_line_count "$ACT_CALL_LOG" "$FIXTURE_ROOT" 2 "fixed working directory"
assert_line_count "$ACT_CALL_LOG" "--strict" 2 "strict workflow parsing"
assert_line_count "$ACT_CALL_LOG" "--concurrent-jobs" 2 "sequential matrix flag"
assert_line_count "$ACT_CALL_LOG" "1" 2 "sequential matrix value"
assert_line_count "$ACT_CALL_LOG" "--matrix" 2 "explicit matrix filters"
assert_line "$ACT_CALL_LOG" "os:ubuntu-24.04" "Ubuntu matrix value"
assert_line "$ACT_CALL_LOG" "os:macos-15" "macOS matrix value"
assert_call_line 1 "os:ubuntu-24.04" "first matrix invocation"
assert_call_line 1 "ubuntu-24.04=$PINNED_IMAGE" "first platform mapping"
assert_call_has_no_line 1 "os:macos-15" "first matrix isolation"
assert_call_has_no_line 1 "macos-15=-self-hosted" "first platform isolation"
assert_call_line 2 "os:macos-15" "second matrix invocation"
assert_call_line 2 "macos-15=-self-hosted" "second platform mapping"
assert_call_line 2 "SKILLS_ACT_MACOS_PYTHON=$FAKE_BIN/python3" "selected macOS Python"
assert_call_line 2 "SKILLS_ACT_MACOS_NODE=$FAKE_BIN/node" "selected macOS Node"
assert_call_line 2 "SKILLS_ACT_MACOS_NPM=$FAKE_BIN/npm" "selected macOS npm"
assert_call_line 2 "SKILLS_ACT_MACOS_NPX=$FAKE_BIN/npx" "selected macOS npx"
assert_call_line 2 "SKILLS_ACT_MACOS_BUN=$FAKE_BIN/bun" "selected macOS Bun"
assert_call_has_no_line 2 "os:ubuntu-24.04" "second matrix isolation"
assert_call_has_no_line 2 "ubuntu-24.04=$PINNED_IMAGE" "second platform isolation"
assert_call_has_no_line 1 "SKILLS_ACT_MACOS_PYTHON=$FAKE_BIN/python3" "macOS Python isolation"
assert_call_has_no_line 1 "SKILLS_ACT_MACOS_NODE=$FAKE_BIN/node" "macOS Node isolation"
assert_call_has_no_line 1 "SKILLS_ACT_MACOS_BUN=$FAKE_BIN/bun" "macOS Bun isolation"
assert_line_count "$ACT_CALL_LOG" "--rm" 2 "failed-workspace cleanup"
assert_line_count "$ACT_CALL_LOG" "--reuse=false" 2 "successful-workspace cleanup"
assert_line_count "$ACT_CALL_LOG" "--container-daemon-socket" 2 "disabled Docker socket mount"
assert_line_count "$ACT_CALL_LOG" "-" 2 "Docker socket disable value"
assert_line_count "$ACT_CALL_LOG" "--dryrun=false" 2 "real job execution"
assert_line_count "$ACT_CALL_LOG" "--bind=false" 2 "isolated checkout copy"
assert_line_count "$ACT_CALL_LOG" "--no-skip-checkout=false" 2 "local checkout bridge"
assert_line_count "$ACT_CALL_LOG" "--use-gitignore=true" 2 "ignored-file exclusion"
assert_line "$ACT_CALL_LOG" "ubuntu-24.04=$PINNED_IMAGE" "pinned Ubuntu image"
assert_line "$ACT_CALL_LOG" "macos-15=-self-hosted" "native macOS mapping"
assert_line_count "$ACT_CALL_LOG" "--env-file" 2 "disabled default environment files"
assert_line_count "$ACT_CALL_LOG" "--input-file" 2 "disabled default input files"
assert_line_count "$ACT_CALL_LOG" "--secret-file" 2 "disabled default secret files"
assert_line_count "$ACT_CALL_LOG" "--var-file" 2 "disabled default variable files"
assert_line_count "$ACT_CALL_LOG" "/dev/null" 8 "empty act input files"
assert_line_count "$ACT_CALL_LOG" "GITHUB_TOKEN=" 2 "disabled ambient GitHub token import"
assert_line_count "$ACT_CALL_LOG" "AUDIFY_RUN_LIVE_TESTS=0" 2 "disabled live probes"
assert_no_line "$ACT_CALL_LOG" "SKILLS_VALIDATE_ALLOW_UNTRACKED_SKILL_WORKTREE=1" "strict untracked-file guard"
assert_line "$DOCKER_CALL_LOG" "info" "Docker preflight"

mv "$FAKE_BIN/bun" "$FAKE_BIN/bun.disabled"
mv "$FAKE_BIN/python3" "$FAKE_BIN/python3.disabled"
mv "$FAKE_BIN/python3.11" "$FAKE_BIN/python3.11.disabled"
mv "$FAKE_BIN/node" "$FAKE_BIN/node.disabled"
mv "$FAKE_BIN/npm" "$FAKE_BIN/npm.disabled"
mv "$FAKE_BIN/npx" "$FAKE_BIN/npx.disabled"
FAKE_UNAME_S=Linux FAKE_UNAME_M=x86_64 run_wrapper --ubuntu -- --verbose
assert_status 0 "Ubuntu-only mode"
assert_line "$ACT_CALL_LOG" "--matrix" "Ubuntu matrix filter"
assert_line "$ACT_CALL_LOG" "os:ubuntu-24.04" "Ubuntu matrix value"
assert_line "$ACT_CALL_LOG" "--verbose" "act passthrough argument"
mv "$FAKE_BIN/python3.disabled" "$FAKE_BIN/python3"
mv "$FAKE_BIN/python3.11.disabled" "$FAKE_BIN/python3.11"
mv "$FAKE_BIN/node.disabled" "$FAKE_BIN/node"
mv "$FAKE_BIN/npm.disabled" "$FAKE_BIN/npm"
mv "$FAKE_BIN/npx.disabled" "$FAKE_BIN/npx"
mv "$FAKE_BIN/bun.disabled" "$FAKE_BIN/bun"

mv "$FAKE_BIN/docker" "$FAKE_BIN/docker.disabled"
run_wrapper --macos
assert_status 0 "macOS-only mode without Docker"
assert_line "$ACT_CALL_LOG" "os:macos-15" "macOS matrix value"
assert_empty "$DOCKER_CALL_LOG" "macOS must not probe Docker"
mv "$FAKE_BIN/docker.disabled" "$FAKE_BIN/docker"

FAKE_PYTHON3_STATUS=1 run_wrapper --macos
assert_status 0 "macOS mode selects an exact versioned Python"
assert_line "$ACT_CALL_LOG" "SKILLS_ACT_MACOS_PYTHON=$FAKE_BIN/python3.11" "versioned macOS Python"

TEST_MACOS_PYTHON="$FAKE_BIN/python3.11" run_wrapper --macos
assert_status 0 "explicit macOS Python"
assert_line "$ACT_CALL_LOG" "SKILLS_ACT_MACOS_PYTHON=$FAKE_BIN/python3.11" "explicit macOS Python forwarding"

FAKE_PYTHON3_STATUS=1 TEST_MACOS_PYTHON="$FAKE_BIN/python3" run_wrapper --macos
assert_status 64 "invalid explicit macOS Python"
assert_stderr_contains "SKILLS_ACT_MACOS_PYTHON must select Python 3.11 or newer" "invalid explicit macOS Python diagnostic"
assert_empty "$ACT_CALL_LOG" "invalid explicit macOS Python must not run act"

mv "$FAKE_BIN/python3" "$FAKE_BIN/python3.disabled"
mv "$FAKE_BIN/python3.11" "$FAKE_BIN/python3.11.disabled"
run_wrapper --macos
assert_status 127 "missing compatible macOS Python"
assert_stderr_contains "requires host Python 3.11 or newer" "missing compatible macOS Python diagnostic"
assert_empty "$ACT_CALL_LOG" "missing compatible macOS Python must not run act"
mv "$FAKE_BIN/python3.disabled" "$FAKE_BIN/python3"
mv "$FAKE_BIN/python3.11.disabled" "$FAKE_BIN/python3.11"

FAKE_NODE_STATUS=1 run_wrapper --macos
assert_status 64 "broken macOS Node"
assert_stderr_contains "must select a working Node.js runtime" "broken macOS Node diagnostic"
assert_empty "$ACT_CALL_LOG" "broken macOS Node must not run act"

FAKE_BUN_VERSION=1.4.0 run_wrapper --macos
assert_status 0 "alternate working macOS Bun version"
assert_line "$ACT_CALL_LOG" "SKILLS_ACT_MACOS_BUN=$FAKE_BIN/bun" "flexible macOS Bun forwarding"

FAKE_BUN_STATUS=1 run_wrapper --macos
assert_status 64 "broken macOS Bun"
assert_stderr_contains "must select a working Bun runtime" "broken macOS Bun diagnostic"
assert_empty "$ACT_CALL_LOG" "broken macOS Bun must not run act"

FAKE_UNAME_S=Linux FAKE_UNAME_M=x86_64 run_wrapper --macos
assert_status 64 "macOS mode on Linux"
assert_stderr_contains "requires an Apple Silicon macOS host" "Linux host rejection"
assert_empty "$ACT_CALL_LOG" "rejected Linux host must not run act"

FAKE_UNAME_S=Darwin FAKE_UNAME_M=x86_64 run_wrapper --macos
assert_status 64 "macOS mode on Intel"
assert_stderr_contains "Detected: Darwin/x86_64" "Intel host rejection"
assert_empty "$ACT_CALL_LOG" "rejected Intel host must not run act"

mv "$FAKE_BIN/docker" "$FAKE_BIN/docker.disabled"
mv "$FAKE_BIN/bun" "$FAKE_BIN/bun.disabled"
run_wrapper --list
assert_status 0 "list mode without runtime prerequisites"
assert_line "$ACT_CALL_LOG" "--list" "list mode"
assert_empty "$DOCKER_CALL_LOG" "list mode must not probe Docker"
mv "$FAKE_BIN/bun.disabled" "$FAKE_BIN/bun"
mv "$FAKE_BIN/docker.disabled" "$FAKE_BIN/docker"

TEST_PULL=false TEST_OFFLINE=true run_wrapper --ubuntu
assert_status 0 "offline Ubuntu mode"
assert_line "$ACT_CALL_LOG" "--action-offline-mode" "offline action cache"
assert_line_count "$ACT_CALL_LOG" "--pull=false" 1 "offline pull suppression"

TEST_ACT_OS=invalid run_wrapper
assert_status 64 "invalid environment mode"
assert_stderr_contains "SKILLS_ACT_OS must be" "invalid mode diagnostic"
assert_empty "$ACT_CALL_LOG" "invalid mode must not run act"

TEST_PULL=maybe run_wrapper --ubuntu
assert_status 64 "invalid pull setting"
assert_stderr_contains "SKILLS_ACT_PULL must be" "invalid pull diagnostic"

TEST_OFFLINE=maybe run_wrapper --ubuntu
assert_status 64 "invalid offline setting"
assert_stderr_contains "SKILLS_ACT_OFFLINE must be" "invalid offline diagnostic"

run_wrapper --ubuntu --macos
assert_status 64 "conflicting mode flags"
assert_stderr_contains "choose exactly one" "conflicting mode diagnostic"

run_wrapper --ubuntu -- --bind
assert_status 64 "managed act argument override"
assert_stderr_contains "is not allowed by this wrapper" "managed argument diagnostic"
assert_empty "$ACT_CALL_LOG" "managed argument override must not run act"

run_wrapper --ubuntu -- -C/tmp/alternate-worktree
assert_status 64 "attached working-directory override"
assert_stderr_contains "is not allowed by this wrapper" "attached short argument diagnostic"
assert_empty "$ACT_CALL_LOG" "attached working-directory override must not run act"

run_wrapper --ubuntu -- --dryrun
assert_status 64 "execution-bypass argument"
assert_stderr_contains "is not allowed by this wrapper" "execution-bypass diagnostic"
assert_empty "$ACT_CALL_LOG" "execution-bypass argument must not run act"

run_wrapper --ubuntu -- --pull=true
assert_status 64 "managed pull override"
assert_stderr_contains "is not allowed by this wrapper" "managed pull diagnostic"
assert_empty "$ACT_CALL_LOG" "managed pull override must not run act"

run_wrapper --ubuntu -- -vn
assert_status 64 "grouped shorthand bypass"
assert_stderr_contains "is not allowed by this wrapper" "grouped shorthand diagnostic"
assert_empty "$ACT_CALL_LOG" "grouped shorthand bypass must not run act"

printf '%s\n' '--dryrun' > "$TEST_HOME/.actrc"
run_wrapper --ubuntu
assert_status 64 "home act config injection"
assert_stderr_contains "HOME-level act arguments are disabled" "home config diagnostic"
assert_empty "$ACT_CALL_LOG" "home act config must not run act"
mv "$TEST_HOME/.actrc" "$TEST_HOME/.actrc.disabled"

printf '%s\n' '--matrix os:ubuntu-24.04' > "$FIXTURE_ROOT/.actrc"
run_wrapper --macos
assert_status 0 "isolated repository act config"
assert_line "$ACT_CALL_LOG" "os:macos-15" "repository config must not filter matrix"
mv "$FIXTURE_ROOT/.actrc" "$FIXTURE_ROOT/.actrc.disabled"

FAKE_ACT_VERSION='act version 0.2.88' run_wrapper --ubuntu
assert_status 64 "unsupported act version"
assert_stderr_contains "v0.2.89 or later is required" "unsupported act version diagnostic"
assert_empty "$ACT_CALL_LOG" "unsupported act version must not run jobs"

FAKE_ACT_VERSION='act version development' run_wrapper --ubuntu
assert_status 64 "unparseable act version"
assert_stderr_contains "could not parse act version" "unparseable act version diagnostic"
assert_empty "$ACT_CALL_LOG" "unparseable act version must not run jobs"

mv "$FAKE_BIN/act" "$FAKE_BIN/act.disabled"
run_wrapper --ubuntu
assert_status 127 "missing act"
assert_stderr_contains "act is not installed" "missing act diagnostic"
mv "$FAKE_BIN/act.disabled" "$FAKE_BIN/act"

mv "$FAKE_BIN/docker" "$FAKE_BIN/docker.disabled"
run_wrapper --ubuntu
assert_status 127 "missing Docker"
assert_stderr_contains "Docker is required" "missing Docker diagnostic"
mv "$FAKE_BIN/docker.disabled" "$FAKE_BIN/docker"

FAKE_DOCKER_STATUS=1 run_wrapper --ubuntu
assert_status 1 "stopped Docker daemon"
assert_stderr_contains "Docker is not running" "stopped Docker diagnostic"
assert_empty "$ACT_CALL_LOG" "stopped Docker must not run act"

mv "$FAKE_BIN/http" "$FAKE_BIN/http.disabled"
run_wrapper --macos
assert_status 127 "missing macOS host tool"
assert_stderr_contains "requires 'http'" "missing host tool diagnostic"
assert_empty "$ACT_CALL_LOG" "missing host tool must not run act"
mv "$FAKE_BIN/http.disabled" "$FAKE_BIN/http"

TEST_WORKFLOW=.github/workflows/missing.yml run_wrapper --ubuntu
assert_status 1 "missing workflow"
assert_stderr_contains "workflow file not found" "missing workflow diagnostic"

FAKE_ACT_STATUS=23 run_wrapper --ubuntu
assert_status 23 "act failure propagation"

FAKE_ACT_STATUS_1=23 FAKE_ACT_STATUS_2=0 run_wrapper --matrix
assert_status 23 "Ubuntu failure propagation"
assert_line_count "$ACT_CALL_LOG" "<call>" 2 "macOS still runs after Ubuntu failure"
assert_call_line 2 "os:macos-15" "macOS run after Ubuntu failure"

FAKE_ACT_STATUS_1=0 FAKE_ACT_STATUS_2=29 run_wrapper --matrix
assert_status 29 "macOS failure propagation"
assert_line_count "$ACT_CALL_LOG" "<call>" 2 "both legs run before macOS failure"

FAKE_ACT_STATUS_1=23 FAKE_ACT_STATUS_2=29 run_wrapper --matrix
assert_status 23 "first matrix failure wins"
assert_line_count "$ACT_CALL_LOG" "<call>" 2 "both failing legs execute"

printf '%s\n' 'PASS: act wrapper enforces honest Ubuntu-container and macOS-host matrix execution'

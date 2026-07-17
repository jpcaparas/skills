#!/usr/bin/env bash

set -euo pipefail

unset AGENT_HOOK_HARNESS AGENT_HOOK_SESSION_ID SKILLS_AGENT_STOP_FORCE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_SCRIPT="$SCRIPT_DIR/agent-stop-checks.sh"
SOURCE_SESSION_CONTEXT_SCRIPT="$SCRIPT_DIR/agent-session-context.sh"
SOURCE_SNAPSHOT_SCRIPT="$SCRIPT_DIR/agent-repo-snapshot.sh"
TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/agent-stop-checks-test.XXXXXX")"
TEST_REPO="$TEST_ROOT/repo"
COUNT_FILE="$TEST_ROOT/validation-count"

cleanup() {
    rm -rf "$TEST_ROOT"
}
trap cleanup EXIT

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

assert_validation_count() {
    local expected="$1"
    local actual="0"
    if [ -f "$COUNT_FILE" ]; then
        actual="$(sed -n '1p' "$COUNT_FILE")"
    fi
    if [ "$actual" != "$expected" ]; then
        fail "expected validator count $expected, got $actual"
    fi
}

assert_status() {
    local expected="$1"
    local actual="$2"
    local scenario="$3"
    if [ "$actual" != "$expected" ]; then
        fail "$scenario: expected status $expected, got $actual"
    fi
}

snapshot_hash_with_deadline() {
    local scenario="$1"

    SNAPSHOT_REPO="$TEST_REPO" \
        SNAPSHOT_SCRIPT="$TEST_REPO/scripts/agent-repo-snapshot.sh" \
        SNAPSHOT_SCENARIO="$scenario" \
        python3 - <<'PY'
import os
import re
import signal
import subprocess
import sys

command = [
    "bash",
    "-c",
    'set -euo pipefail; source "$1"; agent_repo_snapshot_hash "$2"',
    "snapshot-test",
    os.environ["SNAPSHOT_SCRIPT"],
    os.environ["SNAPSHOT_REPO"],
]
process = subprocess.Popen(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    start_new_session=True,
)
try:
    stdout, stderr = process.communicate(timeout=5)
except subprocess.TimeoutExpired:
    os.killpg(process.pid, signal.SIGKILL)
    process.communicate()
    print(
        f'{os.environ["SNAPSHOT_SCENARIO"]}: snapshot calculation timed out',
        file=sys.stderr,
    )
    raise SystemExit(124)

if process.returncode != 0:
    print(stderr, file=sys.stderr, end="")
    raise SystemExit(process.returncode)
if re.fullmatch(r"[0-9a-f]{64}\n?", stdout) is None:
    print(
        f'{os.environ["SNAPSHOT_SCENARIO"]}: invalid snapshot output {stdout!r}',
        file=sys.stderr,
    )
    raise SystemExit(1)
sys.stdout.write(stdout)
PY
}

assert_snapshot_completes() {
    local scenario="$1"

    if ! snapshot_hash_with_deadline "$scenario" >/dev/null; then
        fail "$scenario did not produce a bounded repository snapshot"
    fi
}

mkdir -p "$TEST_REPO/scripts"
cp "$SOURCE_SCRIPT" "$TEST_REPO/scripts/agent-stop-checks.sh"
cp "$SOURCE_SESSION_CONTEXT_SCRIPT" "$TEST_REPO/scripts/agent-session-context.sh"
cp "$SOURCE_SNAPSHOT_SCRIPT" "$TEST_REPO/scripts/agent-repo-snapshot.sh"
cat >"$TEST_REPO/scripts/validate-all-skills.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

count=0
if [ -f "$COUNT_FILE" ]; then
    count="$(sed -n '1p' "$COUNT_FILE")"
fi
printf '%s\n' "$((count + 1))" >"$COUNT_FILE"

if [ "${MUTATE_REPO_DURING_VALIDATION:-0}" = "1" ]; then
    printf 'validator mutation\n' >>tracked.txt
fi

if [ "${FAIL_VALIDATION:-0}" = "1" ]; then
    exit 1
fi
EOF

git -C "$TEST_REPO" init -q
git -C "$TEST_REPO" config user.email "stop-checks-test@example.invalid"
git -C "$TEST_REPO" config user.name "Stop Checks Test"
printf 'baseline\n' >"$TEST_REPO/tracked.txt"
git -C "$TEST_REPO" add scripts tracked.txt
git -C "$TEST_REPO" commit -qm "test: create stop-check fixture"

snapshot_without_special_file="$(
    snapshot_hash_with_deadline "repository without special files"
)" || fail "could not capture the special-file control snapshot"

ln -s /dev/zero "$TEST_REPO/untracked-zero-link"
assert_snapshot_completes "untracked symlink to /dev/zero"
snapshot_with_zero_link="$(
    snapshot_hash_with_deadline "repository with symlink to /dev/zero"
)" || fail "could not capture the symlink snapshot"
if [ "$snapshot_with_zero_link" = "$snapshot_without_special_file" ]; then
    fail "an untracked symlink did not affect the repository snapshot"
fi
unlink "$TEST_REPO/untracked-zero-link"

mkfifo "$TEST_REPO/untracked-pipe"
assert_snapshot_completes "untracked FIFO without a writer"
snapshot_with_fifo="$(
    snapshot_hash_with_deadline "repository with FIFO"
)" || fail "could not capture the FIFO snapshot"
if [ "$snapshot_with_fifo" = "$snapshot_without_special_file" ]; then
    fail "an untracked FIFO did not affect the repository snapshot"
fi
unlink "$TEST_REPO/untracked-pipe"

snapshot_after_special_files="$(
    snapshot_hash_with_deadline "repository after removing special files"
)" || fail "could not capture the restored special-file snapshot"
if [ "$snapshot_after_special_files" != "$snapshot_without_special_file" ]; then
    fail "removing untracked special files did not restore the repository snapshot"
fi

DISCOVERY_FAILURE_BIN="$TEST_ROOT/discovery-failure-bin"
DISCOVERY_FAILURE_OUTPUT="$TEST_ROOT/discovery-failure-output.txt"
mkdir -p "$DISCOVERY_FAILURE_BIN"
cat >"$DISCOVERY_FAILURE_BIN/find" <<'EOF'
#!/usr/bin/env bash
exit 73
EOF
chmod +x "$DISCOVERY_FAILURE_BIN/find"

set +e
(
    cd "$TEST_REPO"
    PATH="$DISCOVERY_FAILURE_BIN:$PATH" \
        COUNT_FILE="$COUNT_FILE" \
        SKILLS_AGENT_STOP_FORCE=1 \
        bash scripts/agent-stop-checks.sh \
        >"$DISCOVERY_FAILURE_OUTPUT" 2>&1
)
discovery_failure_status=$?
set -e
assert_status 2 "$discovery_failure_status" "snapshot discovery failure"
assert_validation_count 0
if ! grep -Fq \
    "Unable to capture a complete repository snapshot; stop validation cannot proceed safely." \
    "$DISCOVERY_FAILURE_OUTPUT"; then
    fail "snapshot discovery failure did not report the blocking decision"
fi

FAILED_SESSION_BASELINE="$TEST_REPO/.git/agent-hooks/session-baselines/test-snapshot-failure.env"
set +e
(
    cd "$TEST_ROOT"
    PATH="$DISCOVERY_FAILURE_BIN:$PATH" \
        AGENT_HOOK_PROJECT_ROOT="$TEST_REPO" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=snapshot-failure \
        bash "$TEST_REPO/scripts/agent-session-context.sh" >/dev/null 2>&1
)
failed_session_status=$?
set -e
assert_status 1 "$failed_session_status" "SessionStart snapshot discovery failure"
if [ -e "$FAILED_SESSION_BASELINE" ] || [ -L "$FAILED_SESSION_BASELINE" ]; then
    fail "SessionStart wrote a baseline after snapshot discovery failed"
fi

HASH_FAILURE_BIN="$TEST_ROOT/hash-failure-bin"
mkdir -p "$HASH_FAILURE_BIN"
cat >"$HASH_FAILURE_BIN/perl" <<'EOF'
#!/usr/bin/env bash
exit 74
EOF
chmod +x "$HASH_FAILURE_BIN/perl"
printf 'untracked hash evidence\n' >"$TEST_REPO/untracked-evidence.txt"
set +e
(
    cd "$TEST_REPO"
    PATH="$HASH_FAILURE_BIN:$PATH" \
        COUNT_FILE="$COUNT_FILE" \
        SKILLS_AGENT_STOP_FORCE=1 \
        bash scripts/agent-stop-checks.sh >/dev/null 2>&1
)
hash_failure_status=$?
set -e
assert_status 2 "$hash_failure_status" "untracked-file hashing failure"
assert_validation_count 0
unlink "$TEST_REPO/untracked-evidence.txt"

if [ -e "$TEST_REPO/.git/agent-hooks/last-successful-stop.env" ] \
    || [ -L "$TEST_REPO/.git/agent-hooks/last-successful-stop.env" ]; then
    fail "snapshot evidence failure created a validation cache record"
fi

AGENT_HOOKS_DIR="$TEST_REPO/.git/agent-hooks"
STATE_REDIRECT_DIR="$TEST_ROOT/state-redirect"
mkdir -p "$STATE_REDIRECT_DIR"
ln -s "$STATE_REDIRECT_DIR" "$AGENT_HOOKS_DIR"

set +e
(
    cd "$TEST_ROOT"
    AGENT_HOOK_PROJECT_ROOT="$TEST_REPO" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=agent-hooks-symlink \
        bash "$TEST_REPO/scripts/agent-session-context.sh" >/dev/null 2>&1
)
agent_hooks_symlink_status=$?
set -e
assert_status 1 "$agent_hooks_symlink_status" "symlinked agent-hooks directory"
if [ -e "$STATE_REDIRECT_DIR/session-baselines/test-agent-hooks-symlink.env" ]; then
    fail "session baseline recording followed the agent-hooks directory symlink"
fi
unlink "$AGENT_HOOKS_DIR"

mkdir -p "$AGENT_HOOKS_DIR"
ln -s "$STATE_REDIRECT_DIR" "$AGENT_HOOKS_DIR/session-baselines"
set +e
(
    cd "$TEST_ROOT"
    AGENT_HOOK_PROJECT_ROOT="$TEST_REPO" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=baseline-dir-symlink \
        bash "$TEST_REPO/scripts/agent-session-context.sh" >/dev/null 2>&1
)
baseline_dir_symlink_status=$?
set -e
assert_status 1 "$baseline_dir_symlink_status" "symlinked session-baselines directory"
if [ -e "$STATE_REDIRECT_DIR/test-baseline-dir-symlink.env" ]; then
    fail "session baseline recording followed the session-baselines directory symlink"
fi
unlink "$AGENT_HOOKS_DIR/session-baselines"

CACHE_DIR="$TEST_REPO/.git/agent-hooks"
CACHE_FILE="$CACHE_DIR/last-successful-stop.env"
CACHE_VICTIM="$TEST_ROOT/cache-victim.txt"
mkdir -p "$CACHE_DIR"
printf 'cache victim must stay unchanged\n' >"$CACHE_VICTIM"
ln -s "$CACHE_VICTIM" "$CACHE_FILE"

(
    cd "$TEST_REPO"
    CACHE_FILE="$CACHE_FILE" \
        CACHE_VICTIM="$CACHE_VICTIM" \
        COUNT_FILE="$COUNT_FILE" \
        bash -c '
            ln -s "$CACHE_VICTIM" "${CACHE_FILE}.tmp.$$"
            SKILLS_AGENT_STOP_FORCE=1 exec bash scripts/agent-stop-checks.sh
        ' >/dev/null
)
assert_validation_count 1
if [ "$(sed -n '1p' "$CACHE_VICTIM")" != "cache victim must stay unchanged" ]; then
    fail "validation cache recording followed a predictable temporary symlink"
fi
if [ -L "$CACHE_FILE" ] || [ ! -f "$CACHE_FILE" ]; then
    fail "validation cache recording did not replace the symlink with a regular file"
fi
if ! LC_ALL=C grep -Eq '^snapshot=[0-9a-f]{64}$' "$CACHE_FILE"; then
    fail "validation cache recording did not write an exact snapshot data line"
fi

(
    cd "$TEST_REPO"
    COUNT_FILE="$COUNT_FILE" bash scripts/agent-stop-checks.sh >/dev/null
)
assert_validation_count 1

printf 'first change\n' >>"$TEST_REPO/tracked.txt"
(
    cd "$TEST_REPO"
    COUNT_FILE="$COUNT_FILE" bash scripts/agent-stop-checks.sh >/dev/null
)
assert_validation_count 2

printf 'failing change\n' >>"$TEST_REPO/tracked.txt"
set +e
(
    cd "$TEST_REPO"
    COUNT_FILE="$COUNT_FILE" FAIL_VALIDATION=1 bash scripts/agent-stop-checks.sh >/dev/null 2>&1
)
failure_status=$?
set -e
assert_status 2 "$failure_status" "failing validator"
assert_validation_count 3

(
    cd "$TEST_REPO"
    COUNT_FILE="$COUNT_FILE" bash scripts/agent-stop-checks.sh >/dev/null
)
assert_validation_count 4

printf 'concurrent-change setup\n' >>"$TEST_REPO/tracked.txt"
set +e
(
    cd "$TEST_REPO"
    COUNT_FILE="$COUNT_FILE" MUTATE_REPO_DURING_VALIDATION=1 bash scripts/agent-stop-checks.sh >/dev/null 2>&1
)
mutation_status=$?
set -e
assert_status 2 "$mutation_status" "repository mutation during validation"
assert_validation_count 5

(
    cd "$TEST_REPO"
    COUNT_FILE="$COUNT_FILE" bash scripts/agent-stop-checks.sh >/dev/null
)
assert_validation_count 6

git -C "$TEST_REPO" add tracked.txt
git -C "$TEST_REPO" commit -qm "test: establish hook-session baseline"

MISSING_BASELINE_OUTPUT="$TEST_ROOT/missing-baseline-output.txt"
set +e
(
    cd "$TEST_ROOT"
    COUNT_FILE="$COUNT_FILE" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=missing-session \
        bash "$TEST_REPO/scripts/agent-stop-checks.sh" \
        >/dev/null 2>"$MISSING_BASELINE_OUTPUT"
)
missing_baseline_status=$?
set -e
assert_status 0 "$missing_baseline_status" "missing hook-session baseline"
assert_validation_count 7
if ! grep -Fq \
    "No agent session baseline found; running stop validation instead of skipping." \
    "$MISSING_BASELINE_OUTPUT"; then
    fail "missing baseline did not report its fail-safe validation decision"
fi

printf 'dirty before session start\n' >>"$TEST_REPO/tracked.txt"
(
    cd "$TEST_ROOT"
    AGENT_HOOK_PROJECT_ROOT="$TEST_REPO" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=dirty-session \
        bash "$TEST_REPO/scripts/agent-session-context.sh" >/dev/null
)
(
    cd "$TEST_ROOT"
    COUNT_FILE="$COUNT_FILE" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=dirty-session \
        bash "$TEST_REPO/scripts/agent-stop-checks.sh" >/dev/null 2>&1
)
assert_validation_count 7

BASELINE_DIR="$TEST_REPO/.git/agent-hooks/session-baselines"
SYMLINK_BASELINE="$BASELINE_DIR/test-symlink-session.env"
SYMLINK_VICTIM="$TEST_ROOT/symlink-victim.txt"
mkdir -p "$BASELINE_DIR"
printf 'victim must stay unchanged\n' >"$SYMLINK_VICTIM"
ln -s "$SYMLINK_VICTIM" "$SYMLINK_BASELINE"

(
    cd "$TEST_ROOT"
    AGENT_HOOK_PROJECT_ROOT="$TEST_REPO" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=symlink-session \
        bash "$TEST_REPO/scripts/agent-session-context.sh" >/dev/null
)

if [ "$(sed -n '1p' "$SYMLINK_VICTIM")" != "victim must stay unchanged" ]; then
    fail "session baseline recording followed a symlink and overwrote its target"
fi
if [ -L "$SYMLINK_BASELINE" ] || [ ! -f "$SYMLINK_BASELINE" ]; then
    fail "session baseline recording did not replace the symlink with a regular file"
fi
if ! LC_ALL=C grep -Eq '^snapshot=[0-9a-f]{64}$' "$SYMLINK_BASELINE"; then
    fail "session baseline recording did not write an exact snapshot data line"
fi

BASELINE_FILE="$BASELINE_DIR/test-baseline-session.env"
OUTSIDE_BASELINE="$TEST_ROOT/.git/agent-hooks/session-baselines/test-baseline-session.env"
(
    cd "$TEST_ROOT"
    AGENT_HOOK_PROJECT_ROOT="$TEST_REPO" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=baseline-session \
        bash "$TEST_REPO/scripts/agent-session-context.sh" >/dev/null
)

if [ ! -f "$BASELINE_FILE" ]; then
    fail "session baseline was not written inside the repository git directory"
fi
if [ -e "$OUTSIDE_BASELINE" ] || [ -L "$OUTSIDE_BASELINE" ]; then
    fail "session baseline used a relative git directory from the caller's cwd"
fi

(
    cd "$TEST_ROOT"
    COUNT_FILE="$COUNT_FILE" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=baseline-session \
        bash "$TEST_REPO/scripts/agent-stop-checks.sh" >/dev/null 2>&1
)
assert_validation_count 7

COMMAND_MARKER="$TEST_ROOT/baseline-command-ran"
printf 'touch "%s"\n' "$COMMAND_MARKER" >>"$BASELINE_FILE"
printf 'invalid-baseline change\n' >>"$TEST_REPO/tracked.txt"

set +e
(
    cd "$TEST_ROOT"
    COUNT_FILE="$COUNT_FILE" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=baseline-session \
        bash "$TEST_REPO/scripts/agent-stop-checks.sh" >/dev/null 2>&1
)
invalid_baseline_status=$?
set -e
assert_status 0 "$invalid_baseline_status" "baseline containing non-data shell content"
if [ -e "$COMMAND_MARKER" ]; then
    fail "stop checks executed shell content from the session baseline"
fi
assert_validation_count 8

printf 'hook-session change\n' >>"$TEST_REPO/tracked.txt"
(
    cd "$TEST_ROOT"
    COUNT_FILE="$COUNT_FILE" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=baseline-session \
        bash "$TEST_REPO/scripts/agent-stop-checks.sh" >/dev/null 2>&1
)
assert_validation_count 9

(
    cd "$TEST_ROOT"
    COUNT_FILE="$COUNT_FILE" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=baseline-session \
        bash "$TEST_REPO/scripts/agent-stop-checks.sh" >/dev/null 2>&1
)
assert_validation_count 9

printf 'hook-session failing change\n' >>"$TEST_REPO/tracked.txt"
set +e
(
    cd "$TEST_ROOT"
    COUNT_FILE="$COUNT_FILE" \
        FAIL_VALIDATION=1 \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=baseline-session \
        bash "$TEST_REPO/scripts/agent-stop-checks.sh" >/dev/null 2>&1
)
hook_failure_status=$?
set -e
assert_status 2 "$hook_failure_status" "hook-session failing validator"
assert_validation_count 10

(
    cd "$TEST_ROOT"
    COUNT_FILE="$COUNT_FILE" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=baseline-session \
        bash "$TEST_REPO/scripts/agent-stop-checks.sh" >/dev/null 2>&1
)
assert_validation_count 11

cache_snapshot="$(sed -n 's/^snapshot=\([0-9a-f]\{64\}\)$/\1/p' "$CACHE_FILE")"
printf 'snapshot=%s\n' "$cache_snapshot" >>"$CACHE_FILE"
(
    cd "$TEST_ROOT"
    COUNT_FILE="$COUNT_FILE" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=baseline-session \
        bash "$TEST_REPO/scripts/agent-stop-checks.sh" >/dev/null 2>&1
)
assert_validation_count 12

cache_validated_at="$(sed -n '/^validated_at=/p' "$CACHE_FILE")"
printf '%s\n' "$cache_validated_at" >>"$CACHE_FILE"
(
    cd "$TEST_ROOT"
    COUNT_FILE="$COUNT_FILE" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=baseline-session \
        bash "$TEST_REPO/scripts/agent-stop-checks.sh" >/dev/null 2>&1
)
assert_validation_count 13

printf 'unexpected=cache-data\n' >>"$CACHE_FILE"
(
    cd "$TEST_ROOT"
    COUNT_FILE="$COUNT_FILE" \
        AGENT_HOOK_HARNESS=test \
        AGENT_HOOK_SESSION_ID=baseline-session \
        bash "$TEST_REPO/scripts/agent-stop-checks.sh" >/dev/null 2>&1
)
assert_validation_count 14

printf 'PASS: stop checks protect hook state, validate unsafe baselines, cache successful snapshots, and return exact blocking statuses\n'

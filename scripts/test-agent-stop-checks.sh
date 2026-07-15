#!/usr/bin/env bash

set -euo pipefail

unset AGENT_HOOK_HARNESS AGENT_HOOK_SESSION_ID SKILLS_AGENT_STOP_FORCE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_SCRIPT="$SCRIPT_DIR/agent-stop-checks.sh"
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

mkdir -p "$TEST_REPO/scripts"
cp "$SOURCE_SCRIPT" "$TEST_REPO/scripts/agent-stop-checks.sh"
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

(
    cd "$TEST_REPO"
    COUNT_FILE="$COUNT_FILE" SKILLS_AGENT_STOP_FORCE=1 bash scripts/agent-stop-checks.sh >/dev/null
)
assert_validation_count 1

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
if (
    cd "$TEST_REPO"
    COUNT_FILE="$COUNT_FILE" FAIL_VALIDATION=1 bash scripts/agent-stop-checks.sh >/dev/null 2>&1
); then
    fail "a failing validator was accepted"
fi
assert_validation_count 3

(
    cd "$TEST_REPO"
    COUNT_FILE="$COUNT_FILE" bash scripts/agent-stop-checks.sh >/dev/null
)
assert_validation_count 4

printf 'concurrent-change setup\n' >>"$TEST_REPO/tracked.txt"
if (
    cd "$TEST_REPO"
    COUNT_FILE="$COUNT_FILE" MUTATE_REPO_DURING_VALIDATION=1 bash scripts/agent-stop-checks.sh >/dev/null 2>&1
); then
    fail "a repository mutation during validation was accepted"
fi
assert_validation_count 5

(
    cd "$TEST_REPO"
    COUNT_FILE="$COUNT_FILE" bash scripts/agent-stop-checks.sh >/dev/null
)
assert_validation_count 6

printf 'PASS: stop checks cache only unchanged successful snapshots\n'

#!/usr/bin/env bash
# Regression tests for executable temporary-directory selection and cleanup.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=executable-temp-dir.sh
source "$SCRIPT_DIR/executable-temp-dir.sh"

TEST_ROOT="$(create_executable_temp_dir "$SCRIPT_DIR/.." "executable-temp-dir-test")"

cleanup() {
    cleanup_executable_temp_dir "$TEST_ROOT"
}
trap cleanup EXIT

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

assert_under_root() {
    local path="$1"
    local expected_root="$2"
    local label="$3"

    case "$path" in
        "$expected_root"/*) ;;
        *) fail "$label: expected $path under $expected_root" ;;
    esac
}

assert_directly_executable() {
    local temp_dir="$1"
    local probe="$temp_dir/direct-execution-probe"

    printf '#!/bin/sh\nexit 0\n' >"$probe"
    chmod 700 "$probe"
    "$probe" || fail "created directory did not permit direct execution"
}

override_root="$TEST_ROOT/override"
mkdir "$override_root"
override_dir="$(
    SKILLS_EXECUTABLE_TMPDIR="$override_root" \
        create_executable_temp_dir "$SCRIPT_DIR/.." "explicit-override"
)"
assert_under_root "$override_dir" "$override_root" "explicit override"
assert_directly_executable "$override_dir"
cleanup_executable_temp_dir "$override_dir"
[ ! -e "$override_dir" ] || fail "explicit override directory was not removed"

fallback_root="$TEST_ROOT/fallback"
mkdir "$fallback_root"
fallback_dir="$(
    TMPDIR="$TEST_ROOT/does-not-exist" \
        create_executable_temp_dir "$fallback_root" "unavailable-preferred-root"
)"
assert_under_root "$fallback_dir" "$fallback_root" "fallback selection"
assert_directly_executable "$fallback_dir"
cleanup_executable_temp_dir "$fallback_dir"
[ ! -e "$fallback_dir" ] || fail "fallback directory was not removed"

set +e
override_error="$(
    SKILLS_EXECUTABLE_TMPDIR="$TEST_ROOT/does-not-exist" \
        create_executable_temp_dir "$fallback_root" "invalid-override" 2>&1
)"
override_status=$?
set -e
if [ "$override_status" -ne 1 ] \
    || [[ "$override_error" != *"SKILLS_EXECUTABLE_TMPDIR is not writable and executable"* ]]; then
    fail "invalid explicit override did not fail with the expected diagnostic"
fi

unmarked_dir="$TEST_ROOT/unmarked"
mkdir "$unmarked_dir"
set +e
cleanup_error="$(cleanup_executable_temp_dir "$unmarked_dir" 2>&1)"
cleanup_status=$?
set -e
if [ "$cleanup_status" -ne 2 ] \
    || [[ "$cleanup_error" != *"refusing unmarked path"* ]] \
    || [ ! -d "$unmarked_dir" ]; then
    fail "cleanup did not preserve and reject an unmarked directory"
fi

printf 'PASS: executable temporary-directory selection and cleanup are safe\n'

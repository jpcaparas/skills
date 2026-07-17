#!/usr/bin/env bash
# Regression tests for exact, offline skills discovery validation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_SCRIPT="$SCRIPT_DIR/check-codex-skills-context-budget.sh"
TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/skills-discovery-test.XXXXXX")"
SKILLS_ROOT="$TEST_ROOT/skills"
FAKE_BIN="$TEST_ROOT/bin"

cleanup() {
    rm -rf "$TEST_ROOT"
}
trap cleanup EXIT

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

mkdir -p "$FAKE_BIN"
for skill_name in alpha beta gamma; do
    mkdir -p "$SKILLS_ROOT/$skill_name"
    : >"$SKILLS_ROOT/$skill_name/SKILL.md"
done

# Fixture-driven checks must never fall through to the network-capable npx
# command. The fake makes that boundary fail loudly if the test seam regresses.
cat >"$FAKE_BIN/npx" <<'EOF'
#!/usr/bin/env sh
echo "fixture test unexpectedly invoked npx" >&2
exit 99
EOF
chmod +x "$FAKE_BIN/npx"

write_discovery_output() {
    local path="$1"
    shift
    {
        printf '│\n◇  Available Skills\n│\n'
        for skill_name in "$@"; do
            printf '│    %s\n│\n│      Fixture description for %s.\n│\n' \
                "$skill_name" "$skill_name"
        done
        printf '└  Use --skill <name> to install specific skills\n'
    } >"$path"
}

run_check() {
    local fixture_path="$1"
    PATH="$FAKE_BIN:$PATH" \
        SKILLS_DISCOVERY_OUTPUT_FILE="$fixture_path" \
        SKILLS_DISCOVERY_SKILLS_ROOT="$SKILLS_ROOT" \
        bash "$CHECK_SCRIPT"
}

assert_passes() {
    local label="$1"
    local fixture_path="$2"
    local output
    if ! output="$(run_check "$fixture_path" 2>&1)"; then
        fail "$label should pass; output: $output"
    fi
}

assert_fails_with() {
    local label="$1"
    local fixture_path="$2"
    local expected_message="$3"
    local output status

    set +e
    output="$(run_check "$fixture_path" 2>&1)"
    status=$?
    set -e

    if [ "$status" -eq 0 ]; then
        fail "$label unexpectedly passed"
    fi
    case "$output" in
        *"$expected_message"*) ;;
        *) fail "$label missed expected diagnostic '$expected_message'; output: $output" ;;
    esac
    case "$output" in
        *"unexpectedly invoked npx"*) fail "$label invoked npx instead of using its fixture" ;;
    esac
}

VALID_OUTPUT="$TEST_ROOT/valid.txt"
EMPTY_OUTPUT="$TEST_ROOT/empty.txt"
TRUNCATED_OUTPUT="$TEST_ROOT/truncated.txt"
DUPLICATE_OUTPUT="$TEST_ROOT/duplicate.txt"
UNEXPECTED_OUTPUT="$TEST_ROOT/unexpected.txt"

write_discovery_output "$VALID_OUTPUT" alpha beta gamma
: >"$EMPTY_OUTPUT"
write_discovery_output "$TRUNCATED_OUTPUT" alpha beta
write_discovery_output "$DUPLICATE_OUTPUT" alpha alpha beta gamma
write_discovery_output "$UNEXPECTED_OUTPUT" alpha beta delta gamma

assert_passes "exact discovery set" "$VALID_OUTPUT"
assert_fails_with "empty discovery output" "$EMPTY_OUTPUT" \
    "skills discovery output contained no parseable skill names"
assert_fails_with "truncated discovery output" "$TRUNCATED_OUTPUT" \
    "on-disk skills missing from discovery output"
assert_fails_with "duplicate discovery output" "$DUPLICATE_OUTPUT" \
    "duplicate skill names in discovery output"
assert_fails_with "unexpected discovery output" "$UNEXPECTED_OUTPUT" \
    "unexpected skill names in discovery output"

mkdir -p "$SKILLS_ROOT/symlinked"
ln -s "$SKILLS_ROOT/alpha/SKILL.md" "$SKILLS_ROOT/symlinked/SKILL.md"
assert_fails_with "symlinked SKILL.md" "$VALID_OUTPUT" \
    "installable SKILL.md must not be a symlink"

printf 'PASS: discovery fixtures enforce one exact on-disk skill-name set\n'

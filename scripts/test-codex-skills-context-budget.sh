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
    mkdir -p "$SKILLS_ROOT/testing/$skill_name"
    printf '%s\n' '---' "name: $skill_name" "description: Fixture skill." '---' \
        >"$SKILLS_ROOT/testing/$skill_name/SKILL.md"
done

# A second category and a nested fixture distinguish namespace discovery from
# either a flat glob or an unrestricted recursive SKILL.md search.
mkdir -p "$SKILLS_ROOT/engineering" "$SKILLS_ROOT/testing/alpha/evals/fixture"
mv "$SKILLS_ROOT/testing/gamma" "$SKILLS_ROOT/engineering/gamma"
printf 'not an installable skill\n' >"$SKILLS_ROOT/testing/alpha/evals/fixture/SKILL.md"

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

# A clean checkout without installed dependencies must fail with an install
# command, not resolve a cached or remote npm package. Bash reads this copy;
# no executable test double is needed on a potentially noexec temporary mount.
mkdir -p "$TEST_ROOT/scripts"
cp "$CHECK_SCRIPT" "$TEST_ROOT/scripts/"
if missing_install_output="$(PATH="$FAKE_BIN:$PATH" \
    SKILLS_DISCOVERY_OUTPUT_FILE= \
    bash "$TEST_ROOT/scripts/check-codex-skills-context-budget.sh" 2>&1)"; then
    fail "missing locked installer unexpectedly passed"
fi
case "$missing_install_output" in
    *"install the locked discovery tool"*) ;;
    *) fail "missing installer did not explain the frozen-lockfile repair: $missing_install_output" ;;
esac
case "$missing_install_output" in
    *"unexpectedly invoked npx"*) fail "missing installer fell back to npx" ;;
esac

mkdir -p "$SKILLS_ROOT/testing/symlinked"
ln -s "$SKILLS_ROOT/testing/alpha/SKILL.md" "$SKILLS_ROOT/testing/symlinked/SKILL.md"
assert_fails_with "symlinked SKILL.md" "$VALID_OUTPUT" \
    "installable SKILL.md must not be a symlink"

printf 'PASS: discovery fixtures enforce one exact on-disk skill-name set\n'

#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Tool doubles need an executable filesystem on both Linux and macOS.
source "$REPO_ROOT/scripts/executable-temp-dir.sh"
TEST_ROOT="$(create_executable_temp_dir "$REPO_ROOT" "orb-lifecycle-test")"
trap 'cleanup_executable_temp_dir "$TEST_ROOT"' EXIT

validation_python="${SKILLS_VALIDATION_PYTHON:-}"
if [ -z "$validation_python" ] && [ -x "$REPO_ROOT/.venv/bin/python3" ]; then
    validation_python="$REPO_ROOT/.venv/bin/python3"
fi
validation_python="$(command -v "${validation_python:-python3}")"

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_link() { [ "$(readlink "$1")" = "$2" ] || fail "unexpected link $1"; }

mkdir -p "$TEST_ROOT/repo/.agents" "$TEST_ROOT/repo/scripts" "$TEST_ROOT/repo/skills/engineering/alpha" "$TEST_ROOT/repo/skills/engineering/beta/fixtures/example" "$TEST_ROOT/bin" "$TEST_ROOT/home/.gemini/skills"
cp "$REPO_ROOT/.agents/link-repository-skills" "$TEST_ROOT/repo/.agents/"
cp "$REPO_ROOT/scripts/skill_catalog.py" "$TEST_ROOT/repo/scripts/"
cp "$REPO_ROOT/scripts/yaml_validation.py" "$TEST_ROOT/repo/scripts/"
printf '%s\n' '---' 'name: alpha' 'description: alpha' '---' >"$TEST_ROOT/repo/skills/engineering/alpha/SKILL.md"
printf '%s\n' '---' 'name: beta' 'description: beta' '---' >"$TEST_ROOT/repo/skills/engineering/beta/SKILL.md"
printf '%s\n' '---' 'name: fixture' 'description: fixture' '---' >"$TEST_ROOT/repo/skills/engineering/beta/fixtures/example/SKILL.md"
cat >"$TEST_ROOT/bin/gemini" <<'EOF'
#!/usr/bin/env bash
echo called >>"${GEMINI_CALL_LOG:?}"
exit 99
EOF
chmod +x "$TEST_ROOT/bin/gemini"

export HOME="$TEST_ROOT/home" PATH="$TEST_ROOT/bin:$PATH" GEMINI_CALL_LOG="$TEST_ROOT/calls"
export SKILLS_VALIDATION_PYTHON="$validation_python" SKILLS_GEMINI_CLI=gemini
unset SKILLS_GEMINI_SKILLS_DIR
touch "$GEMINI_CALL_LOG"
"$TEST_ROOT/repo/.agents/link-repository-skills"
assert_link "$HOME/.gemini/skills/alpha" "$TEST_ROOT/repo/skills/engineering/alpha"
assert_link "$HOME/.gemini/skills/beta" "$TEST_ROOT/repo/skills/engineering/beta"
[ ! -e "$HOME/.gemini/skills/example" ] || fail 'fixture skill was linked'
[ ! -s "$GEMINI_CALL_LOG" ] || fail 'Gemini was unnecessarily launched'

start=$SECONDS
"$TEST_ROOT/repo/.agents/link-repository-skills"
[ "$((SECONDS - start))" -lt 10 ] || fail 'warm resume exceeded 10 seconds'
[ ! -s "$GEMINI_CALL_LOG" ] || fail 'warm run launched Gemini'

printf 'mine\n' >"$HOME/.gemini/skills/user-owned"
mkdir -p "$TEST_ROOT/repo/skills/engineering/user-owned"
printf '%s\n' '---' 'name: user-owned' 'description: Fixture.' '---' \
    >"$TEST_ROOT/repo/skills/engineering/user-owned/SKILL.md"
if "$TEST_ROOT/repo/.agents/link-repository-skills" >/dev/null 2>&1; then fail 'user file was accepted'; fi
[ "$(cat "$HOME/.gemini/skills/user-owned")" = mine ] || fail 'user file was replaced'
rm -rf "$TEST_ROOT/repo/skills/engineering/user-owned"

if PATH=/usr/bin:/bin SKILLS_GEMINI_CLI=missing-gemini "$TEST_ROOT/repo/.agents/link-repository-skills" >/dev/null 2>&1; then fail 'missing Gemini succeeded'; fi
cat >"$TEST_ROOT/bad-python" <<'EOF'
#!/usr/bin/env bash
echo /must/not/be/linked
exit 7
EOF
chmod +x "$TEST_ROOT/bad-python"
before="$(ls -1 "$HOME/.gemini/skills")"
if SKILLS_VALIDATION_PYTHON="$TEST_ROOT/bad-python" "$TEST_ROOT/repo/.agents/link-repository-skills" >/dev/null 2>&1; then fail 'invalid inventory succeeded'; fi
[ "$before" = "$(ls -1 "$HOME/.gemini/skills")" ] || fail 'inventory failure changed links'
assert_link "$HOME/.gemini/skills/alpha" "$TEST_ROOT/repo/skills/engineering/alpha"
assert_link "$HOME/.gemini/skills/beta" "$TEST_ROOT/repo/skills/engineering/beta"

# Repair a link to this repository's pre-namespace path, but never take over a
# name already linked to another repository, including a dangling foreign link.
rm "$HOME/.gemini/skills/alpha"
ln -s "$TEST_ROOT/repo/skills/alpha" "$HOME/.gemini/skills/alpha"
"$TEST_ROOT/repo/.agents/link-repository-skills"
assert_link "$HOME/.gemini/skills/alpha" "$TEST_ROOT/repo/skills/engineering/alpha"
rm "$HOME/.gemini/skills/alpha"
ln -s "$TEST_ROOT/other-repo/alpha" "$HOME/.gemini/skills/alpha"
if "$TEST_ROOT/repo/.agents/link-repository-skills" >/dev/null 2>&1; then fail 'foreign link was accepted'; fi
assert_link "$HOME/.gemini/skills/alpha" "$TEST_ROOT/other-repo/alpha"

echo 'orb lifecycle tests passed'

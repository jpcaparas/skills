#!/usr/bin/env bash
#
# scaffold.sh — Create an intentionally incomplete skill draft.
#
# Usage:
#   ./scaffold.sh <skill-name> [blueprint-type]
#   ./scaffold.sh <skill-name> [blueprint-type] --output-root /path/to/skills
#   ./scaffold.sh <skill-name> [blueprint-type] --dry-run
#
# Blueprint types: api-wrapper, cli-tool, progressive-docs
# If no blueprint is given, creates a minimal SKILL.md with authoring placeholders.
# Only directories backed by real scaffold content are created.
#
# Examples:
#   ./scaffold.sh stripe-api api-wrapper
#   ./scaffold.sh my-tool cli-tool
#   ./scaffold.sh aws-reference progressive-docs
#   ./scaffold.sh quick-util
#   ./scaffold.sh ffmpeg-helper cli-tool --output-root ~/.agents/skills
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_CREATOR_DIR="$(dirname "$SCRIPT_DIR")"
# Private override supports isolated regression fixtures without mutating the
# installed creator package.
TEMPLATES_DIR="${SKILL_CREATOR_TEMPLATES_DIR:-$SKILL_CREATOR_DIR/templates}"
INFER_DESTINATION_SCRIPT="${SKILL_CREATOR_INFER_DESTINATION_SCRIPT:-$SCRIPT_DIR/infer_destination.py}"
OUTPUT_ROOT=""
DRY_RUN=0

usage() {
    echo "Usage: $0 <skill-name> [blueprint-type] [--output-root DIR] [--dry-run]"
    echo ""
    echo "Blueprint types: api-wrapper, cli-tool, progressive-docs"
    echo "If no blueprint is given, creates a minimal incomplete draft."
    echo "Dry runs report the destination without creating the output root."
}

# --- Argument parsing ---

POSITIONAL=()
while [ $# -gt 0 ]; do
    case "$1" in
        --output-root)
            if [ $# -lt 2 ] || [ -z "$2" ] || [[ "$2" == -* ]]; then
                echo "Error: --output-root requires a non-empty directory path, not an option."
                exit 1
            fi
            OUTPUT_ROOT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done

set -- "${POSITIONAL[@]}"

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    usage
    exit 1
fi

SKILL_NAME="$1"
BLUEPRINT="${2:-minimal}"

# --- Validate skill name ---

if [ ${#SKILL_NAME} -lt 1 ] || [ ${#SKILL_NAME} -gt 64 ]; then
    echo "Error: skill name must be 1-64 characters. Got: ${#SKILL_NAME}"
    exit 1
fi

if [[ ! "$SKILL_NAME" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]] || [[ "$SKILL_NAME" == *--* ]]; then
    echo "Error: skill name must be lowercase letters, digits, and hyphens only."
    echo "  - Must start and end with a letter or digit"
    echo "  - No consecutive hyphens"
    echo "  Got: '$SKILL_NAME'"
    exit 1
fi

# --- Validate blueprint type ---

case "$BLUEPRINT" in
    api-wrapper|cli-tool|progressive-docs|minimal)
        ;;
    *)
        echo "Error: unknown blueprint type '$BLUEPRINT'"
        echo "Valid types: api-wrapper, cli-tool, progressive-docs"
        exit 1
        ;;
esac

# --- Preflight the exact requested blueprint before creating output ---

MISSING_TEMPLATE=0
require_template() {
    local relative_path="$1"
    if [ ! -f "$TEMPLATES_DIR/$relative_path" ]; then
        echo "Error: required blueprint template is missing: $TEMPLATES_DIR/$relative_path"
        MISSING_TEMPLATE=1
    fi
}

case "$BLUEPRINT" in
    api-wrapper)
        require_template "api-wrapper/SKILL.template.md"
        require_template "api-wrapper/references/api.md"
        require_template "api-wrapper/references/patterns.md"
        require_template "api-wrapper/references/configuration.md"
        require_template "api-wrapper/references/gotchas.md"
        ;;
    cli-tool)
        require_template "cli-tool/SKILL.template.md"
        require_template "cli-tool/references/commands.md"
        require_template "cli-tool/references/patterns.md"
        require_template "cli-tool/references/configuration.md"
        require_template "cli-tool/references/gotchas.md"
        ;;
    progressive-docs)
        require_template "progressive-docs/SKILL.template.md"
        require_template "progressive-docs/references/shared.md"
        ;;
esac

if [ "$MISSING_TEMPLATE" -ne 0 ]; then
    exit 1
fi

# --- Determine output directory ---

if [ -z "$OUTPUT_ROOT" ]; then
    INFERENCE_SNAPSHOT="$(
        python3 "$INFER_DESTINATION_SCRIPT" \
            --format json \
            --skill-name "$SKILL_NAME"
    )"
    python3 -c 'import json, os, sys
payload = json.loads(sys.argv[1])
root = payload["recommended_root"]
reason = payload["reason"]
print(f"Recommended destination: {os.path.join(root, sys.argv[2])}")
print(f"Reason: {reason}")
alternatives = payload.get("alternatives", [])
if alternatives:
    print(f"Alternative: {alternatives[0]}")' "$INFERENCE_SNAPSHOT" "$SKILL_NAME"
    OUTPUT_ROOT="$(
        python3 -c 'import json, sys; print(json.loads(sys.argv[1])["recommended_root"])' \
            "$INFERENCE_SNAPSHOT"
    )"
fi

OUTPUT_ROOT="$(python3 -c 'import os, sys
raw = sys.argv[1]
expanded = os.path.expanduser(raw)
if raw.startswith("~") and expanded == raw:
    raise SystemExit(f"Error: cannot expand unknown user in output root: {raw}")
print(os.path.abspath(expanded))' "$OUTPUT_ROOT")"
if { [ -e "$OUTPUT_ROOT" ] || [ -L "$OUTPUT_ROOT" ]; } && [ ! -d "$OUTPUT_ROOT" ]; then
    echo "Error: output root is not a directory: $OUTPUT_ROOT"
    exit 1
fi
OUTPUT_DIR="$OUTPUT_ROOT/$SKILL_NAME"

if [ -e "$OUTPUT_DIR" ] || [ -L "$OUTPUT_DIR" ]; then
    echo "Error: path '$OUTPUT_DIR' already exists."
    exit 1
fi

echo "Skill draft: $SKILL_NAME (blueprint: $BLUEPRINT)"
echo "Root: $OUTPUT_ROOT"
echo "Location: $OUTPUT_DIR"

if [ "$DRY_RUN" -eq 1 ]; then
    echo ""
    echo "Dry run only. Would create an incomplete draft; no directories or files were created."
    exit 0
fi

# --- Stage atomically inside the destination filesystem ---

mkdir -p "$OUTPUT_ROOT"
OUTPUT_ROOT="$(cd "$OUTPUT_ROOT" && pwd -P)"
OUTPUT_DIR="$OUTPUT_ROOT/$SKILL_NAME"

if [ -e "$OUTPUT_DIR" ] || [ -L "$OUTPUT_DIR" ]; then
    echo "Error: path '$OUTPUT_DIR' already exists."
    exit 1
fi

if ! exec 9<"$OUTPUT_ROOT"; then
    echo "Error: could not anchor output root for safe publication: $OUTPUT_ROOT"
    exit 1
fi

STAGING_DIR=""
STAGING_NAME=""
cleanup() {
    if [ -n "${STAGING_NAME:-}" ]; then
        python3 - "$OUTPUT_ROOT" "$STAGING_NAME" <<'PY' || true
import os
import shutil
import stat
import sys


root_path, staging_name = sys.argv[1:]
root_fd = 9


def same_directory(left: os.stat_result, right: os.stat_result) -> bool:
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def remove_entry(parent_fd: int, name: str) -> None:
    try:
        entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if stat.S_ISDIR(entry.st_mode):
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        child_fd = os.open(name, flags, dir_fd=parent_fd)
        try:
            for child_name in os.listdir(child_fd):
                remove_entry(child_fd, child_name)
        finally:
            os.close(child_fd)
        os.rmdir(name, dir_fd=parent_fd)
        return
    os.unlink(name, dir_fd=parent_fd)


if os.name == "nt":
    expected = os.fstat(root_fd)
    try:
        current = os.stat(root_path, follow_symlinks=False)
    except OSError:
        current = None
    if current is not None and same_directory(expected, current):
        shutil.rmtree(os.path.join(root_path, staging_name), ignore_errors=True)
else:
    remove_entry(root_fd, staging_name)
PY
    fi
}
trap cleanup EXIT

STAGING_DIR="$(mktemp -d "$OUTPUT_ROOT/.${SKILL_NAME}.draft.XXXXXX")"
STAGING_NAME="${STAGING_DIR##*/}"
WORK_DIR="$STAGING_DIR/$SKILL_NAME"
mkdir "$WORK_DIR"

copy_reference() {
    local source_path="$1"
    local relative_path="$2"
    if [ ! -f "$source_path" ]; then
        echo "Error: required blueprint reference disappeared: $source_path"
        exit 1
    fi
    mkdir -p "$WORK_DIR/references"
    sed "s/{{SKILL_NAME}}/$SKILL_NAME/g" "$source_path" > "$WORK_DIR/references/$relative_path"
}

# --- Create SKILL.md based on blueprint ---

case "$BLUEPRINT" in
    api-wrapper)
        sed "s/{{SKILL_NAME}}/$SKILL_NAME/g" "$TEMPLATES_DIR/api-wrapper/SKILL.template.md" > "$WORK_DIR/SKILL.md"
        for ref in api.md patterns.md configuration.md gotchas.md; do
            copy_reference "$TEMPLATES_DIR/api-wrapper/references/$ref" "$ref"
        done
        ;;

    cli-tool)
        sed "s/{{SKILL_NAME}}/$SKILL_NAME/g" "$TEMPLATES_DIR/cli-tool/SKILL.template.md" > "$WORK_DIR/SKILL.md"
        for ref in commands.md patterns.md configuration.md gotchas.md; do
            copy_reference "$TEMPLATES_DIR/cli-tool/references/$ref" "$ref"
        done
        ;;

    progressive-docs)
        sed \
            -e "s/{{SKILL_NAME}}/$SKILL_NAME/g" \
            -e 's#references/signing\.md#references/{{DOMAIN_AREA_FILE}}.md#g' \
            "$TEMPLATES_DIR/progressive-docs/SKILL.template.md" > "$WORK_DIR/SKILL.md"
        for ref in shared.md; do
            copy_reference "$TEMPLATES_DIR/progressive-docs/references/$ref" "$ref"
        done
        ;;
esac

# Minimal fallback (also the default)
if [ "$BLUEPRINT" = "minimal" ]; then
    cat > "$WORK_DIR/SKILL.md" << SKILLEOF
---
name: $SKILL_NAME
description: "TODO: Describe what this skill does and when to trigger it."
---

# ${SKILL_NAME}

TODO: One-line summary of what this skill does.

## Operating Contract

TODO: Define the invocation branches, owner, inputs, and intended result.

## Instructions

TODO: Add ordered steps with checkable completion criteria, a flat peer set of
rules, or both. Add routing only when the skill has genuine branches.

## Completion Gate

TODO: Name the observable evidence required before the skill reports success.
SKILLEOF
fi

# --- Require the correctly named staged package to be structurally sound ---

if ! python3 "$SCRIPT_DIR/validate.py" "$WORK_DIR" --profile draft > /dev/null; then
    echo "Error: staged skill draft failed structural validation."
    python3 "$SCRIPT_DIR/validate.py" "$WORK_DIR" --profile draft || true
    exit 1
fi

# Private synchronization hook for the deterministic publication-race
# regression. Normal scaffolds never set it.
if [ -n "${_SKILL_CREATOR_TEST_PUBLISH_BARRIER:-}" ]; then
    python3 - "$_SKILL_CREATOR_TEST_PUBLISH_BARRIER" <<'PY'
import os
import sys
import time


barrier = sys.argv[1]
ready = f"{barrier}.ready"
hold = f"{barrier}.hold"
with open(ready, "x", encoding="utf-8"):
    pass
try:
    deadline = time.monotonic() + 5
    while os.path.lexists(hold):
        if time.monotonic() >= deadline:
            raise SystemExit("Error: timed out waiting for test publication barrier")
        time.sleep(0.01)
finally:
    try:
        os.unlink(ready)
    except FileNotFoundError:
        pass
PY
fi

# --- Publish without replacing a destination created during staging ---

# Darwin, Linux, and Windows expose atomic no-replace directory moves. Fail
# closed on hosts or filesystems without one: publishing a partially visible
# tree would make an interrupted draft look complete.
python3 - "$OUTPUT_ROOT" "$STAGING_NAME" "$SKILL_NAME" <<'PY'
import ctypes
import errno
import os
import stat
import sys


root_path, staging_name, skill_name = sys.argv[1:]
root_fd = 9
source_relative = f"{staging_name}/{skill_name}"
destination_relative = skill_name
source = os.path.join(root_path, source_relative)
destination = os.path.join(root_path, destination_relative)
expected_root = os.fstat(root_fd)
windows_root_handle = None


def same_directory(left: os.stat_result, right: os.stat_result) -> bool:
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def current_root_matches_anchor() -> bool:
    try:
        current = os.stat(root_path, follow_symlinks=False)
    except OSError:
        return False
    return stat.S_ISDIR(current.st_mode) and same_directory(expected_root, current)


def lock_windows_root() -> int:
    """Prevent a Windows output-root rename while publication is in flight."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    handle = create_file(
        root_path,
        0x80,
        0x1 | 0x2,
        None,
        3,
        0x02000000,
        None,
    )
    if handle == ctypes.c_void_p(-1).value:
        error_number = ctypes.get_last_error()
        raise OSError(error_number, "could not anchor output root", root_path)
    return int(handle)


def native_no_replace() -> bool:
    """Publish atomically when the host exposes a no-replace rename."""
    if os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        move_file = kernel32.MoveFileExW
        move_file.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        move_file.restype = ctypes.c_int
        if move_file(source, destination, 0):
            return True
        error_number = ctypes.get_last_error()
        if error_number in {80, 183}:
            raise FileExistsError(error_number, "destination exists", destination)
        raise OSError(error_number, "atomic directory move failed", destination)

    libc = ctypes.CDLL(None, use_errno=True)

    if sys.platform == "darwin":
        renameatx_np = getattr(libc, "renameatx_np", None)
        if renameatx_np is None:
            return False
        renameatx_np.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameatx_np.restype = ctypes.c_int
        result = renameatx_np(
            root_fd,
            os.fsencode(source_relative),
            root_fd,
            os.fsencode(destination_relative),
            0x00000004,
        )
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        renameat2 = libc.renameat2
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            root_fd,
            os.fsencode(source_relative),
            root_fd,
            os.fsencode(destination_relative),
            0x1,
        )
    else:
        return False

    if result == 0:
        return True

    error_number = ctypes.get_errno()
    if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FileExistsError(error_number, os.strerror(error_number), destination)
    if error_number in {errno.EINVAL, errno.ENOSYS, errno.ENOTSUP, errno.EOPNOTSUPP}:
        return False
    raise OSError(error_number, os.strerror(error_number), destination)


try:
    if os.name == "nt":
        windows_root_handle = lock_windows_root()
    if not current_root_matches_anchor():
        raise SystemExit(
            "Error: output root changed after staging; no draft was published."
        )
    if os.name == "nt":
        staged_source = os.stat(source, follow_symlinks=False)
    else:
        staged_source = os.stat(
            source_relative, dir_fd=root_fd, follow_symlinks=False
        )
    if not stat.S_ISDIR(staged_source.st_mode):
        raise SystemExit("Error: anchored staged draft is no longer a directory.")

    force_unsupported = os.environ.get(
        "_SKILL_CREATOR_TEST_FORCE_UNSUPPORTED_PUBLISH"
    ) == "1"
    if force_unsupported or not native_no_replace():
        raise SystemExit(
            "Error: this host or filesystem does not support atomic no-replace "
            "directory publication; no draft was published."
        )
    if not current_root_matches_anchor():
        try:
            os.rename(
                destination_relative,
                source_relative,
                src_dir_fd=root_fd,
                dst_dir_fd=root_fd,
            )
        except OSError as rollback_error:
            raise SystemExit(
                "Error: output root changed during publication and rollback failed: "
                f"{rollback_error}"
            )
        raise SystemExit(
            "Error: output root changed during publication; publication was rolled back."
        )

    if os.name == "nt":
        os.rmdir(os.path.join(root_path, staging_name))
    else:
        os.rmdir(staging_name, dir_fd=root_fd)
except FileExistsError:
    raise SystemExit(f"Error: path already exists at publish time: {destination}")
finally:
    if windows_root_handle is not None:
        close_handle = ctypes.WinDLL(
            "kernel32", use_last_error=True
        ).CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_int
        close_handle(ctypes.c_void_p(windows_root_handle))
PY
STAGING_DIR=""
STAGING_NAME=""
trap - EXIT

# --- Summary ---

echo ""
echo "Incomplete skill draft created:"
echo ""
find "$OUTPUT_DIR" -type f | sort | while read -r f; do
    echo "  ${f#$OUTPUT_DIR/}"
done
echo ""
echo "Required before release:"
echo "  1. Edit SKILL.md to fill in placeholders"
echo "  2. Add only the references, scripts, templates, assets, or agents the skill uses"
echo "  3. Add meaningful test cases to evals/evals.json"
printf '  4. Check the draft: python3 %q %q --profile draft\n' \
    "$SKILL_CREATOR_DIR/scripts/validate.py" "$OUTPUT_DIR"
printf '  5. Gate the release: python3 %q %q --profile release\n' \
    "$SKILL_CREATOR_DIR/scripts/validate.py" "$OUTPUT_DIR"

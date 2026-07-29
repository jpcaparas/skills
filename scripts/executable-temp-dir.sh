#!/usr/bin/env bash
# Create and clean temporary directories for tests that execute tool doubles.

create_executable_temp_dir() {
    local fallback_root="${1:-}"
    local prefix="${2:-}"
    local preferred_root result

    if [ -z "$fallback_root" ] || [ ! -d "$fallback_root" ]; then
        printf 'create_executable_temp_dir: fallback root must be an existing directory\n' >&2
        return 2
    fi
    case "$prefix" in
        ""|*[!A-Za-z0-9._-]*)
            printf 'create_executable_temp_dir: prefix must use only letters, digits, dot, underscore, or hyphen\n' >&2
            return 2
            ;;
    esac

    # An explicit override is authoritative. Fail with context instead of
    # silently placing executable fixtures somewhere the caller did not choose.
    if [ -n "${SKILLS_EXECUTABLE_TMPDIR:-}" ]; then
        if result="$(_try_create_executable_temp_dir "$SKILLS_EXECUTABLE_TMPDIR" "$prefix")"; then
            printf '%s\n' "$result"
            return 0
        fi
        printf 'SKILLS_EXECUTABLE_TMPDIR is not writable and executable: %s\n' \
            "$SKILLS_EXECUTABLE_TMPDIR" >&2
        return 1
    fi

    preferred_root="${TMPDIR:-/tmp}"
    if result="$(_try_create_executable_temp_dir "$preferred_root" "$prefix")"; then
        printf '%s\n' "$result"
        return 0
    fi
    if [ "$fallback_root" != "$preferred_root" ] \
        && result="$(_try_create_executable_temp_dir "$fallback_root" "$prefix")"; then
        printf '%s\n' "$result"
        return 0
    fi

    printf 'No writable, executable temporary directory is available under %s or %s\n' \
        "$preferred_root" "$fallback_root" >&2
    return 1
}

cleanup_executable_temp_dir() {
    local temp_dir="${1:-}"
    local marker

    case "$temp_dir" in
        ""|"/"|"."|"..")
            printf 'cleanup_executable_temp_dir: refusing unsafe path: %s\n' "$temp_dir" >&2
            return 2
            ;;
    esac
    marker="$temp_dir/.skills-executable-temp-dir"
    if [ ! -d "$temp_dir" ] || [ -L "$temp_dir" ] \
        || [ ! -f "$marker" ] || [ -L "$marker" ]; then
        printf 'cleanup_executable_temp_dir: refusing unmarked path: %s\n' "$temp_dir" >&2
        return 2
    fi

    rm -rf "$temp_dir"
}

_try_create_executable_temp_dir() {
    local root="$1"
    local prefix="$2"
    local template temp_dir probe marker

    [ -d "$root" ] && [ -w "$root" ] || return 1
    if [ "$root" = "/" ]; then
        template="/.${prefix}.XXXXXX"
    else
        template="${root%/}/.${prefix}.XXXXXX"
    fi
    temp_dir="$(mktemp -d "$template" 2>/dev/null)" || return 1
    probe="$temp_dir/.execution-probe"
    marker="$temp_dir/.skills-executable-temp-dir"

    # chmod cannot override a noexec mount. Run a real probe so the helper
    # detects the filesystem policy instead of relying on permission bits.
    if ! printf '#!/bin/sh\nexit 0\n' >"$probe" \
        || ! chmod 700 "$probe" \
        || ! "$probe" >/dev/null 2>&1; then
        [ ! -e "$probe" ] || unlink "$probe"
        rmdir "$temp_dir" 2>/dev/null || true
        return 1
    fi
    unlink "$probe"
    if ! printf '%s\n' "skills executable temporary directory" >"$marker"; then
        [ ! -e "$marker" ] || unlink "$marker"
        rmdir "$temp_dir" 2>/dev/null || true
        return 1
    fi

    (
        cd "$temp_dir"
        pwd -P
    )
}

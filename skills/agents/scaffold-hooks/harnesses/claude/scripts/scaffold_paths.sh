#!/usr/bin/env bash
# Canonical scaffold destination checks. Identical copies are bundled in each
# harness's scripts/ directory so direct, standalone component use stays safe.
# After editing, copy this file to harnesses/*/scripts/scaffold_paths.sh;
# the package validator checks that the copies match.

validate_scaffold_path() {
    local root="$1"
    local relative="$2"
    local label="$3"
    local mode="${4:-path}"
    local current="${root%/}"
    local part links
    local -a parts=()

    case "$relative" in
        ''|/*|\~*|*$'\n'*|*$'\r'*|*\\*)
            printf 'Unsafe scaffold path (%s): expected a relative path within the selected root.\n' "$label" >&2
            return 1
            ;;
    esac
    IFS='/' read -r -a parts <<< "$relative"
    for part in "${parts[@]}"; do
        case "$part" in
            ''|.) continue ;;
            ..)
                printf 'Unsafe scaffold path (%s): parent traversal is not allowed.\n' "$label" >&2
                return 1
                ;;
        esac
        current="$current/$part"
        if [ -L "$current" ]; then
            printf 'Unsafe scaffold path (%s): symlink at %s\n' "$label" "$current" >&2
            return 1
        fi
        if [ -e "$current" ] && [ ! -d "$current" ] && [ ! -f "$current" ]; then
            printf 'Unsafe scaffold path (%s): not a regular file or directory.\n' "$label" >&2
            return 1
        fi
    done
    if [ "$current" = "${root%/}" ]; then
        printf 'Unsafe scaffold path (%s): the selected root itself is not an output.\n' "$label" >&2
        return 1
    fi

    # Generators also rewrite/chmod descendants and overhaul removes state.
    # Checking only the top-level directory would miss redirected leaf writes.
    if [ "$mode" = "tree" ] && [ -d "$current" ]; then
        if ! links="$(find "$current" -type l -print -quit)"; then
            printf 'Cannot inspect scaffold output tree (%s).\n' "$label" >&2
            return 1
        fi
        if [ -n "$links" ]; then
            printf 'Unsafe scaffold path (%s): symlink inside output tree: %s\n' "$label" "$links" >&2
            return 1
        fi
    fi
}

validate_scaffold_output() {
    # Standalone merge helpers accept an explicitly selected file, including an
    # absolute one, but must not read private link targets into project config.
    local output="$1"
    if [ -L "$output" ]; then
        printf 'Unsafe scaffold path (output): refusing to replace symlink: %s\n' "$output" >&2
        return 1
    fi
}

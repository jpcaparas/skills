#!/usr/bin/env bash
#
# Shared repository snapshot algorithm for SessionStart and Stop hooks.
#
# This file is sourced by the hook scripts. Keep every input to the snapshot in
# this one implementation so a dirty-but-unchanged session compares equal.
#
# Trust boundary: repository path components are assumed not to be replaced by
# a hostile process during capture. O_NOFOLLOW protects the final entry, and a
# post-validation snapshot detects ordinary concurrent edits, but preventing a
# parent-directory symlink swap would require a platform-specific dirfd walk.

agent_external_ignored_skill_files() {
    local repo_root="$1"
    local file source_line source_file ignored_paths_file

    ignored_paths_file="$(mktemp "${TMPDIR:-/tmp}/agent-ignored-paths.XXXXXX")"
    if ! git -C "$repo_root" \
        ls-files --others --ignored --exclude-standard -z skills \
        >"$ignored_paths_file"; then
        rm -f "$ignored_paths_file"
        return 1
    fi

    while IFS= read -r -d '' file; do
        if ! source_line="$(git -C "$repo_root" check-ignore -v -- "$file")"; then
            rm -f "$ignored_paths_file"
            return 1
        fi
        source_file="${source_line%%:*}"
        if [[ "$source_file" == /* ]] || [[ "$source_file" == *".git/info/exclude" ]]; then
            printf '%s\0' "$file"
        fi
    done <"$ignored_paths_file"
    rm -f "$ignored_paths_file"
}

agent_untracked_special_paths() {
    local repo_root="$1"
    local candidate_path source_line source_file discovery_status
    local discovered_paths_file

    discovered_paths_file="$(mktemp "${TMPDIR:-/tmp}/agent-special-paths.XXXXXX")"
    if ! (
        cd "$repo_root"
        find -P . -xdev -type d -name .git -prune -o \
            \( -type p -o -type s -o -type b -o -type c \) -print0
    ) >"$discovered_paths_file"; then
        rm -f "$discovered_paths_file"
        return 1
    fi

    # Git intentionally omits FIFOs, sockets, and devices from its untracked
    # file listing. Discover those nodes with lstat-based find predicates, then
    # apply the same ignore policy as the Git-provided untracked paths.
    while IFS= read -r -d '' candidate_path; do
        candidate_path="${candidate_path#./}"
        if source_line="$(
            git -C "$repo_root" check-ignore -v -- "$candidate_path"
        )"; then
            discovery_status=0
        else
            discovery_status=$?
        fi
        if [ "$discovery_status" -eq 1 ]; then
            printf '%s\0' "$candidate_path"
            continue
        fi
        if [ "$discovery_status" -ne 0 ]; then
            rm -f "$discovered_paths_file"
            return 1
        fi

        source_file="${source_line%%:*}"
        if [[ "$candidate_path" == skills/* ]] \
            && { [[ "$source_file" == /* ]] \
                || [[ "$source_file" == *".git/info/exclude" ]]; }; then
            printf '%s\0' "$candidate_path"
        fi
    done <"$discovered_paths_file"
    rm -f "$discovered_paths_file"
}

agent_untracked_path_snapshot_record() {
    local file="$1"

    # Classify with lstat and attempt content reads only for regular paths.
    # O_NOFOLLOW prevents a symlink swap from redirecting the read, while
    # O_NONBLOCK prevents a concurrent FIFO/device swap from blocking it. The
    # opened descriptor is verified before hashing. Static symlinks and special
    # files contribute metadata without being opened.
    perl -MDigest::SHA -MFcntl=':DEFAULT,:mode' -e '
        use strict;
        use warnings;

        my $path = shift;
        print "path-sha256=", Digest::SHA::sha256_hex($path), "\n";

        sub evidence_error {
            my ($message) = @_;
            print STDERR "Unable to snapshot $path: $message\n";
            exit 1;
        }

        my @metadata = lstat($path);
        evidence_error("lstat failed or the path changed") if !@metadata;

        my $mode = $metadata[2];
        my $type = S_ISREG($mode)  ? "regular"
                 : S_ISLNK($mode)  ? "symlink"
                 : S_ISFIFO($mode) ? "fifo"
                 : S_ISSOCK($mode) ? "socket"
                 : S_ISBLK($mode)  ? "block-device"
                 : S_ISCHR($mode)  ? "character-device"
                 : S_ISDIR($mode)  ? "directory"
                 :                   "other";

        print "type=$type\n";
        printf "mode=%04o\n", $mode & 07777;
        print "uid=$metadata[4]\n";
        print "gid=$metadata[5]\n";
        print "rdev=$metadata[6]\n";
        print "size=$metadata[7]\n";
        print "mtime=$metadata[9]\n";
        print "ctime=$metadata[10]\n";

        if ($type eq "symlink") {
            my $target = readlink($path);
            evidence_error("readlink failed or the path changed") if !defined($target);
            print "target-sha256=", Digest::SHA::sha256_hex($target), "\n";
            exit 0;
        }

        # Never open FIFOs, sockets, devices, directories, or unknown types.
        exit 0 if $type ne "regular";

        if (!defined(&O_NOFOLLOW) || !defined(&O_NONBLOCK)) {
            evidence_error("safe regular-file open flags are unavailable");
        }

        my $flags = O_RDONLY | O_NOFOLLOW | O_NONBLOCK;
        my $handle;
        if (!sysopen($handle, $path, $flags)) {
            evidence_error("regular-file open failed or the path changed");
        }

        my @opened_metadata = stat($handle);
        if (!@opened_metadata
                || !S_ISREG($opened_metadata[2])
                || $opened_metadata[0] != $metadata[0]
                || $opened_metadata[1] != $metadata[1]) {
            evidence_error("path identity or type changed before hashing");
        }

        binmode($handle);
        my $digest = Digest::SHA->new(256);
        $digest->addfile($handle);
        print "content-sha256=", $digest->hexdigest, "\n";
    ' -- "./$file"
}

agent_untracked_and_external_skill_file_hashes() {
    local repo_root="$1"
    local file record_status=0
    local paths_file sorted_paths_file

    paths_file="$(mktemp "${TMPDIR:-/tmp}/agent-snapshot-paths.XXXXXX")"
    sorted_paths_file="$(mktemp "${TMPDIR:-/tmp}/agent-sorted-paths.XXXXXX")"

    if ! git -C "$repo_root" ls-files --others --exclude-standard -z \
        >"$paths_file" \
        || ! agent_untracked_special_paths "$repo_root" >>"$paths_file" \
        || ! agent_external_ignored_skill_files "$repo_root" >>"$paths_file" \
        || ! LC_ALL=C sort -zu "$paths_file" >"$sorted_paths_file"; then
        rm -f "$paths_file" "$sorted_paths_file"
        return 1
    fi

    while IFS= read -r -d '' file; do
        if ! agent_untracked_path_snapshot_record "$file"; then
            record_status=1
            break
        fi
    done <"$sorted_paths_file"

    rm -f "$paths_file" "$sorted_paths_file"
    return "$record_status"
}

agent_repo_snapshot_hash() {
    local requested_root="$1"
    local repo_root snapshot_value upstream_ref
    local head_oid head_ref head_status head_ref_status
    if ! repo_root="$(git -C "$requested_root" rev-parse --show-toplevel)"; then
        return 1
    fi

    # File paths emitted by Git are repository-relative. Hash inside the root
    # so SessionStart and Stop resolve those paths identically from any caller.
    if ! snapshot_value="$(
        set -o pipefail
        cd "$repo_root"
        {
            if head_oid="$(git rev-parse --verify --quiet HEAD)"; then
                printf 'head:%s\n' "$head_oid"
            else
                head_status=$?
                if [ "$head_status" -ne 1 ] \
                    || ! head_ref="$(git symbolic-ref -q HEAD)"; then
                    return 1
                fi
                if git show-ref --verify --quiet "$head_ref"; then
                    # The branch ref exists, so an unreadable HEAD is corrupt
                    # rather than a legitimate repository with no first commit.
                    return 1
                else
                    head_ref_status=$?
                fi
                if [ "$head_ref_status" -ne 1 ]; then
                    return 1
                fi
                printf 'unborn-head:%s\n' "$head_ref"
            fi
            git status --porcelain=v1 --untracked-files=all || return 1
            if [ -n "$head_oid" ]; then
                git diff --binary --no-ext-diff HEAD -- || return 1
            else
                git diff --cached --binary --no-ext-diff -- || return 1
            fi
            agent_untracked_and_external_skill_file_hashes "$repo_root" || return 1
            if upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"; then
                printf 'upstream:%s\n' "$upstream_ref"
                git rev-list --count "${upstream_ref}..HEAD" || return 1
            fi
        } | shasum -a 256 | awk '{print $1}'
    )"; then
        return 1
    fi
    if ! [[ "$snapshot_value" =~ ^[0-9a-f]{64}$ ]]; then
        return 1
    fi
    printf '%s\n' "$snapshot_value"
}

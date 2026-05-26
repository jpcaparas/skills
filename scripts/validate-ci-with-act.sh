#!/usr/bin/env bash
#
# validate-ci-with-act.sh
#
# Run a local GitHub Actions simulation for the Linux validation matrix leg.
# This is intentionally a small wrapper so humans, Git hooks, and agentic stop
# hooks can call the same path without hard-coding machine-specific commands.
#
# macOS GitHub-hosted runners are not Docker environments, so act cannot prove
# the macOS matrix leg. Use this as the Ubuntu preflight, then rely on the real
# GitHub Actions matrix for macOS.
#
# Usage:
#   bash scripts/validate-ci-with-act.sh
#   SKILLS_ACT_PULL=false SKILLS_ACT_OFFLINE=1 bash scripts/validate-ci-with-act.sh
#   bash scripts/validate-ci-with-act.sh --list
#
# Environment:
#   SKILLS_ACT_EVENT=pull_request
#   SKILLS_ACT_WORKFLOW=.github/workflows/validate-skills.yml
#   SKILLS_ACT_JOB=validate
#   SKILLS_ACT_OS=ubuntu-24.04
#   SKILLS_ACT_IMAGE=ghcr.io/catthehacker/ubuntu:act-24.04
#   SKILLS_ACT_ARCH=linux/amd64
#   SKILLS_ACT_PULL=true
#   SKILLS_ACT_OFFLINE=0
#

set -euo pipefail

unset GREP_OPTIONS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

event="${SKILLS_ACT_EVENT:-pull_request}"
workflow="${SKILLS_ACT_WORKFLOW:-.github/workflows/validate-skills.yml}"
job="${SKILLS_ACT_JOB:-validate}"
matrix_os="${SKILLS_ACT_OS:-ubuntu-24.04}"
image="${SKILLS_ACT_IMAGE:-ghcr.io/catthehacker/ubuntu:act-24.04}"
arch="${SKILLS_ACT_ARCH:-linux/amd64}"
pull="${SKILLS_ACT_PULL:-true}"
offline="${SKILLS_ACT_OFFLINE:-0}"

usage() {
    cat <<'USAGE'
validate-ci-with-act.sh

Run the Linux validation matrix leg through a local act container.

Usage:
  bash scripts/validate-ci-with-act.sh
  SKILLS_ACT_PULL=false SKILLS_ACT_OFFLINE=1 bash scripts/validate-ci-with-act.sh
  bash scripts/validate-ci-with-act.sh --list

Environment:
  SKILLS_ACT_EVENT=pull_request
  SKILLS_ACT_WORKFLOW=.github/workflows/validate-skills.yml
  SKILLS_ACT_JOB=validate
  SKILLS_ACT_OS=ubuntu-24.04
  SKILLS_ACT_IMAGE=ghcr.io/catthehacker/ubuntu:act-24.04
  SKILLS_ACT_ARCH=linux/amd64
  SKILLS_ACT_PULL=true
  SKILLS_ACT_OFFLINE=0
USAGE
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    usage
    exit 0
fi

if [ ! -f "$workflow" ]; then
    echo "ERROR: workflow file not found: $workflow" >&2
    exit 1
fi

if [[ "$matrix_os" == macos-* ]]; then
    {
        echo "ERROR: act cannot simulate GitHub-hosted macOS runners."
        echo "Run bash scripts/validate-all-skills.sh locally and let the real GitHub Actions matrix cover $matrix_os."
    } >&2
    exit 64
fi

if ! command -v act >/dev/null 2>&1; then
    {
        echo "ERROR: act is not installed."
        echo "Install with: brew install act"
    } >&2
    exit 127
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker is not installed or not on PATH." >&2
    exit 127
fi

if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker is not running; start Docker before running act." >&2
    exit 1
fi

if [ "${1:-}" = "--list" ]; then
    exec act -W "$workflow" -l
fi

cmd=(
    act "$event"
    -W "$workflow"
    -j "$job"
    --matrix "os:$matrix_os"
    --container-architecture "$arch"
    -P "$matrix_os=$image"
)

if [ "$pull" = "false" ] || [ "$pull" = "0" ]; then
    cmd+=(--pull=false)
fi

if [ "$offline" = "true" ] || [ "$offline" = "1" ]; then
    cmd+=(--action-offline-mode --pull=false)
fi

exec "${cmd[@]}" "$@"

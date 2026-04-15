#!/usr/bin/env sh

set -eu

# Copy these helpers when you want HTTPie to stay fully transient.
# Every HTTPie call runs inside a disposable HTTPIE_CONFIG_DIR that is removed
# on exit. curl fallbacks are only provided where there is a clean semantic
# translation.

has_httpie() {
  command -v http >/dev/null 2>&1
}

transient_httpie() (
  set -eu
  tmpdir="$(mktemp -d)"
  cleanup() {
    rm -rf "$tmpdir"
  }
  trap cleanup EXIT HUP INT TERM
  export HTTPIE_CONFIG_DIR="$tmpdir"
  http --ignore-stdin "$@"
)

http_get_body() {
  url=$1
  if has_httpie; then
    transient_httpie --check-status --body GET "$url"
  else
    curl --fail --silent --show-error "$url"
  fi
}

http_bearer_get() {
  url=$1
  token=$2
  if has_httpie; then
    transient_httpie --check-status --body -A bearer -a "$token" GET "$url"
  else
    curl --fail --silent --show-error -H "Authorization: Bearer $token" "$url"
  fi
}

http_post_json_file() {
  url=$1
  json_file=$2
  if has_httpie; then
    transient_httpie --check-status --body POST "$url" Content-Type:application/json @"$json_file"
  else
    curl --fail --silent --show-error -H "Content-Type: application/json" --data @"$json_file" "$url"
  fi
}

http_download() {
  url=$1
  output=$2
  if has_httpie; then
    transient_httpie --check-status --download --output "$output" GET "$url"
  else
    curl --fail --silent --show-error --location --output "$output" "$url"
  fi
}

http_session_pair() {
  login_url=$1
  reuse_url=$2
  user=$3
  pass=$4

  if ! has_httpie; then
    echo "http_session_pair requires HTTPie because this template keeps session reuse transient via a temporary session file." >&2
    return 1
  fi

  (
    set -eu
    tmpdir="$(mktemp -d)"
    session_file="$tmpdir/session.json"
    cleanup() {
      rm -rf "$tmpdir"
    }
    trap cleanup EXIT HUP INT TERM
    export HTTPIE_CONFIG_DIR="$tmpdir"
    http --ignore-stdin --check-status --session="$session_file" -a "$user:$pass" GET "$login_url" >/dev/null
    http --ignore-stdin --check-status --body --session-read-only="$session_file" GET "$reuse_url"
  )
}

http_preview_post() {
  if ! has_httpie; then
    echo "http_preview_post requires HTTPie because curl has no offline request-builder equivalent." >&2
    return 1
  fi
  transient_httpie --offline "$@"
}

# Examples:
#   http_get_body https://api.example.com/health
#   http_bearer_get https://api.example.com/me "$TOKEN"
#   http_post_json_file https://api.example.com/items ./payload.json
#   http_download https://downloads.example.com/artifact.tgz artifact.tgz
#   http_session_pair https://httpbin.org/basic-auth/demo/password https://httpbin.org/headers demo password
#   http_preview_post POST https://api.example.com/items name=JP active:=true

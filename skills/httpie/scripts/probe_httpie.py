#!/usr/bin/env python3
"""
probe_httpie.py - Verify key HTTPie behaviors against live commands and temp state.

Usage:
    python3 probe_httpie.py --format pretty
    python3 probe_httpie.py --format json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def run_command(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    allowed: set[int] | None = None,
) -> dict[str, object]:
    allowed = {0} if allowed is None else allowed
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    proc = subprocess.run(
        args,
        env=merged_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "args": args,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "ok": proc.returncode in allowed,
    }


def run_shell(
    script: str,
    *,
    env: dict[str, str] | None = None,
    allowed: set[int] | None = None,
    extra_args: list[str] | None = None,
) -> dict[str, object]:
    args = ["sh", "-c", script, "sh"]
    if extra_args:
        args.extend(extra_args)
    return run_command(args, env=env, allowed=allowed)


def check(name: str, passed: bool, command: dict[str, object], detail: str) -> dict[str, object]:
    return {
        "name": name,
        "passed": passed,
        "command": command["args"],
        "returncode": command["returncode"],
        "detail": detail,
        "stdout": command["stdout"].strip(),
        "stderr": command["stderr"].strip(),
    }


def run_suite(*, keep_temp: bool = False) -> dict[str, object]:
    temp_root = Path(tempfile.mkdtemp(prefix="httpie-skill-"))
    checks: list[dict[str, object]] = []
    env = {"HTTPIE_CONFIG_DIR": str(temp_root)}
    download_path = temp_root / "image.png"
    payload_path = temp_root / "payload.json"
    payload_path.write_text('{"name":"JP","active":true}\n', encoding="utf-8")

    try:
        version = run_command(["http", "--version"], env=env)
        checks.append(
            check(
                "version",
                version["ok"] and bool(str(version["stdout"]).strip()),
                version,
                "http --version returned a usable version string.",
            )
        )

        help_cmd = run_command(["http", "--help"], env=env)
        checks.append(
            check(
                "help-surface",
                help_cmd["ok"]
                and "--download" in str(help_cmd["stdout"])
                and "--session" in str(help_cmd["stdout"])
                and "--ignore-stdin" in str(help_cmd["stdout"]),
                help_cmd,
                "http --help advertised download, session, and ignore-stdin options.",
            )
        )

        transient_marker = temp_root / "transient-dir.txt"
        transient_script = """
set -eu
marker=$1
tmpdir=$(mktemp -d)
printf '%s\n' "$tmpdir" > "$marker"
trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
export HTTPIE_CONFIG_DIR="$tmpdir"
http --ignore-stdin --check-status --body GET https://pie.dev/get >/dev/null
"""
        transient_wrapper = run_shell(transient_script, extra_args=[str(transient_marker)])
        transient_dir = Path(transient_marker.read_text(encoding="utf-8").strip())
        checks.append(
            check(
                "transient-config-cleanup",
                transient_wrapper["ok"] and transient_dir != Path() and not transient_dir.exists(),
                transient_wrapper,
                "A disposable HTTPIE_CONFIG_DIR wrapper cleaned up its temp directory after the command exited.",
            )
        )

        transient_cli_marker = temp_root / "transient-cli-dir.txt"
        transient_cli_script = """
set -eu
marker=$1
tmpdir=$(mktemp -d)
printf '%s\n' "$tmpdir" > "$marker"
trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
export HTTPIE_CONFIG_DIR="$tmpdir"
httpie cli export-args >/dev/null
"""
        transient_cli = run_shell(transient_cli_script, extra_args=[str(transient_cli_marker)])
        transient_cli_dir = Path(transient_cli_marker.read_text(encoding="utf-8").strip())
        checks.append(
            check(
                "transient-cli-cleanup",
                transient_cli["ok"] and not transient_cli_dir.exists(),
                transient_cli,
                "A disposable HTTPIE_CONFIG_DIR wrapper also cleaned up after httpie cli usage.",
            )
        )

        offline = run_command(
            [
                "http",
                "--ignore-stdin",
                "--offline",
                "POST",
                "https://pie.dev/post",
                "name=JP",
                "active:=true",
            ],
            env=env,
        )
        checks.append(
            check(
                "offline-json-request",
                offline["ok"]
                and "POST /post HTTP/1.1" in str(offline["stdout"])
                and '"active": true' in str(offline["stdout"]),
                offline,
                "Offline mode rendered a JSON request body from request items.",
            )
        )

        get_request = run_command(
            [
                "http",
                "--ignore-stdin",
                "--body",
                "GET",
                "https://pie.dev/get",
                "hello==world",
            ],
            env=env,
        )
        checks.append(
            check(
                "query-parameters",
                get_request["ok"]
                and '"hello": "world"' in str(get_request["stdout"])
                and "https://pie.dev/get?hello=world" in str(get_request["stdout"]),
                get_request,
                "GET request returned JSON showing the query-string parameter.",
            )
        )

        https_alias = run_command(
            [
                "https",
                "--ignore-stdin",
                "--body",
                "pie.dev/get",
                "hello==world",
            ],
            env=env,
        )
        checks.append(
            check(
                "https-alias",
                https_alias["ok"]
                and '"hello": "world"' in str(https_alias["stdout"])
                and "https://pie.dev/get?hello=world" in str(https_alias["stdout"]),
                https_alias,
                "The https alias defaulted the scheme to HTTPS and returned the expected query-string response.",
            )
        )

        form_request = run_command(
            [
                "http",
                "--ignore-stdin",
                "--body",
                "--form",
                "POST",
                "https://pie.dev/post",
                "hello=World",
            ],
            env=env,
        )
        checks.append(
            check(
                "form-request",
                form_request["ok"]
                and '"hello": "World"' in str(form_request["stdout"])
                and "application/x-www-form-urlencoded" in str(form_request["stdout"]),
                form_request,
                "Form mode serialized the body as application/x-www-form-urlencoded.",
            )
        )

        raw_json_file = run_command(
            [
                "http",
                "--ignore-stdin",
                "--check-status",
                "--body",
                "POST",
                "https://pie.dev/post",
                "Content-Type:application/json",
                f"@{payload_path}",
            ],
            env=env,
        )
        checks.append(
            check(
                "raw-json-file",
                raw_json_file["ok"]
                and '"name": "JP"' in str(raw_json_file["stdout"])
                and '"active": true' in str(raw_json_file["stdout"]),
                raw_json_file,
                "A raw JSON body loaded from a file was accepted and parsed by the server.",
            )
        )

        headers_only = run_command(
            [
                "http",
                "--ignore-stdin",
                "--headers",
                "GET",
                "https://pie.dev/get",
            ],
            env=env,
        )
        checks.append(
            check(
                "headers-only",
                headers_only["ok"]
                and "HTTP/" in str(headers_only["stdout"])
                and "Content-Type:" in str(headers_only["stdout"]),
                headers_only,
                "Header-only output returned an HTTP status line and response headers without the body.",
            )
        )

        redirect_chain = run_command(
            [
                "http",
                "--ignore-stdin",
                "--all",
                "--follow",
                "--headers",
                "GET",
                "https://httpbin.org/redirect/1",
            ],
            env=env,
        )
        redirect_stdout = str(redirect_chain["stdout"])
        checks.append(
            check(
                "redirect-chain",
                redirect_chain["ok"]
                and ("302" in redirect_stdout or "301" in redirect_stdout or "303" in redirect_stdout)
                and "200 OK" in redirect_stdout,
                redirect_chain,
                "Redirect-chain inspection showed both an intermediate redirect response and the final 200 response.",
            )
        )

        stream_request = run_command(
            [
                "http",
                "--ignore-stdin",
                "--stream",
                "--body",
                "GET",
                "https://httpbin.org/stream/3",
            ],
            env=env,
        )
        checks.append(
            check(
                "stream-response",
                stream_request["ok"] and str(stream_request["stdout"]).count('"url": "https://httpbin.org/stream/3"') == 3,
                stream_request,
                "Finite streaming output returned all three streamed JSON objects.",
            )
        )

        download = run_command(
            [
                "http",
                "--ignore-stdin",
                "--download",
                "--output",
                str(download_path),
                "GET",
                "https://httpbin.org/image/png",
            ],
            env=env,
        )
        checks.append(
            check(
                "download",
                download["ok"] and download_path.is_file() and download_path.stat().st_size > 0,
                download,
                "Download mode wrote a non-empty file to the requested output path.",
            )
        )

        session_marker = temp_root / "session-file.txt"
        transient_session_script = """
set -eu
marker=$1
tmpdir=$(mktemp -d)
session_file="$tmpdir/session.json"
printf '%s\n' "$session_file" > "$marker"
trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
export HTTPIE_CONFIG_DIR="$tmpdir"
http --ignore-stdin --check-status --session="$session_file" -a demo:password GET https://httpbin.org/basic-auth/demo/password >/dev/null
http --ignore-stdin --check-status --body --session-read-only="$session_file" GET https://httpbin.org/headers
"""
        session_reuse = run_shell(transient_session_script, extra_args=[str(session_marker)])
        session_file = Path(session_marker.read_text(encoding="utf-8").strip())
        checks.append(
            check(
                "transient-session-reuse",
                session_reuse["ok"]
                and "Authorization" in str(session_reuse["stdout"]),
                session_reuse,
                "A temporary session-file path reused auth across requests.",
            )
        )
        checks.append(
            check(
                "transient-session-cleanup",
                session_reuse["ok"] and not session_file.exists(),
                session_reuse,
                "The temporary session file disappeared after the surrounding temp directory was cleaned up.",
            )
        )

        export_args = run_command(["httpie", "cli", "export-args"], env=env)
        export_payload: dict[str, object] | None = None
        try:
            export_payload = json.loads(str(export_args["stdout"]))
        except json.JSONDecodeError:
            export_payload = None
        checks.append(
            check(
                "export-args",
                export_args["ok"]
                and isinstance(export_payload, dict)
                and export_payload.get("spec", {}).get("name") == "http",
                export_args,
                "httpie cli export-args returned parser metadata in JSON.",
            )
        )

        plugins_list = run_command(["httpie", "cli", "plugins", "list"], env=env)
        checks.append(
            check(
                "plugins-list",
                plugins_list["ok"],
                plugins_list,
                "httpie cli plugins list executed successfully inside a disposable config dir.",
            )
        )

        template_tmp_root = temp_root / "template-tmp"
        template_tmp_root.mkdir(parents=True, exist_ok=True)
        template_output_dir = temp_root / "template-outs"
        template_output_dir.mkdir(parents=True, exist_ok=True)
        template_download = template_output_dir / "template-image.png"
        template_get = template_output_dir / "get.out"
        template_bearer = template_output_dir / "bearer.out"
        template_post = template_output_dir / "post.out"
        template_session = template_output_dir / "session.out"
        template_preview = template_output_dir / "preview.out"
        template_file = Path(__file__).resolve().parents[1] / "templates" / "httpie-fallback.sh"
        template_script = """
set -eu
template_file=$1
template_tmp_root=$2
payload_file=$3
download_out=$4
get_out=$5
bearer_out=$6
post_out=$7
session_out=$8
preview_out=$9
export TMPDIR="$template_tmp_root"
. "$template_file"
http_get_body https://pie.dev/get >"$get_out"
http_bearer_get https://httpbin.org/bearer abc123 >"$bearer_out"
http_post_json_file https://pie.dev/post "$payload_file" >"$post_out"
http_download https://httpbin.org/image/png "$download_out" >/dev/null 2>&1
http_session_pair https://httpbin.org/basic-auth/demo/password https://httpbin.org/headers demo password >"$session_out"
http_preview_post POST https://pie.dev/post name=JP active:=true >"$preview_out"
"""
        template_run = run_shell(
            template_script,
            extra_args=[
                str(template_file),
                str(template_tmp_root),
                str(payload_path),
                str(template_download),
                str(template_get),
                str(template_bearer),
                str(template_post),
                str(template_session),
                str(template_preview),
            ],
        )
        checks.append(
            check(
                "template-helpers",
                template_run["ok"]
                and template_download.is_file()
                and template_download.stat().st_size > 0
                and '"url": "https://pie.dev/get"' in template_get.read_text(encoding="utf-8")
                and '"authenticated": true' in template_bearer.read_text(encoding="utf-8")
                and '"name": "JP"' in template_post.read_text(encoding="utf-8")
                and "Authorization" in template_session.read_text(encoding="utf-8")
                and "POST /post HTTP/1.1" in template_preview.read_text(encoding="utf-8")
                and '"active": true' in template_preview.read_text(encoding="utf-8"),
                template_run,
                "Every helper in the bundled fallback template executed successfully against live endpoints.",
            )
        )
        checks.append(
            check(
                "template-cleanup",
                template_run["ok"] and not any(template_tmp_root.iterdir()),
                template_run,
                "The bundled fallback template cleaned up all temporary HTTPie directories after helper execution.",
            )
        )

        check_status = run_command(
            [
                "http",
                "--ignore-stdin",
                "--check-status",
                "--body",
                "GET",
                "https://httpbin.org/status/404",
            ],
            env=env,
            allowed={0, 4},
        )
        checks.append(
            check(
                "check-status-exit-code",
                check_status["returncode"] == 4,
                check_status,
                "--check-status mapped a 404 response to exit code 4.",
            )
        )

        total = len(checks)
        passed = sum(1 for item in checks if item["passed"])
        return {
            "passed": all(item["passed"] for item in checks),
            "summary": {
                "checks_total": total,
                "checks_passed": passed,
                "checks_skipped": 0,
            },
            "checks": checks,
            "tempdir": str(temp_root) if keep_temp else None,
        }
    finally:
        if not keep_temp:
            shutil.rmtree(temp_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HTTPie verification probes.")
    parser.add_argument("--format", choices=("pretty", "json"), default="pretty")
    parser.add_argument("--keep-temp", action="store_true", help="Keep the temporary HTTPie config directory.")
    args = parser.parse_args()

    result = run_suite(keep_temp=args.keep_temp)

    if args.format == "json":
        json.dump(result, fp=os.sys.stdout, indent=2)
        os.sys.stdout.write("\n")
    else:
        summary = result["summary"]
        print("httpie probe suite")
        print(f"Checks: {summary['checks_passed']}/{summary['checks_total']} passed")
        for item in result["checks"]:
            status = "PASS" if item["passed"] else "FAIL"
            print(f"- {status}: {item['name']} - {item['detail']}")
        if result["tempdir"]:
            print(f"Tempdir: {result['tempdir']}")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

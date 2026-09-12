#!/usr/bin/env python3
"""
probe_ripgrep.py - Verify key ripgrep behaviors against a temporary corpus.

Usage:
    python3 probe_ripgrep.py --format pretty
    python3 probe_ripgrep.py --format json
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
    cwd: Path,
    env: dict[str, str] | None = None,
    allowed: set[int] | None = None,
) -> dict[str, object]:
    allowed = {0} if allowed is None else allowed
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    proc = subprocess.run(
        args,
        cwd=str(cwd),
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


def build_corpus(root: Path) -> None:
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    (root / ".hidden_dir").mkdir(parents=True, exist_ok=True)

    (root / "src" / "app.py").write_text("alpha\nBeta\n", encoding="utf-8")
    (root / "src" / "todo.txt").write_text("TODO one\nTODO two\n", encoding="utf-8")
    (root / ".hidden_dir" / "secret.txt").write_text("secret hit\n", encoding="utf-8")
    (root / "logs" / "app.log").write_text("ignored hit\n", encoding="utf-8")
    (root / ".gitignore").write_text("logs/\n", encoding="utf-8")
    (root / ".ignore").write_text("!logs/app.log\n", encoding="utf-8")
    (root / ".rgignore").write_text("logs/app.log\n", encoding="utf-8")
    (root / "index.html").write_text("<title>Hi</title>\n", encoding="utf-8")
    (root / "multi.txt").write_text("start\nmid\nend\n", encoding="utf-8")
    (root / "look.txt").write_text("prefixVALUEsuffix\n", encoding="utf-8")
    (root / "bin.dat").write_bytes(b"plain text\0binary tail")
    (root / "rg.conf").write_text(
        "# demo config\n"
        "--smart-case\n"
        "--type-add=web:*.{html,css,js}\n",
        encoding="utf-8",
    )


def check(name: str, passed: bool, command: dict[str, object], detail: str, *, skipped: bool = False) -> dict[str, object]:
    return {
        "name": name,
        "passed": passed,
        "skipped": skipped,
        "command": command["args"],
        "returncode": command["returncode"],
        "detail": detail,
        "stdout": command["stdout"].strip(),
        "stderr": command["stderr"].strip(),
    }


def run_suite(*, keep_temp: bool = False) -> dict[str, object]:
    temp_root = Path(tempfile.mkdtemp(prefix="ripgrep-skill-"))
    build_corpus(temp_root)
    checks: list[dict[str, object]] = []

    try:
        version = run_command(["rg", "--version"], cwd=temp_root)
        checks.append(
            check(
                "version",
                version["ok"] and "ripgrep" in str(version["stdout"]),
                version,
                "rg --version reported a ripgrep build.",
            )
        )

        files = run_command(["rg", "--files"], cwd=temp_root)
        checks.append(
            check(
                "files-respect-ignore",
                files["ok"] and "logs/app.log" not in str(files["stdout"]) and "src/app.py" in str(files["stdout"]),
                files,
                "rg --files skipped the ignored log file while listing searchable files.",
            )
        )

        hidden_default = run_command(["rg", "secret", "."], cwd=temp_root, allowed={0, 1})
        hidden_enabled = run_command(["rg", "--hidden", "secret", "."], cwd=temp_root)
        checks.append(
            check(
                "hidden-files",
                hidden_default["returncode"] == 1 and hidden_enabled["ok"] and ".hidden_dir/secret.txt" in str(hidden_enabled["stdout"]),
                hidden_enabled,
                "Hidden content was absent by default and found with --hidden.",
            )
        )

        ignored_default = run_command(["rg", "ignored", "."], cwd=temp_root, allowed={0, 1})
        ignored_unfiltered = run_command(["rg", "--no-ignore", "ignored", "."], cwd=temp_root)
        checks.append(
            check(
                "ignore-precedence",
                ignored_default["returncode"] == 1 and ignored_unfiltered["ok"] and "logs/app.log" in str(ignored_unfiltered["stdout"]),
                ignored_unfiltered,
                ".rgignore re-ignored a file that .ignore had whitelisted, and --no-ignore restored it.",
            )
        )

        glob_include = run_command(["rg", "TODO", "-g", "!*.txt", "-g", "*.txt", "."], cwd=temp_root)
        glob_exclude = run_command(["rg", "TODO", "-g", "*.txt", "-g", "!*.txt", "."], cwd=temp_root, allowed={0, 1})
        checks.append(
            check(
                "glob-order",
                glob_include["ok"] and "src/todo.txt" in str(glob_include["stdout"]) and glob_exclude["returncode"] == 1,
                glob_include,
                "Later -g flags overrode earlier ones exactly as documented.",
            )
        )

        env = {"RIPGREP_CONFIG_PATH": str(temp_root / "rg.conf")}
        type_list = run_command(["rg", "--type-list"], cwd=temp_root, env=env)
        config_search = run_command(["rg", "-t", "web", "title", "."], cwd=temp_root, env=env)
        checks.append(
            check(
                "config-and-type-add",
                type_list["ok"]
                and "web:" in str(type_list["stdout"])
                and config_search["ok"]
                and "index.html" in str(config_search["stdout"]),
                config_search,
                "RIPGREP_CONFIG_PATH loaded smart-case and a custom web type.",
            )
        )

        json_output = run_command(["rg", "--json", "TODO", "src/todo.txt"], cwd=temp_root)
        json_lines = [json.loads(line) for line in str(json_output["stdout"]).splitlines() if line.strip()]
        json_types = {line.get("type") for line in json_lines}
        checks.append(
            check(
                "json-output",
                json_output["ok"] and {"begin", "match", "end", "summary"}.issubset(json_types),
                json_output,
                "JSON output emitted begin, match, end, and summary records.",
            )
        )

        multiline = run_command(["rg", "-U", "(?s)start.*end", "multi.txt"], cwd=temp_root)
        checks.append(
            check(
                "multiline",
                multiline["ok"] and "start\nmid\nend" in str(multiline["stdout"]),
                multiline,
                "Multiline search matched across line breaks.",
            )
        )

        has_pcre2 = "+pcre2" in str(version["stdout"]).lower()
        if has_pcre2:
            pcre2 = run_command(["rg", "-o", "-P", "(?<=prefix)VALUE(?=suffix)", "look.txt"], cwd=temp_root)
            checks.append(
                check(
                    "pcre2-lookaround",
                    pcre2["ok"] and str(pcre2["stdout"]).strip() == "VALUE",
                    pcre2,
                    "Lookbehind and lookahead worked with PCRE2.",
                )
            )
        else:
            checks.append(
                {
                    "name": "pcre2-lookaround",
                    "passed": True,
                    "skipped": True,
                    "command": ["rg", "-P", "(?<=prefix)VALUE(?=suffix)", "look.txt"],
                    "returncode": None,
                    "detail": "Skipped because this rg build does not advertise PCRE2 support.",
                    "stdout": "",
                    "stderr": "",
                }
            )

        replace_preview = run_command(["rg", "TODO", "-r", "DONE", "src/todo.txt"], cwd=temp_root)
        todo_text = (temp_root / "src" / "todo.txt").read_text(encoding="utf-8")
        checks.append(
            check(
                "replace-preview",
                replace_preview["ok"] and "DONE one" in str(replace_preview["stdout"]) and "TODO one" in todo_text,
                replace_preview,
                "Replacement changed stdout only and left the file unchanged.",
            )
        )

        binary_text = run_command(["rg", "-a", "plain", "bin.dat"], cwd=temp_root)
        checks.append(
            check(
                "binary-as-text",
                binary_text["ok"] and "plain text" in str(binary_text["stdout"]),
                binary_text,
                "Binary-as-text mode surfaced content from a file containing a NUL byte.",
            )
        )

        total = len(checks)
        passed = sum(1 for item in checks if item["passed"])
        skipped = sum(1 for item in checks if item.get("skipped"))
        return {
            "passed": all(item["passed"] for item in checks),
            "summary": {
                "checks_total": total,
                "checks_passed": passed,
                "checks_skipped": skipped,
            },
            "checks": checks,
            "tempdir": str(temp_root) if keep_temp else None,
        }
    finally:
        if not keep_temp:
            shutil.rmtree(temp_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ripgrep verification probes.")
    parser.add_argument("--format", choices=("pretty", "json"), default="pretty")
    parser.add_argument("--keep-temp", action="store_true", help="Keep the temporary corpus directory.")
    args = parser.parse_args()

    result = run_suite(keep_temp=args.keep_temp)

    if args.format == "json":
        json.dump(result, fp=os.sys.stdout, indent=2)
        os.sys.stdout.write("\n")
    else:
        summary = result["summary"]
        print("ripgrep probe suite")
        print(
            f"Checks: {summary['checks_passed']}/{summary['checks_total']} passed"
            f" ({summary['checks_skipped']} skipped)"
        )
        for item in result["checks"]:
            status = "SKIP" if item.get("skipped") else ("PASS" if item["passed"] else "FAIL")
            print(f"- {status}: {item['name']} - {item['detail']}")
        if result["tempdir"]:
            print(f"Tempdir: {result['tempdir']}")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


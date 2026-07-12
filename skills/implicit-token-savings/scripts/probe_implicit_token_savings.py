#!/usr/bin/env python3
"""
probe_implicit_token_savings.py - Verify compact command behaviors on local temp fixtures.

Usage:
    python3 probe_implicit_token_savings.py --format pretty
    python3 probe_implicit_token_savings.py --format json
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
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    allowed: set[int] | None = None,
) -> dict[str, object]:
    allowed = {0} if allowed is None else allowed
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        return {
            "args": args,
            "returncode": 127,
            "stdout": "",
            "stderr": str(exc),
            "ok": False,
        }

    return {
        "args": args,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "ok": proc.returncode in allowed,
    }


def run_shell(script: str, *, cwd: Path | None = None, allowed: set[int] | None = None) -> dict[str, object]:
    return run_command(["sh", "-c", script], cwd=cwd, allowed=allowed)


def check(name: str, passed: bool, command: dict[str, object], detail: str, *, skipped: bool = False) -> dict[str, object]:
    return {
        "name": name,
        "passed": passed,
        "skipped": skipped,
        "command": command["args"],
        "returncode": command["returncode"],
        "detail": detail,
        "stdout": str(command["stdout"]).strip(),
        "stderr": str(command["stderr"]).strip(),
    }


def skipped_check(name: str, detail: str) -> dict[str, object]:
    return {
        "name": name,
        "passed": True,
        "skipped": True,
        "command": [],
        "returncode": 0,
        "detail": detail,
        "stdout": "",
        "stderr": "",
    }


def build_fixture(root: Path) -> dict[str, Path]:
    workspace = root / "workspace"
    workspace.mkdir()
    (workspace / "src").mkdir()
    (workspace / "docs").mkdir()
    (workspace / "logs").mkdir()
    (workspace / ".hidden").mkdir()
    (workspace / "src" / "app.py").write_text(
        "def greet(name: str) -> str:\n"
        "    return f'hello {name}'\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    print(greet('world'))\n",
        encoding="utf-8",
    )
    (workspace / "docs" / "README.md").write_text(
        "# Fixture\n\nThis workspace exists to verify compact commands.\n",
        encoding="utf-8",
    )
    (workspace / "logs" / "app.log").write_text(
        "line-1\nline-2\nline-3\nline-4\nline-5\n",
        encoding="utf-8",
    )
    (workspace / ".hidden" / ".env").write_text("TOKEN=fixture\n", encoding="utf-8")
    return {"workspace": workspace}


def run_suite() -> dict[str, object]:
    temp_root = Path(tempfile.mkdtemp(prefix="implicit-token-savings-"))
    checks: list[dict[str, object]] = []

    try:
        paths = build_fixture(temp_root)
        workspace = paths["workspace"]

        ls_cmd = run_command(["ls", "-1", str(workspace)])
        checks.append(
            check(
                "ls-top-level",
                ls_cmd["ok"]
                and "src" in str(ls_cmd["stdout"]).splitlines()
                and "docs" in str(ls_cmd["stdout"]).splitlines(),
                ls_cmd,
                "ls -1 returned concise top-level names.",
            )
        )

        if shutil.which("tree"):
            tree_cmd = run_command(["tree", "-a", "-L", "2", str(workspace)])
            checks.append(
                check(
                    "tree-depth-capped",
                    tree_cmd["ok"]
                    and "src" in str(tree_cmd["stdout"])
                    and "app.py" in str(tree_cmd["stdout"]),
                    tree_cmd,
                    "tree -a -L 2 returned capped structure.",
                )
            )
        else:
            checks.append(skipped_check("tree-depth-capped", "tree is not installed on PATH."))

        if shutil.which("rg"):
            files_cmd = run_command(["rg", "--files", str(workspace)])
            checks.append(
                check(
                    "rg-files",
                    files_cmd["ok"]
                    and "src/app.py" in str(files_cmd["stdout"])
                    and "docs/README.md" in str(files_cmd["stdout"]),
                    files_cmd,
                    "rg --files returned candidate paths without reading contents.",
                )
            )

            search_cmd = run_command(["rg", "-n", "-F", "hello", str(workspace)])
            checks.append(
                check(
                    "rg-search",
                    search_cmd["ok"] and "app.py:2:" in str(search_cmd["stdout"]),
                    search_cmd,
                    "rg -n -F found the literal with line numbers.",
                )
            )
        else:
            checks.append(skipped_check("rg-files", "rg is not installed on PATH."))
            checks.append(skipped_check("rg-search", "rg is not installed on PATH."))

        excerpt_cmd = run_shell(f"sed -n '1,2p' {workspace / 'src' / 'app.py'}")
        checks.append(
            check(
                "targeted-read",
                excerpt_cmd["ok"]
                and "def greet" in str(excerpt_cmd["stdout"])
                and "hello" in str(excerpt_cmd["stdout"]),
                excerpt_cmd,
                "sed -n returned a targeted excerpt instead of the whole file.",
            )
        )

        repo = temp_root / "repo"
        remote = temp_root / "remote.git"
        repo.mkdir()
        run_command(["git", "init", "-b", "main"], cwd=repo)
        run_command(["git", "config", "user.name", "Skill Probe"], cwd=repo)
        run_command(["git", "config", "user.email", "skill-probe@example.com"], cwd=repo)
        (repo / "README.md").write_text("# Probe Repo\n", encoding="utf-8")
        add_cmd = run_command(["git", "add", "--", "README.md"], cwd=repo)
        commit_cmd = run_command(["git", "commit", "-m", "chore: initial commit"], cwd=repo)
        (repo / "README.md").write_text("# Probe Repo\nupdated\n", encoding="utf-8")
        status_cmd = run_command(["git", "status", "--short", "--branch"], cwd=repo)
        diff_stat_cmd = run_command(["git", "diff", "--stat"], cwd=repo)
        log_cmd = run_command(["git", "log", "--oneline", "-n", "1"], cwd=repo)
        run_command(["git", "init", "--bare", str(remote)])
        run_command(["git", "remote", "add", "origin", str(remote)], cwd=repo)
        push_cmd = run_command(["git", "push", "-u", "origin", "HEAD"], cwd=repo)

        checks.append(
            check(
                "git-add",
                add_cmd["ok"],
                add_cmd,
                "git add -- <path> staged only the intended file.",
            )
        )
        checks.append(
            check(
                "git-commit",
                commit_cmd["ok"] and "initial commit" in str(commit_cmd["stdout"]),
                commit_cmd,
                "git commit created a concise local commit.",
            )
        )
        checks.append(
            check(
                "git-status-short",
                status_cmd["ok"]
                and "## main" in str(status_cmd["stdout"])
                and " M README.md" in str(status_cmd["stdout"]),
                status_cmd,
                "git status --short --branch showed branch and compact file state.",
            )
        )
        checks.append(
            check(
                "git-diff-stat",
                diff_stat_cmd["ok"] and "README.md" in str(diff_stat_cmd["stdout"]),
                diff_stat_cmd,
                "git diff --stat summarized the working-tree change.",
            )
        )
        checks.append(
            check(
                "git-log-oneline",
                log_cmd["ok"] and "initial commit" in str(log_cmd["stdout"]),
                log_cmd,
                "git log --oneline returned a concise commit headline.",
            )
        )
        checks.append(
            check(
                "git-push-head",
                push_cmd["ok"] and "origin" in str(push_cmd["stderr"] + push_cmd["stdout"]),
                push_cmd,
                "git push -u origin HEAD pushed to a temporary local bare remote.",
            )
        )

        if shutil.which("npm"):
            npm_dir = temp_root / "npm-probe"
            npm_dir.mkdir()
            (npm_dir / "package.json").write_text(
                json.dumps(
                    {
                        "name": "implicit-token-savings-probe",
                        "version": "1.0.0",
                        "scripts": {
                            "test": "sh -c 'printf \"%s\\n\" \"$@\"' --"
                        },
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            npm_cmd = run_command(["npm", "test", "--", "--smoke"], cwd=npm_dir)
            checks.append(
                check(
                    "npm-test-forwarding",
                    npm_cmd["ok"] and "--smoke" in str(npm_cmd["stdout"]),
                    npm_cmd,
                    "npm test forwarded extra args only after --.",
                )
            )
        else:
            checks.append(skipped_check("npm-test-forwarding", "npm is not installed on PATH."))

        optional_tools = [
            ("cargo", ["cargo", "--version"]),
            ("ruff", ["ruff", "--version"]),
            ("pytest", ["pytest", "--version"]),
            ("go", ["go", "version"]),
        ]
        for name, command in optional_tools:
            if shutil.which(name):
                tool_cmd = run_command(command)
                checks.append(
                    check(
                        f"{name}-presence",
                        tool_cmd["ok"] and bool(str(tool_cmd["stdout"]).strip()),
                        tool_cmd,
                        f"{name} is installed and returned a version string.",
                    )
                )
            else:
                checks.append(skipped_check(f"{name}-presence", f"{name} is not installed on PATH."))

        if shutil.which("docker"):
            docker_cmd = run_command(["docker", "ps", "--format", "{{json .}}"], allowed={0, 1})
            docker_output = str(docker_cmd["stdout"]).strip()
            passed = docker_cmd["returncode"] == 0 and (
                not docker_output or docker_output.startswith("{")
            )
            checks.append(
                check(
                    "docker-ps-format",
                    passed,
                    docker_cmd,
                    "docker ps returned structured rows or an empty result set.",
                )
            )
        else:
            checks.append(skipped_check("docker-ps-format", "docker is not installed on PATH."))

        if shutil.which("jq"):
            jq_cmd = run_shell("printf '{\"value\":1}\\n' | jq -r '.value'")
            checks.append(
                check(
                    "jq-raw",
                    jq_cmd["ok"] and str(jq_cmd["stdout"]).strip() == "1",
                    jq_cmd,
                    "jq -r extracted a raw scalar value.",
                )
            )
        else:
            checks.append(skipped_check("jq-raw", "jq is not installed on PATH."))

        checks_total = len(checks)
        checks_passed = sum(1 for item in checks if item["passed"] and not item["skipped"])
        checks_skipped = sum(1 for item in checks if item["skipped"])
        passed = all(item["passed"] for item in checks)

        return {
            "passed": passed,
            "summary": {
                "checks_total": checks_total,
                "checks_passed": checks_passed,
                "checks_skipped": checks_skipped,
            },
            "checks": checks,
        }
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["pretty", "json"], default="pretty")
    args = parser.parse_args()

    suite = run_suite()
    if args.format == "json":
        json.dump(suite, fp=os.sys.stdout, indent=2)
        os.sys.stdout.write("\n")
    else:
        summary = suite["summary"]
        print(
            "Checks: "
            f"{summary['checks_passed']} passed, "
            f"{summary['checks_skipped']} skipped, "
            f"{summary['checks_total']} total"
        )
        for item in suite["checks"]:
            status = "SKIP" if item["skipped"] else ("PASS" if item["passed"] else "FAIL")
            print(f"[{status}] {item['name']}: {item['detail']}")
            if item["stdout"]:
                first_line = str(item["stdout"]).splitlines()[0]
                print(f"  stdout: {first_line}")
            if item["stderr"] and not item["passed"]:
                first_line = str(item["stderr"]).splitlines()[0]
                print(f"  stderr: {first_line}")

    return 0 if suite["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

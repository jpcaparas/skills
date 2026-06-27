#!/usr/bin/env python3
"""Lightweight tests for the maintainable-tests skill."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_TAGS = {"smoke", "edge", "negative", "disclosure", "legacy", "boundary", "review"}
EXPECTED_FINDINGS = {
    "vague-test-name",
    "weak-assertion",
    "over-mocking",
    "implementation-coupling",
    "fixture-noise",
    "hidden-nondeterminism",
    "missing-legacy-rationale",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_fixture(root: Path) -> None:
    tests = root / "tests"
    tests.mkdir()
    (tests / "AccountTest.php").write_text(
        """
<?php

beforeEach(function () {
    $this->gateway = Mockery::mock(PaymentGateway::class);
    $this->ledger = Mockery::mock(Ledger::class);
    $this->mailer = Mockery::mock(Mailer::class);
    $this->clock = Mockery::mock(Clock::class);
    $this->repo = Mockery::mock(AccountRepository::class);
    $this->events = Mockery::mock(EventBus::class);
    $this->audit = Mockery::mock(AuditLog::class);
    $this->flags = ['overdraft' => true];
});

it('works', function () {
    $this->repo->expects('find')->once();
    $this->repo->expects('save')->once();
    $this->gateway->shouldReceive('charge')->once();
    $this->mailer->shouldReceive('send')->once();
    $result = (new AccountService())->withdraw('acct_123', 6);
    expect($result)->toBeTruthy();
});

it('legacy rounding', function () {
    $invoice = LegacyInvoice::draft(10.005);
    expect($invoice->tax())->toBeTruthy();
});
""".lstrip(),
        encoding="utf-8",
    )
    (tests / "payment.spec.ts").write_text(
        """
it("handles error", async () => {
  const gateway = new PaymentGateway("test");
  const startedAt = Date.now();
  const response = await fetch("https://payments.example.test/charge");
  expect(response).not.toBeNull();
  expect(startedAt).toBeTruthy();
});
""".lstrip(),
        encoding="utf-8",
    )


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: python3 scripts/test_skill.py <skill-path>", file=sys.stderr)
        return 1

    root = Path(argv[0]).expanduser().resolve()
    errors: list[str] = []

    validate = subprocess.run(
        [sys.executable, str(root / "scripts" / "validate.py"), str(root)],
        text=True,
        capture_output=True,
        check=False,
    )
    if validate.returncode != 0:
        errors.append("validate.py failed")

    help_check = subprocess.run(
        [sys.executable, str(root / "scripts" / "analyze_maintainable_tests.py"), "--help"],
        text=True,
        capture_output=True,
        check=False,
    )
    if help_check.returncode != 0 or "maintainable test review prompts" not in help_check.stdout:
        errors.append("analyze_maintainable_tests.py --help did not return expected help text")

    scan_kinds: set[str] = set()
    with tempfile.TemporaryDirectory() as temp_dir:
        fixture_root = Path(temp_dir)
        write_fixture(fixture_root)
        scan = subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "analyze_maintainable_tests.py"),
                str(fixture_root),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if scan.returncode != 0:
            errors.append("analyze_maintainable_tests.py failed on fixture")
        else:
            payload = json.loads(scan.stdout)
            scan_kinds = {item["kind"] for item in payload.get("findings", [])}
            for expected in EXPECTED_FINDINGS:
                if expected not in scan_kinds:
                    errors.append(f"scanner did not report expected finding: {expected}")

    evals_path = root / "evals" / "evals.json"
    if not evals_path.is_file():
        errors.append("evals/evals.json is missing")
        evals = []
    else:
        try:
            evals = load_json(evals_path).get("evals", [])
        except json.JSONDecodeError as exc:
            errors.append(f"evals/evals.json is invalid JSON: {exc}")
            evals = []

    tags = set()
    assertion_count = 0
    for item in evals:
        for field in ["id", "name", "prompt", "expected_output", "assertions"]:
            if field not in item:
                errors.append(f"eval missing field {field}: {item}")
        tags.update(item.get("tags", []))
        for assertion in item.get("assertions", []):
            assertion_count += 1
            if "text" not in assertion:
                errors.append(f"assertion missing text: {assertion}")
            if assertion.get("type") and assertion["type"] not in {
                "functional",
                "structural",
                "disclosure",
                "negative",
                "verification",
            }:
                errors.append(f"unknown assertion type: {assertion['type']}")

    missing_tags = REQUIRED_TAGS - tags
    if missing_tags:
        errors.append(f"missing eval tag coverage: {', '.join(sorted(missing_tags))}")
    if assertion_count == 0:
        errors.append("evals contain no assertions")

    template = root / "templates" / "test-review.md"
    if not template.is_file():
        errors.append("test review template is missing")

    print(f"Skill: {root.name}")
    print(f"Validation: {'PASS' if validate.returncode == 0 else 'FAIL'}")
    print(f"Scanner help: {'PASS' if help_check.returncode == 0 else 'FAIL'}")
    print(f"Scanner findings: {', '.join(sorted(scan_kinds))}")
    print(f"Evals: {len(evals)}")
    print(f"Tags: {', '.join(sorted(tags))}")
    print(f"Assertions: {assertion_count}")

    if errors:
        print("Issues:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

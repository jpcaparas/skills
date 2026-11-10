#!/usr/bin/env python3
"""Behavioural tests for analyze_maintainable_tests.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

EXPECTED_FINDING_KINDS = {
    "direct-time-access",
    "fixture-noise",
    "implementation-coupling",
    "missing-legacy-rationale",
    "missing-recognized-assertion",
    "over-mocking",
    "real-sleep",
    "uncontrolled-randomness",
    "vague-test-name",
    "weak-assertion",
}
EXACT_FINDINGS = {
    ("tests/block_local.spec.ts", 1, "vague-test-name", "medium"),
    ("tests/block_local.spec.ts", 2, "weak-assertion", "medium"),
    ("tests/block_local.spec.ts", 4, "missing-recognized-assertion", "medium"),
    ("tests/account_behavior.py", 1, "missing-recognized-assertion", "medium"),
    ("tests/account_behavior.py", 1, "vague-test-name", "medium"),
    ("tests/coupling.spec.ts", 2, "implementation-coupling", "medium"),
    ("tests/legacy.spec.ts", 1, "missing-legacy-rationale", "medium"),
    ("tests/legacy_identifiers.spec.ts", 1, "missing-legacy-rationale", "medium"),
    ("tests/large_lines.spec.ts", 10001, "vague-test-name", "medium"),
    ("tests/log_only_test.go", 3, "missing-recognized-assertion", "medium"),
    ("tests/mocking.spec.ts", 2, "over-mocking", "medium"),
    ("tests/noisy_setup.spec.ts", 1, "fixture-noise", "medium"),
    ("tests/nondeterminism.spec.ts", 2, "direct-time-access", "medium"),
    ("tests/nondeterminism.spec.ts", 3, "real-sleep", "medium"),
    ("tests/nondeterminism.spec.ts", 4, "uncontrolled-randomness", "medium"),
    ("MyApp.Tests/TimeSignals.cs", 6, "direct-time-access", "medium"),
    ("tests/sleep_test.go", 4, "real-sleep", "medium"),
}
CLEAN_PATHS = {
    "MyApp.Tests/ExceptionAssertions.cs",
    "MyApp.Tests/NamespacedFact.cs",
    "MyApp.Tests/VerificationAssertions.cs",
    "spec/exception_assertions_spec.rb",
    "spec/native_literals_spec.rb",
    "spec/ruby_idioms_spec.rb",
    "src/ExceptionAssertionsTest.java",
    "src/JunitAssertionsTest.java",
    "src/SingleAnnotationTest.java",
    "src/SingleAnnotationTest.kt",
    "src/CsvAssertionsTest.java",
    "src/DisplayNameTest.java",
    "src/ExceptionAssertionsTest.kt",
    "src/exception_assertions.rs",
    "src/panic_assertions.rs",
    "src/lifetime_assertions.rs",
    "src/raw_literal.rs",
    "src/KotestAssertionsTest.kt",
    "src/MockitoVerificationTest.java",
    "tests/ExceptionAssertionsTest.php",
    "tests/AttributeTest.php",
    "tests/EffectVerificationTest.php",
    "tests/HeredocTest.php",
    "tests/bom.spec.ts",
    "tests/comment_signals.spec.ts",
    "tests/comments_only.spec.ts",
    "tests/exception.spec.ts",
    "tests/exception_test.go",
    "tests/gomega_test.go",
    "tests/injected_clock.spec.ts",
    "tests/node_options.spec.ts",
    "tests/each.spec.ts",
    "tests/deno.spec.ts",
    "tests/regex_body.spec.ts",
    "tests/regex_fake.spec.ts",
    "tests/test_exception_assertions.py",
    "tests/test_injected_clock.py",
    "tests/test_multiline_signature.py",
    "tests/test_verification_idioms.py",
    "test/assertions_test.rb",
    "test/ruby_expectations_test.rb",
    "spec/ruby_helper_spec.rb",
}

def write_text(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")

def write_fixture(root: Path) -> None:
    fixtures = {
        "tests/block_local.spec.ts": """
it("works", () => {
  expect(result).toBeTruthy();
});
it("records approved transfer outcome", () => {
  auditTransfer();
});
""",
        "tests/mocking.spec.ts": """
it("reports adapter failure to caller", () => {
  const gateway = jest.fn();
  const ledger = jest.fn();
  const mailer = jest.fn();
  const audit = jest.fn();
  expect(run(gateway, ledger, mailer, audit)).toEqual("failed");
});
it("returns cached value when present", () => {
  const cache = jest.fn();
  expect(read(cache)).toEqual("cached");
});
""",
        "tests/legacy.spec.ts": """
it("preserves legacy invoice rounding", () => {
  expect(roundInvoice()).toEqual("10.01");
});
it("preserves legacy account ids because customer contract", () => {
  expect(accountId()).toEqual("A-7");
});
""",
        "tests/legacy_identifiers.spec.ts": """
it("preserves_backwardCompatibility_identifier", () => {
  expect(accountId()).toEqual("A-7");
});
it("preserves regression_case output because issue #123", () => {
  expect(invoiceTotal()).toEqual("10.01");
});
""",
        "tests/nondeterminism.spec.ts": """
it("creates unique report values", async () => {
  const startedAt = Date.now();
  await sleep(10);
  const nonce = Math.random();
  expect([startedAt, nonce]).toEqual(expected);
});
it("returns gateway rejection payload", async () => {
  const response = await fetch("https://payments.example.test/charge");
  expect(response.status).toEqual(402);
});
""",
        "tests/coupling.spec.ts": """
it("invokes withdrawal policy for active account", () => {
  const method = new ReflectionMethod(AccountService, "withdraw");
  expect(method.invoke(account)).toEqual("approved");
});
""",
        "tests/noisy_setup.spec.ts": """
beforeEach(() => {
  gateway = createGateway();
  ledger = createLedger();
  mailer = createMailer();
  clock = createClock();
  repository = createRepository();
  events = createEvents();
  audit = createAudit();
  flags = createFlags();
});
it("records approved withdrawal event", () => {
  expect(withdraw()).toEqual("approved");
});
""",
        "tests/comment_signals.spec.ts": """
it("returns stable configured identifier", () => {
  // Date.now(), sleep(10), Math.random(), and jest.fn() are documentation examples.
  const documentation = "Date.now() sleep(10) Math.random() jest.fn()";
  expect(identifier(documentation)).toEqual("stable-id");
});
""",
        "tests/injected_clock.spec.ts": """
it("advances injected scheduler on demand", async () => {
  await clock.sleep(10);
  expect(clock.elapsed()).toEqual(10);
});
""",
        "tests/node_options.spec.ts": """
test("honors configured node concurrency", { concurrency: true }, () => {
  expect(runJob()).toEqual("complete");
});
""",
        "tests/regex_body.spec.ts": """
it("matches closing brace expression", () => {
  const pattern = /}/;
  expect(pattern.test("}")).toEqual(true);
});
""",
        "tests/regex_fake.spec.ts": """
const documentation = /it\\("works", \\(\\) => \\{ Date\\.now\\(\\); \\}\\)/;
""",
        "tests/comments_only.spec.ts": """
// it("works", () => { expect(value).toBeTruthy(); });
/*
test("handles error", () => {
  Date.now();
});
*/
const example = 'it("works", () => {})';
""",
        "src/production.ts": """
export function registerExample(): void {
  test("works", () => {
    expect(value).toBeTruthy();
  });
}
""",
        "tests/test_exception_assertions.py": """
import pytest

def test_rejects_expired_invitation():
    with pytest.raises(ExpiredInvitation):
        accept_invitation()
""",
        "tests/test_injected_clock.py": """
def test_advances_injected_clock_on_demand():
    fake_clock.time()
    assert fake_clock.elapsed() == 10
""",
        "tests/account_behavior.py": """
def test_works():
    perform_action()
""",
        "tests/ExceptionAssertionsTest.php": """
<?php

function testRejectsExpiredInvitation(): void
{
    $this->expectException(ExpiredInvitation::class);
    acceptInvitation();
}
""",
        "tests/exception.spec.ts": """
it("rejects expired invitation token", () => {
  expect(() => acceptInvitation()).toThrow(ExpiredInvitation);
});
""",
        "tests/exception_test.go": """
package tests

import "testing"

func TestRejectsExpiredInvitation(t *testing.T) {
    if err := acceptInvitation(); err == nil {
        t.Fatal("expected expired invitation")
    }
}
""",
        "tests/log_only_test.go": """
package tests
import "testing"
func TestLogsProcessedBatch(t *testing.T) {
    t.Log("processed batch")
}
""",
        "tests/sleep_test.go": """
package tests
import "testing"
func TestWaitsForWorkerShutdown(t *testing.T) {
    time.Sleep(10)
    if workerRunning() { t.Fatal("worker still running") }
}
""",
        "src/exception_assertions.rs": """
#[test]
fn rejects_expired_invitation() {
    assert_eq!(accept_invitation(), Err(ExpiredInvitation));
}
""",
        "src/panic_assertions.rs": """
#[should_panic(expected = "invalid configuration")]
#[test]
fn rejects_invalid_configuration() {
    load_invalid_configuration();
}
""",
        "src/lifetime_assertions.rs": """
fn borrowed_value<'a>(value: &'a str) -> &'a str { value }

#[test]
fn returns_borrowed_value_unchanged() {
    assert_eq!(borrowed_value("stable"), "stable");
}
""",
        "src/ExceptionAssertionsTest.java": """
final class ExceptionAssertionsTest {
    @Test
    void rejectsExpiredInvitation() {
        assertThrows(ExpiredInvitation.class, () -> acceptInvitation());
    }
}
""",
        "src/JunitAssertionsTest.java": """
final class JunitAssertionsTest {
    @Test
    void returnsConfiguredIdentifier() {
        assertTrue(identifier().startsWith("cfg_"));
    }
}
""",
        "src/SingleAnnotationTest.java": """
final class SingleAnnotationTest {
    @Test
    void returnsConfiguredIdentifier() {
        assertTrue(identifier().startsWith("cfg_"));
    }
}
""",
        "src/SingleAnnotationTest.kt": """
final class SingleAnnotationTest {
    @Test
    fun `returns configured identifier`() {
        true shouldBe true
    }
}
""",
        "src/CsvAssertionsTest.java": """
final class CsvAssertionsTest {
    @ParameterizedTest
    @CsvSource({"active,true", "disabled,false"})
    void returnsExpectedDecision(String state, boolean expected) {
        assertTrue(decision(state) == expected);
    }
}
""",
        "src/DisplayNameTest.java": """
final class DisplayNameTest {
    @Test
    @DisplayName("returns configured identifier for active tenant")
    void Case1() {
        assertTrue(identifier().startsWith("cfg_"));
    }
}
""",
        "src/ExceptionAssertionsTest.kt": """
final class ExceptionAssertionsTest {
    @Test
    fun `rejects expired invitation`() {
        shouldThrow<ExpiredInvitation> { acceptInvitation() }
    }
}
""",
        "MyApp.Tests/ExceptionAssertions.cs": """
public sealed class ExceptionAssertions
{
    [Fact]
    public void RejectsExpiredInvitation()
    {
        Assert.Throws<ExpiredInvitation>(() => AcceptInvitation());
    }
}
""",
        "spec/exception_assertions_spec.rb": """
RSpec.describe Invitation do
  it "rejects expired invitation token" do
    expect { accept_invitation }.to raise_error(ExpiredInvitation)
  end
end
""",
        "test/assertions_test.rb": """
def test_returns_configured_identifier
  assert_equal "cfg_7", identifier
end
""",
        "spec/ruby_helper_spec.rb": """
it "returns configured identifier for tenant" do
  expect(identifier).to eq("cfg_7")
end

def build_mock_bundle
  first = double("first")
  second = double("second")
  third = double("third")
  fourth = double("fourth")
end
""",
        "MyApp.Tests/TimeSignals.cs": """
public sealed class TimeSignals
{
    [Fact]
    public void ReadsCurrentDeadlineValue()
    {
        var now = DateTime.UtcNow;
        Assert.NotEqual(default, now);
    }
}
""",
        "tests/test_multiline_signature.py": """
def test_returns_configured_identifier(
    configured_account,
):
    assert configured_account.identifier == "acct_7"
""",
        "tests/test_verification_idioms.py": """
def test_sends_configured_payload_once(adapter):
    adapter.assert_called_once_with("payload")

def test_warns_when_deprecated_format_is_loaded():
    with pytest.warns(DeprecationWarning):
        load_deprecated_format()
""",
        "spec/native_literals_spec.rb": """
it("keeps ruby native literals opaque") do
  pattern = /end/
  words = %w[end complete]
  document = <<~TXT
end
TXT
  expect(pattern.match?(words.first)).to eq(true)
end
""",
        "spec/ruby_idioms_spec.rb": """
it "returns configured implicit subject" do
  is_expected.to eq("cfg_7")
end
""",
        "test/ruby_expectations_test.rb": """
def test_returns_configured_identifier_value
  identifier.must_equal "cfg_7"
end
""",
        "tests/HeredocTest.php": """
<?php
it('keeps heredoc braces inside payload', function () {
    $payload = <<<JSON
}
JSON;
    expect($payload)->toContain('}');
});
""",
        "src/raw_literal.rs": """
#[test]
fn keeps_raw_string_braces_inside_literal() {
    let payload = r##"}"##;
    assert_eq!(payload, "}");
}
""",
        "tests/each.spec.ts": """
test.each([[1, 2], [2, 4]])("doubles %s value correctly", (input, expected) => {
  expect(input * 2).toEqual(expected);
});
""",
        "tests/AttributeTest.php": """
<?php
#[Test]
public function rejectsExpiredInvitation(): void
{
    $this->expectException(ExpiredInvitation::class);
    acceptInvitation();
}
""",
        "src/KotestAssertionsTest.kt": """
class KotestAssertionsTest : StringSpec({
    "contains configured identifier prefix" {
        identifier() shouldContain "cfg_"
    }

    "verifies adapter effect once" {
        verify { adapter.send("payload") }
    }
})
""",
        "MyApp.Tests/NamespacedFact.cs": """
public sealed class NamespacedFact
{
    [Xunit.Fact]
    public void ReturnsConfiguredIdentifier()
    {
        Assert.Equal("cfg_7", Identifier());
    }
}
""",
        "src/MockitoVerificationTest.java": """
final class MockitoVerificationTest {
    @Test
    void sendsConfiguredPayloadOnce() {
        verify(adapter).send("payload");
    }
}
""",
        "MyApp.Tests/VerificationAssertions.cs": """
public sealed class VerificationAssertions
{
    [Fact]
    public void SendsConfiguredPayloadOnce()
    {
        adapter.Verify(item => item.Send("payload"));
    }

    [Test]
    public void ContainsConfiguredIdentifierPrefix()
    {
        StringAssert.Contains("cfg_", Identifier());
    }
}
""",
        "tests/EffectVerificationTest.php": """
<?php
it('returns successful response status', function () {
    $response = publishPayload();
    $response->assertOk();
});

it('sends configured payload once', function () {
    publishPayload();
    $adapter->shouldHaveReceived('send')->once();
});

it('expects configured payload once at teardown', function () {
    $adapter->shouldReceive('send')->once();
    publishPayload();
});
""",
        "tests/gomega_test.go": """
package tests
import "testing"
func TestReturnsConfiguredIdentifier(t *testing.T) {
    Expect(identifier()).To(Equal("cfg_7"))
}
""",
        "tests/deno.spec.ts": """
Deno.test("returns configured deno identifier", () => {
  assertEquals(identifier(), "cfg_7");
});
""",
        "src/mixed.py": """
def test_works():
    perform_action()
""",
        "node_modules/ignored.spec.ts": """
it("works", () => {
  Date.now();
});
""",
    }
    for relative, content in fixtures.items():
        write_text(root, relative, content)

    bom = root / "tests" / "bom.spec.ts"
    bom.write_bytes(
        b"\xef\xbb\xbfit(\"keeps configured identifier stable\", () => {\n"
        b"  expect(identifier()).toEqual(\"stable\");\n});\n"
    )
    (root / "tests" / "invalid.spec.ts").write_bytes(b"\xff\xfe\x00invalid")
    (root / "tests" / "large.spec.ts").write_bytes(b" " * 2_000_001)
    (root / "tests" / "large_lines.spec.ts").write_text(
        "// filler\n" * 10_000
        + 'it("works", () => { expect(value).toEqual("stable"); });\n',
        encoding="utf-8",
    )

def run_scanner(
    skill_root: Path, fixture_root: Path, *, timeout: int = 10
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(skill_root / "scripts" / "analyze_maintainable_tests.py"),
            str(fixture_root),
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )

def check_scanner_contract(
    skill_root: Path, errors: list[str], platform_skips: list[str]
) -> set[str]:
    scan_kinds: set[str] = set()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        fixture_root = temp / "project"
        fixture_root.mkdir()
        write_fixture(fixture_root)

        external = temp / "external.spec.ts"
        external.write_text('it("works", () => { Date.now(); });\n', encoding="utf-8")
        expected_diagnostics = {
            ("tests/invalid.spec.ts", "invalid-utf8"),
            ("tests/large.spec.ts", "file-too-large"),
        }
        try:
            (fixture_root / "tests" / "escaped.spec.ts").symlink_to(external)
        except (NotImplementedError, OSError) as exc:
            platform_skips.append(f"external symlink containment ({exc})")
        else:
            expected_diagnostics.add(
                ("tests/escaped.spec.ts", "outside-root-symlink")
            )

        fifo = fixture_root / "tests" / "blocked.spec.ts"
        if hasattr(os, "mkfifo"):
            try:
                os.mkfifo(fifo)
            except OSError as exc:
                platform_skips.append(f"FIFO non-regular-file guard ({exc})")
            else:
                expected_diagnostics.add(
                    ("tests/blocked.spec.ts", "non-regular-file")
                )
        else:
            platform_skips.append("FIFO non-regular-file guard (os.mkfifo unavailable)")

        try:
            first = run_scanner(skill_root, fixture_root)
            second = run_scanner(skill_root, fixture_root)
        except subprocess.TimeoutExpired:
            errors.append("scanner exceeded the 10-second timeout on filesystem regressions")
            return scan_kinds
        if first.returncode != 0:
            errors.append(f"scanner failed on regression fixture: {first.stderr.strip()}")
            return scan_kinds
        if first.stdout != second.stdout:
            errors.append("scanner JSON output is not deterministic across identical runs")
        try:
            payload = json.loads(first.stdout)
        except json.JSONDecodeError as exc:
            errors.append(f"scanner returned invalid JSON: {exc}")
            return scan_kinds

        findings = payload.get("findings", [])
        scan_kinds = {item.get("kind", "") for item in findings}
        actual = {
            (item["path"], item["line"], item["kind"], item["severity"])
            for item in findings
        }
        if actual != EXACT_FINDINGS:
            missing = sorted(EXACT_FINDINGS - actual)
            unexpected = sorted(actual - EXACT_FINDINGS)
            if missing:
                errors.append(f"scanner missed exact regression findings: {missing}")
            if unexpected:
                errors.append(f"scanner reported unexpected regression findings: {unexpected}")

        if scan_kinds != EXPECTED_FINDING_KINDS:
            errors.append(
                "scanner finding kinds differ from the bounded contract: "
                f"expected {sorted(EXPECTED_FINDING_KINDS)}, got {sorted(scan_kinds)}"
            )
        clean_findings = [item for item in findings if item.get("path") in CLEAN_PATHS]
        if clean_findings:
            errors.append(f"scanner reported false positives for clean fixtures: {clean_findings}")
        forbidden_paths = {
            "src/mixed.py",
            "src/production.ts",
            "node_modules/ignored.spec.ts",
        }
        leaked = [item for item in findings if item.get("path") in forbidden_paths]
        if leaked:
            errors.append(f"scanner treated excluded or production code as tests: {leaked}")
        if any("network" in json.dumps(item).casefold() for item in findings):
            errors.append("scanner claims network detection without a network recognizer")

        diagnostics = {(item.get("path"), item.get("kind")) for item in payload.get("diagnostics", [])}
        if diagnostics != expected_diagnostics:
            errors.append(
                f"scanner diagnostics differ: expected {sorted(expected_diagnostics)}, got {sorted(diagnostics)}"
            )
        summary = payload.get("summary", {})
        if summary.get("findings") != len(findings):
            errors.append("scanner summary finding count does not match structured findings")
        if summary.get("diagnostics") != len(diagnostics):
            errors.append("scanner summary diagnostic count does not match structured diagnostics")

        try:
            tests_directory = run_scanner(skill_root, fixture_root / "tests")
        except subprocess.TimeoutExpired:
            errors.append("scanner exceeded the timeout on a selected test directory")
        else:
            tests_payload = json.loads(tests_directory.stdout)
            project_test_findings = {
                (item["path"].removeprefix("tests/"), item["line"], item["kind"], item["severity"])
                for item in findings
                if item["path"].startswith("tests/")
            }
            directory_findings = {
                (item["path"], item["line"], item["kind"], item["severity"])
                for item in tests_payload.get("findings", [])
            }
            project_test_diagnostics = {
                (path.removeprefix("tests/"), kind)
                for path, kind in diagnostics
                if path.startswith("tests/")
            }
            directory_diagnostics = {
                (item.get("path"), item.get("kind"))
                for item in tests_payload.get("diagnostics", [])
            }
            if (
                tests_directory.returncode != 0
                or project_test_findings != directory_findings
                or project_test_diagnostics != directory_diagnostics
            ):
                errors.append("project-root and selected test-directory scans differ")

        try:
            direct = run_scanner(skill_root, fixture_root / "src" / "mixed.py")
        except subprocess.TimeoutExpired:
            errors.append("scanner exceeded the timeout on an explicit supported file")
        else:
            direct_payload = json.loads(direct.stdout)
            direct_findings = {
                (item["path"], item["line"], item["kind"], item["severity"])
                for item in direct_payload.get("findings", [])
            }
            expected_direct = {
                ("mixed.py", 1, "missing-recognized-assertion", "medium"),
                ("mixed.py", 1, "vague-test-name", "medium"),
            }
            if direct.returncode != 0 or direct_findings != expected_direct:
                errors.append(
                    "explicit supported file scan differed: "
                    f"expected {sorted(expected_direct)}, got {sorted(direct_findings)}"
                )

        block_cases = {
            "tests/node_options.spec.ts": 1,
            "tests/regex_body.spec.ts": 1,
            "tests/regex_fake.spec.ts": 0,
            "src/CsvAssertionsTest.java": 1,
            "src/SingleAnnotationTest.java": 1,
            "src/SingleAnnotationTest.kt": 1,
            "tests/test_multiline_signature.py": 1,
            "spec/native_literals_spec.rb": 1,
            "tests/HeredocTest.php": 1,
            "src/raw_literal.rs": 1,
            "tests/each.spec.ts": 1,
            "tests/AttributeTest.php": 1,
            "src/KotestAssertionsTest.kt": 2,
            "MyApp.Tests/NamespacedFact.cs": 1,
            "tests/test_verification_idioms.py": 2,
            "src/MockitoVerificationTest.java": 1,
            "MyApp.Tests/VerificationAssertions.cs": 2,
            "tests/EffectVerificationTest.php": 3,
            "tests/gomega_test.go": 1,
            "tests/deno.spec.ts": 1,
            "spec/ruby_idioms_spec.rb": 1,
            "test/ruby_expectations_test.rb": 1,
        }
        for relative, expected_blocks in block_cases.items():
            try:
                block_scan = run_scanner(skill_root, fixture_root / relative)
            except subprocess.TimeoutExpired:
                errors.append(f"scanner exceeded the timeout on block case: {relative}")
                continue
            block_payload = json.loads(block_scan.stdout)
            actual_blocks = block_payload.get("summary", {}).get("test_blocks")
            if (
                block_scan.returncode != 0
                or actual_blocks != expected_blocks
                or block_payload.get("findings")
            ):
                errors.append(
                    f"block case {relative} expected {expected_blocks} blocks and no findings; "
                    f"got {actual_blocks} and {block_payload.get('findings')}"
                )

        unparsed = temp / "unparsed.spec.ts"
        unparsed.write_text(
            'test.each`value\n1`("returns configured value", () => {});\n',
            encoding="utf-8",
        )
        try:
            unparsed_scan = run_scanner(skill_root, unparsed)
        except subprocess.TimeoutExpired:
            errors.append("known-marker diagnostic regression exceeded the timeout")
        else:
            unparsed_payload = json.loads(unparsed_scan.stdout)
            unparsed_kinds = {
                item.get("kind") for item in unparsed_payload.get("diagnostics", [])
            }
            if (
                unparsed_scan.returncode != 0
                or unparsed_payload.get("summary", {}).get("test_blocks") != 0
                or "known-test-marker-unparsed" not in unparsed_kinds
            ):
                errors.append("known but unsupported test syntax lacked a diagnostic")

        stress = temp / "stress.ts"
        stress.write_text(
            'test("works", () => {});\n' * 3_000,
            encoding="utf-8",
        )
        try:
            stress_scan = run_scanner(skill_root, stress)
        except subprocess.TimeoutExpired:
            errors.append("scanner exceeded the timeout while enforcing finding limits")
        else:
            stress_payload = json.loads(stress_scan.stdout)
            stress_diagnostics = {
                item.get("kind") for item in stress_payload.get("diagnostics", [])
            }
            if (
                stress_scan.returncode != 0
                or len(stress_payload.get("findings", [])) != 5_000
                or "finding-limit" not in stress_diagnostics
            ):
                errors.append(
                    "scanner did not enforce the in-scan 5000-finding limit exactly"
                )

        setup_scaling = temp / "setup-scaling.spec.ts"
        setup_scaling.write_text(
            "beforeEach();" * 5_000
            + '\ntest("keeps setup scan bounded", () => {'
            + '\n  expect(value).toEqual("stable");\n});\n',
            encoding="utf-8",
        )
        try:
            scaling_scan = run_scanner(skill_root, setup_scaling, timeout=3)
        except subprocess.TimeoutExpired:
            errors.append("fixture-noise scan exceeded the 3-second scaling budget")
        else:
            scaling_payload = json.loads(scaling_scan.stdout)
            if scaling_scan.returncode != 0 or scaling_payload.get("findings"):
                errors.append(
                    "bounded setup-marker regression produced unexpected findings or failure"
                )

        entry_budget = temp / "entry-budget"
        entry_budget.mkdir()
        for index in range(10_001):
            (entry_budget / f"unsupported-{index:05d}.txt").touch()
        try:
            entry_scan = run_scanner(skill_root, entry_budget)
        except subprocess.TimeoutExpired:
            errors.append("entry-budget regression exceeded the 10-second timeout")
        else:
            entry_payload = json.loads(entry_scan.stdout)
            entry_diagnostics = {
                item.get("kind") for item in entry_payload.get("diagnostics", [])
            }
            if entry_scan.returncode != 0 or "entry-limit" not in entry_diagnostics:
                errors.append("scanner did not report the deterministic entry limit")

        if hasattr(os, "mkfifo"):
            diagnostic_budget = temp / "diagnostic-budget"
            diagnostic_budget.mkdir()
            try:
                for index in range(2_005):
                    os.mkfifo(diagnostic_budget / f"blocked-{index:04d}.spec.ts")
            except OSError as exc:
                platform_skips.append(f"diagnostic cap with FIFOs ({exc})")
            else:
                try:
                    diagnostic_scan = run_scanner(skill_root, diagnostic_budget)
                except subprocess.TimeoutExpired:
                    errors.append("diagnostic-budget regression exceeded the timeout")
                else:
                    diagnostic_payload = json.loads(diagnostic_scan.stdout)
                    diagnostic_items = diagnostic_payload.get("diagnostics", [])
                    diagnostic_kinds = {item.get("kind") for item in diagnostic_items}
                    if (
                        diagnostic_scan.returncode != 0
                        or len(diagnostic_items) > 2_000
                        or "diagnostic-limit" not in diagnostic_kinds
                    ):
                        errors.append("scanner did not cap structured diagnostics")
    return scan_kinds

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCANNER = SKILL_ROOT / "scripts" / "analyze_maintainable_tests.py"

class ScannerTests(unittest.TestCase):
    def test_help_describes_scanner(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCANNER), "--help"],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("maintainable test review prompts", result.stdout)

    def test_rejects_missing_path(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCANNER), str(SKILL_ROOT / "does-not-exist")],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found:", result.stderr)

    def test_scanner_contract(self) -> None:
        errors: list[str] = []
        check_scanner_contract(SKILL_ROOT, errors, [])
        self.assertEqual(errors, [])

if __name__ == "__main__":
    unittest.main()

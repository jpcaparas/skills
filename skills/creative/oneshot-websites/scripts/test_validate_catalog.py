"""validate_catalog is the gate that decides whether a finished output root is trustworthy.

Each test starts from a root the real preparation and cleanup scripts produced, breaks one
rule, and asserts the specific error. Expected values come from the rules in SKILL.md and
references/catalog-index.md, not from the validator's output.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path

import directional_controls
import validate_catalog
from run_fixtures import (
    RACING_PROMPT,
    OutputRoot,
    edit_json,
    required_gauntlet,
)


class AcceptedRoots(OutputRoot):
    def test_finished_gauntlet_run_is_valid(self) -> None:
        self.ok_run()
        self.assert_valid(self.validate())

    def test_required_gauntlet_with_ready_critic_is_valid(self) -> None:
        run = self.prepare()
        self.finalize_ok(run, gauntlet=required_gauntlet("critic-1"), descendants=("critic-1",))
        self.assert_valid(self.validate())

    def test_generation_only_run_is_valid_but_warned_unverified_and_artifact_is_not_inspected(self) -> None:
        run = self.prepare(verification="none")
        self.finalize_unverified(run)
        (run / "artifact" / "package.json").write_text("{}", encoding="utf-8")  # would fail inspection
        result = self.validate()
        self.assert_valid(result)
        self.assertTrue(any("UNVERIFIED" in warning for warning in result["warnings"]))

    def test_rerun_pointing_at_an_existing_run_is_valid(self) -> None:
        first = self.ok_run()
        second = self.prepare(classification="rerun", prior_run=first, experiment="Poster")
        self.finalize_ok(second)
        self.assert_valid(self.validate())

    def test_empty_root_is_rejected(self) -> None:
        self.root.mkdir()
        self.assert_rejected(self.validate(rebuild_index=False), "no run directories")


class PromptIntegrity(OutputRoot):
    def test_prompt_edited_after_sealing_is_rejected(self) -> None:
        run = self.ok_run()
        (run / "artifact" / "PROMPT.md").write_text("A different brief.\n", encoding="utf-8")
        self.assert_rejected(
            self.validate(), "prompt SHA-256 does not match", "differs from the pre-dispatch prompt"
        )

    def test_mojibake_prompt_is_rejected_even_when_digest_matches(self) -> None:
        run = self.prepare()
        corrupted = "Cinnamonâ€™s desktop\n".encode("utf-8")
        (run / "artifact" / "PROMPT.md").write_bytes(corrupted)
        self.assert_rejected(self.validate(), "likely mojibake")

    def test_probe_contract_leaked_into_prompt_is_rejected(self) -> None:
        run = self.prepare()
        (run / "artifact" / "PROMPT.md").write_text(
            "Use window.__ONESHOT_DIRECTIONAL_CONTROL_PROBE__ please.\n", encoding="utf-8"
        )
        self.assert_rejected(self.validate(), "must remain a prose experience brief")

    def test_missing_prompt_is_rejected(self) -> None:
        run = self.ok_run()
        (run / "artifact" / "PROMPT.md").unlink()
        self.assert_rejected(self.validate(), "missing exact-case artifact/PROMPT.md")


class ReceiptAnchoring(OutputRoot):
    def test_run_without_receipt_is_rejected(self) -> None:
        run = self.ok_run()
        self.receipt_path(run).unlink()
        self.assert_rejected(self.validate(), "missing its coordinator provenance receipt")

    def test_run_without_commit_marker_is_rejected(self) -> None:
        run = self.ok_run()
        (self.root / ".oneshot-provenance" / f"{run.name}.commit").unlink()
        self.assert_rejected(self.validate(), "missing its provenance commit marker")

    def test_worker_edited_identity_no_longer_matches_receipt(self) -> None:
        run = self.ok_run()
        edit_json(run / "run.json", lambda d: d["identity"]["model"].update(name="Other Model"))
        self.assert_rejected(self.validate(), "identity does not match the pre-dispatch run record")

    def test_worker_cannot_downgrade_verification_mode(self) -> None:
        run = self.ok_run()
        edit_json(run / "run.json", lambda d: d.update(verificationMode="none"))
        self.assert_rejected(self.validate(), "run verificationMode must match the coordinator receipt")

    def test_ok_status_is_rejected_for_generation_only_receipt(self) -> None:
        run = self.prepare(verification="none")
        self.finalize_unverified(run)
        self.mark_status(run, "OK")
        self.assert_rejected(self.validate(), "generation-only completion must be UNVERIFIED, never OK")

    def test_unverified_status_is_rejected_for_gauntlet_receipt(self) -> None:
        run = self.ok_run()
        self.mark_status(run, "UNVERIFIED")
        self.assert_rejected(self.validate(), "UNVERIFIED requires receipt-anchored verificationMode none")

    def test_orphan_receipt_without_run_is_rejected(self) -> None:
        run = self.ok_run()
        self.ok_run()
        # Remove the first run directory but keep its receipt and commit marker.
        import shutil

        shutil.rmtree(run)
        self.assert_rejected(self.validate(), "orphan provenance receipt has no matching run manifest")

    def test_receipt_pointing_at_a_different_run_path_is_rejected(self) -> None:
        run = self.ok_run()
        edit_json(self.receipt_path(run), lambda r: r.update(runPath="somewhere/else"))
        self.assert_rejected(self.validate(), "runPath must match")

    def test_wrong_slug_in_run_directory_is_rejected(self) -> None:
        run = self.ok_run()
        edit_json(run / "run.json", lambda d: d["identity"]["experiment"].update(name="Something Else"))
        self.assert_rejected(self.validate(), "run-directory slug must match experiment name")


class StatusEvidence(OutputRoot):
    def test_ok_requires_local_static_handoff_verification_flag(self) -> None:
        run = self.ok_run()
        edit_json(run / "worker-report.json", lambda r: r["artifact"].update(staticDeploymentVerified=False))
        self.assert_rejected(self.validate(), "staticDeploymentVerified")

    def test_ok_with_a_failed_check_is_rejected(self) -> None:
        run = self.ok_run()
        edit_json(
            run / "worker-report.json",
            lambda r: r["verification"].append({"kind": "mobile", "result": "failed", "evidence": "overflow"}),
        )
        self.assert_rejected(self.validate(), "must not contain failed verification evidence")

    def test_ok_with_only_evidence_free_passes_is_rejected(self) -> None:
        run = self.ok_run()
        edit_json(
            run / "worker-report.json",
            lambda r: r.update(verification=[{"kind": "smoke", "result": "passed", "evidence": "  "}]),
        )
        self.assert_rejected(self.validate(), "structured passed verification evidence")

    def test_ok_run_must_have_deleted_tmp(self) -> None:
        run = self.ok_run()
        (run / ".tmp").mkdir()
        self.assert_rejected(self.validate(), "must delete its run-local .tmp/")

    def test_running_run_must_keep_tmp(self) -> None:
        run = self.prepare()
        self.mark_status(run, "RUNNING")
        import shutil

        shutil.rmtree(run / ".tmp")
        self.assert_rejected(self.validate(), "missing an exact-case ordinary .tmp/")

    def test_routing_applied_must_be_recorded_for_a_finished_run(self) -> None:
        run = self.ok_run()
        edit_json(run / "worker-report.json", lambda r: r["temporary"].update(routingApplied=None))
        self.assert_rejected(self.validate(), "must record temporary.routingApplied as true or false")

    def test_routing_disabled_needs_an_external_exception(self) -> None:
        run = self.ok_run()
        edit_json(run / "worker-report.json", lambda r: r["temporary"].update(routingApplied=False))
        self.assert_rejected(self.validate(), "temporary routing disabled must record an external exception")

    def test_report_status_must_match_manifest(self) -> None:
        run = self.ok_run()
        edit_json(run / "worker-report.json", lambda r: r.update(status="PARTIAL"))
        self.assert_rejected(self.validate(), "status must match run.json status 'OK'")

    def test_report_worker_ids_must_match_manifest(self) -> None:
        run = self.ok_run()
        edit_json(run / "worker-report.json", lambda r: r.update(leadWorkerId="lead-9"))
        self.assert_rejected(self.validate(), "worker IDs must exactly match")

    def test_lead_id_repeated_as_descendant_is_rejected(self) -> None:
        run = self.ok_run()
        for name in ("run.json", "worker-report.json"):
            edit_json(
                run / name,
                lambda d: (
                    d["execution"] if "execution" in d else d
                ).update(leadWorkerId="w1", descendantWorkerIds=["w1"]),
            )
        self.assert_rejected(self.validate(), "must not repeat leadWorkerId")


class QualityGauntlet(OutputRoot):
    def run_with_gauntlet(self, change) -> dict:
        gauntlet = required_gauntlet("critic-1")
        change(gauntlet)
        run = self.prepare()
        self.finalize_ok(run, gauntlet=gauntlet, descendants=("critic-1",))
        return self.validate()

    def test_a_failed_round_followed_by_a_ready_round_is_valid_but_the_reverse_is_not(self) -> None:
        not_ready = {"verdict": "NOT_READY", "highestLeverageGap": "Gap", "fix": "Fixed it"}

        def fixed_then_ready(g: dict) -> None:
            g["rounds"].insert(0, {**g["rounds"][0], **not_ready})

        self.assert_valid(self.run_with_gauntlet(fixed_then_ready))
        self.rmtree_root()

        def ready_then_broke(g: dict) -> None:
            g["rounds"].append({**g["rounds"][0], **not_ready})

        self.assert_rejected(self.run_with_gauntlet(ready_then_broke), "final critic verdict must be READY")

    def rmtree_root(self) -> None:
        import shutil

        shutil.rmtree(self.root)

    def test_final_verdict_must_be_ready(self) -> None:
        result = self.run_with_gauntlet(
            lambda g: g["rounds"][0].update(verdict="NOT_READY", highestLeverageGap="Layout broken", fix="x")
        )
        self.assert_rejected(result, "final critic verdict must be READY")

    def test_historical_not_ready_round_needs_a_fix(self) -> None:
        def change(g: dict) -> None:
            g["rounds"].insert(
                0, {**g["rounds"][0], "verdict": "NOT_READY", "highestLeverageGap": "Gap", "fix": None}
            )

        self.assert_rejected(self.run_with_gauntlet(change), "fix is required for a historical NOT_READY round")

    def test_blocked_round_needs_a_gap(self) -> None:
        def change(g: dict) -> None:
            g["rounds"].insert(0, {**g["rounds"][0], "verdict": "BLOCKED", "highestLeverageGap": None})

        self.assert_rejected(self.run_with_gauntlet(change), "highestLeverageGap is required for BLOCKED")

    def test_critic_must_be_a_recorded_descendant(self) -> None:
        run = self.prepare()
        self.finalize_ok(run, gauntlet=required_gauntlet("ghost"), descendants=("critic-1",))
        self.assert_rejected(self.validate(), "criticWorkerId must appear in descendantWorkerIds")

    def test_fallback_run_must_not_invent_rounds(self) -> None:
        def change(g: dict) -> None:
            g.update(freshCriticAvailable=False, fallbackEvidence="No subagent available")
            g["barValidation"]["result"] = "fallback-reviewed"

        self.assert_rejected(self.run_with_gauntlet(change), "must not invent critic rounds")

    def test_fresh_critic_cannot_validate_bar_by_fallback_review(self) -> None:
        result = self.run_with_gauntlet(lambda g: g["barValidation"].update(result="fallback-reviewed"))
        self.assert_rejected(result, "fresh critic runs must validate the quality bar independently")

    def test_revised_bar_needs_revisions(self) -> None:
        result = self.run_with_gauntlet(lambda g: g["barValidation"].update(result="revised"))
        self.assert_rejected(result, "revised quality bar must record barRevisions")

    def test_stop_reason_must_be_a_success_reason(self) -> None:
        result = self.run_with_gauntlet(lambda g: g.update(stopReason="user-stopped"))
        self.assert_rejected(result, "must stop on bar-met or no-material-actionable-gap")

    def test_required_integration_pass_needs_passed_result_and_evidence(self) -> None:
        result = self.run_with_gauntlet(
            lambda g: g["integrationPass"].update(required=True, result="failed", evidence=None)
        )
        self.assert_rejected(
            result,
            "required integration pass must record a passed result",
            "required integration pass must record concrete evidence",
        )

    def test_not_required_gauntlet_must_not_have_rounds(self) -> None:
        run = self.prepare()
        gauntlet = required_gauntlet("critic-1")
        gauntlet.update(applicability="not-required", notRequiredReason="Trivial", stopReason="not-required")
        self.finalize_ok(run, gauntlet=gauntlet, descendants=("critic-1",))
        self.assert_rejected(
            self.validate(),
            "not-required qualityGauntlet must not contain critic rounds",
            "must leave freshCriticAvailable null",
        )


class ArtifactTree(OutputRoot):
    def assert_artifact_rejected(self, mutate, *fragments: str) -> None:
        run = self.ok_run()
        mutate(run / "artifact")
        self.assert_rejected(self.validate(), *fragments)

    def test_missing_entrypoint(self) -> None:
        self.assert_artifact_rejected(lambda a: (a / "index.html").unlink(), "missing exact-case artifact/index.html")

    def test_wrong_case_entrypoint(self) -> None:
        self.assert_artifact_rejected(
            lambda a: (a / "index.html").rename(a / "Index.html"), "missing exact-case artifact/index.html"
        )

    def test_package_manifest_and_env_file_are_rejected(self) -> None:
        def mutate(artifact: Path) -> None:
            (artifact / "package.json").write_text("{}", encoding="utf-8")
            (artifact / ".env.local").write_text("X=1", encoding="utf-8")

        self.assert_artifact_rejected(mutate, "package.json: build, provider, package, or secret file", ".env.local")

    def test_preprocess_only_source_is_rejected(self) -> None:
        self.assert_artifact_rejected(
            lambda a: (a / "App.tsx").write_text("x", encoding="utf-8"), "preprocess-only source file"
        )

    def test_dependency_and_cache_directories_are_rejected(self) -> None:
        def mutate(artifact: Path) -> None:
            (artifact / "node_modules").mkdir()
            (artifact / ".next").mkdir()

        self.assert_artifact_rejected(mutate, "node_modules: cache, provider state", ".next: cache, provider state")

    def test_tmp_inside_artifact_is_rejected(self) -> None:
        self.assert_artifact_rejected(lambda a: (a / ".tmp").mkdir(), "run-local .tmp/ must stay outside artifact/")

    def test_symlink_is_rejected(self) -> None:
        self.assert_artifact_rejected(
            lambda a: (a / "link.html").symlink_to(a / "index.html"), "must not contain symbolic links"
        )

    def test_private_key_by_name_and_by_content_is_rejected(self) -> None:
        def mutate(artifact: Path) -> None:
            (artifact / "id_rsa").write_text("k", encoding="utf-8")
            (artifact / "notes.txt").write_text(
                "-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n", encoding="utf-8"
            )

        self.assert_artifact_rejected(mutate, "id_rsa: private key material", "notes.txt: private key material")

    def test_file_over_five_mebibytes_is_rejected_and_exactly_five_is_not(self) -> None:
        run = self.ok_run()
        limit = validate_catalog.DROP_MAX_FILE_BYTES
        (run / "artifact" / "exact.bin").write_bytes(b"\0" * limit)
        self.assert_valid(self.validate())
        (run / "artifact" / "over.bin").write_bytes(b"\0" * (limit + 1))
        self.assert_rejected(self.validate(), "over.bin: file exceeds the conservative 5 MiB")

    def test_file_count_limit_is_one_thousand(self) -> None:
        run = self.ok_run()
        for number in range(validate_catalog.DROP_MAX_FILES - 2):  # index.html + PROMPT.md + these = 1000
            (run / "artifact" / f"f{number}.txt").write_text("x", encoding="utf-8")
        self.assert_valid(self.validate())
        (run / "artifact" / "one-too-many.txt").write_text("x", encoding="utf-8")
        self.assert_rejected(self.validate(), "more than 1000 files")

    def test_unreadable_file_mode_is_rejected(self) -> None:
        if os.geteuid() == 0:
            self.skipTest("root can read anything")
        run = self.ok_run()
        hidden = run / "artifact" / "secret.txt"
        hidden.write_text("x", encoding="utf-8")
        hidden.chmod(0)
        self.addCleanup(hidden.chmod, 0o644)
        self.assert_rejected(self.validate(), "artifact file must have a readable file mode")


class LocalReferences(OutputRoot):
    def run_with_page(self, html: str, **files: str) -> dict:
        run = self.prepare()
        self.finalize_ok(run, index_html=html)
        for name, content in files.items():
            target = run / "artifact" / name.replace("__", "/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return self.validate()

    def test_existing_assets_relative_root_relative_and_srcset_are_accepted(self) -> None:
        html = (
            '<link rel="stylesheet" href="css/site.css"><script src="/js/app.js"></script>'
            '<img src="a.png" srcset="a.png 1x, a@2.png 2x"><img src="data:image/png;base64,AAA,BBB">'
            '<img src="https://cdn.example/x.png"><a href="#top">top</a>'
        )
        result = self.run_with_page(
            html,
            **{"css__site.css": "body{background:url('../a.png')}", "js__app.js": "1", "a.png": "x", "a@2.png": "x"},
        )
        self.assert_valid(result)

    def test_missing_script_is_rejected(self) -> None:
        result = self.run_with_page('<script src="missing.js"></script>')
        self.assert_rejected(result, "referenced local file missing or path casing differs: 'missing.js'")

    def test_wrong_case_reference_is_rejected(self) -> None:
        result = self.run_with_page('<img src="Logo.png">', **{"logo.png": "x"})
        self.assert_rejected(result, "path casing differs")

    def test_missing_asset_referenced_only_from_inline_style_is_rejected(self) -> None:
        result = self.run_with_page('<div style="background:url(bg.jpg)"></div>')
        self.assert_rejected(result, "'bg.jpg'")

    def test_missing_asset_referenced_only_from_style_block_is_rejected(self) -> None:
        result = self.run_with_page("<style>@import 'theme.css'; a{background:url(x.svg)}</style>")
        self.assert_rejected(result, "'theme.css'", "'x.svg'")

    def test_transitive_css_import_chain_is_followed(self) -> None:
        result = self.run_with_page(
            '<link rel="stylesheet" href="a.css">',
            **{"a.css": '@import "b.css";', "b.css": "p{background:url(gone.png)}"},
        )
        self.assert_rejected(result, "gone.png")

    def test_css_image_set_candidates_are_checked(self) -> None:
        result = self.run_with_page(
            '<link rel="stylesheet" href="a.css">',
            **{"a.css": 'p{background:image-set("hi.png" 2x, "lo.png" 1x)}', "lo.png": "x"},
        )
        self.assert_rejected(result, "'hi.png'")

    def test_url_inside_css_comment_or_string_is_not_a_reference(self) -> None:
        css = '/* url(commented.png) */ p::after{content:"url(quoted.png)"}'
        result = self.run_with_page('<link rel="stylesheet" href="a.css">', **{"a.css": css})
        self.assert_valid(result)

    def test_base_href_changes_resolution(self) -> None:
        result = self.run_with_page(
            '<base href="/sub/"><img src="pic.png">', **{"sub__pic.png": "x"}
        )
        self.assert_valid(result)
        result = self.run_with_page('<base href="/sub/"><img src="pic.png">', **{"pic.png": "x"})
        self.assert_rejected(result, "'pic.png'")

    def test_reference_to_preprocess_only_source_is_rejected(self) -> None:
        run = self.prepare()
        self.finalize_ok(run, index_html='<script src="main.ts"></script>')
        (run / "workspace" / "main.ts").write_text("x", encoding="utf-8")
        (run / "artifact" / "main.ts").write_text("x", encoding="utf-8")
        self.assert_rejected(self.validate(), "preprocess-only source")

    def test_encoded_path_traversal_and_backslash_are_rejected_or_not_found(self) -> None:
        result = self.run_with_page('<img src="..%2f..%2fsecret.png"><img src="a%5Cb.png">')
        self.assertFalse(result["valid"])

    def test_unclosed_style_tag_css_is_still_scanned(self) -> None:
        result = self.run_with_page("<style>p{background:url(late.png)}")
        self.assert_rejected(result, "'late.png'")


class ReferenceParsers(unittest.TestCase):
    def test_srcset_keeps_commas_inside_data_urls_and_skips_them(self) -> None:
        value = "a.png 1x, data:image/png;base64,AAAA,BBBB 2x, b.png 3x"
        self.assertEqual(list(validate_catalog.srcset_references(value)), ["a.png", "b.png"])

    def test_srcset_without_descriptors(self) -> None:
        self.assertEqual(list(validate_catalog.srcset_references("one.png, two.png")), ["one.png", "two.png"])

    def test_css_references_cover_url_import_and_image_set_but_not_comments(self) -> None:
        css = (
            '/* url(no.png) */ @import "x.css"; a{background:url( "y.png" )} '
            'b{background:-webkit-image-set("z.png" 1x)} c::after{content:"url(str.png)"}'
        )
        self.assertEqual(sorted(validate_catalog.css_references(css)), ["x.css", "y.png", "z.png"])

    def test_unterminated_comment_hides_following_urls_like_a_browser(self) -> None:
        self.assertEqual(validate_catalog.css_references("a{} /* url(hidden.png)"), [])

    def test_local_reference_resolution(self) -> None:
        errors: list[str] = []
        resolve = lambda ref, base="/index.html": validate_catalog.local_reference_path(  # noqa: E731
            ref, base, Path("src"), errors
        )
        self.assertEqual(resolve("img/a.png"), "img/a.png")
        self.assertEqual(resolve("../a.png", "/css/site.css"), "a.png")
        self.assertEqual(resolve("/abs/a.png", "/css/site.css"), "abs/a.png")
        self.assertEqual(resolve("a.png?v=1#x"), "a.png")
        self.assertIsNone(resolve("https://cdn.example/a.png"))
        self.assertIsNone(resolve("//cdn.example/a.png"))
        self.assertIsNone(resolve("#frag"))
        self.assertIsNone(resolve("a%00b.png"))
        self.assertEqual(len(errors), 1)
        self.assertIn("unsafe decoded local resource URL", errors[0])

    def test_run_id_grammar(self) -> None:
        parse = validate_catalog.parse_flat_run_id
        self.assertIsNotNone(parse("2026-11-10-08-51-35-poster"))
        self.assertEqual(parse("2026-11-10-08-51-35-poster--02").collision, 2)
        for bad in (
            "2026-02-30-08-51-35-poster",  # impossible date
            "2026-11-10-25-00-00-poster",  # impossible hour
            "2026-11-10-08-51-35-poster--01",  # collisions start at 02
            "2026-11-10-08-51-35-poster--2",  # not zero padded
            "2026-11-10-08-51-35",  # slug is mandatory
            "2026-11-10-08-51-35-Poster",  # uppercase slug
            "2026-11-10-08-51-35-" + "a" * 65,  # slug over 64 characters
        ):
            self.assertIsNone(parse(bad), bad)


class RootLayout(OutputRoot):
    def test_stale_root_index_is_rejected(self) -> None:
        self.ok_run()
        self.rebuild_index()
        (self.root / "index.html").write_text("<html>old</html>", encoding="utf-8")
        self.assert_rejected(self.validate(rebuild_index=False), "root catalogue is stale")

    def test_missing_root_index_is_rejected(self) -> None:
        self.ok_run()
        self.assert_rejected(self.validate(rebuild_index=False), "missing exact-case regular root index.html")

    def test_stray_file_and_unknown_directory_in_root_are_rejected(self) -> None:
        self.ok_run()
        (self.root / "notes.txt").write_text("x", encoding="utf-8")
        (self.root / "random-dir").mkdir()
        self.assert_rejected(
            self.validate(rebuild_index=False),
            "unexpected file outside a run",
            "unexpected directory outside a run",
        )

    def test_invalid_timestamp_directory_is_rejected(self) -> None:
        self.ok_run()
        bad = self.root / "2026-02-30-08-51-35-poster"
        bad.mkdir()
        self.assert_rejected(self.validate(rebuild_index=False), "invalid run directory name")

    def test_abandoned_reservation_without_commit_marker_is_ignored(self) -> None:
        self.ok_run()
        abandoned = self.root / "2026-11-10-08-51-36-crashed"
        (abandoned / ".tmp").mkdir(parents=True)
        (abandoned / "workspace").mkdir()
        (abandoned / "artifact").mkdir()
        self.assert_valid(self.validate())

    def test_committed_run_missing_run_json_is_rejected(self) -> None:
        run = self.ok_run()
        (run / "run.json").unlink()
        self.assert_rejected(self.validate(rebuild_index=False), "missing exact-case regular run.json")

    def test_non_object_json_is_reported_with_its_path(self) -> None:
        run = self.ok_run()
        (run / "worker-report.json").write_text("[1]", encoding="utf-8")
        self.assert_rejected(self.validate(rebuild_index=False), "worker-report.json: top-level JSON value must be an object")

    def test_duplicate_json_member_is_rejected(self) -> None:
        run = self.ok_run()
        (run / "run.json").write_text('{"a": 1, "a": 2}', encoding="utf-8")
        self.assert_rejected(self.validate(rebuild_index=False), "duplicate JSON object member")


class RerunGraph(OutputRoot):
    def test_prior_run_that_does_not_exist_is_rejected(self) -> None:
        first = self.ok_run()
        second = self.prepare(classification="rerun", prior_run=first)
        self.finalize_ok(second)
        edit_json(second / "run.json", lambda d: d.update(priorRun="2026-01-01-00-00-00-gone"))
        edit_json(self.receipt_path(second), lambda d: d.update(priorRun="2026-01-01-00-00-00-gone"))
        self.assert_rejected(self.validate(), "priorRun does not point to an exact canonical run")

    def test_two_reruns_pointing_at_each_other_are_a_cycle(self) -> None:
        first = self.ok_run()
        second = self.prepare(classification="rerun", prior_run=first)
        self.finalize_ok(second)
        for run, other in ((first, second), (second, first)):
            edit_json(run / "run.json", lambda d, o=other: d.update(classification="rerun", priorRun=o.name))
            edit_json(self.receipt_path(run), lambda d, o=other: d.update(classification="rerun", priorRun=o.name))
        self.assert_rejected(self.validate(), "priorRun cycle detected")

    def test_autonomous_run_must_not_declare_prior_run(self) -> None:
        first = self.ok_run()
        second = self.ok_run()
        edit_json(second / "run.json", lambda d: d.update(priorRun=first.name))
        edit_json(self.receipt_path(second), lambda d: d.update(priorRun=first.name))
        self.assert_rejected(self.validate(), "autonomous-one-shot must not declare priorRun")

    def test_rerun_pointing_at_itself_is_rejected(self) -> None:
        first = self.ok_run()
        second = self.prepare(classification="rerun", prior_run=first)
        self.finalize_ok(second)
        edit_json(second / "run.json", lambda d: d.update(priorRun=second.name))
        edit_json(self.receipt_path(second), lambda d: d.update(priorRun=second.name))
        self.assert_rejected(self.validate(), "priorRun must not point to the current run")


class DirectionalEvidence(OutputRoot):
    """A directional run is OK only with browser evidence bound to the exact artifact bytes."""

    def racing_ok_run(self) -> Path:
        run = self.prepare(prompt=RACING_PROMPT, experiment="Pod Racing")
        self.finalize_ok(run)
        return run

    def evidence_path(self, run: Path) -> Path:
        return self.root / ".oneshot-provenance" / f"{run.name}.directional-controls.json"

    def write_evidence(self, run: Path, mutate=None) -> None:
        digest = directional_controls.artifact_tree_digest(run / "artifact")
        evidence = {
            "schemaVersion": "1.0",
            "contractVersion": directional_controls.DIRECTIONAL_CONTROL_CONTRACT_VERSION,
            "runId": run.name,
            "artifact": {
                "digestAlgorithm": "oneshot-artifact-tree-v1",
                "sha256": digest.sha256,
                "files": digest.files,
                "bytes": digest.bytes,
            },
            "browser": {"kind": "chromium-cdp", "name": "chrome", "version": "Chromium 1"},
            "input": {"transport": "Chrome DevTools Protocol Input.dispatchKeyEvent"},
            "checks": [
                {"code": code, "expected": side, "frame": "ship", "measurement": "position",
                 "response": value, "passed": True}
                for code, side, value in (
                    ("KeyA", "left", -1.0), ("ArrowLeft", "left", -2.0),
                    ("KeyD", "right", 1.0), ("ArrowRight", "right", 0.5),
                )
            ],
            "passed": True,
            "error": None,
        }
        if mutate:
            mutate(evidence)
        path = self.evidence_path(run)
        path.write_text(__import__("json").dumps(evidence), encoding="utf-8")

    def test_ok_without_evidence_is_rejected(self) -> None:
        self.racing_ok_run()
        self.assert_rejected(self.validate(), "requires passing browser evidence from scripts/verify_directional_controls.py")

    def test_ok_with_matching_evidence_is_accepted(self) -> None:
        run = self.racing_ok_run()
        self.write_evidence(run)
        self.assert_valid(self.validate())

    def test_evidence_goes_stale_when_artifact_changes_afterwards(self) -> None:
        run = self.racing_ok_run()
        self.write_evidence(run)
        (run / "artifact" / "index.html").write_text("<html>edited after verification</html>", encoding="utf-8")
        self.assert_rejected(self.validate(), "does not match the current artifact revision")

    def test_inverted_response_sign_is_rejected(self) -> None:
        run = self.racing_ok_run()
        self.write_evidence(run, lambda e: e["checks"][0].update(response=1.0))  # A moved right
        self.assert_rejected(self.validate(), "KeyA response has the wrong semantic sign")

    def test_response_inside_epsilon_is_not_a_move(self) -> None:
        run = self.racing_ok_run()
        self.write_evidence(run, lambda e: e["checks"][2].update(response=1e-5))
        self.assert_rejected(self.validate(), "KeyD response has the wrong semantic sign")

    def test_missing_key_and_duplicate_key_are_rejected(self) -> None:
        run = self.racing_ok_run()
        self.write_evidence(run, lambda e: e["checks"].__setitem__(3, dict(e["checks"][0])))
        self.assert_rejected(self.validate(), "unknown or duplicate key code", "must cover A/Left and D/Right")

    def test_non_finite_and_boolean_responses_are_rejected(self) -> None:
        run = self.racing_ok_run()
        self.write_evidence(run, lambda e: e["checks"][0].update(response=True))
        self.assert_rejected(self.validate(), "KeyA response must be a finite number")

    def test_evidence_for_another_run_is_rejected(self) -> None:
        run = self.racing_ok_run()
        self.write_evidence(run, lambda e: e.update(runId="2026-01-01-00-00-00-other"))
        self.assert_rejected(self.validate(), "runId must match")

    def test_evidence_without_a_passed_flag_is_rejected(self) -> None:
        run = self.racing_ok_run()
        self.write_evidence(run, lambda e: e.pop("passed"))
        self.assert_rejected(self.validate(), "browser verification did not pass")

    def test_failed_evidence_is_rejected(self) -> None:
        run = self.racing_ok_run()
        self.write_evidence(run, lambda e: e.update(passed=False, error="boom"))
        self.assert_rejected(self.validate(), "browser verification did not pass")

    def test_input_transport_must_be_cdp_key_events(self) -> None:
        run = self.racing_ok_run()
        self.write_evidence(run, lambda e: e["input"].update(transport="synthetic dispatchEvent"))
        self.assert_rejected(self.validate(), "input transport must use Chrome DevTools Protocol key events")

    def test_active_directional_run_needs_its_technical_prompt(self) -> None:
        run = self.prepare(prompt=RACING_PROMPT, experiment="Pod Racing")
        self.mark_status(run, "RUNNING")
        (run / ".tmp" / "TECHNICAL_PROMPT.md").unlink()
        self.assert_rejected(self.validate(), "requires exact-case .tmp/TECHNICAL_PROMPT.md")

    def test_active_directional_run_rejects_a_hollow_technical_prompt(self) -> None:
        run = self.prepare(prompt=RACING_PROMPT, experiment="Pod Racing")
        (run / ".tmp" / "TECHNICAL_PROMPT.md").write_text("Make it good.\n", encoding="utf-8")
        self.assert_rejected(self.validate(), "missing its executable gate contract")

    def test_non_directional_run_must_not_have_technical_prompt(self) -> None:
        run = self.prepare()
        (run / ".tmp" / "TECHNICAL_PROMPT.md").write_text("x", encoding="utf-8")
        self.assert_rejected(self.validate(), "non-applicable run must not create .tmp/TECHNICAL_PROMPT.md")


class WorkerIdentityParsing(unittest.TestCase):
    def parse(self, record: dict):
        errors: list[str] = []
        identity = validate_catalog.parse_worker_identity(record, Path("r.json"), "", errors)
        return identity, errors

    def test_null_lead_and_empty_descendants_are_valid(self) -> None:
        identity, errors = self.parse({"leadWorkerId": None, "descendantWorkerIds": []})
        self.assertEqual(errors, [])
        self.assertEqual((identity.lead, identity.descendants), (None, ()))

    def test_missing_blank_and_duplicate_ids_are_rejected(self) -> None:
        for record, fragment in (
            ({"descendantWorkerIds": []}, "leadWorkerId is required"),
            ({"leadWorkerId": " ", "descendantWorkerIds": []}, "non-blank string"),
            ({"leadWorkerId": None, "descendantWorkerIds": ["a", " a "]}, "unique IDs"),
            ({"leadWorkerId": None, "descendantWorkerIds": "a"}, "must be an array"),
            ({"leadWorkerId": None, "descendantWorkerIds": [3]}, "non-blank string"),
        ):
            identity, errors = self.parse(record)
            self.assertIsNone(identity)
            self.assertTrue(any(fragment in e for e in errors), (record, errors))


if __name__ == "__main__":
    unittest.main()

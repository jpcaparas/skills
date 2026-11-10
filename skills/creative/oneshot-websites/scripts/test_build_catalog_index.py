"""The root index is a provenance table; it must show every run honestly and never trust worker text."""

from __future__ import annotations

import os
import unittest

import build_catalog_index as bci
from run_fixtures import OutputRoot, edit_json, run_script


class RunIdTests(unittest.TestCase):
    def test_collision_numbers_start_at_two_and_are_zero_padded(self) -> None:
        self.assertIsNone(bci.parse_flat_run_id("2026-11-10-08-51-35-poster--01"))
        self.assertIsNone(bci.parse_flat_run_id("2026-11-10-08-51-35-poster--2"))
        self.assertEqual(bci.parse_flat_run_id("2026-11-10-08-51-35-poster--10").collision, 10)

    def test_impossible_dates_and_overlong_slugs_are_not_run_ids(self) -> None:
        self.assertFalse(bci.is_supported_run_id("2026-13-01-00-00-00-x"))
        self.assertFalse(bci.is_supported_run_id("2026-02-29-00-00-00-x"))  # 2026 is not a leap year
        self.assertTrue(bci.is_supported_run_id("2028-02-29-00-00-00-x"))
        self.assertTrue(bci.is_supported_run_id("2026-01-01-00-00-00-" + "a" * 64))
        self.assertFalse(bci.is_supported_run_id("2026-01-01-00-00-00-" + "a" * 65))


class RenderingTests(OutputRoot):
    def render(self) -> str:
        return bci.build_html(self.root.resolve(), self.root.resolve() / "index.html")

    def test_each_run_gets_one_row_with_links_only_to_files_that_exist(self) -> None:
        done = self.ok_run()
        planned = self.prepare(experiment="Unfinished")
        html = self.render()
        self.assertEqual(html.count("<tr>\n          <td data-label=\"Model\">"), 2)
        self.assertIn(f'href="{done.name}/artifact/index.html"', html)
        self.assertIn(f'href="{done.name}/artifact/PROMPT.md"', html)
        self.assertNotIn(f'{planned.name}/artifact/index.html', html)  # no entrypoint yet: no dead link
        self.assertIn("Runs discovered: <code>2</code>", html)

    def test_status_badges_distinguish_ok_unverified_and_progress(self) -> None:
        self.ok_run()
        gen = self.prepare(verification="none", experiment="Gen")
        self.finalize_unverified(gen)
        self.prepare(experiment="Running one")
        html = self.render()
        for css in ("status-ok", "status-unverified", "status-progress"):
            self.assertIn(css, html)
        self.assertIn("Generated without artifact or workspace checks.", html)

    def test_worker_supplied_text_is_html_escaped(self) -> None:
        run = self.ok_run()
        payload = "<script>alert(1)</script>"
        edit_json(run / "worker-report.json", lambda r: r.update(summary=payload))
        html = self.render()
        self.assertNotIn(payload, html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_long_worker_text_is_bounded(self) -> None:
        run = self.ok_run()
        edit_json(run / "worker-report.json", lambda r: r.update(summary="x" * 5000))
        html = self.render()
        self.assertNotIn("x" * 1025, html)
        self.assertIn("(+3976 chars)", html)

    def test_summary_beats_blocker_and_blocker_is_labelled(self) -> None:
        run = self.ok_run()
        edit_json(run / "worker-report.json", lambda r: r.update(summary=None, blocker="No GPU"))
        self.assertIn("Blocker: No GPU", self.render())
        edit_json(run / "worker-report.json", lambda r: r.update(summary="Built it", blocker="No GPU"))
        html = self.render()
        self.assertIn("Built it", html)
        self.assertNotIn("No GPU", html)

    def test_mismatched_worker_ids_are_flagged_not_hidden(self) -> None:
        run = self.ok_run()
        edit_json(run / "worker-report.json", lambda r: r.update(leadWorkerId="rogue"))
        self.assertIn("Worker metadata mismatch", self.render())

    def test_worker_counts_are_pluralised(self) -> None:
        run = self.prepare()
        self.finalize_ok(run, descendants=("w1",))
        self.assertIn("1 descendant<", self.render().replace("</td>", "<"))
        run2 = self.prepare(experiment="Two")
        self.finalize_ok(run2, descendants=("a", "b"))
        self.assertIn("2 descendants", self.render())

    def test_corrupt_manifest_stays_visible_as_invalid_row(self) -> None:
        good = self.ok_run()
        bad = self.prepare(experiment="Broken")
        (bad / "run.json").write_text("{not json", encoding="utf-8")
        html = self.render()
        self.assertIn("INVALID", html)
        self.assertIn("metadata is not valid JSON", html)
        self.assertIn(good.name, html)

    def test_mode_status_contradiction_renders_invalid(self) -> None:
        run = self.ok_run()
        self.mark_status(run, "UNVERIFIED")
        self.assertIn("UNVERIFIED requires receipt-anchored verificationMode none", self.render())

    def test_empty_root_says_so(self) -> None:
        self.root.mkdir()
        self.assertIn("No run manifests found", self.render())


class DiscoveryTests(OutputRoot):
    def test_abandoned_reservations_are_not_rows_but_committed_empty_runs_error(self) -> None:
        self.ok_run()
        abandoned = self.root / "2026-11-10-08-51-36-crashed"
        for name in (".tmp", "workspace", "artifact"):
            (abandoned / name).mkdir(parents=True)
        self.assertEqual(len(bci.discover_runs(self.root.resolve())), 1)

    def test_stray_entries_and_bad_run_names_abort_instead_of_guessing(self) -> None:
        self.ok_run()
        (self.root / "notes.txt").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(bci.CatalogueBuildError, "unexpected entry"):
            bci.discover_runs(self.root.resolve())
        (self.root / "notes.txt").unlink()
        (self.root / "2026-02-30-00-00-00-x").mkdir()
        with self.assertRaisesRegex(bci.CatalogueBuildError, "invalid run directory name"):
            bci.discover_runs(self.root.resolve())

    def test_reserved_files_lock_and_provenance_are_ignored(self) -> None:
        self.ok_run()
        (self.root / bci.CATALOGUE_LOCK).write_text("", encoding="utf-8")
        (self.root / ".oneshot-index-abc.tmp").write_text("", encoding="utf-8")
        (self.root / "._junk").write_bytes(b"\x00\x05\x16\x07rest")
        self.assertEqual(len(bci.discover_runs(self.root.resolve())), 1)


class PublishTests(OutputRoot):
    def test_publish_writes_readable_index_and_leaves_no_temp_file(self) -> None:
        self.ok_run()
        root = self.root.resolve()
        bci.publish_catalogue(root, root / "index.html")
        self.assertTrue((root / "index.html").stat().st_mode & 0o444)
        self.assertEqual([p.name for p in root.iterdir() if p.name.startswith(".oneshot-index-")], [])

    def test_publish_is_idempotent_for_an_unchanged_root(self) -> None:
        self.ok_run()
        root = self.root.resolve()
        bci.publish_catalogue(root, root / "index.html")
        first = (root / "index.html").read_text(encoding="utf-8")
        bci.publish_catalogue(root, root / "index.html")
        self.assertEqual(first, (root / "index.html").read_text(encoding="utf-8"))

    def test_symlinked_destination_is_refused_and_not_followed(self) -> None:
        self.ok_run()
        root = self.root.resolve()
        victim = self.tmp / "victim.txt"
        victim.write_text("keep", encoding="utf-8")
        (root / "index.html").symlink_to(victim)
        with self.assertRaisesRegex(bci.CatalogueBuildError, "regular non-symlink"):
            bci.publish_catalogue(root, root / "index.html")
        self.assertEqual(victim.read_text(encoding="utf-8"), "keep")

    def test_wrong_case_index_name_is_a_collision_error(self) -> None:
        self.ok_run()
        root = self.root.resolve()
        (root / "Index.html").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(bci.CatalogueBuildError, "wrong-case"):
            bci.publish_catalogue(root, root / "index.html")

    def test_lock_file_must_be_private_regular_file(self) -> None:
        root = self.ok_run().parent.resolve()
        other = self.tmp / "other"
        other.write_text("x", encoding="utf-8")
        (root / bci.CATALOGUE_LOCK).symlink_to(other)
        with self.assertRaises(bci.CatalogueBuildError):
            with bci.catalogue_lock(root):
                pass
        (root / bci.CATALOGUE_LOCK).unlink()
        os.link(other, root / bci.CATALOGUE_LOCK)  # second hard link: not private
        with self.assertRaisesRegex(bci.CatalogueBuildError, "private regular"):
            with bci.catalogue_lock(root):
                pass

    def test_command_line_only_writes_the_root_index(self) -> None:
        self.ok_run()
        root = str(self.root.resolve())
        wrong = run_script("build_catalog_index.py", "--root", root, "--out", str(self.tmp / "else.html"))
        self.assertNotEqual(wrong.returncode, 0)
        self.assertFalse((self.tmp / "else.html").exists())
        good = run_script("build_catalog_index.py", "--root", root, "--out", f"{root}/index.html")
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertTrue((self.root / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()

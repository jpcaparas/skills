"""list_prompts is what the user sees first; filters and ranking must be exact and deterministic."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import list_prompts as lp
from run_fixtures import SKILL, run_script

CATALOGUE = json.loads((SKILL / "assets" / "prompt-catalogue.json").read_text(encoding="utf-8"))


def entry(identifier: str, title: str, category: str = "alpha", tags=("one",), prompt="Make a thing.", description="Does a thing.", slug=None) -> dict:
    return {
        "id": identifier, "slug": slug or identifier, "title": title, "description": description,
        "category": category, "prompt": prompt, "tags": list(tags),
    }


def write_catalogue(directory: Path, prompts: list[dict], categories=None) -> Path:
    document = {
        "experienceDirection": "Be vivid.",
        "completionMandate": "Finish.",
        "categories": categories or [
            {"id": "alpha", "title": "Alpha", "description": "First."},
            {"id": "beta", "title": "Beta", "description": "Second."},
        ],
        "prompts": prompts,
    }
    path = directory / "catalogue.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


class ShippedCatalogueTests(unittest.TestCase):
    """Invariants the authoring guide promises for assets/prompt-catalogue.json."""

    def test_loads_and_every_prompt_is_listed_once_without_coordinator_guidance(self) -> None:
        result = run_script("list_prompts.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        for prompt in CATALOGUE["prompts"]:
            self.assertEqual(result.stdout.count(f"`{prompt['id']}`"), 1, prompt["id"])
        self.assertIn(f"{len(CATALOGUE['prompts'])} prompt(s)", result.stdout)
        self.assertNotIn(CATALOGUE["experienceDirection"], result.stdout)
        self.assertNotIn(CATALOGUE["completionMandate"], result.stdout)

    def test_ids_slugs_are_unique_and_browsing_metadata_respects_authoring_limits(self) -> None:
        prompts = CATALOGUE["prompts"]
        for field in ("id", "slug", "title"):
            values = [p[field] for p in prompts]
            self.assertEqual(len(values), len(set(values)), field)
        self.assertGreaterEqual(len(prompts), 100)
        for p in prompts:
            self.assertLessEqual(len(p["title"].split()), 6, p["id"])
            self.assertLessEqual(len(p["title"]), 48, p["id"])
            self.assertLessEqual(len(p["description"].split()), 18, p["id"])
            self.assertLessEqual(len(p["description"]), 140, p["id"])
            self.assertEqual(p["tags"], [t.lower() for t in p["tags"]], p["id"])

    def test_json_format_round_trips_with_every_prompt(self) -> None:
        result = run_script("list_prompts.py", "--format", "json")
        document = json.loads(result.stdout)
        listed = [p["id"] for group in document["categories"] for p in group["prompts"]]
        self.assertEqual(sorted(listed), sorted(p["id"] for p in CATALOGUE["prompts"]))
        self.assertEqual(document["count"], len(listed))


class FilterTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.catalogue = lp.load_catalogue(
            write_catalogue(
                Path(tmp.name),
                [
                    entry("p1", "Garden Planner", "alpha", ("plants", "calm"), "Grow herbs."),
                    entry("p2", "Space Garden", "beta", ("plants", "space"), "Orbit."),
                    entry("p3", "Race Cars", "beta", ("speed",), "Drive a garden path fast."),
                ],
            )
        )

    def select(self, **flags) -> list[str]:
        arguments = lp.parse_arguments([a for k, v in flags.items() for a in (f"--{k}", *([v] if isinstance(v, str) else v))])
        return [e.identifier for e in lp.select_entries(self.catalogue.prompts, arguments)]

    def test_no_filters_keeps_catalogue_order(self) -> None:
        self.assertEqual(self.select(), ["p1", "p2", "p3"])

    def test_category_filter_is_case_insensitive_and_repeatable(self) -> None:
        self.assertEqual(self.select(category="BETA"), ["p2", "p3"])
        self.assertEqual(self.select(category=["alpha", "beta"]), ["p1", "p2", "p3"])

    def test_tags_must_all_match(self) -> None:
        self.assertEqual(self.select(tag="plants"), ["p1", "p2"])
        self.assertEqual(self.select(tag=["plants", "space"]), ["p2"])
        self.assertEqual(self.select(tag="plants,space"), ["p2"])

    def test_ids_accept_comma_lists_case_insensitively(self) -> None:
        self.assertEqual(self.select(ids="P3,p1"), ["p1", "p3"])

    def test_limit_applies_after_filters(self) -> None:
        self.assertEqual(self.select(category="beta", limit="1"), ["p2"])

    def test_limit_must_be_a_positive_integer(self) -> None:
        for bad in ("0", "-1", "x"):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                lp.parse_arguments(["--limit", bad])

    def test_search_requires_every_term_somewhere(self) -> None:
        self.assertEqual(self.select(search="garden herbs"), ["p1"])
        self.assertEqual(self.select(search="nonexistentterm"), [])

    def test_search_ranks_title_over_description_over_prompt(self) -> None:
        # p1 and p2 have "garden" in the title; p3 only in its prompt.
        self.assertEqual(self.select(search="garden")[-1], "p3")
        # An exact-prefix title match beats a later-position title match.
        self.assertEqual(self.select(search="garden")[:2], ["p1", "p2"])

    def test_ranking_is_deterministic_for_equal_scores(self) -> None:
        self.assertEqual(self.select(search="garden"), self.select(search="garden"))


class RenderingTests(unittest.TestCase):
    def test_undeclared_category_and_missing_fields_are_load_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            cases = {
                "undeclared categories": [entry("p1", "T", category="gamma")],
                "tags must be": [{**entry("p1", "T"), "tags": []}],
                "title must be": [{**entry("p1", "T"), "title": " "}],
            }
            for fragment, prompts in cases.items():
                with self.assertRaisesRegex(lp.CatalogueError, fragment):
                    lp.load_catalogue(write_catalogue(directory, prompts))

    def test_invalid_json_duplicate_member_and_wrong_root_are_load_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            for text in ("{", '{"a":1,"a":2}', "[]"):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(lp.CatalogueError, msg=text):
                    lp.load_catalogue(path)
            with self.assertRaises(lp.CatalogueError):
                lp.load_catalogue(Path(tmp) / "missing.json")

    def test_markdown_groups_by_declared_category_order_and_hides_empty_categories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalogue = lp.load_catalogue(
                write_catalogue(Path(tmp), [entry("p2", "In Beta", "beta"), entry("p1", "In Alpha", "alpha")])
            )
            markdown = lp.markdown_output(catalogue, catalogue.prompts)
            self.assertLess(markdown.index("Namespace `alpha`"), markdown.index("Namespace `beta`"))
            empty = lp.markdown_output(catalogue, [catalogue.prompts[0]])
            self.assertNotIn("Namespace `alpha`", empty)
            self.assertIn("1 prompt(s)", empty)

    def test_multiline_descriptions_collapse_to_one_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalogue = lp.load_catalogue(write_catalogue(Path(tmp), [entry("p1", "T", description="line one\n  line two")]))
            self.assertIn("— line one line two —", lp.markdown_output(catalogue, catalogue.prompts))


if __name__ == "__main__":
    unittest.main()

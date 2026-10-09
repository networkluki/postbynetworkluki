import unittest
from datetime import date

from content import (
    PostError,
    all_posts,
    delete_post,
    legacy_slug_map,
    parse_post,
    post_path,
    published_display,
    slugify,
    write_post,
)
from helpers import ContentDirectoryTestCase, write_post_file


class CategoryTests(unittest.TestCase):
    def test_category_must_be_one_of_the_three_sections(self):
        text = VALID.replace("category: Articles", "category: Random")
        with self.assertRaises(PostError) as caught:
            parse_post(text, "x", "x.md")
        self.assertIn("category must be one of", caught.exception.message)

    def test_category_is_normalised_to_its_display_form(self):
        text = VALID.replace("category: Articles", "category: changelog")
        self.assertEqual(parse_post(text, "x", "x.md").category, "Changelog")


class PublishedTimeTests(unittest.TestCase):
    def test_time_is_optional_and_defaults_to_empty(self):
        self.assertEqual(parse_post(VALID, "x", "x.md").published_time, "")

    def test_a_valid_time_is_parsed_and_displayed(self):
        text = VALID.replace(
            "published: 2026-09-24", "published: 2026-09-24\npublished_time: 14:30"
        )
        post = parse_post(text, "x", "x.md")
        self.assertEqual(post.published_time, "14:30")
        self.assertEqual(published_display(post), "2026-09-24 · 14:30")

    def test_a_bad_time_is_rejected(self):
        text = VALID.replace(
            "published: 2026-09-24", "published: 2026-09-24\npublished_time: 25:99"
        )
        with self.assertRaises(PostError) as caught:
            parse_post(text, "x", "x.md")
        self.assertIn("HH:MM", caught.exception.message)

VALID = """---
title: Build less
category: Articles
excerpt: A short summary.
published: 2026-09-24
read_time: 4 min
legacy_slugs: bygg-mindre, gammal-slug
---

First paragraph.


Second paragraph after extra blank lines.
"""


class ParsingTests(unittest.TestCase):
    def test_a_valid_file_parses(self):
        post = parse_post(VALID, "build-less", "build-less.md")
        self.assertEqual(post.title, "Build less")
        self.assertEqual(post.category, "Articles")
        self.assertEqual(post.published, date(2026, 9, 24))
        self.assertEqual(post.legacy_slugs, ("bygg-mindre", "gammal-slug"))
        self.assertEqual(
            post.content,
            ("First paragraph.", "Second paragraph after extra blank lines."),
        )

    def test_front_matter_must_open_and_close(self):
        for text, expected in (
            ("title: No fence\n", "must start with"),
            ("---\ntitle: Unclosed\n", "never closed"),
        ):
            with self.subTest(text=text):
                with self.assertRaises(PostError) as caught:
                    parse_post(text, "x", "x.md")
                self.assertIn(expected, caught.exception.message)

    def test_rejects_unknown_duplicate_and_malformed_fields(self):
        cases = {
            "---\nauthor: Someone\n---\nBody.\n": "unknown field",
            "---\ntitle: One\ntitle: Two\n---\nBody.\n": "appears more than once",
            "---\njust a line\n---\nBody.\n": "not a 'key: value' pair",
        }
        for text, expected in cases.items():
            with self.subTest(expected=expected):
                with self.assertRaises(PostError) as caught:
                    parse_post(text, "x", "x.md")
                self.assertIn(expected, caught.exception.message)

    def test_reports_missing_required_fields(self):
        with self.assertRaises(PostError) as caught:
            parse_post("---\ntitle: Only a title\n---\nBody.\n", "x", "x.md")
        message = caught.exception.message
        self.assertIn("missing field(s)", message)
        for field in ("category", "excerpt", "published", "read_time"):
            self.assertIn(field, message)

    def test_rejects_a_bad_date(self):
        text = VALID.replace("published: 2026-09-24", "published: 24 sep 2026")
        with self.assertRaises(PostError) as caught:
            parse_post(text, "x", "x.md")
        self.assertIn("YYYY-MM-DD", caught.exception.message)

    def test_rejects_an_empty_body_and_an_overlong_field(self):
        with self.assertRaises(PostError) as caught:
            parse_post(VALID.split("---\n\n")[0] + "---\n\n   \n", "x", "x.md")
        self.assertIn("content is required", caught.exception.message)
        long_title = VALID.replace("title: Build less", f"title: {'x' * 121}")
        with self.assertRaises(PostError) as caught:
            parse_post(long_title, "x", "x.md")
        self.assertIn("longer than 120 characters", caught.exception.message)

    def test_rejects_a_file_name_that_is_not_a_slug(self):
        with self.assertRaises(PostError) as caught:
            parse_post(VALID, "Not A Slug", "Not A Slug.md")
        self.assertIn("lowercase letters, digits and dashes", caught.exception.message)

    def test_slugify_strips_accents_and_punctuation(self):
        self.assertEqual(slugify("Ett lugnare flöde!"), "ett-lugnare-flode")
        self.assertEqual(slugify("###"), "")


class DirectoryTests(ContentDirectoryTestCase):
    def test_posts_are_sorted_newest_first(self):
        write_post_file(self.posts_directory, "older", published="2026-01-01")
        write_post_file(self.posts_directory, "newer", published="2026-07-01")
        self.assertEqual([post.slug for post in all_posts()], ["newer", "older"])

    def test_an_empty_directory_yields_no_posts(self):
        self.assertEqual(all_posts(), ())

    def test_a_slug_claimed_twice_is_rejected(self):
        write_post_file(self.posts_directory, "first", legacy_slugs="shared")
        write_post_file(self.posts_directory, "second", legacy_slugs="shared")
        with self.assertRaises(PostError) as caught:
            all_posts()
        self.assertIn("used more than once", caught.exception.message)

    def test_legacy_slug_map_points_aliases_at_the_current_slug(self):
        write_post_file(self.posts_directory, "current", legacy_slugs="old, older")
        self.assertEqual(
            legacy_slug_map(all_posts()), {"old": "current", "older": "current"}
        )

    def test_write_post_round_trips(self):
        post = write_post(
            {
                "title": "Written by the API",
                "category": "Articles",
                "excerpt": "Short.",
                "read_time": "1 min",
                "content": "One.\n\nTwo.",
            },
            published=date(2026, 3, 2),
        )
        self.assertEqual(post.slug, "written-by-the-api")
        self.assertTrue(post_path(post.slug).is_file())
        reloaded = all_posts()[0]
        self.assertEqual(reloaded.title, "Written by the API")
        self.assertEqual(reloaded.content, ("One.", "Two."))
        self.assertEqual(reloaded.published, date(2026, 3, 2))

    def test_write_post_refuses_an_existing_slug_or_alias(self):
        write_post_file(self.posts_directory, "taken", legacy_slugs="also-taken")
        for slug in ("taken", "also-taken"):
            with self.subTest(slug=slug):
                with self.assertRaises(PostError) as caught:
                    write_post(
                        {
                            "title": "Clash",
                            "category": "Articles",
                            "excerpt": "Short.",
                            "read_time": "1 min",
                            "content": "Body.",
                        },
                        slug=slug,
                    )
                self.assertIn("already exists", caught.exception.message)

    def test_write_post_leaves_no_temporary_file_behind(self):
        write_post(
            {
                "title": "Clean",
                "category": "Articles",
                "excerpt": "Short.",
                "read_time": "1 min",
                "content": "Body.",
            }
        )
        names = sorted(path.name for path in self.posts_directory.iterdir())
        self.assertEqual(names, ["clean.md"])

    def test_delete_post_reports_whether_it_removed_a_file(self):
        write_post_file(self.posts_directory, "temporary")
        self.assertTrue(delete_post("temporary"))
        self.assertFalse(delete_post("temporary"))


if __name__ == "__main__":
    unittest.main()

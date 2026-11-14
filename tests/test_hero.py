"""Tests for article hero images: the `image:` front matter field and how the
article page renders it. These do not require Pillow; tools/make_hero.py is the
only part that needs it."""

import unittest

from content import PostError, parse_post
from helpers import ContentDirectoryTestCase, write_post_file
from test_app import request

HEADER = (
    "---\n"
    "title: A post with a hero\n"
    "category: Articles\n"
    "excerpt: Short description.\n"
    "published: 2026-06-01\n"
    "published_time: 10:00\n"
    "read_time: 3 min\n"
)


def post_text(image_line=""):
    return HEADER + image_line + "---\n\nFirst paragraph.\n"


class HeroFrontMatterTests(unittest.TestCase):
    def test_image_is_optional_and_defaults_to_empty(self):
        post = parse_post(post_text(), "a-post", "a-post.md")
        self.assertEqual(post.image, "")

    def test_a_valid_image_name_is_accepted(self):
        post = parse_post(post_text("image: my-hero.webp\n"), "a-post", "a-post.md")
        self.assertEqual(post.image, "my-hero.webp")

    def test_digits_and_other_extensions_are_accepted(self):
        for name in ("post-2.webp", "cover.jpg", "a.jpeg", "banner.png"):
            with self.subTest(name=name):
                post = parse_post(
                    post_text(f"image: {name}\n"), "a-post", "a-post.md"
                )
                self.assertEqual(post.image, name)

    def test_unsafe_image_values_are_rejected(self):
        for bad in (
            "../secret.webp",  # traversal
            "/etc/passwd",  # absolute path, no extension
            "a/b.webp",  # sub-directory
            "evil.svg",  # disallowed extension
            "Upper.webp",  # uppercase
            "under_score.webp",  # underscore not allowed
            "-leading.webp",  # leading dash
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(PostError):
                    parse_post(post_text(f"image: {bad}\n"), "a-post", "a-post.md")


class HeroRenderTests(ContentDirectoryTestCase):
    def test_article_renders_the_hero_image_when_set(self):
        write_post_file(self.posts_directory, "with-hero", image="my-hero.webp")
        body = request("/blog/with-hero")["body"].decode()
        self.assertIn('class="post-hero"', body)
        self.assertIn('src="/static/img/heroes/my-hero.webp"', body)
        self.assertIn('width="800"', body)
        self.assertIn('height="300"', body)
        self.assertIn('loading="lazy"', body)

    def test_article_has_no_hero_when_image_is_absent(self):
        write_post_file(self.posts_directory, "no-hero")
        body = request("/blog/no-hero")["body"].decode()
        self.assertNotIn("post-hero", body)


if __name__ == "__main__":
    unittest.main()

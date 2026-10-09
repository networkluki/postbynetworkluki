"""Shared fixtures for the test suite."""

import os
import tempfile
import unittest
from pathlib import Path

POST = {
    "title": "A fixture post",
    "category": "Articles",
    "excerpt": "Used by the tests.",
    "published": "2026-05-04",
    "read_time": "2 min",
}


def write_post_file(directory, slug, body="First paragraph.\n\nSecond paragraph.", **fields):
    """Write a post file, overriding any front matter field by keyword."""
    values = {**POST, **fields}
    lines = ["---"]
    lines += [f"{key}: {value}" for key, value in values.items() if value is not None]
    lines.append("---")
    path = Path(directory) / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n\n" + body + "\n", encoding="utf-8")
    return path


class ContentDirectoryTestCase(unittest.TestCase):
    """Point the content loader at a temporary directory for each test."""

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.posts_directory = Path(self.temp_directory.name) / "posts"
        self.posts_directory.mkdir()
        os.environ["BLOG_POSTS_DIR"] = str(self.posts_directory)
        self.addCleanup(os.environ.pop, "BLOG_POSTS_DIR", None)
        self.addCleanup(self.temp_directory.cleanup)

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import build
from helpers import ContentDirectoryTestCase, write_post_file


class BuildTests(ContentDirectoryTestCase):
    def setUp(self):
        super().setUp()
        self.output = Path(self.temp_directory.name) / "public"
        write_post_file(
            self.posts_directory,
            "newest-post",
            title="The newest post",
            published="2026-06-01",
            legacy_slugs="aldsta-slugen",
        )

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = build.main(argv)
        return code, out.getvalue(), err.getvalue()

    def read(self, relative):
        return (self.output / relative).read_text(encoding="utf-8")

    def test_build_writes_every_page(self):
        written = build.build(self.output)
        for relative in (
            ".nojekyll",
            "index.html",
            "404.html",
            "ideas/index.html",
            "blog/index.html",
            "changelog/index.html",
            "blog/newest-post/index.html",
            "static/style.css",
            "CNAME",
        ):
            with self.subTest(relative=relative):
                self.assertIn(relative, written)
                self.assertTrue((self.output / relative).is_file())
        self.assertIn("The newest post", self.read("index.html"))
        self.assertIn("First paragraph.", self.read("blog/newest-post/index.html"))
        self.assertIn("There is nothing here.", self.read("404.html"))
        self.assertIn(".nav-card", self.read("static/style.css"))
        # The pages must link to the fingerprinted copy, and it must exist.
        import app

        name = app.stylesheet_name()
        self.assertIn(f"static/{name}", written)
        self.assertIn(".nav-card", self.read(f"static/{name}"))
        self.assertIn(f'href="/static/{name}"', self.read("index.html"))
        self.assertEqual(self.read("CNAME").strip(), "blog.networkluki.com")

    def test_retired_paths_become_redirect_pages(self):
        build.build(self.output)
        cases = {
            "ideer/index.html": "/ideas",
            "blogg/index.html": "/blog",
            "blog/aldsta-slugen/index.html": "/blog/newest-post",
            "blogg/aldsta-slugen/index.html": "/blog/newest-post",
            "blogg/newest-post/index.html": "/blog/newest-post",
        }
        for relative, target in cases.items():
            with self.subTest(relative=relative):
                page = self.read(relative)
                self.assertIn(f'content="0; url={target}"', page)
                self.assertIn(f'rel="canonical" href="{target}"', page)
                self.assertIn('content="noindex"', page)

    def test_rebuilding_removes_stale_pages(self):
        build.build(self.output)
        stale = self.output / "blog" / "deleted-post" / "index.html"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("old", encoding="utf-8")
        second = build.build(self.output)
        self.assertFalse(stale.exists())
        self.assertEqual(second, build.build(self.output), "build must be repeatable")

    def test_it_refuses_to_delete_a_directory_it_did_not_create(self):
        self.output.mkdir()
        precious = self.output / "important.txt"
        precious.write_text("do not delete", encoding="utf-8")
        code, _, errors = self.run_cli(["--output", str(self.output)])
        self.assertEqual(code, 1)
        self.assertIn("Refusing to delete", errors)
        self.assertTrue(precious.is_file())
        code, _, _ = self.run_cli(["--output", str(self.output), "--force", "--quiet"])
        self.assertEqual(code, 0)
        self.assertFalse(precious.exists())

    def test_it_fails_cleanly_without_posts(self):
        for path in self.posts_directory.glob("*.md"):
            path.unlink()
        code, _, errors = self.run_cli(["--output", str(self.output)])
        self.assertEqual(code, 1)
        self.assertIn("no posts found", errors)

    def test_it_reports_an_invalid_post_file(self):
        (self.posts_directory / "broken.md").write_text("no fence\n", encoding="utf-8")
        code, _, errors = self.run_cli(["--output", str(self.output)])
        self.assertEqual(code, 1)
        self.assertIn("broken.md", errors)

    def test_cli_prints_the_written_files(self):
        code, output, _ = self.run_cli(["--output", str(self.output)])
        self.assertEqual(code, 0)
        self.assertIn("blog/newest-post/index.html", output)
        self.assertIn("file(s) written to", output)


class RepositoryContentTests(unittest.TestCase):
    """Build the real src/posts content, the way the workflow does."""

    def test_the_committed_content_builds(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "public"
            written = build.build(output)
            self.assertIn("index.html", written)
            self.assertTrue(
                any(name.startswith("blog/") for name in written),
                "the committed content must produce post pages",
            )


if __name__ == "__main__":
    unittest.main()

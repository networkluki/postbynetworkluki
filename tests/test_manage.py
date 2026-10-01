import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import manage
from app import POSTS
from test_app import request

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELDS = [
    "--title",
    "Publishing from the shell",
    "--category",
    "Notes",
    "--excerpt",
    "A post created with manage.py instead of the browser form.",
    "--read-time",
    "2 min",
]


class ManageTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database = os.path.join(self.temp_directory.name, "posts.db")
        os.environ["BLOG_DB_PATH"] = self.database
        # Every test runs without a terminal, so the CLI never waits for input.
        stdin = patch("sys.stdin", io.StringIO())
        stdin.start()
        self.addCleanup(stdin.stop)

    def tearDown(self):
        self.temp_directory.cleanup()
        os.environ.pop("BLOG_DB_PATH", None)

    def run_cli(self, argv):
        """Run manage.main, returning (exit code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = manage.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_new_publishes_a_post_that_the_site_serves(self):
        code, output, _ = self.run_cli(
            ["new", *FIELDS, "--content", "First paragraph.\n\nSecond paragraph."]
        )
        self.assertEqual(code, 0)
        self.assertIn("/blog/publishing-from-the-shell", output)
        listing = request("/blog")["body"].decode()
        self.assertIn("Publishing from the shell", listing)
        article = request("/blog/publishing-from-the-shell")
        self.assertEqual(article["status"], "200 OK")
        body = article["body"].decode()
        self.assertIn("First paragraph.", body)
        self.assertIn("Second paragraph.", body)

    def test_new_reads_content_from_a_file(self):
        path = os.path.join(self.temp_directory.name, "body.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("Content from a file with ÅÄÖ.")
        code, _, _ = self.run_cli(["new", *FIELDS, "--content-file", path])
        self.assertEqual(code, 0)
        self.assertIn(
            "Content from a file with ÅÄÖ.",
            request("/blog/publishing-from-the-shell")["body"].decode(),
        )

    def test_new_reads_content_from_standard_input(self):
        with patch("sys.stdin", io.StringIO("Piped content.")):
            code, _, _ = self.run_cli(["new", *FIELDS, "--content-file", "-"])
        self.assertEqual(code, 0)
        self.assertIn(
            "Piped content.",
            request("/blog/publishing-from-the-shell")["body"].decode(),
        )

    def test_new_reports_a_missing_file(self):
        missing = os.path.join(self.temp_directory.name, "absent.txt")
        code, _, errors = self.run_cli(["new", *FIELDS, "--content-file", missing])
        self.assertEqual(code, 1)
        self.assertIn("cannot read", errors)

    def test_new_requires_every_field_without_a_terminal(self):
        code, _, errors = self.run_cli(["new", "--title", "Only a title"])
        self.assertEqual(code, 1)
        self.assertIn("--category is required", errors)

    def test_new_requires_content_without_a_terminal(self):
        code, _, errors = self.run_cli(["new", *FIELDS])
        self.assertEqual(code, 1)
        self.assertIn("content is required", errors)

    def test_new_rejects_content_over_the_limit(self):
        code, _, errors = self.run_cli(["new", *FIELDS, "--content", "x" * 20001])
        self.assertEqual(code, 1)
        self.assertIn("Make sure every field is completed.", errors)

    def test_new_rejects_a_duplicate_and_a_bundled_slug(self):
        self.run_cli(["new", *FIELDS, "--content", "Body."])
        code, _, errors = self.run_cli(["new", *FIELDS, "--content", "Body."])
        self.assertEqual(code, 1)
        self.assertIn("already exists", errors)
        code, _, errors = self.run_cli(
            [
                "new",
                "--title",
                POSTS[0].title,
                "--category",
                "Notes",
                "--excerpt",
                "Clashes with a bundled post.",
                "--read-time",
                "1 min",
                "--content",
                "Body.",
            ]
        )
        self.assertEqual(code, 1)
        self.assertIn("already exists", errors)

    def test_new_rejects_a_title_without_letters_or_numbers(self):
        code, _, errors = self.run_cli(
            [
                "new",
                "--title",
                "###",
                "--category",
                "Notes",
                "--excerpt",
                "No usable slug.",
                "--read-time",
                "1 min",
                "--content",
                "Body.",
            ]
        )
        self.assertEqual(code, 1)
        self.assertIn("must contain letters or numbers", errors)

    def test_new_accepts_a_custom_slug_and_date(self):
        code, _, _ = self.run_cli(
            [
                "new",
                *FIELDS,
                "--content",
                "Body.",
                "--slug",
                "Custom Slug",
                "--published",
                "2026-01-05",
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(request("/blog/custom-slug")["status"], "200 OK")
        _, listing, _ = self.run_cli(["list"])
        self.assertIn("2026-01-05   database  custom-slug", listing)

    def test_published_must_be_an_iso_date(self):
        with self.assertRaises(SystemExit):
            self.run_cli(["new", *FIELDS, "--content", "Body.", "--published", "5 maj"])

    def test_list_and_show_cover_stored_and_bundled_posts(self):
        self.run_cli(["new", *FIELDS, "--content", "Body."])
        _, listing, _ = self.run_cli(["list"])
        self.assertIn("database  publishing-from-the-shell", listing)
        self.assertIn(f"bundled   {POSTS[0].slug}", listing)
        self.assertIn("4 post(s).", listing)
        _, stored, _ = self.run_cli(["show", "publishing-from-the-shell"])
        self.assertIn("Source:   database", stored)
        _, bundled, _ = self.run_cli(["show", POSTS[0].slug])
        self.assertIn("Source:   bundled", bundled)
        code, _, errors = self.run_cli(["show", "nothing-here"])
        self.assertEqual(code, 1)
        self.assertIn("no post with slug", errors)

    def test_delete_removes_a_stored_post_only(self):
        self.run_cli(["new", *FIELDS, "--content", "Body."])
        code, _, errors = self.run_cli(["delete", "publishing-from-the-shell"])
        self.assertEqual(code, 1, "a delete without --yes must not proceed")
        self.assertIn("refusing to delete without --yes", errors)
        code, output, _ = self.run_cli(
            ["delete", "publishing-from-the-shell", "--yes"]
        )
        self.assertEqual(code, 0)
        self.assertIn("Deleted publishing-from-the-shell", output)
        self.assertEqual(request("/blog/publishing-from-the-shell")["status"], "404 Not Found")
        code, _, errors = self.run_cli(["delete", POSTS[0].slug, "--yes"])
        self.assertEqual(code, 1)
        self.assertIn("bundled starter post", errors)
        code, _, errors = self.run_cli(["delete", "never-existed", "--yes"])
        self.assertEqual(code, 1)
        self.assertIn("no stored post", errors)

    def test_script_entry_point_runs(self):
        """Guard the real command line, not just manage.main."""
        environment = {**os.environ, "BLOG_DB_PATH": self.database}
        completed = subprocess.run(
            [
                sys.executable,
                os.path.join(REPOSITORY_ROOT, "manage.py"),
                "new",
                *FIELDS,
                "--content",
                "Body from a subprocess.",
            ],
            capture_output=True,
            text=True,
            cwd=REPOSITORY_ROOT,
            env=environment,
            timeout=60,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("/blog/publishing-from-the-shell", completed.stdout)


if __name__ == "__main__":
    unittest.main()

import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import manage
from helpers import ContentDirectoryTestCase, write_post_file

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
FIELDS = [
    "--title",
    "Publishing from the shell",
    "--category",
    "Articles",
    "--excerpt",
    "A post created with manage.py instead of by hand.",
    "--read-time",
    "2 min",
]


class ManageTests(ContentDirectoryTestCase):
    def setUp(self):
        super().setUp()
        # Every test runs without a terminal, so the CLI never waits for input.
        stdin = patch("sys.stdin", io.StringIO())
        stdin.start()
        self.addCleanup(stdin.stop)

    def run_cli(self, argv):
        """Run manage.main, returning (exit code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = manage.main(argv)
        return code, out.getvalue(), err.getvalue()

    def post_file(self, slug="publishing-from-the-shell"):
        return (self.posts_directory / f"{slug}.md").read_text(encoding="utf-8")

    def test_new_writes_a_parsable_post_file(self):
        code, output, _ = self.run_cli(
            ["new", *FIELDS, "--content", "First paragraph.\n\nSecond paragraph."]
        )
        self.assertEqual(code, 0)
        self.assertIn("publishing-from-the-shell.md", output)
        self.assertIn("python build.py", output)
        text = self.post_file()
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("title: Publishing from the shell", text)
        self.assertIn("First paragraph.\n\nSecond paragraph.", text)
        _, listed, _ = self.run_cli(["list"])
        self.assertIn("publishing-from-the-shell", listed)

    def test_new_reads_content_from_a_file_and_from_stdin(self):
        path = Path(self.temp_directory.name) / "body.txt"
        path.write_text("Content from a file with ÅÄÖ.", encoding="utf-8")
        code, _, _ = self.run_cli(["new", *FIELDS, "--content-file", str(path)])
        self.assertEqual(code, 0)
        self.assertIn("Content from a file with ÅÄÖ.", self.post_file())
        with patch("sys.stdin", io.StringIO("Piped content.")):
            code, _, _ = self.run_cli(
                ["new", *FIELDS, "--slug", "piped", "--content-file", "-"]
            )
        self.assertEqual(code, 0)
        self.assertIn("Piped content.", self.post_file("piped"))

    def test_new_reports_a_missing_file(self):
        missing = Path(self.temp_directory.name) / "absent.txt"
        code, _, errors = self.run_cli(["new", *FIELDS, "--content-file", str(missing)])
        self.assertEqual(code, 1)
        self.assertIn("cannot read", errors)

    def test_new_requires_fields_and_content_without_a_terminal(self):
        code, _, errors = self.run_cli(["new", "--title", "Only a title"])
        self.assertEqual(code, 1)
        self.assertIn("--category is required", errors)
        code, _, errors = self.run_cli(["new", *FIELDS])
        self.assertEqual(code, 1)
        self.assertIn("content is required", errors)

    def test_new_rejects_content_over_the_limit(self):
        code, _, errors = self.run_cli(["new", *FIELDS, "--content", "x" * 20001])
        self.assertEqual(code, 1)
        self.assertIn("longer than 20000 characters", errors)

    def test_new_rejects_a_duplicate_slug_and_never_overwrites(self):
        write_post_file(
            self.posts_directory, "publishing-from-the-shell", body="Original body."
        )
        code, _, errors = self.run_cli(["new", *FIELDS, "--content", "New body."])
        self.assertEqual(code, 1)
        self.assertIn("already exists", errors)
        self.assertIn("Original body.", self.post_file())

    def test_new_rejects_a_title_without_letters_or_numbers(self):
        code, _, errors = self.run_cli(
            [
                "new",
                "--title",
                "###",
                "--category",
                "Articles",
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
        self.assertIn("published: 2026-01-05", self.post_file("custom-slug"))

    def test_published_must_be_an_iso_date(self):
        with self.assertRaises(SystemExit):
            self.run_cli(["new", *FIELDS, "--content", "Body.", "--published", "5 maj"])

    def test_list_and_show(self):
        self.run_cli(["new", *FIELDS, "--content", "Body."])
        _, listing, _ = self.run_cli(["list"])
        self.assertIn("publishing-from-the-shell", listing)
        self.assertIn("1 post(s) in", listing)
        _, shown, _ = self.run_cli(["show", "publishing-from-the-shell"])
        self.assertIn("Title:    Publishing from the shell", shown)
        self.assertIn("publishing-from-the-shell.md", shown)
        code, _, errors = self.run_cli(["show", "nothing-here"])
        self.assertEqual(code, 1)
        self.assertIn("no post with slug", errors)

    def test_list_and_show_report_a_broken_file(self):
        (self.posts_directory / "broken.md").write_text("no fence\n", encoding="utf-8")
        for argv in (["list"], ["show", "broken"]):
            with self.subTest(argv=argv):
                code, _, errors = self.run_cli(argv)
                self.assertEqual(code, 1)
                self.assertIn("broken.md", errors)

    def test_delete_requires_confirmation_and_removes_the_file(self):
        self.run_cli(["new", *FIELDS, "--content", "Body."])
        code, _, errors = self.run_cli(["delete", "publishing-from-the-shell"])
        self.assertEqual(code, 1, "a delete without --yes must not proceed")
        self.assertIn("refusing to delete without --yes", errors)
        self.assertTrue((self.posts_directory / "publishing-from-the-shell.md").exists())
        code, output, _ = self.run_cli(["delete", "publishing-from-the-shell", "--yes"])
        self.assertEqual(code, 0)
        self.assertIn("Deleted", output)
        self.assertFalse(
            (self.posts_directory / "publishing-from-the-shell.md").exists()
        )
        code, _, errors = self.run_cli(["delete", "never-existed", "--yes"])
        self.assertEqual(code, 1)
        self.assertIn("no post file", errors)

    def test_script_entry_point_runs(self):
        """Guard the real command line, not just manage.main."""
        environment = {**os.environ, "BLOG_POSTS_DIR": str(self.posts_directory)}
        completed = subprocess.run(
            [
                sys.executable,
                str(REPOSITORY_ROOT / "manage.py"),
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
        self.assertIn("publishing-from-the-shell.md", completed.stdout)
        self.assertIn("Body from a subprocess.", self.post_file())


if __name__ == "__main__":
    unittest.main()

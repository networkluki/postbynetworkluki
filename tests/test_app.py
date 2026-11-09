import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import application
from helpers import ContentDirectoryTestCase, write_post_file


def request(path, method="GET"):
    response = {}

    def start_response(status, headers):
        response["status"] = status
        response["headers"] = dict(headers)

    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": "0",
        "wsgi.input": io.BytesIO(b""),
    }
    response["body"] = b"".join(application(environ, start_response))
    return response


class BlogTests(ContentDirectoryTestCase):
    def setUp(self):
        super().setUp()
        write_post_file(
            self.posts_directory,
            "newest-post",
            title="The newest post",
            published="2026-06-01",
            legacy_slugs="aldsta-slugen",
        )
        write_post_file(
            self.posts_directory,
            "older-post",
            title="The older post",
            published="2026-02-01",
        )

    def test_main_pages_are_available(self):
        for path in ("/", "/ideas", "/blog", "/changelog"):
            with self.subTest(path=path):
                response = request(path)
                self.assertEqual(response["status"], "200 OK")
                self.assertEqual(
                    response["headers"]["Content-Type"], "text/html; charset=utf-8"
                )

    def test_home_shows_the_latest_post_and_links_to_each_section(self):
        body = request("/")["body"].decode()
        self.assertIn('<html lang="en">', body)
        self.assertIn("The newest post", body)
        self.assertNotIn("The older post", body)
        for path in ("/ideas", "/blog", "/changelog"):
            self.assertIn(f'href="{path}"', body)

    def test_listing_shows_every_post(self):
        body = request("/blog")["body"].decode()
        self.assertIn("The newest post", body)
        self.assertIn("The older post", body)

    def test_stylesheet_is_served_under_both_names(self):
        import app

        for path in ("/static/style.css", app.stylesheet_href()):
            with self.subTest(path=path):
                response = request(path)
                self.assertEqual(response["status"], "200 OK")
                self.assertEqual(
                    response["headers"]["Content-Type"], "text/css; charset=utf-8"
                )
                self.assertIn(b".nav-card", response["body"])

    def test_pages_link_to_the_fingerprinted_stylesheet(self):
        import app

        href = app.stylesheet_href()
        self.assertRegex(href, r"^/static/style\.[0-9a-f]{12}\.css$")
        self.assertIn(f'href="{href}"', request("/")["body"].decode())

    def test_the_fingerprint_follows_the_stylesheet_contents(self):
        """A changed stylesheet must produce a new URL, or caches keep the old one."""
        import shutil

        import app

        before = app.stylesheet_href()
        fake_root = Path(self.temp_directory.name) / "root"
        (fake_root / "static").mkdir(parents=True)
        shutil.copy(app.BASE_DIR / "static" / "style.css", fake_root / "static")
        with (fake_root / "static" / "style.css").open("a", encoding="utf-8") as handle:
            handle.write("\n/* a change */\n")
        with patch.object(app, "BASE_DIR", fake_root):
            self.assertNotEqual(app.stylesheet_href(), before)

    def test_responses_include_security_headers(self):
        headers = request("/")["headers"]
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_every_post_has_a_page(self):
        for slug in ("newest-post", "older-post"):
            with self.subTest(slug=slug):
                response = request(f"/blog/{slug}")
                self.assertEqual(response["status"], "200 OK")
                self.assertIn(b"First paragraph.", response["body"])

    def test_retired_paths_still_work(self):
        for path in ("/ideer", "/blogg"):
            with self.subTest(path=path):
                self.assertEqual(request(path)["status"], "200 OK")
        for path in ("/blog/aldsta-slugen", "/blogg/aldsta-slugen", "/blogg/newest-post"):
            with self.subTest(path=path):
                response = request(path)
                self.assertEqual(response["status"], "200 OK")
                self.assertIn(b"The newest post", response["body"])

    def test_write_methods_are_rejected_and_head_is_supported(self):
        for path in ("/", "/blog", "/static/style.css"):
            with self.subTest(path=path):
                response = request(path, method="POST")
                self.assertEqual(response["status"], "405 Method Not Allowed")
                self.assertEqual(response["headers"]["Allow"], "GET, HEAD")
                head = request(path, method="HEAD")
                self.assertEqual(head["status"], "200 OK")
                self.assertEqual(head["body"], b"")

    def test_post_text_is_escaped(self):
        write_post_file(
            self.posts_directory,
            "injection-attempt",
            title="<script>alert(1)</script>",
            excerpt='" onload="alert(2)',
            body="<img src=x onerror=alert(3)>",
            published="2026-07-01",
        )
        body = request("/blog/injection-attempt")["body"].decode()
        self.assertNotIn("<script>alert(1)</script>", body)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body)
        # The payload may appear as inert escaped text, never as live markup.
        self.assertNotIn("<img src=x", body)
        self.assertIn("&lt;img src=x onerror=alert(3)&gt;", body)
        home = request("/")["body"].decode()
        self.assertNotIn('onload="alert(2)', home)

    def test_rss_feed_is_served(self):
        response = request("/feed.xml")
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(
            response["headers"]["Content-Type"], "application/rss+xml; charset=utf-8"
        )
        body = response["body"].decode()
        self.assertIn("<rss", body)
        self.assertIn("<title>The newest post</title>", body)
        self.assertIn("https://blog.networkluki.com/blog/newest-post", body)
        self.assertIn("<pubDate>", body)
        head = request("/feed.xml", method="HEAD")
        self.assertEqual(head["status"], "200 OK")
        self.assertEqual(head["body"], b"")

    def test_quotes_page_is_served(self):
        response = request("/quotes")
        self.assertEqual(response["status"], "200 OK")
        self.assertIn(b"<h1>Quotes</h1>", response["body"])

    def test_stuffs_page_is_served(self):
        response = request("/stuffs")
        self.assertEqual(response["status"], "200 OK")
        self.assertIn(b"<h1>Stuffs</h1>", response["body"])

    def test_unknown_page_returns_custom_404(self):
        for path in ("/missing", "/blog/missing"):
            with self.subTest(path=path):
                response = request(path)
                self.assertEqual(response["status"], "404 Not Found")
                self.assertIn(b"There is nothing here.", response["body"])


class StuffsTests(unittest.TestCase):
    def _file(self, text):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "stuffs.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def test_parses_url_title_and_description(self):
        from app import read_stuffs

        items = read_stuffs(self._file("https://example.com/ | Example | A thing I built.\n"))
        self.assertEqual(items, [("https://example.com/", "Example", "A thing I built.")])

    def test_title_defaults_to_the_url(self):
        from app import read_stuffs

        items = read_stuffs(self._file("https://example.com/path/\n"))
        self.assertEqual(items, [("https://example.com/path/", "https://example.com/path/", "")])

    def test_description_may_contain_pipes(self):
        from app import read_stuffs

        items = read_stuffs(self._file("https://x.com/ | T | a | b | c\n"))
        self.assertEqual(items, [("https://x.com/", "T", "a | b | c")])

    def test_unsafe_urls_are_skipped(self):
        from app import read_stuffs

        text = (
            "javascript:alert(1) | X | bad\n"
            "data:text/html,x | Y | bad\n"
            "//evil.com | Z | bad\n"
            "/relative/path | W | bad\n"
            "https://ok.com/ | Good | fine\n"
        )
        items = read_stuffs(self._file(text))
        self.assertEqual(items, [("https://ok.com/", "Good", "fine")])

    def test_comments_and_blank_lines_are_ignored(self):
        from app import read_stuffs

        items = read_stuffs(self._file("# a comment\n\nhttps://a.com/ | A | d\n"))
        self.assertEqual(len(items), 1)

    def test_missing_file_gives_no_items(self):
        from app import read_stuffs

        self.assertEqual(read_stuffs(Path("/no/such/stuffs.txt")), [])

    def test_fields_are_escaped_in_the_page(self):
        import app

        crafted = [('https://x.com/"><script>', "<b>title</b>", "<i>desc</i>")]
        with patch("app.read_stuffs", return_value=crafted):
            body = app.stuffs().decode()
        self.assertNotIn("<script>", body)
        self.assertNotIn("<b>title</b>", body)
        self.assertNotIn("<i>desc</i>", body)
        self.assertIn("&lt;b&gt;title&lt;/b&gt;", body)
        # The quote in the url is escaped so it cannot break out of the attribute.
        self.assertIn("https://x.com/&quot;&gt;&lt;script&gt;", body)


if __name__ == "__main__":
    unittest.main()

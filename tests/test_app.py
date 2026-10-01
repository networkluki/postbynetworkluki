import io
import unittest

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

    def test_stylesheet_is_served(self):
        response = request("/static/style.css")
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(response["headers"]["Content-Type"], "text/css; charset=utf-8")
        self.assertIn(b".nav-card", response["body"])

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

    def test_unknown_page_returns_custom_404(self):
        for path in ("/missing", "/blog/missing"):
            with self.subTest(path=path):
                response = request(path)
                self.assertEqual(response["status"], "404 Not Found")
                self.assertIn(b"There is nothing here.", response["body"])


if __name__ == "__main__":
    unittest.main()

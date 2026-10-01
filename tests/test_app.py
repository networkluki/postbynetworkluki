import unittest
import base64
import io
import os
import tempfile
from urllib.parse import urlencode

from app import POSTS, application, csrf_token


def request(path, method="GET", data=None, authorized=False):
    response = {}

    def start_response(status, headers):
        response["status"] = status
        response["headers"] = dict(headers)

    payload = urlencode(data or {}).encode()
    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(payload)),
        "wsgi.input": io.BytesIO(payload),
    }
    if authorized:
        credentials = base64.b64encode(b"editor:test-password").decode()
        environ["HTTP_AUTHORIZATION"] = f"Basic {credentials}"
    response["body"] = b"".join(application(environ, start_response))
    return response


class BlogTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        os.environ["BLOG_DB_PATH"] = os.path.join(self.temp_directory.name, "posts.db")
        os.environ["BLOG_ADMIN_PASSWORD"] = "test-password"

    def tearDown(self):
        self.temp_directory.cleanup()
        os.environ.pop("BLOG_DB_PATH", None)
        os.environ.pop("BLOG_ADMIN_PASSWORD", None)

    def test_main_pages_are_available(self):
        for path in ("/", "/ideas", "/blog", "/changelog"):
            with self.subTest(path=path):
                response = request(path)
                self.assertEqual(response["status"], "200 OK")
                self.assertEqual(response["headers"]["Content-Type"], "text/html; charset=utf-8")

    def test_home_links_to_each_section(self):
        body = request("/")["body"].decode()
        self.assertIn('<html lang="en">', body)
        self.assertIn("Thoughts worth", body)
        for path in ("/ideas", "/blog", "/changelog"):
            self.assertIn(f'href="{path}"', body)

    def test_stylesheet_is_served(self):
        response = request("/static/style.css")
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(response["headers"]["Content-Type"], "text/css; charset=utf-8")
        self.assertIn(b".cards", response["body"])

    def test_every_post_has_a_page(self):
        for post in POSTS:
            with self.subTest(slug=post.slug):
                response = request(f"/blog/{post.slug}")
                self.assertEqual(response["status"], "200 OK")
                self.assertIn(post.title, response["body"].decode())

    def test_previous_swedish_urls_still_work(self):
        self.assertEqual(request("/ideer")["status"], "200 OK")
        self.assertEqual(request("/blogg")["status"], "200 OK")
        response = request("/blogg/bygg-mindre-lanserar-snabbare")
        self.assertEqual(response["status"], "200 OK")
        self.assertIn("Build less. Launch faster.", response["body"].decode())

    def test_unknown_page_returns_custom_404(self):
        response = request("/does-not-exist")
        self.assertEqual(response["status"], "404 Not Found")
        self.assertIn("There is nothing here", response["body"].decode())

    def test_admin_requires_authentication(self):
        response = request("/admin/new")
        self.assertEqual(response["status"], "401 Unauthorized")
        self.assertIn("WWW-Authenticate", response["headers"])

    def test_admin_can_publish_unicode_post(self):
        response = request(
            "/admin/new",
            method="POST",
            authorized=True,
            data={
                "csrf_token": csrf_token(),
                "title": "A better café idea",
                "category": "Lessons",
                "excerpt": "A short introduction.",
                "content": "The first paragraph.\n\nThe second paragraph.",
                "read_time": "2 min",
            },
        )
        self.assertEqual(response["status"], "303 See Other")
        self.assertEqual(response["headers"]["Location"], "/blog/a-better-cafe-idea")
        article = request("/blog/a-better-cafe-idea")
        self.assertEqual(article["status"], "200 OK")
        self.assertIn("A better café idea", article["body"].decode())

    def test_admin_rejects_missing_and_invalid_csrf_data(self):
        missing = request(
            "/admin/new", method="POST", authorized=True, data={"csrf_token": csrf_token()}
        )
        invalid_csrf = request(
            "/admin/new", method="POST", authorized=True, data={"csrf_token": "wrong"}
        )
        self.assertEqual(missing["status"], "400 Bad Request")
        self.assertEqual(invalid_csrf["status"], "403 Forbidden")


if __name__ == "__main__":
    unittest.main()

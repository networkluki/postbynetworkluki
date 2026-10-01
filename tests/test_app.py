import unittest

from app import POSTS, application


def request(path):
    response = {}

    def start_response(status, headers):
        response["status"] = status
        response["headers"] = dict(headers)

    response["body"] = b"".join(application({"PATH_INFO": path}, start_response))
    return response


class BlogTests(unittest.TestCase):
    def test_main_pages_are_available(self):
        for path in ("/", "/ideer", "/blogg", "/changelog"):
            with self.subTest(path=path):
                response = request(path)
                self.assertEqual(response["status"], "200 OK")
                self.assertEqual(response["headers"]["Content-Type"], "text/html; charset=utf-8")

    def test_home_links_to_each_section(self):
        body = request("/")["body"].decode()
        for path in ("/ideer", "/blogg", "/changelog"):
            self.assertIn(f'href="{path}"', body)

    def test_stylesheet_is_served(self):
        response = request("/static/style.css")
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(response["headers"]["Content-Type"], "text/css; charset=utf-8")
        self.assertIn(b".cards", response["body"])

    def test_every_post_has_a_page(self):
        for post in POSTS:
            with self.subTest(slug=post.slug):
                response = request(f"/blogg/{post.slug}")
                self.assertEqual(response["status"], "200 OK")
                self.assertIn(post.title, response["body"].decode())

    def test_unknown_page_returns_custom_404(self):
        response = request("/finns-inte")
        self.assertEqual(response["status"], "404 Not Found")
        self.assertIn("Här fanns ingenting", response["body"].decode())


if __name__ == "__main__":
    unittest.main()

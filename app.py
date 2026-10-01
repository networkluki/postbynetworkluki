"""A tiny dependency-free WSGI blog for Post by networkluki."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
import re
import sqlite3
import unicodedata
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path
from typing import Iterable, Mapping
from urllib.parse import parse_qs, unquote
from wsgiref.simple_server import make_server


BASE_DIR = Path(__file__).parent
MAX_FORM_SIZE = 64 * 1024
POST_FIELD_LIMITS = {
    "title": 120,
    "category": 50,
    "excerpt": 300,
    "content": 20000,
    "read_time": 20,
}
SECURITY_HEADERS = [
    (
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; base-uri 'none'; form-action 'self'; "
        "frame-ancestors 'none'",
    ),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("X-Content-Type-Options", "nosniff"),
]


@dataclass(frozen=True)
class Post:
    slug: str
    category: str
    title: str
    excerpt: str
    published: date
    read_time: str
    content: tuple[str, ...]


POSTS = (
    Post(
        "build-less-launch-faster",
        "Workflow",
        "Build less. Launch faster.",
        "Three simple questions that help you find the smallest version that actually creates value.",
        date(2026, 9, 24),
        "4 min",
        (
            "A good first version does not need to solve everything. It needs to solve one clear problem for one specific person.",
            "Start by asking what must be true for the idea to work. Then choose the smallest experiment that can give you an honest answer.",
            "Once something is out in the world, you get feedback from reality. That is usually more valuable than another week of assumptions.",
        ),
    ),
    Post(
        "a-calmer-digital-experience",
        "Design",
        "A calmer digital experience",
        "How we use hierarchy, space, and constraints to make content easier to understand.",
        date(2026, 9, 12),
        "6 min",
        (
            "Good design helps visitors understand what matters without making them think about the interface itself.",
            "Clear typography, generous space, and a limited palette create rhythm. Constraints are not an obstacle—they give the content a stage.",
            "Look at the page from a distance. If the headings, groups, and next step are still visible, the hierarchy is starting to work.",
        ),
    ),
    Post(
        "notes-from-a-fresh-start",
        "Behind the scenes",
        "Notes from a fresh start",
        "Why Post has a new home and what we want to fill it with next.",
        date(2026, 8, 29),
        "3 min",
        (
            "Post is our place for things worth saving: ideas in progress, lessons from our work, and small changes along the way.",
            "We would rather publish useful notes often than perfect manifestos rarely. The format can grow alongside the content.",
        ),
    ),
)

LEGACY_SLUGS = {
    "bygg-mindre-lanserar-snabbare": "build-less-launch-faster",
    "ett-lugnare-digitalt-flode": "a-calmer-digital-experience",
    "anteckningar-fran-en-omstart": "notes-from-a-fresh-start",
}


def database_path() -> Path:
    """Return the configurable path used for posts created in the admin UI."""
    return Path(os.environ.get("BLOG_DB_PATH", BASE_DIR / "data" / "posts.db"))


def connect_database() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.execute(
        """CREATE TABLE IF NOT EXISTS posts (
        slug TEXT PRIMARY KEY, category TEXT NOT NULL, title TEXT NOT NULL,
        excerpt TEXT NOT NULL, published TEXT NOT NULL, read_time TEXT NOT NULL,
        content TEXT NOT NULL
        )"""
    )
    return connection


def all_posts() -> tuple[Post, ...]:
    """Combine posts created on the site with the bundled starter posts."""
    with closing(connect_database()) as connection:
        rows = connection.execute(
            "SELECT slug, category, title, excerpt, published, read_time, content FROM posts"
        ).fetchall()
    created = tuple(
        Post(
            row[0],
            row[1],
            row[2],
            row[3],
            date.fromisoformat(row[4]),
            row[5],
            tuple(row[6].split("\n\n")),
        )
        for row in rows
    )
    return tuple(sorted(created + POSTS, key=lambda post: post.published, reverse=True))


def slugify(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug[:80]


def is_admin(environ: dict) -> bool:
    password = os.environ.get("BLOG_ADMIN_PASSWORD")
    authorization = environ.get("HTTP_AUTHORIZATION", "")
    if not password or not authorization.startswith("Basic "):
        return False
    try:
        supplied = (
            base64.b64decode(authorization[6:], validate=True)
            .decode("utf-8")
            .partition(":")[2]
        )
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return False
    return hmac.compare_digest(supplied, password)


def csrf_token() -> str:
    password = os.environ.get("BLOG_ADMIN_PASSWORD", "")
    return hmac.new(password.encode(), b"post-admin-form", hashlib.sha256).hexdigest()


def page(
    title: str,
    content: str,
    *,
    description: str = "Ideas, articles, and updates from networkluki.",
) -> bytes:
    template = (BASE_DIR / "templates" / "base.html").read_text(encoding="utf-8")
    html = (
        template.replace("{{ title }}", escape(title))
        .replace("{{ description }}", escape(description, quote=True))
        .replace("{{ content }}", content)
    )
    return html.encode("utf-8")


def post_card(post: Post) -> str:
    return f"""
      <article class="post-card">
        <p class="eyebrow">{escape(post.category)}</p>
        <h2><a href="/blog/{escape(post.slug)}">{escape(post.title)}</a></h2>
        <p>{escape(post.excerpt)}</p>
        <div class="post-meta"><time datetime="{post.published.isoformat()}">{post.published.strftime("%Y-%m-%d")}</time><span>{escape(post.read_time)} read</span></div>
      </article>"""


def home() -> bytes:
    latest = all_posts()[0]
    content = f"""
<section class="hero">
  <p class="kicker">POST BY NETWORKLUKI</p>
  <h1>Thoughts worth<br><em>taking further.</em></h1>
  <p class="intro">A collection of ideas, stories, and small improvements from our corner of the internet.</p>
</section>
<div class="cards" aria-label="Explore the content">
  <a href="/ideas" class="nav-card ideas"><div class="icon" aria-hidden="true">&#128161;</div><div class="body"><h3>Ideas &amp; tips</h3><p>Thoughts and suggestions</p></div><div class="arrow" aria-hidden="true">&rarr;</div></a>
  <a href="/blog" class="nav-card blog"><div class="icon" aria-hidden="true">&#128221;</div><div class="body"><h3>Blog</h3><p>Posts and articles</p></div><div class="arrow" aria-hidden="true">&rarr;</div></a>
  <a href="/changelog" class="nav-card changelog"><div class="icon" aria-hidden="true">&#128203;</div><div class="body"><h3>Changelog</h3><p>Changes and updates</p></div><div class="arrow" aria-hidden="true">&rarr;</div></a>
</div>
<section class="featured">
  <div><p class="eyebrow">Latest post · {latest.published.strftime("%Y-%m-%d")}</p><h2>{escape(latest.title)}</h2><p>{escape(latest.excerpt)}</p></div>
  <a class="text-link" href="/blog/{latest.slug}">Read the post <span aria-hidden="true">↗</span></a>
</section>"""
    return page("Post by networkluki", content)


def listing() -> bytes:
    cards = "".join(post_card(post) for post in all_posts())
    return page(
        "Blog · Post",
        f'<header class="page-heading"><p class="kicker">BLOG</p><h1>Posts &amp; articles</h1><p>Thoughts, methods, and things we learn along the way.</p></header><section class="post-grid">{cards}</section>',
    )


def ideas() -> bytes:
    items = (
        (
            "01",
            "Make room for boring ideas",
            "The obvious is often a better starting point than the original. Write it down anyway.",
        ),
        (
            "02",
            "Change perspective for ten minutes",
            "Describe the problem as a new visitor, an expert, and someone with very little time.",
        ),
        (
            "03",
            "End with the next step",
            "A note becomes more useful when it tells you what you can actually do now.",
        ),
    )
    rows = "".join(
        f'<article class="idea-row"><span>{n}</span><div><h2>{escape(t)}</h2><p>{escape(p)}</p></div></article>'
        for n, t, p in items
    )
    return page(
        "Ideas & tips · Post",
        f'<header class="page-heading"><p class="kicker">IDEAS &amp; TIPS</p><h1>Small things to try</h1><p>Short prompts for better digital work.</p></header><section class="idea-list">{rows}</section>',
    )


def changelog() -> bytes:
    entries = (
        (
            "2026-10-01",
            "Post gets a home of its own",
            "We launched a new home page, blog, idea collection, and changelog.",
        ),
        (
            "2026-09-24",
            "The first article",
            "We published our first longer piece about building less and learning faster.",
        ),
        (
            "2026-08-29",
            "The work begins",
            "The first sketches, words, and technical decisions fell into place.",
        ),
    )
    rows = "".join(
        f'<article class="change-row"><time datetime="{d}">{d}</time><div><h2>{escape(t)}</h2><p>{escape(p)}</p></div></article>'
        for d, t, p in entries
    )
    return page(
        "Changelog · Post",
        f'<header class="page-heading"><p class="kicker">CHANGELOG</p><h1>What is new?</h1><p>A straightforward record of how this place evolves.</p></header><section class="change-list">{rows}</section>',
    )


def article(post: Post) -> bytes:
    paragraphs = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in post.content)
    content = f'<article class="article"><a class="back" href="/blog">← All posts</a><p class="eyebrow">{escape(post.category)}</p><h1>{escape(post.title)}</h1><div class="post-meta"><time datetime="{post.published.isoformat()}">{post.published.strftime("%Y-%m-%d")}</time><span>{escape(post.read_time)} read</span></div><p class="lead">{escape(post.excerpt)}</p><div class="prose">{paragraphs}</div></article>'
    return page(f"{post.title} · Post", content, description=post.excerpt)


class PostError(Exception):
    """A post could not be stored. Carries the matching HTTP status for the web UI."""

    def __init__(self, message: str, status: str = "400 Bad Request") -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def validate_post_fields(values: Mapping[str, str]) -> dict[str, str]:
    """Return the trimmed, length-checked fields or raise PostError."""
    cleaned: dict[str, str] = {}
    for field, limit in POST_FIELD_LIMITS.items():
        value = (values.get(field) or "").strip()
        if not value or len(value) > limit:
            raise PostError("Make sure every field is completed.")
        cleaned[field] = value
    return cleaned


def store_post(
    values: Mapping[str, str],
    *,
    published: date | None = None,
    slug: str | None = None,
) -> Post:
    """Validate and insert a post, returning the stored post.

    Raises PostError for invalid input, an unusable title or a duplicate slug.
    This is the single write path: the admin form and manage.py both use it.
    """
    cleaned = validate_post_fields(values)
    slug = slugify(slug or cleaned["title"])
    if not slug:
        raise PostError("The title must contain letters or numbers.")
    if any(post.slug == slug for post in POSTS):
        raise PostError("A post with that title already exists.", "409 Conflict")
    published = published or date.today()
    try:
        with closing(connect_database()) as connection, connection:
            connection.execute(
                "INSERT INTO posts VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    slug,
                    cleaned["category"],
                    cleaned["title"],
                    cleaned["excerpt"],
                    published.isoformat(),
                    cleaned["read_time"],
                    cleaned["content"],
                ),
            )
    except sqlite3.IntegrityError:
        raise PostError(
            "A post with that title already exists.", "409 Conflict"
        ) from None
    return Post(
        slug,
        cleaned["category"],
        cleaned["title"],
        cleaned["excerpt"],
        published,
        cleaned["read_time"],
        tuple(cleaned["content"].split("\n\n")),
    )


def delete_post(slug: str) -> bool:
    """Remove a stored post. Returns False when no stored post has that slug.

    Bundled starter posts live in POSTS and cannot be deleted from the database.
    """
    with closing(connect_database()) as connection, connection:
        cursor = connection.execute("DELETE FROM posts WHERE slug = ?", (slug,))
        return cursor.rowcount > 0


def admin_form(error: str = "") -> bytes:
    alert = f'<p class="form-error" role="alert">{escape(error)}</p>' if error else ""
    content = f'''<section class="admin"><p class="kicker">ADMIN</p><h1>New blog post</h1>
    <p>Publish a post directly on blog.networkluki.com. All fields are required.</p>{alert}
    <form method="post" action="/admin/new">
      <input type="hidden" name="csrf_token" value="{csrf_token()}">
      <label>Title<input name="title" maxlength="120" required></label>
      <label>Category<input name="category" maxlength="50" required></label>
      <label>Excerpt<textarea name="excerpt" maxlength="300" rows="3" required></textarea></label>
      <label>Content<textarea name="content" maxlength="20000" rows="14" required></textarea><small>Separate paragraphs with a blank line.</small></label>
      <label>Reading time<input name="read_time" maxlength="20" value="5 min" required></label>
      <button type="submit">Publish post</button>
    </form></section>'''
    return page("New post · Post", content)


def read_form(environ: dict) -> dict[str, str] | None:
    content_type = environ.get("CONTENT_TYPE", "").partition(";")[0].strip().lower()
    if content_type != "application/x-www-form-urlencoded":
        return None
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        return None
    if length <= 0 or length > MAX_FORM_SIZE:
        return None
    try:
        payload = environ["wsgi.input"].read(length).decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        return None
    values = parse_qs(payload, keep_blank_values=True)
    return {key: items[0].strip() for key, items in values.items()}


def create_post(environ: dict) -> tuple[bytes, str, list[tuple[str, str]]]:
    form = read_form(environ)
    if not form or not hmac.compare_digest(form.get("csrf_token", ""), csrf_token()):
        return (
            admin_form("The form has expired. Please try again."),
            "403 Forbidden",
            [],
        )
    try:
        post = store_post(form)
    except PostError as error:
        return admin_form(error.message), error.status, []
    return b"", "303 See Other", [("Location", f"/blog/{post.slug}")]


def not_found() -> bytes:
    return page(
        "Page not found · Post",
        '<section class="empty"><p class="kicker">404</p><h1>There is nothing here.</h1><p>The page may have moved or may never have existed.</p><a class="button" href="/">Back to the home page</a></section>',
    )


def application(environ: dict, start_response) -> Iterable[bytes]:
    """Serve the site through the WSGI interface."""
    path = unquote(environ.get("PATH_INFO", "/")).rstrip("/") or "/"
    method = environ.get("REQUEST_METHOD", "GET").upper()
    if path == "/static/style.css":
        if method not in ("GET", "HEAD"):
            start_response(
                "405 Method Not Allowed", [("Allow", "GET, HEAD"), *SECURITY_HEADERS]
            )
            return [b""]
        body = (BASE_DIR / "static" / "style.css").read_bytes()
        start_response(
            "200 OK",
            [
                ("Content-Type", "text/css; charset=utf-8"),
                ("Content-Length", str(len(body))),
                *SECURITY_HEADERS,
            ],
        )
        return [b"" if method == "HEAD" else body]
    if path in ("/admin/new", "/admin/nytt"):
        if not is_admin(environ):
            body = page(
                "Sign-in required · Post",
                '<section class="empty"><p class="kicker">ADMIN</p><h1>Sign-in required.</h1><p>Use the blog administrator password.</p></section>',
            )
            headers = [
                ("WWW-Authenticate", 'Basic realm="Post admin", charset="UTF-8"')
            ]
            status = "401 Unauthorized"
        elif method == "GET":
            body, status, headers = admin_form(), "200 OK", []
        elif method == "POST":
            body, status, headers = create_post(environ)
        else:
            body, status, headers = (
                b"",
                "405 Method Not Allowed",
                [("Allow", "GET, POST")],
            )
        headers.extend(
            [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
                *SECURITY_HEADERS,
            ]
        )
        start_response(status, headers)
        return [body]
    if method not in ("GET", "HEAD"):
        start_response(
            "405 Method Not Allowed", [("Allow", "GET, HEAD"), *SECURITY_HEADERS]
        )
        return [b""]
    routes = {
        "/": home,
        "/ideas": ideas,
        "/blog": listing,
        "/changelog": changelog,
        "/ideer": ideas,
        "/blogg": listing,
    }
    status = "200 OK"
    if path in routes:
        body = routes[path]()
    elif path.startswith(("/blog/", "/blogg/")):
        slug = path.split("/", 2)[2]
        slug = LEGACY_SLUGS.get(slug, slug)
        match = next((post for post in all_posts() if post.slug == slug), None)
        if match:
            body = article(match)
        else:
            status, body = "404 Not Found", not_found()
    else:
        status, body = "404 Not Found", not_found()
    start_response(
        status,
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(body))),
            *SECURITY_HEADERS,
        ],
    )
    return [b"" if method == "HEAD" else body]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Post is running on port {port}")
    with make_server("0.0.0.0", port, application) as server:
        server.serve_forever()

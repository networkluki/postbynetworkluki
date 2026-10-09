"""A dependency-free renderer for Post by networkluki.

The same page functions serve two purposes:

* ``python build.py`` renders every page to static HTML in ``public/``, which is
  what GitHub Pages publishes.
* ``python app.py`` starts a local preview server on the identical output, so a
  change can be checked before it is committed.

Posts live in ``src/posts`` as text files; see ``content.py``.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote
from wsgiref.simple_server import make_server

from content import (
    Post,
    all_posts,
    legacy_slug_map,
    published_display,
    published_machine,
)

BASE_DIR = Path(__file__).resolve().parent
# The public origin, used for absolute links in the RSS feed.
SITE_URL = "https://blog.networkluki.com"
SECURITY_HEADERS = [
    (
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; "
        "base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
    ),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("X-Content-Type-Options", "nosniff"),
]
STATIC_TYPES = {"css": "text/css; charset=utf-8", "js": "text/javascript; charset=utf-8"}
# Retired paths kept as aliases so older links do not break.
SECTION_ALIASES = {"/ideer": "/ideas", "/blogg": "/blog"}


def stylesheet_path() -> Path:
    return BASE_DIR / "static" / "style.css"


def stylesheet_name() -> str:
    """The stylesheet's file name, including a hash of its contents.

    GitHub Pages serves static files with a four hour Cache-Control, so a
    stylesheet at a fixed URL keeps reaching returning visitors long after it
    changed. Putting the content hash in the name means a changed stylesheet is
    a new URL that no cache can have, while an unchanged one stays cacheable.
    """
    digest = hashlib.sha256(stylesheet_path().read_bytes()).hexdigest()[:12]
    return f"style.{digest}.css"


def stylesheet_href() -> str:
    return f"/static/{stylesheet_name()}"


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
        .replace("{{ stylesheet }}", stylesheet_href())
        .replace("{{ content }}", content)
    )
    return html.encode("utf-8")


def post_card(post: Post) -> str:
    cat_class = "cat-" + post.category.lower()
    return f"""
      <article class="post-card">
        <p class="eyebrow {cat_class}">{escape(post.category)}</p>
        <h2><a href="/blog/{escape(post.slug)}">{escape(post.title)}</a></h2>
        <p>{escape(post.excerpt)}</p>
        <div class="post-meta"><time datetime="{published_machine(post)}">{escape(published_display(post))}</time><span>{escape(post.read_time)} read</span></div>
      </article>"""


def section_listing(category: str, kicker: str, heading: str, intro: str) -> bytes:
    """List every post in one category, or an empty-state message."""
    selected = [post for post in all_posts() if post.category == category]
    if selected:
        cards = "".join(post_card(post) for post in selected)
        body = f'<section class="post-grid">{cards}</section>'
    else:
        body = '<p class="post-empty">No posts in this section yet.</p>'
    return page(
        f"{heading} · Post",
        f'<header class="page-heading"><p class="kicker">{escape(kicker)}</p>'
        f"<h1>{escape(heading)}</h1><p>{escape(intro)}</p></header>{body}",
    )


def home() -> bytes:
    latest = all_posts()[0]
    content = f"""
<section class="hero">
  <p class="kicker">POST BY NETWORKLUKI</p>
  <h1>Thoughts worth<br><em>taking further.</em></h1>
  <p class="intro">Articles, changelog entries, and ideas from networkluki.</p>
</section>
<div class="cards" aria-label="Explore the content">
  <a href="/blog" class="nav-card articles"><div class="icon" aria-hidden="true">&#128221;</div><div class="body"><h3>Articles</h3><p>Posts and write-ups</p></div><div class="arrow" aria-hidden="true">&rarr;</div></a>
  <a href="/changelog" class="nav-card changelog"><div class="icon" aria-hidden="true">&#128203;</div><div class="body"><h3>Changelog</h3><p>Changes and updates</p></div><div class="arrow" aria-hidden="true">&rarr;</div></a>
  <a href="/ideas" class="nav-card ideas"><div class="icon" aria-hidden="true">&#128161;</div><div class="body"><h3>Ideas</h3><p>Thoughts and sparks</p></div><div class="arrow" aria-hidden="true">&rarr;</div></a>
</div>
<section class="featured">
  <div><p class="eyebrow">Latest · {escape(published_display(latest))}</p><h2>{escape(latest.title)}</h2><p>{escape(latest.excerpt)}</p></div>
  <a class="text-link" href="/blog/{latest.slug}">Read the post <span aria-hidden="true">↗</span></a>
</section>"""
    return page("Post by networkluki", content)


def listing() -> bytes:
    """The /blog section lists every post in the Articles category."""
    return section_listing(
        "Articles",
        "ARTICLES",
        "Posts & articles",
        "Thoughts, methods, and things we learn along the way.",
    )


def ideas() -> bytes:
    return section_listing(
        "Ideas",
        "IDEAS",
        "Ideas & tips",
        "Short prompts and sparks worth exploring.",
    )


def changelog() -> bytes:
    return section_listing(
        "Changelog",
        "CHANGELOG",
        "What is new?",
        "A straightforward record of how this place evolves.",
    )


def article(post: Post) -> bytes:
    """Render one post using the same heading block as the section pages."""
    paragraphs = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in post.content)
    cat_class = "cat-" + post.category.lower()
    content = (
        '<article class="article">'
        f'<header class="page-heading"><p class="kicker {cat_class}">{escape(post.category)}</p>'
        f"<h1>{escape(post.title)}</h1><p>{escape(post.excerpt)}</p></header>"
        f'<div class="post-meta"><time datetime="{published_machine(post)}">'
        f"{escape(published_display(post))}</time>"
        f"<span>{escape(post.read_time)} read</span></div>"
        f'<div class="prose">{paragraphs}</div>'
        '<a class="back" href="/blog">← All posts</a>'
        "</article>"
    )
    return page(f"{post.title} · Post", content, description=post.excerpt)


def not_found() -> bytes:
    return page(
        "Page not found · Post",
        '<section class="empty"><p class="kicker">404</p><h1>There is nothing here.</h1><p>The page may have moved or may never have existed.</p><a class="button" href="/">Back to the home page</a></section>',
    )


DEFAULT_QUOTE_AUTHOR = "Luki Hackwell"


def read_quotes() -> list[tuple[str, str]]:
    """Read src/quotes.txt: one quote per line, optional '| author'."""
    path = BASE_DIR / "src" / "quotes.txt"
    if not path.is_file():
        return []
    quotes_list: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            text, author = line.rsplit("|", 1)
            text, author = text.strip(), (author.strip() or DEFAULT_QUOTE_AUTHOR)
        else:
            text, author = line, DEFAULT_QUOTE_AUTHOR
        if text:
            quotes_list.append((text, author))
    return quotes_list


def quotes() -> bytes:
    items = read_quotes()
    if items:
        blocks = "".join(
            f'<figure class="quote"><blockquote>{escape(text)}</blockquote>'
            f"<figcaption>— {escape(author)}</figcaption></figure>"
            for text, author in items
        )
        body = f'<section class="quote-list">{blocks}</section>'
    else:
        body = '<p class="post-empty">No quotes yet.</p>'
    return page(
        "Quotes · Post",
        '<header class="page-heading"><p class="kicker">QUOTES</p>'
        "<h1>Quotes</h1><p>Lines worth keeping.</p></header>" + body,
    )


def _rfc822(post: Post) -> str:
    """A post's publish moment as an RFC 822 date, in UTC (for <pubDate>)."""
    hour, minute = (post.published_time.split(":") + ["0"])[:2] if post.published_time else ("0", "0")
    moment = datetime(
        post.published.year,
        post.published.month,
        post.published.day,
        int(hour),
        int(minute),
        tzinfo=timezone.utc,
    )
    return format_datetime(moment)


def feed() -> bytes:
    """An RSS 2.0 feed of every post, newest first."""
    posts = all_posts()
    items = []
    for post in posts:
        url = f"{SITE_URL}/blog/{post.slug}"
        items.append(
            "<item>"
            f"<title>{escape(post.title)}</title>"
            f"<link>{escape(url)}</link>"
            f'<guid isPermaLink="true">{escape(url)}</guid>'
            f"<category>{escape(post.category)}</category>"
            f"<pubDate>{_rfc822(post)}</pubDate>"
            f"<description>{escape(post.excerpt)}</description>"
            "</item>"
        )
    # Use the newest post's date so the feed is reproducible across builds.
    last_build = _rfc822(posts[0]) if posts else format_datetime(datetime.now(timezone.utc))
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "<channel>"
        "<title>Post by networkluki</title>"
        f"<link>{SITE_URL}/</link>"
        "<description>Articles, changelog entries, and ideas from networkluki.</description>"
        "<language>en</language>"
        f'<atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>'
        f"<lastBuildDate>{last_build}</lastBuildDate>"
        + "".join(items)
        + "</channel>\n</rss>\n"
    )
    return xml.encode("utf-8")

def application(environ: dict, start_response) -> Iterable[bytes]:
    """Serve the rendered pages over WSGI. Read-only: GET and HEAD alone."""
    path = unquote(environ.get("PATH_INFO", "/")).rstrip("/") or "/"
    method = environ.get("REQUEST_METHOD", "GET").upper()
    if method not in ("GET", "HEAD"):
        start_response(
            "405 Method Not Allowed", [("Allow", "GET, HEAD"), *SECURITY_HEADERS]
        )
        return [b""]
    if path.startswith("/static/"):
        name = "style.css" if path == stylesheet_href() else path[len("/static/") :]
        static_root = (BASE_DIR / "static").resolve()
        target = (static_root / name).resolve()
        if static_root in target.parents and target.is_file():
            body = target.read_bytes()
            start_response(
                "200 OK",
                [
                    (
                        "Content-Type",
                        STATIC_TYPES.get(target.suffix.lstrip("."), "application/octet-stream"),
                    ),
                    ("Content-Length", str(len(body))),
                    *SECURITY_HEADERS,
                ],
            )
            return [b"" if method == "HEAD" else body]
        body = not_found()
        start_response(
            "404 Not Found",
            [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(body))),
                *SECURITY_HEADERS,
            ],
        )
        return [b"" if method == "HEAD" else body]

    if path == "/feed.xml":
        body = feed()
        start_response(
            "200 OK",
            [
                ("Content-Type", "application/rss+xml; charset=utf-8"),
                ("Content-Length", str(len(body))),
                *SECURITY_HEADERS,
            ],
        )
        return [b"" if method == "HEAD" else body]

    path = SECTION_ALIASES.get(path, path)
    routes = {
        "/": home,
        "/ideas": ideas,
        "/blog": listing,
        "/changelog": changelog,
        "/quotes": quotes,
    }
    status = "200 OK"
    if path in routes:
        body = routes[path]()
    elif path.startswith(("/blog/", "/blogg/")):
        posts = all_posts()
        slug = path.split("/", 2)[2]
        slug = legacy_slug_map(posts).get(slug, slug)
        match = next((post for post in posts if post.slug == slug), None)
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
    print(f"Preview server on http://127.0.0.1:{port} (Ctrl-C to stop)")
    print("This is for local checking. Production is the static build in public/.")
    with make_server("127.0.0.1", port, application) as server:
        server.serve_forever()

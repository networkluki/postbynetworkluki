"""A dependency-free renderer for Post by networkluki.

The same page functions serve two purposes:

* ``python build.py`` renders every page to static HTML in ``public/``, which is
  what GitHub Pages publishes.
* ``python app.py`` starts a local preview server on the identical output, so a
  change can be checked before it is committed.

Posts live in ``src/posts`` as text files; see ``content.py``.
"""

from __future__ import annotations

import os
from html import escape
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote
from wsgiref.simple_server import make_server

from content import Post, all_posts, legacy_slug_map

BASE_DIR = Path(__file__).resolve().parent
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
# Retired paths kept as aliases so older links do not break.
SECTION_ALIASES = {"/ideer": "/ideas", "/blogg": "/blog"}


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
    """Render one post using the same heading block as the section pages."""
    paragraphs = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in post.content)
    content = (
        '<article class="article">'
        f'<header class="page-heading"><p class="kicker">{escape(post.category)}</p>'
        f"<h1>{escape(post.title)}</h1><p>{escape(post.excerpt)}</p></header>"
        f'<div class="post-meta"><time datetime="{post.published.isoformat()}">'
        f'{post.published.strftime("%Y-%m-%d")}</time>'
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

def application(environ: dict, start_response) -> Iterable[bytes]:
    """Serve the rendered pages over WSGI. Read-only: GET and HEAD alone."""
    path = unquote(environ.get("PATH_INFO", "/")).rstrip("/") or "/"
    method = environ.get("REQUEST_METHOD", "GET").upper()
    if method not in ("GET", "HEAD"):
        start_response(
            "405 Method Not Allowed", [("Allow", "GET, HEAD"), *SECURITY_HEADERS]
        )
        return [b""]
    if path == "/static/style.css":
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

    path = SECTION_ALIASES.get(path, path)
    routes = {"/": home, "/ideas": ideas, "/blog": listing, "/changelog": changelog}
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

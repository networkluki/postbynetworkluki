#!/usr/bin/env python3
"""Render the whole site into a directory of static files.

The output is what GitHub Pages publishes:

    public/
      index.html                      home page
      ideas/index.html                sections
      blog/index.html
      changelog/index.html
      blog/<slug>/index.html          one directory per post
      blog/<legacy-slug>/index.html   redirect to the current slug
      404.html                        served by Pages for unknown paths
      static/style.css
      CNAME                           copied when present
      .nojekyll                       keep Pages from post-processing the output

Pages are rendered by the same functions the preview server uses, so the static
output and `python app.py` cannot drift apart.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from html import escape
from pathlib import Path

from app import (
    article,
    changelog,
    feed,
    home,
    ideas,
    listing,
    not_found,
    stylesheet_name,
)
from content import Post, PostError, all_posts

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "public"
# Also the marker that identifies a directory as build output we may delete.
MARKER = ".nojekyll"
SECTIONS = {"ideas": ideas, "blog": listing, "changelog": changelog}
# Retired section paths, kept as redirects.
SECTION_REDIRECTS = {"ideer": "/ideas", "blogg": "/blog"}


class BuildError(Exception):
    pass


def redirect_page(target: str) -> bytes:
    """A static redirect: no server rules are available on a static host.

    The colours are inline rather than loaded from the stylesheet. These pages are
    visible for as long as the browser takes to follow the refresh, and an external
    stylesheet would let them flash white first, or stay white on a slow connection.
    """
    safe = escape(target, quote=True)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="robots" content="noindex">\n'
        '<meta name="theme-color" content="#1a1917">\n'
        f'<link rel="canonical" href="{safe}">\n'
        f'<meta http-equiv="refresh" content="0; url={safe}">\n'
        "<title>Moved</title>\n"
        "<style>:root{color-scheme:dark}"
        "body{margin:0;min-height:100vh;display:flex;align-items:center;"
        "justify-content:center;color:#f2efe9;background:#1a1917;"
        "font:400 1rem/1.6 system-ui,sans-serif}"
        "a{color:#e08a6f}</style>\n</head>\n"
        f'<body><p>This page moved to <a href="{safe}">{safe}</a>.</p></body>\n'
        "</html>\n"
    ).encode("utf-8")


def write(output: Path, relative: str, body: bytes) -> str:
    path = output / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return relative


def prepare_output(output: Path, force: bool) -> None:
    """Empty the output directory, refusing to touch unrelated content."""
    if output.exists():
        if not output.is_dir():
            raise BuildError(f"{output} exists and is not a directory")
        if any(output.iterdir()) and not (output / MARKER).exists() and not force:
            raise BuildError(
                f"{output} is not empty and was not created by build.py. "
                "Refusing to delete it; pass --force to overwrite anyway."
            )
        shutil.rmtree(output)
    output.mkdir(parents=True)


def post_pages(output: Path, posts: tuple[Post, ...]) -> list[str]:
    written = []
    for post in posts:
        written.append(write(output, f"blog/{post.slug}/index.html", article(post)))
        # Old Swedish article paths, both section spellings.
        for alias in (post.slug, *post.legacy_slugs):
            written.append(
                write(
                    output,
                    f"blogg/{alias}/index.html",
                    redirect_page(f"/blog/{post.slug}"),
                )
            )
        for alias in post.legacy_slugs:
            written.append(
                write(
                    output,
                    f"blog/{alias}/index.html",
                    redirect_page(f"/blog/{post.slug}"),
                )
            )
    return written


def build(output: Path = OUTPUT, *, force: bool = False) -> list[str]:
    """Render every page. Returns the written paths, relative to the output."""
    posts = all_posts()
    if not posts:
        raise BuildError(
            "no posts found in src/posts; the home page needs at least one post"
        )
    prepare_output(output, force)
    written = [write(output, MARKER, b"")]
    written.append(write(output, "index.html", home()))
    for name, render in SECTIONS.items():
        written.append(write(output, f"{name}/index.html", render()))
    for name, target in SECTION_REDIRECTS.items():
        written.append(write(output, f"{name}/index.html", redirect_page(target)))
    written.extend(post_pages(output, posts))
    written.append(write(output, "404.html", not_found()))
    written.append(write(output, "feed.xml", feed()))

    stylesheet = ROOT / "static" / "style.css"
    if not stylesheet.is_file():
        raise BuildError(f"missing stylesheet: {stylesheet}")
    styles = stylesheet.read_bytes()
    # The fingerprinted name is what the pages link to.
    written.append(write(output, f"static/{stylesheet_name()}", styles))
    # The plain name stays for HTML that a visitor already has cached.
    written.append(write(output, "static/style.css", styles))
    # Copy the rest of static/ verbatim (theme scripts, etc.).
    for extra in sorted((ROOT / "static").iterdir()):
        if extra.is_file() and extra.name != "style.css":
            written.append(write(output, f"static/{extra.name}", extra.read_bytes()))

    cname = ROOT / "CNAME"
    if cname.is_file():
        # Without this the custom domain is dropped on every deploy.
        written.append(write(output, "CNAME", cname.read_bytes()))
    return sorted(written)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build.py", description="Render the site into static files."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT,
        help=f"output directory (default: {OUTPUT.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite the output directory even if build.py did not create it",
    )
    parser.add_argument("--quiet", action="store_true", help="only print the summary")
    args = parser.parse_args(argv)
    try:
        written = build(args.output, force=args.force)
    except (BuildError, PostError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if not args.quiet:
        for relative in written:
            print(relative)
    print(f"{len(written)} file(s) written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

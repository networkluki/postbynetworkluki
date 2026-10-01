#!/usr/bin/env python3
"""Command-line publishing for the Post blog.

Writes to the same SQLite database as the web admin form and reuses its
validation, so a post added here is identical to one published in the browser.

    python manage.py new --title "Hello" --category Notes \
        --excerpt "Short summary." --read-time "4 min" --content-file post.txt
    python manage.py list
    python manage.py show hello
    python manage.py delete hello --yes

The database location follows BLOG_DB_PATH, exactly like the web app. Set it to
the same value the server uses, or posts are written to a database the site
never reads.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from app import (
    POST_FIELD_LIMITS,
    POSTS,
    PostError,
    all_posts,
    database_path,
    delete_post,
    store_post,
)

PROMPTS = {
    "title": "Title",
    "category": "Category (for example Notes)",
    "excerpt": "Excerpt, one or two sentences",
    "read_time": "Reading time (for example 5 min)",
}
BUNDLED_SLUGS = frozenset(post.slug for post in POSTS)


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{value!r} is not a date in YYYY-MM-DD form"
        ) from None


def prompt_field(field: str) -> str:
    """Ask for a single field. Only called when stdin is a terminal."""
    limit = POST_FIELD_LIMITS[field]
    return input(f"{PROMPTS[field]} (max {limit} characters): ").strip()


def prompt_content() -> str:
    """Read paragraphs from the terminal until a single '.' line or EOF."""
    print(
        "Content. Separate paragraphs with a blank line. "
        "Finish with a line containing only '.' or press Ctrl-D:"
    )
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == ".":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def resolve_content(args: argparse.Namespace, interactive: bool) -> str:
    """Return post content from --content, --content-file, stdin or a prompt."""
    if args.content is not None:
        return args.content
    if args.content_file == "-":
        return sys.stdin.read()
    if args.content_file is not None:
        path = Path(args.content_file).expanduser()
        try:
            return path.read_text(encoding="utf-8")
        except OSError as error:
            raise PostError(f"cannot read {path}: {error.strerror}")
        except UnicodeDecodeError:
            raise PostError(f"{path} is not valid UTF-8 text")
    if interactive:
        return prompt_content()
    raise PostError("content is required: use --content, --content-file or a terminal")


def command_new(args: argparse.Namespace) -> int:
    interactive = sys.stdin.isatty()
    values = {field: getattr(args, field) for field in PROMPTS}
    try:
        for field, value in values.items():
            if value is None:
                if not interactive:
                    raise PostError(f"--{field.replace('_', '-')} is required")
                values[field] = prompt_field(field)
        values["content"] = resolve_content(args, interactive)
        post = store_post(values, published=args.published, slug=args.slug)
    except PostError as error:
        return fail(error.message)
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        return fail("aborted")
    print(f"Published {post.title!r} as /blog/{post.slug}")
    print(f"Database: {database_path()}")
    return 0


def command_list(args: argparse.Namespace) -> int:
    posts = all_posts()
    if not posts:
        print("No posts.")
        return 0
    print(f"{'DATE':<12} {'SOURCE':<9} {'SLUG':<42} TITLE")
    for post in posts:
        source = "bundled" if post.slug in BUNDLED_SLUGS else "database"
        print(
            f"{post.published.isoformat():<12} {source:<9} {post.slug:<42} {post.title}"
        )
    print(f"\n{len(posts)} post(s). Database: {database_path()}")
    return 0


def command_show(args: argparse.Namespace) -> int:
    match = next((post for post in all_posts() if post.slug == args.slug), None)
    if match is None:
        return fail(f"no post with slug {args.slug!r}")
    print(f"Title:    {match.title}")
    print(f"Slug:     {match.slug}")
    print(f"Category: {match.category}")
    print(f"Date:     {match.published.isoformat()}")
    print(f"Reading:  {match.read_time}")
    print(f"Source:   {'bundled' if match.slug in BUNDLED_SLUGS else 'database'}")
    print(f"Excerpt:  {match.excerpt}\n")
    print("\n\n".join(match.content))
    return 0


def command_delete(args: argparse.Namespace) -> int:
    if args.slug in BUNDLED_SLUGS:
        return fail(
            f"{args.slug!r} is a bundled starter post defined in app.py "
            "and cannot be deleted from the database"
        )
    if not args.yes:
        if not sys.stdin.isatty():
            return fail("refusing to delete without --yes")
        answer = input(f"Delete {args.slug!r} permanently? Type yes to confirm: ")
        if answer.strip().lower() != "yes":
            return fail("aborted")
    if not delete_post(args.slug):
        return fail(f"no stored post with slug {args.slug!r}")
    print(f"Deleted {args.slug}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="Publish and manage Post blog entries from the command line.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    new = subparsers.add_parser("new", help="publish a new post")
    new.add_argument("--title", help=f"max {POST_FIELD_LIMITS['title']} characters")
    new.add_argument(
        "--category", help=f"max {POST_FIELD_LIMITS['category']} characters"
    )
    new.add_argument("--excerpt", help=f"max {POST_FIELD_LIMITS['excerpt']} characters")
    new.add_argument(
        "--read-time",
        dest="read_time",
        help=f"max {POST_FIELD_LIMITS['read_time']} characters",
    )
    content_source = new.add_mutually_exclusive_group()
    content_source.add_argument(
        "--content",
        help=f"post body, max {POST_FIELD_LIMITS['content']} characters, "
        "paragraphs separated by a blank line",
    )
    content_source.add_argument(
        "--content-file",
        dest="content_file",
        help="read the body from a UTF-8 file, or - for standard input",
    )
    new.add_argument("--slug", help="override the slug derived from the title")
    new.add_argument(
        "--published",
        type=iso_date,
        help="publication date as YYYY-MM-DD (default: today)",
    )
    new.set_defaults(handler=command_new)

    listing = subparsers.add_parser("list", help="list every post")
    listing.set_defaults(handler=command_list)

    show = subparsers.add_parser("show", help="print one post")
    show.add_argument("slug")
    show.set_defaults(handler=command_show)

    delete = subparsers.add_parser("delete", help="delete a stored post")
    delete.add_argument("slug")
    delete.add_argument(
        "--yes", action="store_true", help="skip the confirmation prompt"
    )
    delete.set_defaults(handler=command_delete)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())

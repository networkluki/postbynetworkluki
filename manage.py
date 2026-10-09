#!/usr/bin/env python3
"""Write blog posts from Python instead of by hand.

A post is a text file in src/posts. This tool creates, lists, prints and removes
those files using the same validation the build uses, so an accepted post is
guaranteed to render:

    python manage.py new --title "Hello" --category Articles \
        --excerpt "Short summary." --read-time "4 min" --content-file post.txt
    python manage.py list
    python manage.py show hello
    python manage.py delete hello --yes

Writing a file only changes the working tree. The post appears on the site after
`python build.py` is verified locally and the file is committed and pushed, which
is what triggers the GitHub Pages deployment.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from content import (
    CATEGORIES,
    FIELD_LIMITS,
    PostError,
    TIME_PATTERN,
    all_posts,
    delete_post,
    post_path,
    posts_directory,
    published_display,
    write_post,
)

PROMPTS = {
    "title": "Title",
    "category": f"Category ({' / '.join(CATEGORIES.values())})",
    "excerpt": "Excerpt, one or two sentences",
    "read_time": "Reading time (for example 5 min)",
}


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


def clock_time(value: str) -> str:
    if not TIME_PATTERN.match(value):
        raise argparse.ArgumentTypeError(f"{value!r} is not a 24-hour HH:MM time")
    return value


def prompt_field(field: str) -> str:
    """Ask for a single field. Only called when stdin is a terminal."""
    return input(f"{PROMPTS[field]} (max {FIELD_LIMITS[field]} characters): ").strip()


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
        post = write_post(
            values,
            published=args.published,
            slug=args.slug,
            published_time=args.time or "",
        )
    except PostError as error:
        return fail(error.message)
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        return fail("aborted")
    print(f"Wrote {post_path(post.slug)}")
    print(f"Local path: /blog/{post.slug}")
    print("Next: python build.py, then commit and push the file to publish it.")
    return 0


def command_list(args: argparse.Namespace) -> int:
    try:
        posts = all_posts()
    except PostError as error:
        return fail(error.message)
    if not posts:
        print(f"No posts in {posts_directory()}")
        return 0
    print(f"{'PUBLISHED':<20} {'SLUG':<42} TITLE")
    for post in posts:
        print(f"{published_display(post):<20} {post.slug:<42} {post.title}")
    print(f"\n{len(posts)} post(s) in {posts_directory()}")
    return 0


def command_show(args: argparse.Namespace) -> int:
    try:
        posts = all_posts()
    except PostError as error:
        return fail(error.message)
    match = next((post for post in posts if post.slug == args.slug), None)
    if match is None:
        return fail(f"no post with slug {args.slug!r}")
    print(f"Title:    {match.title}")
    print(f"Slug:     {match.slug}")
    print(f"Category: {match.category}")
    print(f"Date:     {published_display(match)}")
    print(f"Reading:  {match.read_time}")
    print(f"File:     {post_path(match.slug)}")
    if match.legacy_slugs:
        print(f"Legacy:   {', '.join(match.legacy_slugs)}")
    print(f"Excerpt:  {match.excerpt}\n")
    print("\n\n".join(match.content))
    return 0


def command_delete(args: argparse.Namespace) -> int:
    if not args.yes:
        if not sys.stdin.isatty():
            return fail("refusing to delete without --yes")
        answer = input(f"Delete {post_path(args.slug)} permanently? Type yes: ")
        if answer.strip().lower() != "yes":
            return fail("aborted")
    if not delete_post(args.slug):
        return fail(f"no post file for slug {args.slug!r}")
    print(f"Deleted {post_path(args.slug)}")
    print("Next: python build.py, then commit and push the deletion.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="Create and manage the post files in src/posts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    new = subparsers.add_parser("new", help="write a new post file")
    new.add_argument("--title", help=f"max {FIELD_LIMITS['title']} characters")
    new.add_argument("--category", help=f"max {FIELD_LIMITS['category']} characters")
    new.add_argument("--excerpt", help=f"max {FIELD_LIMITS['excerpt']} characters")
    new.add_argument(
        "--read-time",
        dest="read_time",
        help=f"max {FIELD_LIMITS['read_time']} characters",
    )
    content_source = new.add_mutually_exclusive_group()
    content_source.add_argument(
        "--content",
        help=f"post body, max {FIELD_LIMITS['content']} characters, "
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
    new.add_argument(
        "--time",
        type=clock_time,
        help="optional publication time as HH:MM (24-hour)",
    )
    new.set_defaults(handler=command_new)

    listing = subparsers.add_parser("list", help="list every post file")
    listing.set_defaults(handler=command_list)

    show = subparsers.add_parser("show", help="print one post")
    show.add_argument("slug")
    show.set_defaults(handler=command_show)

    delete = subparsers.add_parser("delete", help="delete a post file")
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

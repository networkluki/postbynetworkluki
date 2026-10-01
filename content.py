"""Blog content stored as text files under src/posts.

The files in the repository are the only source of truth: a static build on a
hosting platform such as GitHub Pages has no database and no running process, so
anything that should appear on the site must be committed. Each file carries a
front matter block and a body of plain-text paragraphs:

    ---
    title: Build less. Launch faster.
    category: Workflow
    excerpt: Three simple questions that help you start smaller.
    published: 2026-09-24
    read_time: 4 min
    legacy_slugs: bygg-mindre-lanserar-snabbare
    ---

    First paragraph.

    Second paragraph.

The file name without its extension is the slug, so the example above is served
at /blog/build-less-launch-faster. Paragraph breaks are the only formatting:
the body is HTML-escaped when rendered, and no Markdown syntax is interpreted.
"""

from __future__ import annotations

import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Mapping

BASE_DIR = Path(__file__).resolve().parent
POSTS_DIR = BASE_DIR / "src" / "posts"
POST_SUFFIX = ".md"
FENCE = "---"

REQUIRED_FIELDS = ("title", "category", "excerpt", "published", "read_time")
OPTIONAL_FIELDS = ("legacy_slugs",)
ALLOWED_FIELDS = frozenset(REQUIRED_FIELDS + OPTIONAL_FIELDS)
FIELD_LIMITS = {
    "title": 120,
    "category": 50,
    "excerpt": 300,
    "content": 20000,
    "read_time": 20,
}
# Fields a writer supplies; published and the slug are handled separately.
TEXT_FIELDS = ("title", "category", "excerpt", "content", "read_time")


class PostError(Exception):
    """A post file is invalid, or a post could not be written."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class Post:
    slug: str
    category: str
    title: str
    excerpt: str
    published: date
    read_time: str
    content: tuple[str, ...]
    legacy_slugs: tuple[str, ...] = field(default=())
    source: str = ""


def slugify(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug[:80]


def posts_directory() -> Path:
    """Return the content directory, overridable with BLOG_POSTS_DIR."""
    override = os.environ.get("BLOG_POSTS_DIR")
    return Path(override).expanduser() if override else POSTS_DIR


def post_path(slug: str, directory: Path | None = None) -> Path:
    return (directory or posts_directory()) / f"{slug}{POST_SUFFIX}"


def parse_front_matter(text: str, source: str) -> tuple[dict[str, str], str]:
    """Split a post file into its front matter fields and body."""
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != FENCE:
        raise PostError(f"{source}: must start with a '{FENCE}' front matter line")
    try:
        end = lines.index(FENCE, 1)
    except ValueError:
        raise PostError(f"{source}: front matter is never closed with '{FENCE}'") from None

    fields: dict[str, str] = {}
    for number, line in enumerate(lines[1:end], start=2):
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        key = key.strip().lower()
        if not separator:
            raise PostError(f"{source}: line {number} is not a 'key: value' pair")
        if key not in ALLOWED_FIELDS:
            allowed = ", ".join(sorted(ALLOWED_FIELDS))
            raise PostError(f"{source}: unknown field {key!r} (allowed: {allowed})")
        if key in fields:
            raise PostError(f"{source}: field {key!r} appears more than once")
        fields[key] = value.strip()
    return fields, "\n".join(lines[end + 1 :]).strip()


def validate_fields(values: Mapping[str, str], source: str = "post") -> dict[str, str]:
    """Return the trimmed, length-checked text fields or raise PostError."""
    cleaned: dict[str, str] = {}
    for name in TEXT_FIELDS:
        value = (values.get(name) or "").strip()
        if not value:
            raise PostError(f"{source}: {name} is required")
        if len(value) > FIELD_LIMITS[name]:
            raise PostError(
                f"{source}: {name} is longer than {FIELD_LIMITS[name]} characters"
            )
        cleaned[name] = value
    return cleaned


def parse_post(text: str, slug: str, source: str) -> Post:
    """Build a Post from one file's contents. Raises PostError when invalid."""
    if slug != slugify(slug):
        raise PostError(
            f"{source}: file name must be lowercase letters, digits and dashes"
        )
    fields, body = parse_front_matter(text, source)
    missing = [name for name in REQUIRED_FIELDS if not fields.get(name)]
    if missing:
        raise PostError(f"{source}: missing field(s): {', '.join(missing)}")
    cleaned = validate_fields({**fields, "content": body}, source)
    try:
        published = date.fromisoformat(fields["published"])
    except ValueError:
        raise PostError(
            f"{source}: published must be a date in YYYY-MM-DD form, "
            f"not {fields['published']!r}"
        ) from None
    legacy = tuple(
        part.strip()
        for part in fields.get("legacy_slugs", "").split(",")
        if part.strip()
    )
    for alias in legacy:
        if alias != slugify(alias):
            raise PostError(f"{source}: legacy slug {alias!r} is not a valid slug")
    return Post(
        slug,
        cleaned["category"],
        cleaned["title"],
        cleaned["excerpt"],
        published,
        cleaned["read_time"],
        tuple(
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", cleaned["content"])
            if paragraph.strip()
        ),
        legacy,
        source,
    )


def all_posts(directory: Path | None = None) -> tuple[Post, ...]:
    """Read every post file, newest first.

    Files are read on every call. The site has a handful of posts, so this keeps
    the preview server and the build honest instead of caching stale content.
    """
    directory = directory or posts_directory()
    if not directory.is_dir():
        return ()
    posts = []
    for path in sorted(directory.glob(f"*{POST_SUFFIX}")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise PostError(f"{path.name}: file is not valid UTF-8 text") from None
        posts.append(parse_post(text, path.stem, path.name))
    duplicates = find_duplicate_slugs(posts)
    if duplicates:
        raise PostError(f"slug used more than once: {', '.join(sorted(duplicates))}")
    return tuple(sorted(posts, key=lambda post: (post.published, post.slug), reverse=True))


def find_duplicate_slugs(posts: list[Post] | tuple[Post, ...]) -> set[str]:
    """Return slugs and legacy slugs that more than one post claims."""
    seen: set[str] = set()
    clashes: set[str] = set()
    for post in posts:
        for name in (post.slug, *post.legacy_slugs):
            if name in seen:
                clashes.add(name)
            seen.add(name)
    return clashes


def legacy_slug_map(posts: tuple[Post, ...]) -> dict[str, str]:
    """Map every retired slug to the slug that replaced it."""
    return {alias: post.slug for post in posts for alias in post.legacy_slugs}


def render_post_file(
    values: Mapping[str, str], published: date, legacy_slugs: tuple[str, ...] = ()
) -> str:
    """Serialise a post back into the on-disk format."""
    header = [
        FENCE,
        f"title: {values['title']}",
        f"category: {values['category']}",
        f"excerpt: {values['excerpt']}",
        f"published: {published.isoformat()}",
        f"read_time: {values['read_time']}",
    ]
    if legacy_slugs:
        header.append(f"legacy_slugs: {', '.join(legacy_slugs)}")
    header.append(FENCE)
    body = "\n\n".join(
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", values["content"].strip())
        if paragraph.strip()
    )
    return "\n".join(header) + "\n\n" + body + "\n"


def write_post(
    values: Mapping[str, str],
    *,
    published: date | None = None,
    slug: str | None = None,
    directory: Path | None = None,
) -> Post:
    """Validate and write a new post file, returning the stored post.

    Never overwrites an existing post: a clashing slug raises PostError.
    """
    directory = directory or posts_directory()
    cleaned = validate_fields(values)
    slug = slugify(slug or cleaned["title"])
    if not slug:
        raise PostError("the title must contain letters or numbers")
    published = published or date.today()
    existing = all_posts(directory)
    taken = {name for post in existing for name in (post.slug, *post.legacy_slugs)}
    if slug in taken:
        raise PostError(f"a post with the slug {slug!r} already exists")

    path = post_path(slug, directory)
    text = render_post_file(cleaned, published)
    directory.mkdir(parents=True, exist_ok=True)
    # Write through a temporary file in the same directory so an interrupted run
    # cannot leave a half-written post behind.
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=directory, prefix=f".{slug}.", delete=False
    )
    try:
        with handle:
            handle.write(text)
        os.replace(handle.name, path)
    except OSError:
        Path(handle.name).unlink(missing_ok=True)
        raise
    return parse_post(text, slug, path.name)


def delete_post(slug: str, directory: Path | None = None) -> bool:
    """Delete a post file. Returns False when no such post exists."""
    path = post_path(slug, directory)
    if not path.is_file():
        return False
    path.unlink()
    return True

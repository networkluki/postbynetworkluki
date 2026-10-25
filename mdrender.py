"""Minimal, dependency-free Markdown rendering for post bodies.

The site generator splits a post body into blocks on blank lines. This module
turns each block into HTML, supporting the features post authors need:

* ATX headings -- a block of ``#`` to ``######`` followed by text becomes an
  ``<h1>``..``<h6>`` element. Post titles already render as the page ``<h1>``,
  so body headings should start at ``##`` (``<h2>``).
* Lists -- a block whose every line is a list item becomes a ``<ul>`` (lines
  marked with ``-`` or ``*``) or an ``<ol>`` (lines marked ``1.``/``1)``).
* Bold spans -- ``**bold**`` inside any block becomes ``<strong>bold</strong>``.
* Italic spans -- ``*italic*`` becomes ``<em>italic</em>``. Single ``*`` markers
  never touch a ``**`` run, so bold and italic compose without clashing.
* Links -- ``[text](url)`` becomes ``<a href="url">text</a>``. Only a strict
  allowlist of URLs is accepted: ``https://``, ``http://`` and ``mailto:``, plus
  same-site ``/path``, ``#anchor`` and ``./``/``../`` relatives. Anything else
  (``javascript:``, ``data:``, protocol-relative ``//host``, ...) is left as
  literal text, so a post can never produce a dangerous href. External links get
  ``rel="noopener noreferrer"``.

Everything else is treated as literal text. All text is HTML-escaped *before*
any markup is inserted, so post content can never inject tags or scripts. This
keeps the output safe under the site's strict ``script-src 'self'`` CSP.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from html import escape

# A heading block: 1-6 leading '#', whitespace, the text, and an optional
# closing run of '#'. The block is a single stripped line, so '.' never needs
# to cross a newline; a multi-line block simply falls through to a list or
# paragraph.
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?$")

# One list item per line: a '-' or '*' bullet, or an 'N.'/'N)' ordinal, then
# whitespace, then the item text. Matched against already-stripped lines.
_UNORDERED_ITEM = re.compile(r"^[-*][ \t]+(.+)$")
_ORDERED_ITEM = re.compile(r"^\d+[.)][ \t]+(.+)$")

# Bold spans. The content must begin and end with a non-whitespace character,
# so stray markers around spaces ("a ** b **") and empty runs ("****") stay
# literal -- an approximation of CommonMark's flanking rules that covers the
# cases post authors actually hit.
_BOLD = re.compile(r"\*\*(\S(?:.*?\S)?)\*\*")

# Italic spans. A single '*' that is not part of a '**' run (guarded by the
# lookarounds), with content that neither starts nor ends on whitespace. Bold
# is substituted first, so by the time this runs every '**' pair is already a
# <strong> element and only genuine single-'*' emphasis remains.
_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(?!\s)(.+?)(?<![\s*])\*(?!\*)")

# A link: '[text](url)'. The text holds no ']' and the url no ')' or space, so
# the pair is unambiguous. The url is validated against _URL_ALLOWED before use.
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")

# Absolute schemes we trust for a post-authored href. Checked case-insensitively.
_ALLOWED_SCHEMES = ("https://", "http://", "mailto:")

# Private-use placeholder for a rendered link while bold/italic run, so neither
# pass can touch an href (e.g. a '*' in a url). It carries no markup character.
_PLACEHOLDER = "{}"
_PLACEHOLDER_RE = re.compile("(\\d+)")


def _is_safe_url(url: str) -> bool:
    """True if *url* (already HTML-escaped) is one a post may link to."""
    lowered = url.lower()
    if lowered.startswith(_ALLOWED_SCHEMES):
        return True
    # Same-site relatives, but never protocol-relative '//host'.
    if url.startswith("#") or url.startswith(("./", "../")):
        return True
    return url.startswith("/") and not url.startswith("//")


def _is_external(url: str) -> bool:
    return url.lower().startswith(_ALLOWED_SCHEMES)


def _emphasis(text: str) -> str:
    """Apply bold then italic to an already-escaped string."""
    bolded = _BOLD.sub(r"<strong>\1</strong>", text)
    return _ITALIC.sub(r"<em>\1</em>", bolded)


def render_inline(text: str) -> str:
    """Escape *text*, then render links, ``**bold**`` and ``*italic*``."""
    # Drop the placeholder sentinel if a post ever contains it literally, so it
    # can never be used to smuggle a forged link index past the link pass.
    escaped = escape(text).replace("", "")

    links: list[str] = []

    def _store_link(match: re.Match[str]) -> str:
        label, url = match.group(1), match.group(2)
        if not _is_safe_url(url):
            return match.group(0)  # unknown scheme -> leave the text literal
        rel = ' rel="noopener noreferrer"' if _is_external(url) else ""
        links.append(f'<a href="{url}"{rel}>{_emphasis(label)}</a>')
        return _PLACEHOLDER.format(len(links) - 1)

    withlinks = _LINK.sub(_store_link, escaped)
    emphasized = _emphasis(withlinks)
    return _PLACEHOLDER_RE.sub(lambda m: links[int(m.group(1))], emphasized)


def _list_items(block: str, pattern: re.Pattern[str]) -> list[str] | None:
    """Return the item texts if every non-empty line matches *pattern*."""
    lines = [line.strip() for line in block.split("\n")]
    lines = [line for line in lines if line]
    if not lines:
        return None
    matches = [pattern.match(line) for line in lines]
    if all(matches):
        return [match.group(1).strip() for match in matches]  # type: ignore[union-attr]
    return None


def render_block(block: str) -> str:
    """Render one blank-line-separated block as a heading, list or paragraph."""
    heading = _HEADING.match(block)
    if heading is not None:
        level = len(heading.group(1))
        return f"<h{level}>{render_inline(heading.group(2))}</h{level}>"

    unordered = _list_items(block, _UNORDERED_ITEM)
    if unordered is not None:
        items = "".join(f"<li>{render_inline(item)}</li>" for item in unordered)
        return f"<ul>{items}</ul>"

    ordered = _list_items(block, _ORDERED_ITEM)
    if ordered is not None:
        items = "".join(f"<li>{render_inline(item)}</li>" for item in ordered)
        return f"<ol>{items}</ol>"

    return f"<p>{render_inline(block)}</p>"


def render_body(blocks: Iterable[str]) -> str:
    """Render an ordered collection of body blocks into HTML."""
    return "".join(render_block(block) for block in blocks)

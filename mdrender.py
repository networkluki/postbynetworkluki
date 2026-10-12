"""Minimal, dependency-free Markdown rendering for post bodies.

The site generator splits a post body into blocks on blank lines. This module
turns each block into HTML, supporting the two features post authors need:

* ATX headings -- a block of ``#`` to ``######`` followed by text becomes an
  ``<h1>``..``<h6>`` element. Post titles already render as the page ``<h1>``,
  so body headings should start at ``##`` (``<h2>``).
* Bold spans -- ``**bold**`` inside any block becomes ``<strong>bold</strong>``.

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
# to cross a newline; a multi-line block simply falls through to a paragraph.
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?$")

# Bold spans. The content must begin and end with a non-whitespace character,
# so stray markers around spaces ("a ** b **") and empty runs ("****") stay
# literal -- an approximation of CommonMark's flanking rules that covers the
# cases post authors actually hit.
_BOLD = re.compile(r"\*\*(\S(?:.*?\S)?)\*\*")


def render_inline(text: str) -> str:
    """Escape *text*, then turn ``**bold**`` spans into <strong> elements."""
    return _BOLD.sub(r"<strong>\1</strong>", escape(text))


def render_block(block: str) -> str:
    """Render one blank-line-separated block as a heading or a paragraph."""
    match = _HEADING.match(block)
    if match is not None:
        level = len(match.group(1))
        return f"<h{level}>{render_inline(match.group(2))}</h{level}>"
    return f"<p>{render_inline(block)}</p>"


def render_body(blocks: Iterable[str]) -> str:
    """Render an ordered collection of body blocks into HTML."""
    return "".join(render_block(block) for block in blocks)

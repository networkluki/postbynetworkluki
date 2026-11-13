#!/usr/bin/env python3
"""Create an 800x300 article hero image from a source photo.

Usage:
    uv run python tools/make_hero.py <source-image> <slug>

This is a LOCAL authoring tool. It reads a photo you supply, cover-crops and
resizes it to exactly 800x300, strips all metadata, and writes an optimised
WebP to static/img/heroes/<slug>.webp. The committed file is what the site
serves; nothing runs at build time and the GitHub Pages build stays
dependency-free.

After running it, add the printed line to the post's front matter:

    image: <slug>.webp

Security notes:
* The source photo is treated as untrusted input. Pillow's decompression-bomb
  guard (Image.MAX_IMAGE_PIXELS) is left enabled; a hostile or corrupt image
  fails closed with a clear message.
* The slug is checked against a strict allowlist, so the output path can never
  escape static/img/heroes/ (no traversal, no absolute paths).
* convert("RGB") plus a fresh WebP encode drop any EXIF/GPS/camera metadata, so
  a public asset never leaks where or how the photo was taken.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ModuleNotFoundError:  # pragma: no cover - environment guard
    sys.exit(
        "Pillow is not installed. Install the dev dependencies first, e.g.\n"
        "    uv sync\n"
        "and re-run with 'uv run python tools/make_hero.py ...'."
    )

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "static" / "img" / "heroes"
TARGET = (800, 300)  # width x height, landscape banner
QUALITY = 82
# Match content.py's IMAGE_PATTERN basename: lowercase, digits, dash-separated.
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SLUG_LENGTH = 80
MAX_SOURCE_BYTES = 25 * 1024 * 1024  # reject absurd uploads before decoding


def safe_slug(value: str) -> str:
    """Return a validated slug or exit with a clear error."""
    slug = value.strip().lower()
    if len(slug) > MAX_SLUG_LENGTH or not SLUG_PATTERN.fullmatch(slug):
        sys.exit(
            f"Invalid slug {value!r}: use lowercase letters, digits and dashes "
            "(for example my-first-post)."
        )
    return slug


def build(source: Path, slug: str) -> Path:
    """Produce static/img/heroes/<slug>.webp from the source photo."""
    if not source.is_file():
        sys.exit(f"Source image not found: {source}")
    size = source.stat().st_size
    if size > MAX_SOURCE_BYTES:
        sys.exit(
            f"Source image is {size // (1024 * 1024)} MB; the limit is "
            f"{MAX_SOURCE_BYTES // (1024 * 1024)} MB."
        )

    destination = OUTPUT_DIR / f"{slug}.webp"
    try:
        with Image.open(source) as img:
            img = ImageOps.exif_transpose(img)  # honour camera orientation
            img = img.convert("RGB")  # drop alpha/palette and all metadata
            fitted = ImageOps.fit(
                img,
                TARGET,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),  # cover-crop around the centre
            )
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            fitted.save(destination, format="WEBP", quality=QUALITY, method=6)
    except (UnidentifiedImageError, OSError, ValueError) as error:
        sys.exit(f"Could not process {source}: {error}")
    return destination


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Create an 800x300 WebP article hero image from a photo.",
    )
    parser.add_argument("source", type=Path, help="Path to the source photo.")
    parser.add_argument(
        "slug",
        help="Post slug; output is static/img/heroes/<slug>.webp.",
    )
    args = parser.parse_args(argv)

    slug = safe_slug(args.slug)
    destination = build(args.source, slug)
    print(f"Wrote {destination.relative_to(ROOT)}  (800x300 WebP)")
    print(f"Add this line to the post front matter:\n    image: {destination.name}")


if __name__ == "__main__":
    main()

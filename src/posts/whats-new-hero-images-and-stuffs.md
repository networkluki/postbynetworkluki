---
title: What's new: hero images and Stuffs
category: Changelog
excerpt: Articles can now carry a hero image, and a new Stuffs section collects the things I have built.
published: 2026-11-14
published_time: 12:21
read_time: 2 min
---

A short summary of what has changed on the blog up to version 1.4.0.

## Hero images on articles

- An article can now show an 800 × 300 banner at the top, set with a single image line in the post file.
- A small [image tool](https://github.com/networkluki/postbynetworkluki/blob/main/tools/make_hero.py) crops and resizes a photo, strips its metadata and saves it as WebP.
- The image is prepared locally with Pillow, managed with [uv](https://github.com/astral-sh/uv). The site build itself still has no third-party dependencies.

## The Stuffs section

- [Stuffs](/stuffs) is a new page for things I have built and the domains they live on.
- Each entry is one line in a text file: a link, a title and a short description.
- The cards are laid out side by side in two columns, and in one column on small screens.

## Housekeeping

- Three early placeholder posts have been removed.
- The footer now shows version 1.4.0.

Write → Review → Test → Build → Publish.

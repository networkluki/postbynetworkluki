---
title: From text to blog
category: Articles
excerpt: How I build my blog with text files, Python and automatic publishing.
published: 2026-11-13
read_time: 2 min
image: from-text-to-blog.webp
---

My blog, Post by networkluki, starts with plain text files. I write the posts in Markdown, and [Python](https://github.com/networkluki/postbynetworkluki/blob/7af2b33e913b5dbb6fa3558359ad91f36ee5b05a/build.py) validates the content and builds finished HTML pages. Text, code and images are version-controlled together in Git.

CSS shapes the look, while [JavaScript](https://github.com/networkluki/postbynetworkluki/blob/7af2b33e913b5dbb6fa3558359ad91f36ee5b05a/static/theme-switch.js) handles features such as light and dark mode. The article text is already in the page and does not need to be fetched from an API.

An article can also have a hero image. My [image tool](https://github.com/networkluki/postbynetworkluki/blob/7af2b33e913b5dbb6fa3558359ad91f36ee5b05a/tools/make_hero.py) uses Pillow to crop the image to 800 × 300 pixels and save it as WebP. The image is prepared locally in a Python environment managed with [uv](https://github.com/networkluki/postbynetworkluki/blob/7af2b33e913b5dbb6fa3558359ad91f36ee5b05a/pyproject.toml).

When I push the changes to main on GitHub, [GitHub Actions](https://github.com/networkluki/postbynetworkluki/blob/7af2b33e913b5dbb6fa3558359ad91f36ee5b05a/.github/workflows/pages.yml) starts. First the tests run, then the site is built. If both steps succeed, the flow continues to publishing on GitHub Pages.

The visitor gets finished pages, with no Python process or database of my own running at the time of the visit.

Write → Review → Test → Build → Publish.

I am responsible for the content and the review. The tools handle the build and the publishing.

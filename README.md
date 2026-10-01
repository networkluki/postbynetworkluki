# Post by networkluki

A small, dependency-free blog. Python renders every page to static HTML, and
GitHub Pages publishes the result at <https://blog.networkluki.com>.

Nothing runs in production: there is no server, no database and no admin login.
A post is a file in the repository, and publishing is a `git push`.

```
src/posts/<slug>.md          one text file per post
        |
        |  python build.py   renders with the page functions in app.py
        v
public/                      static HTML, the deploy artifact
        |
        |  git push to main  .github/workflows/pages.yml
        v
blog.networkluki.com
```

## Write a post

```bash
python manage.py new --title "Publishing from the shell" --category "Notes" \
    --excerpt "A short summary shown in the listing." --read-time "2 min" \
    --content-file post.txt
```

Run `python manage.py new` with no flags in a terminal and it asks for each
field; the body ends with a line containing only `.` or with Ctrl-D. The body can
also come from `--content` or from a pipe with `--content-file -`. `--slug`
overrides the slug derived from the title and `--published YYYY-MM-DD` backdates
a post.

Other commands:

```bash
python manage.py list                 # every post file, newest first
python manage.py show <slug>          # one post in full
python manage.py delete <slug> --yes  # remove a post file
```

`manage.py` only writes files in `src/posts`; it never overwrites an existing
post and exits with `1` on any validation or lookup error, so it is safe in
scripts.

### The file format

A post file can also be written by hand. The file name without `.md` is the
slug, so `src/posts/build-less-launch-faster.md` is served at
`/blog/build-less-launch-faster`.

```
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
```

| Field | Required | Limit | Notes |
|---|---|---|---|
| `title` | yes | 120 chars | |
| `category` | yes | 50 chars | shown above the title |
| `excerpt` | yes | 300 chars | listing text and meta description |
| `published` | yes | — | `YYYY-MM-DD`; posts are sorted newest first |
| `read_time` | yes | 20 chars | rendered as "4 min read" |
| `legacy_slugs` | no | — | comma separated; each becomes a redirect page |
| body | yes | 20000 chars | paragraphs separated by a blank line |

Paragraph breaks are the only formatting. All text is HTML-escaped when
rendered, so Markdown syntax and raw HTML in a post appear literally rather than
being interpreted. The file name must be lowercase letters, digits and dashes,
and no two posts may claim the same slug or legacy slug — the build fails
instead of publishing something ambiguous.

## Preview before publishing

```bash
python build.py                                  # writes public/
python -m http.server 8000 --directory public    # exactly what Pages will serve
```

`python app.py` starts a preview server on <http://127.0.0.1:8000> instead. It
renders with the same functions as the build and reads `src/posts` on every
request, so edits show up on reload. It listens on localhost only and serves
`GET` and `HEAD` alone; it is a development tool, not a production server.

## Publish

```bash
git add src/posts/publishing-from-the-shell.md
git commit -m "Add a post about publishing from the shell"
git push
```

The push to `main` triggers `.github/workflows/pages.yml`, which runs the tests,
runs `build.py` and deploys `public/` to GitHub Pages. A failing test or an
invalid post file fails the workflow and leaves the live site untouched.

Repository settings → Pages → Source must be set to **GitHub Actions**. With the
older "Deploy from a branch" setting, Pages ignores this workflow and serves the
repository root instead.

## Test

```bash
python -m unittest discover -s tests -v
```

## Layout

| Path | Purpose |
|---|---|
| `src/posts/*.md` | the posts; the only content source |
| `content.py` | reads, validates and writes post files |
| `app.py` | page rendering and the local preview server |
| `build.py` | renders everything into `public/` |
| `manage.py` | command-line post management |
| `templates/base.html` | page shell |
| `static/style.css` | styles, copied into the build |
| `CNAME` | custom domain, copied into the build |
| `tests/` | unittest suite |

`public/` is generated and git-ignored. `build.py` empties it on every run and
refuses to delete a directory it did not create unless `--force` is passed.

## What the static model gives up

* **No admin UI and no database.** Earlier versions published through a form at
  `/admin/new` backed by SQLite. Static hosting has no process to run that, so
  both were removed. Publishing is `manage.py` plus a commit.
* **No drafts.** Everything in `src/posts` is published on the next push. Keep
  unfinished posts on a branch.
* **Old URLs** keep working through generated redirect pages: `/ideer` and
  `/blogg` point at `/ideas` and `/blog`, and every `legacy_slugs` entry
  redirects to its post.
* **Pages serves over HTTPS** with the custom domain; enforce HTTPS in the
  repository's Pages settings.

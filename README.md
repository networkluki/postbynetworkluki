# Post by networkluki

A small, dependency-free blog built with Python and WSGI. The site has separate
sections for ideas and tips, blog posts, and a changelog.

## Run the website

```bash
python app.py
```

The server listens on every network interface and uses the `PORT` environment
variable (default `8000`). In production, run the process behind HTTPS and point
`blog.networkluki.com` to the server. The `CNAME` file specifies the domain name,
but a DNS record does not start the Python process; the server or hosting provider
must run `python app.py`.

## Publish directly on the blog

Set a long, unique administrator password in the hosting environment and choose a
persistent location for the SQLite database:

```bash
export BLOG_ADMIN_PASSWORD='replace-with-a-long-unique-password'
export BLOG_DB_PATH='/persistent-volume/posts.db'
python app.py
```

Then open <https://blog.networkluki.com/admin/new> or use the **Write a post**
link in the footer. The browser asks for a username and password; the username can
be anything and the password is the value of `BLOG_ADMIN_PASSWORD`. Only use the
publishing page over HTTPS.

Posts published through the website are stored in the SQLite file. `BLOG_DB_PATH`
must therefore point to persistent storage in production, or new posts will be
lost when the server is rebuilt or restarted.

## Publish from the command line

`manage.py` writes to the same SQLite database as the web form and reuses its
validation, so a post added here is identical to one published in the browser.
No administrator password is needed: access to the database file is the
permission boundary.

```bash
export BLOG_DB_PATH='/persistent-volume/posts.db'

# Everything on one line
python manage.py new --title "Publishing from the shell" --category "Notes" \
    --excerpt "A short summary shown in the listing." --read-time "2 min" \
    --content "First paragraph.

Second paragraph."

# Body from a file, or from a pipe with -
python manage.py new --title "Release notes" --category "Changelog" \
    --excerpt "What changed this week." --read-time "3 min" \
    --content-file notes.txt

# Run it without arguments in a terminal and it asks for each field.
# The body ends with a line containing only '.' or with Ctrl-D.
python manage.py new
```

Paragraphs are separated by a blank line. `--slug` overrides the slug derived
from the title and `--published YYYY-MM-DD` backdates a post.

Other commands:

```bash
python manage.py list                 # every post, with bundled/database source
python manage.py show <slug>          # one post in full
python manage.py delete <slug> --yes  # remove a stored post
```

The three bundled starter posts live in `app.py` and cannot be deleted from the
database. `manage.py` exits with `0` on success and `1` on any validation,
duplicate or lookup error, so it is safe to use in scripts and cron jobs.

**`BLOG_DB_PATH` must match the value the running server uses.** Without it,
both the server and `manage.py` default to `data/posts.db` next to the code,
which is lost on redeploy and is not shared with a server started from a
different directory. On a server, run `manage.py` as the same user that owns the
database file.

## Test

```bash
python -m unittest discover -s tests -v
```

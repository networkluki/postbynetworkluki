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

## Test

```bash
python -m unittest discover -s tests -v
```

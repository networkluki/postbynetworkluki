"""A tiny dependency-free WSGI blog for Post by networkluki."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote
from wsgiref.simple_server import make_server


BASE_DIR = Path(__file__).parent


@dataclass(frozen=True)
class Post:
    slug: str
    category: str
    title: str
    excerpt: str
    published: date
    read_time: str
    content: tuple[str, ...]


POSTS = (
    Post(
        "bygg-mindre-lanserar-snabbare",
        "Arbetssätt",
        "Bygg mindre. Lansera snabbare.",
        "Tre enkla frågor som hjälper dig att hitta den minsta versionen som faktiskt skapar värde.",
        date(2026, 9, 24),
        "4 min",
        (
            "En bra första version behöver inte lösa allt. Den behöver lösa ett tydligt problem för en tydlig person.",
            "Börja med att fråga vad som måste vara sant för att idén ska fungera. Välj sedan det minsta experiment som ger ett ärligt svar.",
            "När något är ute i världen får du återkoppling från verkligheten. Det är oftast mer värdefullt än ännu en vecka av antaganden.",
        ),
    ),
    Post(
        "ett-lugnare-digitalt-flode",
        "Design",
        "Ett lugnare digitalt flöde",
        "Så använder vi hierarki, luft och begränsningar för att göra innehåll enklare att ta till sig.",
        date(2026, 9, 12),
        "6 min",
        (
            "Bra design hjälper besökaren att förstå vad som är viktigt utan att behöva tänka på själva gränssnittet.",
            "Tydlig typografi, gott om luft och få konkurrerande färger skapar rytm. Begränsningar är inte ett hinder – de ger innehållet en scen.",
            "Testa sidan på avstånd. Om rubriker, grupper och nästa steg fortfarande syns har hierarkin börjat fungera.",
        ),
    ),
    Post(
        "anteckningar-fran-en-omstart",
        "Bakom kulisserna",
        "Anteckningar från en omstart",
        "Varför Post fick ett nytt hem och vad vi vill fylla det med framöver.",
        date(2026, 8, 29),
        "3 min",
        (
            "Post är vår plats för sådant som är värt att spara: idéer under utveckling, lärdomar från arbetet och små förändringar längs vägen.",
            "Vi vill hellre publicera användbara anteckningar ofta än perfekta manifest sällan. Formatet får växa tillsammans med innehållet.",
        ),
    ),
)


def page(title: str, content: str, *, description: str = "Idéer, artiklar och uppdateringar från networkluki.") -> bytes:
    template = (BASE_DIR / "templates" / "base.html").read_text(encoding="utf-8")
    html = template.replace("{{ title }}", escape(title)).replace(
        "{{ description }}", escape(description, quote=True)
    ).replace("{{ content }}", content)
    return html.encode("utf-8")


def post_card(post: Post) -> str:
    return f"""
      <article class="post-card">
        <p class="eyebrow">{escape(post.category)}</p>
        <h2><a href="/blogg/{escape(post.slug)}">{escape(post.title)}</a></h2>
        <p>{escape(post.excerpt)}</p>
        <div class="post-meta"><time datetime="{post.published.isoformat()}">{post.published.strftime('%Y-%m-%d')}</time><span>{escape(post.read_time)} läsning</span></div>
      </article>"""


def home() -> bytes:
    latest = POSTS[0]
    content = f"""
<section class="hero">
  <p class="kicker">POST BY NETWORKLUKI</p>
  <h1>Tankar värda att<br><em>ta vidare.</em></h1>
  <p class="intro">En samling idéer, berättelser och små förbättringar från vårt hörn av internet.</p>
</section>
<div class="cards" aria-label="Utforska innehållet">
  <a href="/ideer" class="nav-card ideas"><div class="icon" aria-hidden="true">&#128161;</div><div class="body"><h3>Idéer &amp; tips</h3><p>Tankar och förslag</p></div><div class="arrow" aria-hidden="true">&rarr;</div></a>
  <a href="/blogg" class="nav-card blog"><div class="icon" aria-hidden="true">&#128221;</div><div class="body"><h3>Blogg</h3><p>Inlägg och artiklar</p></div><div class="arrow" aria-hidden="true">&rarr;</div></a>
  <a href="/changelog" class="nav-card changelog"><div class="icon" aria-hidden="true">&#128203;</div><div class="body"><h3>Ändringslogg</h3><p>Förändringar och nytt</p></div><div class="arrow" aria-hidden="true">&rarr;</div></a>
</div>
<section class="featured">
  <div><p class="eyebrow">Senaste inlägget · {latest.published.strftime('%Y-%m-%d')}</p><h2>{escape(latest.title)}</h2><p>{escape(latest.excerpt)}</p></div>
  <a class="text-link" href="/blogg/{latest.slug}">Läs inlägget <span aria-hidden="true">↗</span></a>
</section>"""
    return page("Post by networkluki", content)


def listing() -> bytes:
    cards = "".join(post_card(post) for post in POSTS)
    return page("Blogg · Post", f'<header class="page-heading"><p class="kicker">BLOGG</p><h1>Inlägg &amp; artiklar</h1><p>Resonemang, metoder och sådant vi lär oss på vägen.</p></header><section class="post-grid">{cards}</section>')


def ideas() -> bytes:
    items = (
        ("01", "Gör plats för tråkiga idéer", "Det uppenbara är ofta en bättre startpunkt än det originella. Skriv ner det ändå."),
        ("02", "Byt perspektiv i tio minuter", "Beskriv problemet som en ny besökare, en expert och någon med väldigt lite tid."),
        ("03", "Avsluta med nästa steg", "En anteckning blir mer användbar när den berättar vad du faktiskt kan göra nu."),
    )
    rows = "".join(f'<article class="idea-row"><span>{n}</span><div><h2>{escape(t)}</h2><p>{escape(p)}</p></div></article>' for n, t, p in items)
    return page("Idéer & tips · Post", f'<header class="page-heading"><p class="kicker">IDÉER &amp; TIPS</p><h1>Små saker att prova</h1><p>Korta impulser för bättre digitalt arbete.</p></header><section class="idea-list">{rows}</section>')


def changelog() -> bytes:
    entries = (
        ("2026-10-01", "Post får ett eget hem", "Vi lanserade en ny startsida, blogg, idésamling och ändringslogg."),
        ("2026-09-24", "Första artikeln", "Vår första längre text om att bygga mindre och lära snabbare publicerades."),
        ("2026-08-29", "Arbetet börjar", "De första skisserna, orden och tekniska besluten kom på plats."),
    )
    rows = "".join(f'<article class="change-row"><time datetime="{d}">{d}</time><div><h2>{escape(t)}</h2><p>{escape(p)}</p></div></article>' for d, t, p in entries)
    return page("Ändringslogg · Post", f'<header class="page-heading"><p class="kicker">ÄNDRINGSLOGG</p><h1>Vad är nytt?</h1><p>En rak lista över hur den här platsen utvecklas.</p></header><section class="change-list">{rows}</section>')


def article(post: Post) -> bytes:
    paragraphs = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in post.content)
    content = f'<article class="article"><a class="back" href="/blogg">← Alla inlägg</a><p class="eyebrow">{escape(post.category)}</p><h1>{escape(post.title)}</h1><div class="post-meta"><time datetime="{post.published.isoformat()}">{post.published.strftime("%Y-%m-%d")}</time><span>{escape(post.read_time)} läsning</span></div><p class="lead">{escape(post.excerpt)}</p><div class="prose">{paragraphs}</div></article>'
    return page(f"{post.title} · Post", content, description=post.excerpt)


def not_found() -> bytes:
    return page("Sidan hittades inte · Post", '<section class="empty"><p class="kicker">404</p><h1>Här fanns ingenting.</h1><p>Sidan kan ha flyttat eller aldrig ha funnits.</p><a class="button" href="/">Till startsidan</a></section>')


def application(environ: dict, start_response) -> Iterable[bytes]:
    """Serve the site through the WSGI interface."""
    path = unquote(environ.get("PATH_INFO", "/")).rstrip("/") or "/"
    if path == "/static/style.css":
        body = (BASE_DIR / "static" / "style.css").read_bytes()
        start_response(
            "200 OK",
            [("Content-Type", "text/css; charset=utf-8"), ("Content-Length", str(len(body)))],
        )
        return [body]
    routes = {"/": home, "/ideer": ideas, "/blogg": listing, "/changelog": changelog}
    status = "200 OK"
    if path in routes:
        body = routes[path]()
    elif path.startswith("/blogg/"):
        slug = path.removeprefix("/blogg/")
        match = next((post for post in POSTS if post.slug == slug), None)
        if match:
            body = article(match)
        else:
            status, body = "404 Not Found", not_found()
    else:
        status, body = "404 Not Found", not_found()
    start_response(status, [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))])
    return [body]


if __name__ == "__main__":
    print("Post is running on http://localhost:8000")
    with make_server("0.0.0.0", 8000, application) as server:
        server.serve_forever()

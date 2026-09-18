#!/usr/bin/env python3
"""
Static site builder for ohlala.cloud.

Pipeline
--------
1. load()      site.yaml + every content/*.md (YAML front matter + Markdown body)
2. validate()  slugs unique, every game page points at an existing games/<slug>/index.html
3. render()    Jinja2 templates -> dist/
                 /                      home: game grid
                 /games/<slug>/         story page for one game (+ embedded/linked player)
                 /play/<slug>/          the raw game file, copied untouched
                 /<slug>/               any other content page (about, ...)
                 /404.html
4. extras()    sitemap.xml, robots.txt, llms.txt, feed.xml, og/<slug>.png
5. copy()      static/ -> dist/static/

Content model (front matter keys)
---------------------------------
title        required
slug         required, unique, used in the URL
date         YYYY-MM-DD; games are listed newest first
tagline      one line under the title, also the meta description
game         path to the playable file, e.g. games/aisle-be-back/index.html
             -> its presence makes the page a *game* page
iterations   int, shown as a stat on the page
prompts      int, shown as a stat on the page
session      free text, when it was built
tags         list of strings
draft        true -> built but not linked, not in sitemap/feed (for previews)

Usage: python build.py [--out dist] [--drafts]
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
GAMES = ROOT / "games"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"

FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


# ---------------------------------------------------------------- model
@dataclass
class Page:
    slug: str
    title: str
    body_md: str
    meta: dict = field(default_factory=dict)
    source: Path | None = None

    @property
    def is_game(self) -> bool:
        return bool(self.meta.get("game"))

    @property
    def draft(self) -> bool:
        return bool(self.meta.get("draft"))

    @property
    def date(self) -> dt.date:
        d = self.meta.get("date")
        if isinstance(d, dt.date):
            return d
        return dt.date.fromisoformat(str(d)) if d else dt.date(1970, 1, 1)

    @property
    def url(self) -> str:
        return f"/games/{self.slug}/" if self.is_game else f"/{self.slug}/"

    @property
    def play_url(self) -> str:
        return f"/play/{self.slug}/"

    @property
    def tagline(self) -> str:
        return self.meta.get("tagline", "")

    @property
    def body_html(self) -> str:
        return markdown.markdown(
            self.body_md,
            extensions=["fenced_code", "tables", "smarty", "sane_lists"],
        )

    @property
    def plain_text(self) -> str:
        """Body without markup, for llms.txt and the feed summary."""
        text = re.sub(r"<[^>]+>", "", self.body_html)
        return html.unescape(re.sub(r"\s+", " ", text)).strip()


@dataclass
class Site:
    config: dict
    pages: list[Page]

    @property
    def games(self) -> list[Page]:
        return sorted((p for p in self.pages if p.is_game), key=lambda p: p.date, reverse=True)

    @property
    def others(self) -> list[Page]:
        return [p for p in self.pages if not p.is_game]

    @property
    def public(self) -> list[Page]:
        return [p for p in self.pages if not p.draft]


# ---------------------------------------------------------------- load
def parse_markdown_file(path: Path) -> Page:
    raw = path.read_text(encoding="utf-8")
    m = FRONT_MATTER.match(raw)
    if not m:
        sys.exit(f"{path}: missing front matter (--- block at the top)")
    meta = yaml.safe_load(m.group(1)) or {}
    body = raw[m.end():]
    for key in ("title", "slug"):
        if key not in meta:
            sys.exit(f"{path}: front matter needs '{key}'")
    return Page(slug=str(meta["slug"]), title=str(meta["title"]), body_md=body, meta=meta, source=path)


def verification_token(value: object) -> str:
    """Google hands out a whole <meta ...> tag; accept that or the token alone."""
    text = str(value or "").strip()
    m = re.search(r"""content=["']([^"']+)["']""", text)
    return m.group(1) if m else text


def load(include_drafts: bool) -> Site:
    config = yaml.safe_load((ROOT / "site.yaml").read_text(encoding="utf-8"))
    config["google_site_verification"] = verification_token(config.get("google_site_verification"))
    pages = [parse_markdown_file(p) for p in sorted(CONTENT.glob("*.md"))]
    if not include_drafts:
        pages = [p for p in pages if not p.draft]
    return Site(config=config, pages=pages)


# ---------------------------------------------------------------- validate
def validate(site: Site) -> None:
    seen: dict[str, Path] = {}
    for p in site.pages:
        if not re.fullmatch(r"[a-z0-9-]+", p.slug):
            sys.exit(f"{p.source}: slug '{p.slug}' must be lowercase letters, digits and dashes")
        if p.slug in seen:
            sys.exit(f"{p.source}: slug '{p.slug}' already used by {seen[p.slug]}")
        seen[p.slug] = p.source
        if p.is_game:
            game_file = ROOT / p.meta["game"]
            if not game_file.is_file():
                sys.exit(f"{p.source}: game file not found: {p.meta['game']}")
            if not p.meta.get("date"):
                sys.exit(f"{p.source}: game pages need a 'date'")


# ---------------------------------------------------------------- render
def make_env(site: Site) -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["site"] = site.config
    env.globals["games"] = [g for g in site.games if not g.draft]
    env.globals["now"] = dt.datetime.now(dt.timezone.utc)
    env.filters["isodate"] = lambda d: d.isoformat()
    env.filters["nicedate"] = lambda d: d.strftime("%-d %B %Y")
    return env


def write(out: Path, rel: str, content: str) -> None:
    target = out / rel.lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def render(site: Site, out: Path) -> None:
    env = make_env(site)
    write(out, "index.html", env.get_template("index.html").render(page=None))
    write(out, "404.html", env.get_template("404.html").render(page=None))
    for p in site.pages:
        tpl = env.get_template("game.html" if p.is_game else "page.html")
        write(out, f"{p.url}index.html", tpl.render(page=p))
        if p.is_game:
            src = ROOT / p.meta["game"]
            dst = out / p.play_url.lstrip("/") / "index.html"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)


# ---------------------------------------------------------------- extras
def sitemap(site: Site, out: Path) -> None:
    base = site.config["url"].rstrip("/")
    urls = ["/"] + [p.url for p in site.public] + [p.play_url for p in site.public if p.is_game]
    body = "\n".join(f"  <url><loc>{base}{u}</loc></url>" for u in urls)
    write(out, "sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          f"{body}\n</urlset>\n")


def robots(site: Site, out: Path) -> None:
    base = site.config["url"].rstrip("/")
    # Everyone welcome, AI crawlers included: the stories are meant to be read.
    write(out, "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n")


def llms_txt(site: Site, out: Path) -> None:
    """Plain-text summary for AI crawlers: https://llmstxt.org"""
    base = site.config["url"].rstrip("/")
    lines = [f"# {site.config['title']}", "", f"> {site.config['description'].strip()}", ""]
    lines += ["## Games", ""]
    for g in site.games:
        if g.draft:
            continue
        stats = []
        if g.meta.get("iterations"):
            stats.append(f"{g.meta['iterations']} iterations")
        if g.meta.get("prompts"):
            stats.append(f"{g.meta['prompts']} prompts")
        stat = f" ({', '.join(stats)})" if stats else ""
        lines.append(f"- [{g.title}]({base}{g.url}): {g.tagline}{stat} Play: {base}{g.play_url}")
    lines += ["", "## Pages", ""]
    for p in site.others:
        if not p.draft:
            lines.append(f"- [{p.title}]({base}{p.url})")
    write(out, "llms.txt", "\n".join(lines) + "\n")


def feed(site: Site, out: Path) -> None:
    base = site.config["url"].rstrip("/")
    items = []
    for g in site.games:
        if g.draft:
            continue
        pub = dt.datetime.combine(g.date, dt.time(12, 0), tzinfo=dt.timezone.utc)
        items.append(
            "  <item>\n"
            f"    <title>{html.escape(g.title)}</title>\n"
            f"    <link>{base}{g.url}</link>\n"
            f"    <guid>{base}{g.url}</guid>\n"
            f"    <pubDate>{pub.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>\n"
            f"    <description>{html.escape(g.tagline)}</description>\n"
            "  </item>"
        )
    write(out, "feed.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>\n'
          f"  <title>{html.escape(site.config['title'])}</title>\n"
          f"  <link>{base}/</link>\n"
          f"  <description>{html.escape(site.config['tagline'])}</description>\n"
          + "\n".join(items) + "\n</channel></rss>\n")


def og_images(site: Site, out: Path) -> None:
    """1200x630 share images: coloured background, title, tagline, site name."""
    from PIL import Image, ImageDraw, ImageFont

    def font(size: int, bold: bool = True):
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        for base in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "C:/Windows/Fonts"):
            f = Path(base) / name
            if f.exists():
                return ImageFont.truetype(str(f), size)
        return ImageFont.load_default()

    colors = site.config.get("og_colors", {})
    targets = [(p.slug, p.title, p.tagline) for p in site.public]
    targets.append(("default", site.config["title"], site.config["tagline"]))
    for slug, title, tagline in targets:
        img = Image.new("RGB", (1200, 630), colors.get(slug, colors.get("default", "#1f2937")))
        d = ImageDraw.Draw(img)
        d.text((80, 200), title, font=font(84), fill="white")
        wrapped = wrap(tagline, 46)
        d.text((80, 320), wrapped, font=font(38, bold=False), fill="#e5e7eb", spacing=12)
        d.text((80, 540), site.config["title"], font=font(30), fill="#d1d5db")
        (out / "og").mkdir(parents=True, exist_ok=True)
        img.save(out / "og" / f"{slug}.png", optimize=True)


def wrap(text: str, width: int) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines[:3])


def copy_static(out: Path) -> None:
    if STATIC.is_dir():
        shutil.copytree(STATIC, out / "static", dirs_exist_ok=True)


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="dist")
    ap.add_argument("--drafts", action="store_true", help="also build pages marked draft: true")
    args = ap.parse_args()

    out = (ROOT / args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    site = load(include_drafts=args.drafts)
    validate(site)
    render(site, out)
    sitemap(site, out)
    robots(site, out)
    llms_txt(site, out)
    feed(site, out)
    og_images(site, out)
    copy_static(out)

    n_games = sum(1 for p in site.pages if p.is_game)
    print(f"built {len(site.pages)} pages ({n_games} games) -> {out}")


if __name__ == "__main__":
    main()

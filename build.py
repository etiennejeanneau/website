#!/usr/bin/env python3
"""
Static site builder for ohlala.cloud.

Pipeline
--------
1. load()      site.yaml + languages.yaml + every content/<lang>/*.md
                 (YAML front matter + Markdown body)
2. validate()  slugs unique per language, every translation has an original,
               every game page points at an existing games/<slug>/index.html
3. render()    Jinja2 templates -> dist/, once per language
                 /                      home: game grid (default language)
                 /fr/                   same home in French
                 /games/<slug>/         story page for one game
                 /fr/games/<slug>/      the same story in French
                 /play/<slug>/          the raw game file, copied untouched
                                        (one copy: games have no language)
                 /<slug>/, /fr/<slug>/  any other content page (about, ...)
                 /404.html              one page, all languages on it
4. extras()    sitemap.xml, robots.txt, ads.txt, llms.txt, feed.xml,
               og/<slug>.png (per language: og/fr/<slug>.png)
5. copy()      static/ -> dist/static/

Languages
---------
languages.yaml lists them and holds every word that is not part of a page.
The default language sits at the root, the others under /<key>/. Pages live in
content/<key>/<slug>.md, one folder per language, same file name on both sides.

A translation only has to carry the words: title, slug, tagline and the body.
Everything else in its front matter (game, date, iterations, prompts, tags,
draft) is inherited from the same slug in the default language, so the numbers
can never drift between two versions of the same story.

Content model (front matter keys)
---------------------------------
title        required
slug         required, unique inside its language, used in the URL
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

# Front matter keys a translation inherits from the default language when it
# does not set them itself. Only the words are expected in a translated file.
INHERITED = ("game", "date", "iterations", "prompts", "tags", "draft", "session")


# ---------------------------------------------------------------- model
@dataclass
class Lang:
    key: str                 # "en", "fr": the folder, the URL prefix, <html lang>
    strings: dict            # everything from languages.yaml for this language
    is_default: bool

    @property
    def prefix(self) -> str:
        """URL prefix: "" for the default language, "/fr" for the others."""
        return "" if self.is_default else f"/{self.key}"

    @property
    def home(self) -> str:
        return f"{self.prefix}/"

    @property
    def name(self) -> str:
        return self.strings["name"]


@dataclass
class Page:
    slug: str
    title: str
    body_md: str
    lang: Lang
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
        p = self.lang.prefix
        return f"{p}/games/{self.slug}/" if self.is_game else f"{p}/{self.slug}/"

    @property
    def play_url(self) -> str:
        """The game itself. One copy for every language: it has no words of ours."""
        return f"/play/{self.slug}/"

    @property
    def og_path(self) -> str:
        """Share image, one per language because the tagline is on it."""
        folder = "og" if self.lang.is_default else f"og/{self.lang.key}"
        return f"/{folder}/{self.slug}.png"

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
    langs: list[Lang]
    pages: list[Page]

    @property
    def default(self) -> Lang:
        return next(l for l in self.langs if l.is_default)

    def games(self, lang: Lang) -> list[Page]:
        pages = (p for p in self.pages if p.is_game and p.lang is lang)
        return sorted(pages, key=lambda p: p.date, reverse=True)

    def others(self, lang: Lang) -> list[Page]:
        return [p for p in self.pages if not p.is_game and p.lang is lang]

    @property
    def public(self) -> list[Page]:
        return [p for p in self.pages if not p.draft]

    def translation(self, slug: str, lang: Lang) -> Page | None:
        """The same story in another language, or None if it is not written yet."""
        for p in self.pages:
            if p.slug == slug and p.lang is lang:
                return p
        return None


# ---------------------------------------------------------------- load
def parse_markdown_file(path: Path, lang: Lang) -> Page:
    raw = path.read_text(encoding="utf-8")
    m = FRONT_MATTER.match(raw)
    if not m:
        sys.exit(f"{path}: missing front matter (--- block at the top)")
    meta = yaml.safe_load(m.group(1)) or {}
    body = raw[m.end():]
    for key in ("title", "slug"):
        if key not in meta:
            sys.exit(f"{path}: front matter needs '{key}'")
    return Page(slug=str(meta["slug"]), title=str(meta["title"]), body_md=body,
                lang=lang, meta=meta, source=path)


def verification_token(value: object) -> str:
    """Google hands out a whole <meta ...> tag; accept that or the token alone."""
    text = str(value or "").strip()
    m = re.search(r"""content=["']([^"']+)["']""", text)
    return m.group(1) if m else text


def load_languages() -> list[Lang]:
    data = yaml.safe_load((ROOT / "languages.yaml").read_text(encoding="utf-8"))
    default = str(data.get("default") or "")
    keys = [k for k in data if k != "default"]
    if default not in keys:
        sys.exit(f"languages.yaml: default '{default}' is not one of {keys}")
    # Default language first: it is the one everything else falls back to.
    keys.sort(key=lambda k: (k != default, k))
    return [Lang(key=k, strings=data[k], is_default=(k == default)) for k in keys]


def load(include_drafts: bool) -> Site:
    config = yaml.safe_load((ROOT / "site.yaml").read_text(encoding="utf-8"))
    config["google_site_verification"] = verification_token(config.get("google_site_verification"))

    langs = load_languages()
    pages: list[Page] = []
    for lang in langs:
        folder = CONTENT / lang.key
        if not folder.is_dir():
            sys.exit(f"content/{lang.key}/ is missing (languages.yaml lists '{lang.key}')")
        pages += [parse_markdown_file(p, lang) for p in sorted(folder.glob("*.md"))]

    site = Site(config=config, langs=langs, pages=pages)
    inherit_meta(site)
    if not include_drafts:
        site.pages = [p for p in site.pages if not p.draft]
    return site


def inherit_meta(site: Site) -> None:
    """A translation says the words; the facts come from the default language."""
    originals = {p.slug: p for p in site.pages if p.lang is site.default}
    for p in site.pages:
        if p.lang is site.default:
            continue
        original = originals.get(p.slug)
        if original is None:
            continue  # reported by validate()
        for key in INHERITED:
            if key not in p.meta and key in original.meta:
                p.meta[key] = original.meta[key]


# ---------------------------------------------------------------- validate
def validate(site: Site) -> None:
    seen: dict[tuple[str, str], Path] = {}
    originals = {p.slug for p in site.pages if p.lang is site.default}
    for p in site.pages:
        if not re.fullmatch(r"[a-z0-9-]+", p.slug):
            sys.exit(f"{p.source}: slug '{p.slug}' must be lowercase letters, digits and dashes")
        key = (p.lang.key, p.slug)
        if key in seen:
            sys.exit(f"{p.source}: slug '{p.slug}' already used by {seen[key]}")
        seen[key] = p.source
        if p.slug != p.source.stem:
            sys.exit(f"{p.source}: slug '{p.slug}' should match the file name")
        if p.lang is not site.default and p.slug not in originals:
            sys.exit(f"{p.source}: no content/{site.default.key}/{p.slug}.md to translate")
        if p.is_game:
            game_file = ROOT / p.meta["game"]
            if not game_file.is_file():
                sys.exit(f"{p.source}: game file not found: {p.meta['game']}")
            if not p.meta.get("date"):
                sys.exit(f"{p.source}: game pages need a 'date'")

    # Missing translations are not an error: the language menu falls back to
    # the home page of that language. Say it out loud so it is not forgotten.
    for lang in site.langs:
        if lang is site.default:
            continue
        missing = [p.slug for p in site.pages
                   if p.lang is site.default and not site.translation(p.slug, lang)]
        if missing:
            print(f"note: no {lang.key} version of {', '.join(sorted(missing))}")

    client = str(site.config.get("adsense_client") or "").strip()
    if client and not re.fullmatch(r"ca-pub-\d{16}", client):
        sys.exit(f"site.yaml: adsense_client should look like ca-pub-0000000000000000, got '{client}'")


# ---------------------------------------------------------------- render
def make_env(site: Site, lang: Lang) -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def alternates(page: Page | None) -> list[dict]:
        """The same page in every language, for the menu and for hreflang.

        A language that has not translated this page points at its home page
        instead, and is left out of the hreflang tags (it is not the same page).
        """
        out = []
        for other in site.langs:
            twin = None if page is None else site.translation(page.slug, other)
            same = page is None or twin is not None
            out.append({
                "key": other.key,
                "name": other.strings["name"],
                "short": other.strings["short"],
                "url": (other.home if page is None else twin.url) if same else other.home,
                "translated": same,
                "is_default": other.is_default,
                "current": other is lang,
            })
        return out

    env.globals["site"] = site.config
    env.globals["t"] = lang.strings
    env.globals["lang"] = lang.key
    env.globals["prefix"] = lang.prefix
    env.globals["home"] = lang.home
    env.globals["og_default"] = "/og/default.png" if lang.is_default else f"/og/{lang.key}/default.png"
    env.globals["games"] = [g for g in site.games(lang) if not g.draft]
    env.globals["languages"] = site.langs
    env.globals["alternates"] = alternates
    env.globals["now"] = dt.datetime.now(dt.timezone.utc)
    env.filters["isodate"] = lambda d: d.isoformat()
    env.filters["nicedate"] = lambda d: nicedate(d, lang.key)
    return env


FRENCH_MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                 "août", "septembre", "octobre", "novembre", "décembre"]


def nicedate(d: dt.date, lang_key: str) -> str:
    """Dates spelled out, without depending on system locales being installed."""
    if lang_key == "fr":
        day = "1er" if d.day == 1 else str(d.day)
        return f"{day} {FRENCH_MONTHS[d.month - 1]} {d.year}"
    return d.strftime("%-d %B %Y")


def write(out: Path, rel: str, content: str) -> None:
    target = out / rel.lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def render(site: Site, out: Path) -> None:
    for lang in site.langs:
        env = make_env(site, lang)
        write(out, f"{lang.home}index.html", env.get_template("index.html").render(page=None))
        for p in site.pages:
            if p.lang is not lang:
                continue
            tpl = env.get_template("game.html" if p.is_game else "page.html")
            write(out, f"{p.url}index.html", tpl.render(page=p))

    # One copy of each game, shared by every language.
    for p in site.pages:
        if p.is_game and p.lang is site.default:
            dst = out / p.play_url.lstrip("/") / "index.html"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / p.meta["game"], dst)

    # One 404 for the whole site: CloudFront serves the same file whatever the
    # address was, so the page says it in every language.
    env = make_env(site, site.default)
    write(out, "404.html", env.get_template("404.html").render(page=None))


# ---------------------------------------------------------------- extras
def sitemap(site: Site, out: Path) -> None:
    base = site.config["url"].rstrip("/")
    urls = [l.home for l in site.langs]
    urls += [p.url for p in site.public]
    urls += [p.play_url for p in site.public if p.is_game and p.lang is site.default]
    body = "\n".join(f"  <url><loc>{base}{u}</loc></url>" for u in urls)
    write(out, "sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          f"{body}\n</urlset>\n")


def robots(site: Site, out: Path) -> None:
    base = site.config["url"].rstrip("/")
    # Everyone welcome, AI crawlers included: the stories are meant to be read.
    write(out, "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n")


def ads_txt(site: Site, out: Path) -> None:
    """Tells ad buyers that Google is allowed to sell this site's ad space.

    Without it AdSense treats the inventory as unauthorised and pays less or
    nothing. The long number is Google's own id, the same for every publisher;
    only the pub- part is ours. No publisher id in site.yaml -> no file.
    """
    client = str(site.config.get("adsense_client") or "").strip()
    if not client:
        return
    publisher = client[3:] if client.startswith("ca-") else client
    write(out, "ads.txt", f"google.com, {publisher}, DIRECT, f08c47fec0942fa0\n")


def llms_txt(site: Site, out: Path) -> None:
    """Plain-text summary for AI crawlers: https://llmstxt.org (one per language)"""
    base = site.config["url"].rstrip("/")
    for lang in site.langs:
        s = lang.strings
        lines = [f"# {site.config['title']}", "", f"> {s['description'].strip()}", ""]
        lines += [f"## {s['games_heading']}", ""]
        for g in site.games(lang):
            if g.draft:
                continue
            stats = []
            if g.meta.get("iterations"):
                stats.append(f"{g.meta['iterations']} {s['iterations']}")
            if g.meta.get("prompts"):
                stats.append(f"{g.meta['prompts']} {s['prompts']}")
            stat = f" ({', '.join(stats)})" if stats else ""
            lines.append(f"- [{g.title}]({base}{g.url}): {g.tagline}{stat} {s['play']}: {base}{g.play_url}")
        lines += ["", "## Pages", ""]
        for p in site.others(lang):
            if not p.draft:
                lines.append(f"- [{p.title}]({base}{p.url})")
        write(out, f"{lang.home}llms.txt", "\n".join(lines) + "\n")


def feed(site: Site, out: Path) -> None:
    base = site.config["url"].rstrip("/")
    for lang in site.langs:
        items = []
        for g in site.games(lang):
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
        write(out, f"{lang.home}feed.xml",
              '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>\n'
              f"  <title>{html.escape(site.config['title'])}</title>\n"
              f"  <link>{base}{lang.home}</link>\n"
              f"  <language>{lang.key}</language>\n"
              f"  <description>{html.escape(lang.strings['tagline'])}</description>\n"
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
    targets = [(p.og_path, p.slug, p.title, p.tagline) for p in site.public]
    for lang in site.langs:
        folder = "og" if lang.is_default else f"og/{lang.key}"
        targets.append((f"/{folder}/default.png", "default",
                        site.config["title"], lang.strings["tagline"]))
    for path, slug, title, tagline in targets:
        img = Image.new("RGB", (1200, 630), colors.get(slug, colors.get("default", "#1f2937")))
        d = ImageDraw.Draw(img)
        d.text((80, 200), title, font=font(84), fill="white")
        wrapped = wrap(tagline, 46)
        d.text((80, 320), wrapped, font=font(38, bold=False), fill="#e5e7eb", spacing=12)
        d.text((80, 540), site.config["title"], font=font(30), fill="#d1d5db")
        target = out / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        img.save(target, optimize=True)


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
    ads_txt(site, out)
    llms_txt(site, out)
    feed(site, out)
    og_images(site, out)
    copy_static(out)

    n_games = sum(1 for p in site.pages if p.is_game and p.lang is site.default)
    langs = ", ".join(l.key for l in site.langs)
    print(f"built {len(site.pages)} pages ({n_games} games, {langs}) -> {out}")


if __name__ == "__main__":
    main()

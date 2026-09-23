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
                 /play/<slug>/          the game file, plus the share button
                                        (one copy: games have no language)
                 /animations/<slug>/    story page for one animation
                 /fr/animations/<slug>/ the same story in French
                 /watch/<slug>/         the animation's folder, copied as it is
                                        (sounds and pictures included)
                 /<slug>/, /fr/<slug>/  any other content page (about, ...)
                 /404.html              one page, all languages on it
4. extras()    sitemap.xml, robots.txt, ads.txt, llms.txt, feed.xml,
               og/<slug>.png (per language: og/fr/<slug>.png)
5. copy()      static/ -> dist/static/, shots/ -> dist/shots/

Screenshots
-----------
shots/<slug>.png is a picture of the game, taken in a real browser by
scripts/shots.py and committed like the game itself. The build never opens a
browser: it copies the file and points the card, the story page and the share
image at it. No file for a slug is not an error — that game falls back to the
plain coloured card, and the build says so on the console.

Animations
----------
Not everything here is a game. An animation is a folder, animations/<slug>/,
with its index.html and whatever it loads beside it (audio/, pictures). The
whole folder is published as it is under /watch/<slug>/, so the relative paths
inside it keep working; nothing is added to it, not even the share button,
which would sit on its controls. Its story page embeds it at 16:9 and lists it
in its own section on the home page, under the games.

Its card and share image are a picture that comes with the folder (`picture`
in the front matter, already 16:9), not a screenshot taken by scripts/shots.py.

Share button
------------
A shared score should bring someone back here, so the copy of the game that is
published under /play/<slug>/ gets templates/share.html added just before its
</body>: a small Share button in the corner, and a fix for the Share score
buttons the games already have, which send the address of the bare game file
instead of the game's page. The file in games/ is never touched — it stays the
game as it was vibe coded, and still plays on its own with none of this.

site.yaml's `scores` says where each game keeps the player's best score in the
browser, so the button can say it. A game missing from that list shares without
a score.

Languages
---------
languages.yaml lists them and holds every word that is not part of a page.
The default language sits at the root, the others under /<key>/. Pages live in
content/<key>/<slug>.md, one folder per language, same file name on both sides.

A translation only has to carry the words: title, slug, tagline and the body.
Everything else in its front matter (game, date, iterations, prompts, tags,
draft) is inherited from the same slug in the default language, so the numbers
can never drift between two versions of the same story.

Feedback form
-------------
Nothing on this site can receive a form: there is no server. So the feedback
block built into every page (templates/feedback.html) is a link to a form
hosted by Tally, which emails the answers. site.yaml's tally_form_id switches
it on; empty means no block at all. It is a link and not an embedded form on
purpose, so that no page here loads anything from another site until a visitor
chooses to click.

Content model (front matter keys)
---------------------------------
title        required
slug         required, unique inside its language, used in the URL
date         YYYY-MM-DD; games are listed newest first
tagline      one line under the title, also the meta description
game         path to the playable file, e.g. games/aisle-be-back/index.html
             -> its presence makes the page a *game* page
animation    path to the animation, e.g. animations/le-lion-et-le-rat/index.html
             -> its presence makes the page an *animation* page
picture      animation only: the 16:9 picture in its folder, for the card and
             the share image, e.g. vignette-clemence.jpg
duration     animation only: how long it runs, minutes:seconds, e.g. "2:34"
narration    animation only: the language it is told in, e.g. fr
based_on     animation only: the text it tells, {title, author, year}
seo_title    optional: a longer title for search engines and shares; the page
             itself keeps `title`
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
SHOTS = ROOT / "shots"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"

FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)

# Front matter keys a translation inherits from the default language when it
# does not set them itself. Only the words are expected in a translated file.
INHERITED = ("game", "animation", "picture", "duration", "narration", "based_on",
             "date", "iterations", "prompts", "tags", "draft", "session")

# What templates/share.html says, in every language. A language that has not
# translated them falls back to the default language's words.
SHARE_WORDS = ("share_button", "share_score", "share_best", "share_invite", "share_copied")


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
    def is_animation(self) -> bool:
        return bool(self.meta.get("animation"))

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
        if self.is_game:
            return f"{p}/games/{self.slug}/"
        if self.is_animation:
            return f"{p}/animations/{self.slug}/"
        return f"{p}/{self.slug}/"

    @property
    def play_url(self) -> str:
        """The game itself. One copy for every language: it has no words of ours."""
        return f"/play/{self.slug}/"

    @property
    def watch_url(self) -> str:
        """The animation itself, with its sounds beside it. One copy, like the games."""
        return f"/watch/{self.slug}/"

    @property
    def animation_dir(self) -> Path:
        return (ROOT / self.meta["animation"]).parent

    @property
    def picture_file(self) -> Path | None:
        """The animation's own 16:9 picture, if its front matter names one."""
        name = self.meta.get("picture")
        f = self.animation_dir / str(name) if self.is_animation and name else None
        return f if f and f.is_file() else None

    @property
    def picture_url(self) -> str | None:
        return f"{self.watch_url}{self.meta['picture']}" if self.picture_file else None

    @property
    def seconds(self) -> int:
        """duration "2:34" -> 154. Zero when there is none."""
        m = re.fullmatch(r"(\d+):(\d{2})", str(self.meta.get("duration") or ""))
        return int(m.group(1)) * 60 + int(m.group(2)) if m else 0

    @property
    def shot_file(self) -> Path | None:
        """The screenshot of the game on disk, if one was taken."""
        f = SHOTS / f"{self.slug}.png"
        return f if self.is_game and f.is_file() else None

    @property
    def shot_url(self) -> str | None:
        """Where that screenshot sits on the site. One copy for every language."""
        return f"/shots/{self.slug}.png" if self.shot_file else None

    @property
    def og_path(self) -> str:
        """Share image, one per language because the tagline is on it.

        An animation shares its own picture instead: it already is a 16:9
        image made for that, with nothing on it to translate.
        """
        if self.picture_url:
            return self.picture_url
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

    def animations(self, lang: Lang) -> list[Page]:
        pages = (p for p in self.pages if p.is_animation and p.lang is lang)
        return sorted(pages, key=lambda p: p.date, reverse=True)

    def others(self, lang: Lang) -> list[Page]:
        return [p for p in self.pages
                if not p.is_game and not p.is_animation and p.lang is lang]

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


def tally_id(value: object) -> str:
    """Accept the form id (wkKqJb) or the whole address Tally shows you."""
    text = str(value or "").strip().rstrip("/")
    return text.rsplit("/", 1)[-1]


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
    config["tally_form_id"] = tally_id(config.get("tally_form_id"))

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
        if p.is_game and p.is_animation:
            sys.exit(f"{p.source}: a page is a game or an animation, not both")
        if p.is_animation:
            anim_file = ROOT / p.meta["animation"]
            if not anim_file.is_file():
                sys.exit(f"{p.source}: animation file not found: {p.meta['animation']}")
            if anim_file.parent.name != p.slug:
                sys.exit(f"{p.source}: the animation should sit in animations/{p.slug}/")
            if not p.meta.get("date"):
                sys.exit(f"{p.source}: animation pages need a 'date'")
            if p.meta.get("picture") and not p.picture_file:
                sys.exit(f"{p.source}: picture not found in {p.meta['animation']}'s folder: {p.meta['picture']}")
            if p.meta.get("duration") and not p.seconds:
                sys.exit(f"{p.source}: duration should look like \"2:34\", got '{p.meta['duration']}'")

    # Missing translations are not an error: the language menu falls back to
    # the home page of that language. Say it out loud so it is not forgotten.
    for lang in site.langs:
        if lang is site.default:
            continue
        missing = [p.slug for p in site.pages
                   if p.lang is site.default and not site.translation(p.slug, lang)]
        if missing:
            print(f"note: no {lang.key} version of {', '.join(sorted(missing))}")

    # A game without a picture is not an error either: its card stays the
    # plain coloured one. Say it out loud so it is not forgotten.
    bare = sorted(p.slug for p in site.pages
                  if p.is_game and p.lang is site.default and not p.shot_file)
    if bare:
        print(f"note: no screenshot for {', '.join(bare)} (python scripts/shots.py)")
    bare = sorted(p.slug for p in site.pages
                  if p.is_animation and p.lang is site.default and not p.picture_file)
    if bare:
        print(f"note: no picture for the animation {', '.join(bare)} ('picture' in its front matter)")

    # The share button needs its words, and needs to know which game it is on.
    missing_words = [k for k in SHARE_WORDS if not site.default.strings.get(k)]
    if missing_words:
        sys.exit(f"languages.yaml: {site.default.key} needs {', '.join(missing_words)}")
    slugs = {p.slug for p in site.pages if p.is_game}
    for slug, where in (site.config.get("scores") or {}).items():
        if slug not in slugs:
            sys.exit(f"site.yaml: scores has '{slug}', which is not a game")
        if not str((where or {}).get("key") or "").strip():
            sys.exit(f"site.yaml: scores.{slug} needs a 'key'")

    client = str(site.config.get("adsense_client") or "").strip()
    if client and not re.fullmatch(r"ca-pub-\d{16}", client):
        sys.exit(f"site.yaml: adsense_client should look like ca-pub-0000000000000000, got '{client}'")

    # No feedback form is a choice, not a mistake; a mistyped one is a mistake.
    form = str(site.config.get("tally_form_id") or "")
    if not form:
        print("note: site.yaml has no tally_form_id, so no page gets a feedback button")
    elif not re.fullmatch(r"[A-Za-z0-9]{4,24}", form):
        sys.exit(f"site.yaml: tally_form_id should look like wkKqJb, got '{form}'")


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
    env.globals["animations"] = [a for a in site.animations(lang) if not a.draft]
    env.globals["languages"] = site.langs
    env.globals["alternates"] = alternates
    env.globals["now"] = dt.datetime.now(dt.timezone.utc)
    env.filters["isodate"] = lambda d: d.isoformat()
    env.filters["nicedate"] = lambda d: nicedate(d, lang.key)
    env.filters["runtime"] = lambda s: lang.strings["runtime"].format(m=s // 60, s=f"{s % 60:02d}")
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


BODY_END = re.compile(r"</body\s*>", re.I)


def playable(site: Site, page: Page, env: Environment) -> str:
    """The game file as it is, with the site's share button slipped in at the end.

    Nothing is written back to games/: that file stays the game as it was vibe
    coded, and still plays on its own, share button or not. A game with no
    </body> (none so far) simply gets the button appended.
    """
    raw = (ROOT / page.meta["game"]).read_text(encoding="utf-8")
    words = {
        l.key: {k: l.strings.get(k, site.default.strings[k]) for k in SHARE_WORDS}
        for l in site.langs
    }
    block = env.get_template("share.html").render(
        page=page,
        words=words,
        default_lang=site.default.key,
        score=(site.config.get("scores") or {}).get(page.slug),
        share_url=site.config["url"].rstrip("/") + page.url,
    )
    ends = list(BODY_END.finditer(raw))
    if not ends:
        return raw + "\n" + block
    cut = ends[-1].start()
    return raw[:cut] + block + raw[cut:]


def render(site: Site, out: Path) -> None:
    for lang in site.langs:
        env = make_env(site, lang)
        write(out, f"{lang.home}index.html", env.get_template("index.html").render(page=None))
        for p in site.pages:
            if p.lang is not lang:
                continue
            name = "game" if p.is_game else "animation" if p.is_animation else "page"
            tpl = env.get_template(f"{name}.html")
            write(out, f"{p.url}index.html", tpl.render(page=p))

    # One copy of each game, shared by every language, with the share button
    # added on the way out.
    share_env = make_env(site, site.default)
    for p in site.pages:
        if p.is_game and p.lang is site.default:
            dst = out / p.play_url.lstrip("/") / "index.html"
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(playable(site, p, share_env), encoding="utf-8")

    # One copy of each animation, the whole folder exactly as it was made: its
    # sounds and pictures are loaded from beside it.
    for p in site.pages:
        if p.is_animation and p.lang is site.default:
            shutil.copytree(p.animation_dir, out / p.watch_url.lstrip("/"), dirs_exist_ok=True)

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
    urls += [p.watch_url for p in site.public if p.is_animation and p.lang is site.default]
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
        shown = [a for a in site.animations(lang) if not a.draft]
        if shown:
            lines += ["", f"## {s['animations_heading']}", ""]
        for a in shown:
            lines.append(f"- [{a.title}]({base}{a.url}): {a.tagline} {s['watch']}: {base}{a.watch_url}")
        lines += ["", "## Pages", ""]
        for p in site.others(lang):
            if not p.draft:
                lines.append(f"- [{p.title}]({base}{p.url})")
        write(out, f"{lang.home}llms.txt", "\n".join(lines) + "\n")


def feed(site: Site, out: Path) -> None:
    base = site.config["url"].rstrip("/")
    for lang in site.langs:
        items = []
        stories = sorted(site.games(lang) + site.animations(lang), key=lambda p: p.date, reverse=True)
        for g in stories:
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
    """1200x630 share images: the game's own screenshot beside its name.

    A page with no screenshot (the home page, About, a game whose picture has
    not been taken yet) gets the plain coloured card the site started with.
    """
    from PIL import Image, ImageDraw, ImageFont

    def font(size: int, bold: bool = True):
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        for base in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "C:/Windows/Fonts"):
            f = Path(base) / name
            if f.exists():
                return ImageFont.truetype(str(f), size)
        return ImageFont.load_default()

    colors = site.config.get("og_colors", {})
    targets = [(p.og_path, p.slug, p.title, p.tagline, p.shot_file)
               for p in site.public if not p.picture_file]
    for lang in site.langs:
        folder = "og" if lang.is_default else f"og/{lang.key}"
        targets.append((f"/{folder}/default.png", "default",
                        site.config["title"], lang.strings["tagline"], None))

    small, footer = font(38, bold=False), font(30)
    for path, slug, title, tagline, shot in targets:
        img = Image.new("RGB", (1200, 630), colors.get(slug, colors.get("default", "#1f2937")))
        column = 1040                       # room the words have, left to right
        if shot:
            picture = phone_picture(shot, height=470)
            img.paste(picture, (1200 - 80 - picture.width, 80), picture)
            column = 1200 - 80 - picture.width - 60 - 80

        d = ImageDraw.Draw(img)
        # The title takes the biggest size that still fits next to the picture:
        # a long name on one unbreakable word must not run into the phone.
        title_lines, big = fit(title, column, font, max_lines=2)
        step = round(big.size * 1.2) if hasattr(big, "size") else 100
        tag_lines = wrap(tagline, small, column, max_lines=3)
        block = len(title_lines) * step + 30 + len(tag_lines) * 52
        y = 130 + max(0, (370 - block) // 2)
        for line in title_lines:
            d.text((80, y), line, font=big, fill="white")
            y += step
        y += 30
        for line in tag_lines:
            d.text((80, y), line, font=small, fill="#e5e7eb")
            y += 52
        d.text((80, 540), site.config["title"], font=footer, fill="#d1d5db")

        target = out / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        img.save(target, optimize=True)


def phone_picture(shot: Path, height: int):
    """The screenshot as a little phone: rounded corners and a thin light edge."""
    from PIL import Image, ImageDraw

    im = Image.open(shot).convert("RGBA")
    width = round(im.width * height / im.height)
    im = im.resize((width, height), Image.LANCZOS)
    box, radius = (0, 0, width - 1, height - 1), round(width * 0.10)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius, fill=255)
    im.putalpha(mask)
    ImageDraw.Draw(im).rounded_rectangle(box, radius, outline=(255, 255, 255, 110), width=3)
    return im


def fit(text: str, width: int, font_of, max_lines: int = 2):
    """The title, at the biggest size that still fits the room it has."""
    for size in (84, 74, 64, 54, 46):
        f = font_of(size)
        lines = wrap(text, f, width, max_lines=max_lines)
        if all(f.getlength(line) <= width for line in lines):
            return lines, f
    return lines, f


def wrap(text: str, font, width: int, max_lines: int = 3) -> list[str]:
    """Break a sentence into lines that fit, measured in the font that draws it."""
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if current and font.getlength(trial) > width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines[:max_lines]


def copy_static(out: Path) -> None:
    if STATIC.is_dir():
        shutil.copytree(STATIC, out / "static", dirs_exist_ok=True)


def copy_shots(out: Path) -> None:
    """The game screenshots, one copy for the whole site (they have no words)."""
    if SHOTS.is_dir():
        shutil.copytree(SHOTS, out / "shots", dirs_exist_ok=True)


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
    copy_shots(out)

    n_games = sum(1 for p in site.pages if p.is_game and p.lang is site.default)
    n_anims = sum(1 for p in site.pages if p.is_animation and p.lang is site.default)
    langs = ", ".join(l.key for l in site.langs)
    print(f"built {len(site.pages)} pages ({n_games} games, {n_anims} animations, {langs}) -> {out}")


if __name__ == "__main__":
    main()

# ohlala.cloud — instructions for Claude

Static site of small vibe-coded phone games, each with the story of how it was
prompted. Python build (`build.py`), deployed to S3 + CloudFront by GitHub
Actions on every push to `main`. Nothing runs on a server.

The site is bilingual: English at the root, French under `/fr/`. The games
themselves are not translated — there is one copy of each, at `/play/<slug>/`,
shared by both languages.

The owner does not read the code. Explain choices in plain words, keep things
small, and never add a framework or a build step beyond `python build.py`.

## Publishing a new game (the routine)

1. Copy the finished single-file game to `games/<slug>/index.html`.
   `<slug>` is lowercase, dashes only, and becomes the URL.
   Do not edit the game file; it must stay playable standalone.
2. Write `content/en/<slug>.md` with this front matter (all of it):
   ```yaml
   ---
   title: Game Name
   slug: <slug>                 # must match the folder and the file name
   date: YYYY-MM-DD
   tagline: One funny sentence. Doubles as the meta description.
   game: games/<slug>/index.html
   iterations: N                # versions published during the build session
   prompts: N                   # messages the owner sent during the build session
   session: "Thursday evening, 21:05 to 22:12"
   tags: [arcade, mobile]
   ---
   ```
   Body: `## The prompt` (the opening request, quoted verbatim in a `>` block),
   `## The iterations` (numbered list, one line per version, driven by the owner's
   own feedback quotes), `## What I learned` (two or three sentences). Under
   400 words. English. No technical details about the code.
   Quote the owner's messages exactly as typed (typos are fine); when
   translating a French message, say so.
3. Write the French version in `content/fr/<slug>.md`. Same slug, same file
   name; only the words change. Its front matter carries just `title`, `slug`,
   `tagline` and `session` — the date, the counts, the tags and the game file
   are inherited from the English file, so the numbers can never disagree.
   Keep the owner's quotes in the language he typed them in and say so in a
   short aside (`(tapés en anglais, traduits ici)`), rather than putting words
   in his mouth.
4. Add a colour for the slug under `og_colors` in `site.yaml`. It is the
   background of the share image, and the card's colour while its picture
   loads (or instead of it, if there is no picture).
5. Take the picture of the game: `python scripts/shots.py`. It runs the game in
   a real browser and saves `shots/<slug>.png`, which becomes the card on the
   home page, the phone on the story page and the share image. Most games open
   on a title screen, so add a line for the slug in the `RECIPES` list at the
   top of that script (`"tap, wait 2s"`) to photograph the game being played
   instead. Look at the file before committing it; if the moment it caught is a
   dull one, change the waits and run `python scripts/shots.py <slug>` again.
   It needs Playwright, which the site itself does not: `pip install playwright`
   then `playwright install chromium`, once.
6. Run `python build.py`. It fails loudly if a slug or file is wrong, and
   prints a note listing any page that has no French version or no picture yet.
7. Commit with a message like `Add <Game Name>` and push. The workflow builds,
   syncs to S3 and invalidates CloudFront; the page is live in about a minute.

Use `draft: true` in the English front matter to build a page without listing
it (`python build.py --drafts` to include it locally); the French version
inherits the draft flag.

## Languages

`languages.yaml` holds every word that is not part of a page: the tagline, the
description, the menu, the buttons, the 404. One block per language, the same
keys on both sides. `default: en` is the language that sits at the root; the
others get a `/<key>/` prefix and a `content/<key>/` folder.

A missing translation is not an error. The page simply does not exist in that
language, the language menu points at that language's home page instead, and
the build says so on the console.

The visitor's language is chosen in the browser, not on the server: a small
script in the page head sends a first-time visitor to the version matching the
browser's own preference, and after that the last flag clicked wins (kept in
local storage, no cookie, nothing sent anywhere). Adding a language therefore
needs no AWS change at all.

## Layout

```
build.py            the whole build; docstring at the top describes the pipeline
site.yaml           title, URL, author, Tally form id, AdSense id, OG colours
languages.yaml      the languages, and every word outside the pages
content/en/*.md     one file per page; a `game:` key makes it a game page
content/fr/*.md     the same pages in French, same file names
games/<slug>/       the playable files, copied untouched to /play/<slug>/
shots/<slug>.png    a picture of each game, taken by scripts/shots.py and
                    committed like the games; the build only copies it
templates/*.html    Jinja2: base, index, game, page, 404, feedback
                    feedback.html is the block base.html puts at the bottom of
                    every page: a link to the Tally form, built only when
                    site.yaml has a tally_form_id. See the README to set it up.
static/             style.css, favicon.svg
infra/site.yaml     CloudFormation for the whole AWS side (deploy in us-east-1)
scripts/shots.py    takes the game pictures (needs Playwright; the build
                    itself never opens a browser)
scripts/stats.py    visitor counts from CloudFront logs (no cookies)
.github/workflows/  build on PR, build + deploy on main
```

URLs: `/` home, `/games/<slug>/` story page, `/play/<slug>/` the game itself,
`/about/`, `/sitemap.xml`, `/feed.xml`, `/llms.txt`, `/og/<slug>.png`,
`/shots/<slug>.png`, and the same set under `/fr/` (except the games, the
pictures and the sitemap, which are shared).

## Checks before pushing

- `python build.py` succeeds.
- The new game page and the home page look right at phone width (390px), in
  both languages — French sentences are longer and break differently.
- The game's card on the home page shows the game, not a flat colour, and the
  story page shows it in the phone frame.
- Front matter counts (`iterations`, `prompts`) match what happened in the
  build conversation; do not guess them.

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

If the game keeps a best score in the browser, add a line for the slug under
`scores` in `site.yaml` saying where: the share button in the corner of the
game then says that score. A game missing from that list still gets the
button; it just shares the game without a number in it.

## Publishing an animation

Not everything is a game. An animation (a short story to watch and listen to)
has its own section on the home page, under the games.

1. Copy the whole delivered folder to `animations/<slug>/`: its `index.html`
   and everything it loads beside it (`audio/`, pictures). Do not edit any of
   it; it is published as it is under `/watch/<slug>/`, and nothing is added to
   it (no share button).
2. `content/en/<slug>.md`, front matter:
   ```yaml
   ---
   title: Le Lion et le Rat
   slug: <slug>
   date: YYYY-MM-DD
   tagline: One sentence. Doubles as the meta description.
   seo_title: A longer title for search engines and shares (optional)
   animation: animations/<slug>/index.html
   picture: vignette.jpg        # a 16:9 picture in that folder: card + share image
   duration: "2:34"             # minutes:seconds
   narration: fr                # the language it is told in
   based_on: {title: ..., author: ..., year: ...}   # the text it tells, if any
   tags: [animation]
   ---
   ```
   `iterations`, `prompts` and `session` work as for games, but only when the
   real numbers are known.
3. `content/fr/<slug>.md`: `title`, `slug`, `tagline`, `seo_title`. The rest is
   inherited. Keep the credits (voice, sounds, text) at the end of both pages;
   a free ElevenLabs voice must credit ElevenLabs.
4. A colour under `og_colors` in `site.yaml`. No `scripts/shots.py`: the
   picture comes with the folder.
5. `python build.py`, commit, push. Sound files (`.mp3`) are cached 30 days by
   browsers: to change one, give it a new file name.

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
animations/<slug>/  an animation's whole folder, copied untouched to /watch/<slug>/
shots/<slug>.png    a picture of each game, taken by scripts/shots.py and
                    committed like the games; the build only copies it
templates/*.html    Jinja2: base, index, game, animation, page, 404, feedback, share
                    feedback.html is the block base.html puts at the bottom of
                    every page: a link to the Tally form, built only when
                    site.yaml has a tally_form_id. See the README to set it up.
                    share.html is the block build.py puts at the bottom of every
                    game when it copies it to /play/. See "The share button".
static/             style.css, favicon.svg
infra/site.yaml     CloudFormation for the whole AWS side (deploy in us-east-1)
scripts/shots.py    takes the game pictures (needs Playwright; the build
                    itself never opens a browser)
scripts/stats.py    visitor counts from CloudFront logs (no cookies)
.github/workflows/  build on PR, build + deploy on main
```

URLs: `/` home, `/games/<slug>/` story page, `/play/<slug>/` the game itself,
`/animations/<slug>/` an animation's story page, `/watch/<slug>/` the animation,
`/about/`, `/sitemap.xml`, `/feed.xml`, `/llms.txt`, `/og/<slug>.png`,
`/shots/<slug>.png`, and the same set under `/fr/` (except the games, the
animations, the pictures and the sitemap, which are shared).

## The share button

A score is worth sharing only if it brings someone back here, so every game
published under `/play/<slug>/` gets `templates/share.html` added just before
its `</body>` — a small Share button in the corner, which sends the player's
best score and the address of the game's story page (`/games/<slug>/`, the one
with the picture and the link to the other games).

The same block also fixes the Share score buttons the games already have.
Those send the address of the file they are running in, which is the bare game
on a page with no title, no picture and no way back to the site; the message
keeps its score, only the link is swapped.

The files in `games/` are never touched by any of this. They stay exactly the
games that were vibe coded and still play on their own, share button or not —
that is why the button is added by the build and not written into the game.

`scores` in `site.yaml` says, one line per game, where each game keeps the best
score in the browser. `languages.yaml` holds the button's words.

## Checks before pushing

- `python build.py` succeeds.
- The new game page and the home page look right at phone width (390px), in
  both languages — French sentences are longer and break differently.
- The game's card on the home page shows the game, not a flat colour, and the
  story page shows it in the phone frame.
- Front matter counts (`iterations`, `prompts`) match what happened in the
  build conversation; do not guess them.
- The Share button in the corner of the game is there and does not sit on top
  of anything the game itself draws in that corner.

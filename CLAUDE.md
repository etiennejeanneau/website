# ohlala.cloud — instructions for Claude

Static site of small vibe-coded phone games, each with the story of how it was
prompted. Python build (`build.py`), deployed to S3 + CloudFront by GitHub
Actions on every push to `main`. Nothing runs on a server.

The owner does not read the code. Explain choices in plain words, keep things
small, and never add a framework or a build step beyond `python build.py`.

## Publishing a new game (the routine)

1. Copy the finished single-file game to `games/<slug>/index.html`.
   `<slug>` is lowercase, dashes only, and becomes the URL.
   Do not edit the game file; it must stay playable standalone.
2. Write `content/<slug>.md` with this front matter (all of it):
   ```yaml
   ---
   title: Game Name
   slug: <slug>                 # must match the folder
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
3. Add a colour for the slug under `og_colors` in `site.yaml` (share image and card).
4. Run `python build.py`. It fails loudly if a slug or file is wrong.
5. Commit with a message like `Add <Game Name>` and push. The workflow builds,
   syncs to S3 and invalidates CloudFront; the page is live in about a minute.

Use `draft: true` in the front matter to build a page without listing it
(`python build.py --drafts` to include it locally).

## Layout

```
build.py            the whole build; docstring at the top describes the pipeline
site.yaml           title, URL, author, Tally form id, AdSense id, OG colours
content/*.md        one file per page; a `game:` key makes it a game page
games/<slug>/       the playable files, copied untouched to /play/<slug>/
templates/*.html    Jinja2: base, index, game, page, 404
static/             style.css, favicon.svg
infra/site.yaml     CloudFormation for the whole AWS side (deploy in us-east-1)
scripts/stats.py    visitor counts from CloudFront logs (no cookies)
.github/workflows/  build on PR, build + deploy on main
```

URLs: `/` home, `/games/<slug>/` story page, `/play/<slug>/` the game itself,
`/about/`, `/sitemap.xml`, `/feed.xml`, `/llms.txt`, `/og/<slug>.png`.

## Checks before pushing

- `python build.py` succeeds.
- The new game page and the home page look right at phone width (390px).
- Front matter counts (`iterations`, `prompts`) match what happened in the
  build conversation; do not guess them.

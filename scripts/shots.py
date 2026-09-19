#!/usr/bin/env python3
"""
Take a picture of each game, for the cards on the home page and the stories.

Why this is a separate script: photographing a game means actually running it
in a browser, and the site's build has to stay `python build.py` with nothing
else installed. So the pictures are taken here, by hand, once per game, and
committed to the repo like the games themselves. `build.py` only copies them.

    pip install playwright
    playwright install chromium
    python scripts/shots.py                 # only games with no picture yet
    python scripts/shots.py --all           # all of them, again
    python scripts/shots.py pigeon-in-paris # just that one

Each picture is what a phone shows: 390 by 844 points, taken at double
resolution, saved to shots/<slug>.png. Nothing else has to be done: the build
picks up any file it finds there, and a game without one falls back to the
plain coloured card the site had before.

A game usually opens on a title screen. RECIPES below says what to do before
the picture is taken, one line per game, in plain words:

    "tap, wait 2s"           tap the middle of the screen, then wait
    "tap #play, wait 1s"     tap that button (an id from the game's own HTML)
    "tap 195 610"            tap that exact point
    "wait 3s"                just wait

A game with no line here gets its title screen, which is a fine picture too.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAMES = ROOT / "games"
SHOTS = ROOT / "shots"

# What a phone shows. Doubled when saving, so the picture stays sharp on the
# screens that count (everyone's).
WIDTH, HEIGHT, SCALE = 390, 844, 2

# Time given to the game to load and finish its opening animation before the
# recipe starts. Generous on purpose: a picture taken too early is a blank one.
SETTLE = 2000

# One line per game: what to do before the picture is taken. See the top of
# this file for the words it understands. Nothing here = the title screen.
RECIPES = {
    "aisle-be-back":     "tap, wait 2.2s",
    "desktop-tycoon":    "tap #m-ok, wait 1s",
    "every-drop-counts": "tap #play, wait 3s",
    "pigeon-in-paris":   "tap, wait 0.9s, tap, wait 0.7s",
    "whack-a-president": "tap 195 607, wait 4s, tap 195 300, wait 0.3s, tap 65 300, wait 1.2s",
}


def steps(recipe: str) -> list[tuple]:
    """Turn one plain-words line into the taps and waits to perform."""
    out = []
    for raw in recipe.split(","):
        step = raw.strip()
        if not step:
            continue
        m = re.fullmatch(r"wait\s+([\d.]+)\s*(m?s)", step)
        if m:
            out.append(("wait", float(m.group(1)) * (1 if m.group(2) == "ms" else 1000)))
            continue
        m = re.fullmatch(r"tap\s+(\d+)\s+(\d+)", step)
        if m:
            out.append(("point", int(m.group(1)), int(m.group(2))))
            continue
        m = re.fullmatch(r"tap\s+(\S+)", step)
        if m:
            out.append(("element", m.group(1)))
            continue
        if step == "tap":
            out.append(("point", WIDTH // 2, HEIGHT // 2))
            continue
        sys.exit(f"shots.py: don't know how to '{step}' (see the top of this file)")
    return out


def capture(browser, slug: str) -> Path:
    page_file = GAMES / slug / "index.html"
    if not page_file.is_file():
        sys.exit(f"shots.py: no game at games/{slug}/index.html")

    context = browser.new_context(
        viewport={"width": WIDTH, "height": HEIGHT},
        device_scale_factor=SCALE,
        is_mobile=True,
        has_touch=True,
    )
    page = context.new_page()
    page.goto(page_file.as_uri())
    page.wait_for_timeout(SETTLE)

    for step in steps(RECIPES.get(slug, "")):
        if step[0] == "wait":
            page.wait_for_timeout(step[1])
        elif step[0] == "point":
            page.touchscreen.tap(step[1], step[2])
        else:
            try:
                page.click(step[1], timeout=3000)
            except Exception:
                # A button that moved or was renamed: say so and carry on, so
                # the run still produces a picture instead of nothing.
                print(f"  {slug}: nothing to tap at '{step[1]}', skipped")

    SHOTS.mkdir(exist_ok=True)
    target = SHOTS / f"{slug}.png"
    page.screenshot(path=target)
    context.close()
    shrink(target)
    return target


def shrink(path: Path) -> None:
    """Keep the file small: these games are flat, cartoonish drawings that use
    a few hundred colours at most, so storing 256 of them makes the picture
    about three times lighter with nothing visible lost. Still a PNG."""
    from PIL import Image

    im = Image.open(path).convert("RGB")
    im.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG).save(path, optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Screenshots of the games.")
    ap.add_argument("slugs", nargs="*", help="which games; default: those with no picture")
    ap.add_argument("--all", action="store_true", help="redo every game")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("shots.py needs Playwright:\n  pip install playwright\n  playwright install chromium")

    every = sorted(p.parent.name for p in GAMES.glob("*/index.html"))
    if args.slugs:
        wanted = args.slugs
    elif args.all:
        wanted = every
    else:
        wanted = [s for s in every if not (SHOTS / f"{s}.png").is_file()]

    if not wanted:
        print("every game already has a picture (--all to take them again)")
        return

    with sync_playwright() as pw:
        # CHROME_PATH: use a Chromium already on this machine instead of the
        # one Playwright downloads. --no-sandbox is for running in a container.
        exe = os.environ.get("CHROME_PATH")
        browser = pw.chromium.launch(executable_path=exe, args=["--no-sandbox"]) if exe \
            else pw.chromium.launch(args=["--no-sandbox"])
        for slug in wanted:
            target = capture(browser, slug)
            print(f"{slug} -> {target.relative_to(ROOT)} ({target.stat().st_size // 1024} kB)")
        browser.close()


if __name__ == "__main__":
    main()

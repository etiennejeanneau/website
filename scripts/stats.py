#!/usr/bin/env python3
"""
Visitor stats from CloudFront standard logs. No cookies, no JavaScript: the
CDN already writes one line per request, this script just counts them.

A "visitor" is a (day, client IP, user agent) triple. That's a rough proxy:
it undercounts people behind one NAT and overcounts people whose IP changes.
Good enough to see whether anyone is coming.

A "visit" is one run of requests from the same visitor with no gap longer than
half an hour. Three things are read off each visit:

  a browser?  A browser asks for the style sheet, the icon and the game
              pictures all by itself, along with the page. Something that takes
              the HTML and nothing else, for a whole visit, is a machine
              whatever name it gives for itself. Everything is cached for five
              minutes only, so even a long visit re-asks for the style; a
              returning reader is not mistaken for a robot. The one thing that
              asks for the share picture and nothing else is a chat app drawing
              the card under a link somebody sent: those are counted apart,
              because a link being passed around is good news, not a scraper.
              --agents lists the names behind each group.
  where from  The log never names the country. This is the country of the
              CloudFront city that served the request, so someone in Belgium
              may well appear as France or the Netherlands. Read these as
              neighbourhoods, not passports.
  how long    The time between the first request of a visit and the last. It is
              a floor, not the truth: a game talks to nobody once it is
              running, so twenty minutes of playing leaves no line in the log.
              Reading the site shows up; playing does not.

Usage:
  python scripts/stats.py --bucket ohlala-cloud-logs --days 7
  python scripts/stats.py --bucket ohlala-cloud-logs --days 30 --pages
  python scripts/stats.py --bucket ohlala-cloud-logs --days 7 --agents

Needs: boto3 and AWS credentials with s3:GetObject/ListBucket on the log bucket.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import io
import statistics
import urllib.parse
from collections import Counter, defaultdict

import boto3

BOTS = ("bot", "crawl", "spider", "slurp", "facebookexternalhit", "preview", "monitor")

# A new visit starts after this much silence from the same visitor.
VISIT_GAP = dt.timedelta(minutes=30)

# The files a browser fetches on its own, with nobody clicking anything: the
# style sheet, the icon, the pictures of the games, and the pictures and sounds
# an animation is made of. Asking for none of them, all visit long, is what
# gives a scraper away. "/watch/" catches the animation's own files only: the
# page it sits on, /watch/<slug>/, ends in a slash and is counted above as a
# page like any other.
BROWSER_FILES = ("/static/", "/shots/", "/favicon.ico", "/watch/")

# The share picture, named in the page head and fetched by nothing else. A
# browser never asks for it; WhatsApp, Slack, Discord and the rest ask for it
# and nothing more when they draw the little card under a shared link. So a
# visit that took this and no style sheet is a link being passed around.
PREVIEW_FILES = ("/og/",)

KINDS = ("a browser", "a link being previewed", "a game and nothing else", "the HTML alone")

# How long a visit lasted, in words.
LENGTHS = ((30, "under 30 s"), (120, "30 s to 2 min"), (600, "2 to 10 min"),
           (1800, "10 to 30 min"), (None, "over 30 min"))

# The log says which CloudFront city served the request (IAD, CDG, ...) and
# never the visitor's country. This turns the city into the country around it.
# A city missing from the list prints as "? XXX"; add it there and it stops
# being a mystery.
EDGE_COUNTRIES = {
    "United States": "IAD DFW ORD JFK EWR LGA LAX BUR SFO SJC SEA PDX DEN PHX MIA ATL "
                     "BOS PHL IAH MCI MSP DTW CLT TPA MCO SLC LAS SAN STL IND CMH BNA "
                     "AUS OMA PIT RIC HIO",
    "Canada": "YUL YYZ YTO YVR YYC",
    "Mexico": "MEX QRO",
    "Brazil": "GRU GIG FOR",
    "Argentina": "EZE",
    "Chile": "SCL",
    "Colombia": "BOG",
    "Peru": "LIM",
    "United Kingdom": "LHR LON LCY MAN",
    "Ireland": "DUB",
    "France": "CDG MRS",
    "Netherlands": "AMS",
    "Belgium": "BRU",
    "Germany": "FRA DUS MUC HAM BER TXL",
    "Switzerland": "ZRH GVA",
    "Austria": "VIE",
    "Italy": "MXP FCO PMO",
    "Spain": "MAD BCN",
    "Portugal": "LIS",
    "Sweden": "ARN",
    "Denmark": "CPH",
    "Norway": "OSL",
    "Finland": "HEL",
    "Poland": "WAW",
    "Czechia": "PRG",
    "Hungary": "BUD",
    "Romania": "OTP",
    "Bulgaria": "SOF",
    "Serbia": "BEG",
    "Estonia": "TLL",
    "Latvia": "RIX",
    "Lithuania": "VNO",
    "Iceland": "KEF",
    "Turkey": "IST",
    "Croatia": "ZAG",
    "Greece": "ATH SKG",
    "Israel": "TLV",
    "United Arab Emirates": "DXB FJR",
    "Saudi Arabia": "RUH JED",
    "Qatar": "DOH",
    "Bahrain": "BAH",
    "Kuwait": "KWI",
    "Oman": "MCT",
    "South Africa": "CPT JNB",
    "Nigeria": "LOS",
    "Kenya": "NBO",
    "Egypt": "CAI",
    "India": "BOM DEL MAA BLR HYD CCU PNQ",
    "Japan": "NRT HND KIX ITM",
    "South Korea": "ICN SEL GMP",
    "Hong Kong": "HKG",
    "Taiwan": "TPE",
    "Singapore": "SIN",
    "Malaysia": "KUL",
    "Thailand": "BKK",
    "Vietnam": "SGN HAN",
    "Philippines": "MNL",
    "Indonesia": "CGK DPS",
    "Australia": "SYD MEL PER BNE ADL",
    "New Zealand": "AKL",
}
COUNTRY_OF = {city: name for name, cities in EDGE_COUNTRIES.items() for city in cities.split()}


def parse_log(blob: bytes):
    """Yield dicts for each request line; fields come from the '#Fields:' header."""
    fields: list[str] = []
    for line in gzip.GzipFile(fileobj=io.BytesIO(blob)).read().decode("utf-8", "replace").splitlines():
        if line.startswith("#Fields:"):
            fields = line.split()[1:]
        elif line and not line.startswith("#"):
            yield dict(zip(fields, line.split("\t")))


def country(edge: str) -> str:
    """Country around the CloudFront city that served the request ('CDG50-P1')."""
    return COUNTRY_OF.get(edge[:3].upper(), f"? {edge[:3].upper()}")


def split_visits(hits: list):
    """Cut one visitor's requests, oldest first, into visits at every long silence."""
    visit: list = []
    for hit in hits:
        if visit and hit[0] - visit[-1][0] > VISIT_GAP:
            yield visit
            visit = []
        visit.append(hit)
    if visit:
        yield visit


def how_long(seconds: float) -> str:
    """Seconds as something readable: 8s, 3m 20s, 1h 05m."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes, secs = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def length_bucket(seconds: float) -> str:
    for limit, label in LENGTHS:
        if limit is None or seconds < limit:
            return label
    return LENGTHS[-1][1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--prefix", default="cloudfront/")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--pages", action="store_true", help="also list the most visited pages")
    ap.add_argument("--agents", action="store_true", help="also list the names visitors gave for themselves")
    args = ap.parse_args()

    since = dt.date.today() - dt.timedelta(days=args.days)
    s3 = boto3.client("s3")
    visitors: dict[str, set] = defaultdict(set)
    pages: Counter = Counter()
    plays: Counter = Counter()
    watched: Counter = Counter()
    hits: dict[tuple, list] = defaultdict(list)
    agents: dict[tuple, str] = {}

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=args.bucket, Prefix=args.prefix):
        for obj in page.get("Contents", []):
            if obj["LastModified"].date() < since:
                continue
            body = s3.get_object(Bucket=args.bucket, Key=obj["Key"])["Body"].read()
            for r in parse_log(body):
                ua = r.get("cs(User-Agent)", "").lower()
                if not r.get("date") or not r.get("time") or any(b in ua for b in BOTS):
                    continue
                uri, status = r.get("cs-uri-stem", ""), r.get("sc-status")
                key = (r.get("c-ip", ""), ua)
                when = dt.datetime.strptime(f"{r['date']} {r['time']}", "%Y-%m-%d %H:%M:%S")
                where = country(r.get("x-edge-location", ""))
                if uri.endswith("/") and status == "200":
                    visitors[r["date"]].add(key)  # an HTML page, handed to a person
                    pages[uri] += 1
                    if uri.startswith("/play/"):
                        plays[uri] += 1
                    elif uri.startswith("/watch/"):
                        watched[uri] += 1
                    hits[key].append((when, "page", uri, where))
                elif uri.startswith(BROWSER_FILES) and status in ("200", "304", "404"):
                    # 304: a browser being told its copy is still good. 404: the
                    # /favicon.ico the games never declare. Both mean a browser.
                    hits[key].append((when, "browser file", uri, where))
                elif uri.startswith(PREVIEW_FILES) and status in ("200", "304"):
                    hits[key].append((when, "share picture", uri, where))
                else:
                    continue
                agents[key] = urllib.parse.unquote(r.get("cs(User-Agent)", ""))

    kinds: Counter = Counter()
    who: dict[str, Counter] = defaultdict(Counter)
    countries: Counter = Counter()
    buckets: Counter = Counter()
    lengths: list[float] = []
    opened: list[int] = []
    for key, visitor_hits in hits.items():
        for visit in split_visits(sorted(visitor_hits)):
            seen = [h for h in visit if h[1] == "page"]
            if not seen:
                continue  # pictures with no page: a hotlink, not a visit
            if any(h[1] == "browser file" for h in visit):
                kind = "a browser"
            elif any(h[1] == "share picture" for h in visit):
                kind = "a link being previewed"
            elif all(h[2].startswith("/play/") for h in seen):
                kind = "a game and nothing else"  # games ask for no files of ours
            else:
                kind = "the HTML alone"
            kinds[kind] += 1
            who[kind][agents[key] or "(no name given)"] += 1
            if kind != "a browser":
                continue
            seconds = (visit[-1][0] - visit[0][0]).total_seconds()
            countries[seen[0][3]] += 1
            buckets[length_bucket(seconds)] += 1
            lengths.append(seconds)
            opened.append(len(seen))

    print(f"Daily visitors, last {args.days} days")
    for day in sorted(visitors):
        print(f"  {day}  {len(visitors[day]):>5}")
    total = len(set().union(*visitors.values())) if visitors else 0
    print(f"  unique over period: {total}")

    print("\nWere they people? (a browser asks for the style and the pictures too;")
    print("something taking the HTML and nothing else is a machine)")
    for kind in KINDS:
        n = kinds[kind]
        share = f"{100 * n / sum(kinds.values()):.0f}%" if kinds else "0%"
        print(f"  {n:>6}  {share:>4}  {kind}")

    print("\nWhere they connected from, browser visits only (the CloudFront city")
    print("that served them, so the country next door is always possible)")
    for name, n in countries.most_common(12):
        print(f"  {n:>6}  {name}")
    rest = sum(n for _, n in countries.most_common()[12:])
    if rest:
        print(f"  {rest:>6}  other places")

    print("\nHow long they stayed, browser visits only (first page to last; the")
    print("time spent inside a game does not show up at all)")
    for _, label in LENGTHS:
        print(f"  {buckets[label]:>6}  {label}")
    if lengths:
        more = [s for s, n in zip(lengths, opened) if n > 1]
        print(f"  half of them shorter than {how_long(statistics.median(lengths))}, half longer")
        if more:
            print(f"  counting only the {len(more)} who opened more than one page: "
                  f"half shorter than {how_long(statistics.median(more))}")
        print(f"  pages opened per visit: {sum(opened) / len(opened):.1f}")

    if args.agents:
        print("\nWhat they said they were (the name a visitor gives for itself is a")
        print("claim, not a fact; what it asked for is the fact)")
        for kind in KINDS:
            if not who[kind]:
                continue
            print(f"  {kind}")
            for name, n in who[kind].most_common(10):
                print(f"    {n:>5}  {name}")
            rest = len(who[kind]) - 10
            if rest > 0:
                print(f"           ... and {rest} more")

    print("\nGame plays")
    for uri, n in plays.most_common():
        print(f"  {n:>6}  {uri}")
    if watched:
        print("\nAnimations opened (how much of one was actually watched is, like")
        print("time spent in a game, invisible from here)")
        for uri, n in watched.most_common():
            print(f"  {n:>6}  {uri}")
    if args.pages:
        print("\nTop pages")
        for uri, n in pages.most_common(20):
            print(f"  {n:>6}  {uri}")


if __name__ == "__main__":
    main()

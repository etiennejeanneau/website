#!/usr/bin/env python3
"""
Visitor stats from CloudFront standard logs. No cookies, no JavaScript: the
CDN already writes one line per request, this script just counts them.

A "visitor" is a (day, client IP, user agent) triple. That's a rough proxy:
it undercounts people behind one NAT and overcounts people whose IP changes.
Good enough to see whether anyone is coming.

Usage:
  python scripts/stats.py --bucket ohlala-cloud-logs --days 7
  python scripts/stats.py --bucket ohlala-cloud-logs --days 30 --pages

Needs: boto3 and AWS credentials with s3:GetObject/ListBucket on the log bucket.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import io
from collections import Counter, defaultdict

import boto3

BOTS = ("bot", "crawl", "spider", "slurp", "facebookexternalhit", "preview", "monitor")


def parse_log(blob: bytes):
    """Yield dicts for each request line; fields come from the '#Fields:' header."""
    fields: list[str] = []
    for line in gzip.GzipFile(fileobj=io.BytesIO(blob)).read().decode("utf-8", "replace").splitlines():
        if line.startswith("#Fields:"):
            fields = line.split()[1:]
        elif line and not line.startswith("#"):
            yield dict(zip(fields, line.split("\t")))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--prefix", default="cloudfront/")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--pages", action="store_true", help="also list the most visited pages")
    args = ap.parse_args()

    since = dt.date.today() - dt.timedelta(days=args.days)
    s3 = boto3.client("s3")
    visitors: dict[str, set] = defaultdict(set)
    pages: Counter = Counter()
    plays: Counter = Counter()

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=args.bucket, Prefix=args.prefix):
        for obj in page.get("Contents", []):
            if obj["LastModified"].date() < since:
                continue
            body = s3.get_object(Bucket=args.bucket, Key=obj["Key"])["Body"].read()
            for r in parse_log(body):
                uri = r.get("cs-uri-stem", "")
                ua = r.get("cs(User-Agent)", "").lower()
                if not uri.endswith("/") or any(b in ua for b in BOTS) or r.get("sc-status") != "200":
                    continue  # count HTML page views by humans only
                day = r["date"]
                visitors[day].add((r["c-ip"], ua))
                pages[uri] += 1
                if uri.startswith("/play/"):
                    plays[uri] += 1

    print(f"Daily visitors, last {args.days} days")
    for day in sorted(visitors):
        print(f"  {day}  {len(visitors[day]):>5}")
    total = len(set().union(*visitors.values())) if visitors else 0
    print(f"  unique over period: {total}")
    print("\nGame plays")
    for uri, n in plays.most_common():
        print(f"  {n:>6}  {uri}")
    if args.pages:
        print("\nTop pages")
        for uri, n in pages.most_common(20):
            print(f"  {n:>6}  {uri}")


if __name__ == "__main__":
    main()

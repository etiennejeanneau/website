# ohlala.cloud

Silly little phone games, vibe coded in the evening, each published with the
story of its prompts. Static site: Python build, S3 + CloudFront, deployed by
GitHub Actions.

## Local preview

```sh
pip install -r requirements.txt
python build.py
python -m http.server 8000 --directory dist
```

## Adding a game

See [CLAUDE.md](CLAUDE.md): drop the game in `games/<slug>/`, write
`content/<slug>.md`, push to `main`.

## One-time AWS setup

1. Deploy `infra/site.yaml` as a CloudFormation stack **in us-east-1**
   (parameter `HostedZoneId` = the Route 53 zone of ohlala.cloud).
   Certificate validation records are created automatically; the stack takes
   10 to 20 minutes the first time because of CloudFront.
2. In the GitHub repo, Settings → Secrets and variables → Actions → Variables, add:
   - `AWS_DEPLOY_ROLE_ARN` = stack output `DeployRoleArn`
   - `SITE_BUCKET` = stack output `BucketName`
   - `CLOUDFRONT_DISTRIBUTION_ID` = stack output `DistributionId`
3. Settings → Environments → create `production` (no protection rules needed).
4. Push to `main`, or run the workflow by hand from the Actions tab.

## Google Search Console

The property belongs to the domain, not to the old site, so there is nothing to
re-create: open the existing `ohlala.cloud` property and check it is still
verified.

- Still verified (a DNS TXT record in Route 53 keeps working) -> nothing to do.
- Un-verified (the old site served a `google*.html` file that is gone) -> in
  Search Console choose **HTML tag**, paste the token into
  `google_site_verification` in `site.yaml`, push, then click Verify.

Then, under **Sitemaps**, remove any sitemap left over from the old site and
submit `sitemap.xml`. Old pages that no longer exist return the 404 page and
drop out of the index on their own over a few weeks.

## Visitor stats (no cookies)

```sh
pip install boto3
python scripts/stats.py --bucket ohlala.cloud-logs --days 7
```

## Ads and feedback

`site.yaml` holds the AdSense publisher id and the Tally form id. Both are empty
by default; filling them in and pushing is all it takes.

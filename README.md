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
`content/en/<slug>.md` and `content/fr/<slug>.md`, push to `main`.

## Languages

English lives at the root, French under `/fr/`, and the games themselves are
shared (`/play/<slug>/`, one copy, no words of ours in them). `languages.yaml`
lists the languages and holds every word outside the pages; the pages are in
`content/<language>/`. A page with no French version is not an error — the
build prints a note and the language menu falls back to the French home page.

Which version a visitor gets is decided in their browser: a few lines in the
page head send a first-timer to the version matching their browser's language,
and after that the last flag they clicked is remembered in local storage. No
cookie, no redirect on the server, nothing to change in AWS.

## One-time AWS setup

1. Deploy `infra/site.yaml` as a CloudFormation stack **in us-east-1**
   (parameter `HostedZoneId` = the Route 53 zone of ohlala.cloud).
   Certificate validation records are created automatically; the stack takes
   10 to 20 minutes the first time because of CloudFront.

   The other parameters already default to this repo. `GitHubRepo`,
   `GitHubOwnerId` and `GitHubRepoId` together decide which repository is
   allowed to deploy: GitHub signs each build with a token naming the owner and
   repo by name *and* by number, and the stack only trusts that exact string.
   The numbers come from `https://api.github.com/repos/<owner>/<repo>`
   (`id`, and `owner.id`). They are what makes the trust survive a rename —
   and what stops a different account from ever reusing the name.

   Editing this file changes nothing by itself: update the CloudFormation
   stack for it to take effect.
2. In the GitHub repo, Settings → Secrets and variables → Actions, add
   under **Secrets**:
   - `AWS_DEPLOY_ROLE_ARN` = stack output `DeployRoleArn`

   and under **Variables**:
   - `SITE_BUCKET` = stack output `BucketName`
   - `CLOUDFRONT_DISTRIBUTION_ID` = stack output `DistributionId`

   The role ARN is a secret rather than a variable because the runner prints
   variables in the build log, and this repo is public, so its logs are too.
   The ARN contains the AWS account id; secrets show up as `***` instead.
3. Settings → Environments → create `production` (no protection rules needed).
4. Push to `main`, or run the workflow by hand from the Actions tab.

## Google Search Console

The property is verified by a DNS TXT record in the Route 53 zone. That record
belongs to the domain, not to the site sitting on it, so replacing the whole
site changed nothing: the existing `ohlala.cloud` property kept working and
there was nothing to reconnect.

The sitemap takes care of itself too. The build publishes it at
`/sitemap.xml`, which is the same address the previous site used and the one
`robots.txt` advertises, so Google refetches it and picks up the new pages. It
cannot be deleted in Search Console, and does not need to be: a sitemap Google
discovered through `robots.txt` is listed as discovered rather than submitted,
and only submitted ones have a remove button.

Old pages that no longer exist return a real 404 (CloudFront maps both 404 and
403 to `/404.html` and keeps the 404 status, rather than answering "200 OK"
with an error page, which is what keeps dead pages in the index forever). They
drop out of the results on their own over a few weeks. To speed up the new
pages: URL Inspection -> `https://ohlala.cloud/` -> Request indexing, once.
Google follows the links to the games from there. Expect days, not hours.

`www` redirects to the bare domain and the domain property covers both, so the
site is never split across two properties.

If verification ever needs redoing without DNS — a URL-prefix property, or the
zone moving elsewhere — `site.yaml` has a `google_site_verification` key. Pick
**HTML tag** in Search Console, paste the token (or the whole `<meta>` tag,
both work) between the quotes and push; the tag lands in the head of every
page. Empty means no tag, which is the normal state while DNS does the job.

## Visitor stats (no cookies)

```sh
pip install boto3
python scripts/stats.py --bucket ohlala-cloud-logs --days 7
```

## Ads and feedback

`site.yaml` holds the AdSense publisher id and the Tally form id. Both are empty
by default; filling them in and pushing is all it takes.

### The feedback form

A static site cannot receive a form itself — there is no server here to catch
one, only files. So the form lives on [tally.so](https://tally.so), which is
free for this, and every page gets a button pointing at it. Nothing is asked of
Tally until a visitor clicks, so the pages stay as private and as fast as they
are now.

Once, in Tally:

1. Make a form. Two questions are plenty: *what did you think?* and *which game
   was it?*
2. Add two hidden fields, named exactly `Page` and `Lang`, capitals included
   (type `/hidden` in the editor to get one). The site fills them in, so each
   answer tells you which page it was sent from and in which language it was
   read. The names have to match what `templates/feedback.html` sends; rename
   them on Tally and they arrive empty until the template is changed too.
3. Publish it, then under **Integrations → Email notifications** send yourself
   an email on every answer. Slack and webhooks are in the same place if you
   prefer.
4. Copy the form's address (`https://tally.so/r/wkKqJb`) into `tally_form_id`
   in `site.yaml` — the whole address or just the last part, both work — and
   push.

To take the form down again, empty `tally_form_id` and push: the button
disappears from every page and nothing else changes. `python build.py` prints a
note when the id is empty, so it is never a silent omission.

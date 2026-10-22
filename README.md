# Everyday Digital Explained: companion site

A static site with one page per video. Every page is built so AI answer engines and Google can quote it. Each page carries:
- a short answer first
- numbered steps
- an FAQ
- official sources
- a last-verified date
- schema markup

`llms.txt`, `sitemap.xml` and `robots.txt` are generated alongside the pages.

## Build

```
python build.py
```

The build reads `config.json` and `content/*.json`, then writes the site to `docs/`. Internal links get the path from `site_url`, so the same build works on GitHub Pages and on a custom domain. It stops if a page is missing a required field, has fewer than 3 https sources, uses a banned claim, or is a Medicare page with a product link. It prints warnings for titles that are too long, stale `valid_until` dates, and claims listed in `uncertain`.

## Deploy (live on GitHub Pages)

The repo is public: github.com/jirv71/everydaydigitalexplained. GitHub Pages serves `main:/docs` at https://jirv71.github.io/everydaydigitalexplained/.

To update the site: `python build.py`, then `git add -A && git commit -m "..." && git push`. Pages redeploys in about a minute.

**Custom domain (once you own one):**
1. Set `site_url` in `config.json` to `https://yourdomain.com` and rebuild. Links then drop the `/everydaydigitalexplained` prefix.
2. Add a `docs/CNAME` file containing the domain.
3. Point DNS at GitHub Pages: an apex A record, or a `www` CNAME to `jirv71.github.io`.
4. Turn on **Enforce HTTPS** in the repo's Settings → Pages.

**Search engines:** add the site in Google Search Console and Bing Webmaster Tools, then submit `sitemap.xml`. Bing's index feeds ChatGPT search.

**Moving to Cloudflare Pages later:** upload the `docs` folder, or connect the repo with build output `docs`. Cloudflare's free Web Analytics shows referrers such as chatgpt.com and perplexity.ai.

## Fill in later (config.json → `links`)

| Key | What to paste | Shows on |
|---|---|---|
| `gusto`, `freshbooks`, `jobber` | Your affiliate/referral links once approved | Small-business pages |
| `aura`, `nordpass` | Your affiliate links once approved | Scam pages |
| `biz_kit` | The Gumroad link for the Job Notes to Invoice Kit | Small-business pages |
| `kit` | Already set to the Etsy listing. Swap in the Gumroad checkout when it's live. | Scam pages |
| `email_form_action` (top level) | The form action URL from your email tool | Every page |

Links with an empty `url` are hidden, so the site never shows dead links.

## Adding a page for a new video

Add `content/<slug>.json` using the same fields as the existing pages. Once the video is live, add `"youtube_id": "<id>"` and the page gets a thumbnail plus VideoObject schema. Then rebuild and redeploy.

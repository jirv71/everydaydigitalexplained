"""Build the Everyday Digital Explained companion site.

Reads config.json + content/*.json, validates every page, writes static HTML to dist/.
Run: python build.py        (stdlib only; deploy dist/ to Cloudflare Pages)
"""
import datetime as dt
import html
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
DIST = ROOT / "docs"  # GitHub Pages serves main:/docs; also the folder to upload to Cloudflare Pages
TODAY = dt.date.today().isoformat()
LANES = {
    "A": ("small-business", "Small-business money admin"),
    "B": ("protect-your-parents", "Protect your parents"),
}
REQUIRED = ["slug", "topic_id", "lane", "series", "title", "meta_description", "answer",
            "steps", "faqs", "sources", "last_verified", "cta"]
BANNED = ["prevents identity theft", "prevent identity theft", "guaranteed"]

e = html.escape


def load_pages(cfg):
    pages, problems, warnings = [], [], []
    for f in sorted((ROOT / "content").glob("*.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        name = f.stem
        for k in REQUIRED:
            if not p.get(k):
                problems.append(f"{name}: missing {k}")
        if p.get("slug") != name or not re.fullmatch(r"[a-z0-9-]+", name):
            problems.append(f"{name}: slug must match filename and be lowercase-hyphen")
        if p.get("lane") not in LANES:
            problems.append(f"{name}: lane must be A or B")
        if p.get("cta") not in cfg["cta_sets"]:
            problems.append(f"{name}: cta must be one of {list(cfg['cta_sets'])}")
        if p.get("series") == "S-BENEFITS" and p.get("cta") != "none":
            problems.append(f"{name}: Medicare pages must be cta=none (CMS rules)")
        srcs = p.get("sources") or []
        if len(srcs) < 3 or any(not s.get("url", "").startswith("https://") for s in srcs):
            problems.append(f"{name}: needs >=3 sources, all https")
        text = json.dumps(p).lower()
        for b in BANNED:
            if b in text:
                problems.append(f"{name}: banned phrase '{b}'")
        if len(p.get("title", "")) > 70:
            warnings.append(f"{name}: title over 70 chars")
        if len(p.get("meta_description", "")) > 160:
            warnings.append(f"{name}: meta description over 160 chars")
        if p.get("valid_until") and p["valid_until"] < TODAY:
            warnings.append(f"{name}: STALE since {p['valid_until']} - re-verify before deploy")
        if p.get("uncertain"):
            warnings.append(f"{name}: {len(p['uncertain'])} unverified claim(s) listed in 'uncertain'")
        pages.append(p)
    return pages, problems, warnings


def url(cfg, path=""):
    return cfg["site_url"].rstrip("/") + "/" + path


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def layout(cfg, title, desc, path, body, head_extra=""):
    # Analytics: enable Cloudflare Web Analytics on the Pages project (auto-injected); no script here.
    lanes_nav = "".join(f'<a href="/{slug}/">{e(label)}</a>' for slug, label in LANES.values())
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url(cfg, path))}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url(cfg, path))}">
<meta property="og:type" content="article">
<link rel="stylesheet" href="/styles.css">
{head_extra}
</head>
<body>
<header class="site"><div class="wrap">
<a class="brand" href="/">{e(cfg['site_name'])}</a>
<nav>{lanes_nav}<a href="/about/">How we check facts</a></nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="site"><div class="wrap">
<p><strong>Education only.</strong> Not legal, tax, financial or medical advice. We are not affiliated with any government agency,
Medicare, or the companies we mention. Rules change, so check the official source linked on each page.</p>
<p><strong>Disclosure:</strong> some links are affiliate links, and we may earn a commission at no cost to you. Links marked
"our product" are sold by us. See <a href="/about/">how we check facts</a>.</p>
<p>&copy; {dt.date.today().year} {e(cfg['site_name'])} &middot;
<a href="{e(cfg['youtube_channel'])}" rel="me">YouTube</a> &middot; <a href="{e(cfg['tiktok_profile'])}" rel="me">TikTok</a></p>
</div></footer>
</body>
</html>
"""


def cta_block(cfg, p):
    items = [cfg["links"][k] | {"key": k} for k in cfg["cta_sets"][p["cta"]] if cfg["links"][k]["url"]]
    if not items:
        return ""
    lis = []
    for it in items:
        tag = "our product" if it["own"] else "affiliate link"
        rel = "noopener" if it["own"] else "sponsored noopener"
        lis.append(f'<li><a href="{e(it["url"])}" rel="{rel}">{e(it["label"])}</a> <span class="tag">{tag}</span></li>')
    return f"""<aside class="cta"><h2>Tools that help with this</h2><ul>{''.join(lis)}</ul>
<p class="small">Affiliate links may earn us a commission at no cost to you. "Our product" means we sell it.</p></aside>"""


def email_block(cfg):
    action = cfg.get("email_form_action")
    if not action:
        return ""
    return f"""<aside class="email"><h2>Get the free checklist</h2>
<form method="post" action="{e(action)}"><label for="em">Email</label>
<input id="em" type="email" name="email" required autocomplete="email"><button type="submit">Send it</button></form>
<p class="small">One practical email a week. Unsubscribe anytime.</p></aside>"""


def video_block(p):
    vid = p.get("youtube_id")
    if not vid:
        return ""
    return (f'<a class="video" href="https://www.youtube.com/watch?v={e(vid)}">'
            f'<img src="https://i.ytimg.com/vi/{e(vid)}/hqdefault.jpg" alt="Watch the video: {e(p["title"])}" '
            f'width="480" height="360" loading="lazy"><span>&#9654; Watch the short video</span></a>')


def page_html(cfg, p, pages):
    lane_slug, lane_label = LANES[p["lane"]]
    path = f'{p["slug"]}/'
    steps = "".join(f'<li><strong>{e(s["name"])}.</strong> {e(s["text"])}</li>' for s in p["steps"])
    details = "".join(f'<h2>{e(d["heading"])}</h2>' + "".join(f"<p>{e(x)}</p>" for x in d["paragraphs"])
                      for d in p.get("details") or [])
    warnings = "".join(f"<li>{e(w)}</li>" for w in p.get("warnings") or [])
    warnings = f'<div class="warn"><ul>{warnings}</ul></div>' if warnings else ""
    faqs = "".join(f'<h3>{e(f["q"])}</h3><p>{e(f["a"])}</p>' for f in p["faqs"])
    sources = "".join(f'<li><a href="{e(s["url"])}">{e(s["label"])}</a> &mdash; {e(s.get("publisher", ""))}'
                      f' <span class="small">(checked {e(s.get("checked", p["last_verified"]))})</span></li>'
                      for s in p["sources"])
    related = [r for r in pages if r["lane"] == p["lane"] and r["slug"] != p["slug"]][:4]
    related_html = "".join(f'<li><a href="/{e(r["slug"])}/">{e(r["title"])}</a></li>' for r in related)
    related_html = f'<h2>Related</h2><ul class="related">{related_html}</ul>' if related_html else ""

    page_url = url(cfg, path)
    org = {"@type": "Organization", "name": cfg["site_name"], "url": url(cfg),
           "sameAs": [cfg["youtube_channel"], cfg["tiktok_profile"]]}
    graph = [
        {"@type": "Article", "headline": p["title"], "description": p["meta_description"],
         "datePublished": p.get("published", p["last_verified"]), "dateModified": p["last_verified"],
         "author": org, "publisher": org, "mainEntityOfPage": page_url,
         "citation": [s["url"] for s in p["sources"]]},
        {"@type": "HowTo", "name": p["title"], "step": [
            {"@type": "HowToStep", "position": i + 1, "name": s["name"], "text": s["text"]}
            for i, s in enumerate(p["steps"])]},
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in p["faqs"]]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": url(cfg)},
            {"@type": "ListItem", "position": 2, "name": lane_label, "item": url(cfg, f"{lane_slug}/")},
            {"@type": "ListItem", "position": 3, "name": p["title"], "item": page_url}]},
    ]
    if p.get("youtube_id"):
        graph.append({"@type": "VideoObject", "name": p["title"], "description": p["meta_description"],
                      "thumbnailUrl": f'https://i.ytimg.com/vi/{p["youtube_id"]}/hqdefault.jpg',
                      "uploadDate": p.get("video_date", p["last_verified"]),
                      "contentUrl": f'https://www.youtube.com/watch?v={p["youtube_id"]}',
                      "embedUrl": f'https://www.youtube.com/embed/{p["youtube_id"]}'})
    schema = ld({"@context": "https://schema.org", "@graph": graph})

    body = f"""<nav class="crumbs"><a href="/">Home</a> &rsaquo; <a href="/{lane_slug}/">{e(lane_label)}</a></nav>
<article>
<h1>{e(p['title'])}</h1>
<p class="meta">Last verified <time datetime="{e(p['last_verified'])}">{e(p['last_verified'])}</time>
against {len(p['sources'])} official sources</p>
<p class="answer"><strong>Short answer:</strong> {e(p['answer'])}</p>
{video_block(p)}
{warnings}
<h2>Step by step</h2>
<ol class="steps">{steps}</ol>
{details}
{cta_block(cfg, p)}
<h2>Common questions</h2>
{faqs}
<h2>Official sources</h2>
<ul class="sources">{sources}</ul>
{email_block(cfg)}
{related_html}
</article>"""
    return layout(cfg, f'{p["title"]} | {cfg["site_name"]}', p["meta_description"], path, body, schema)


def list_html(pages):
    return "".join(f'<li><a href="/{e(p["slug"])}/">{e(p["title"])}</a><p>{e(p["answer"])}</p></li>' for p in pages)


BASE = ""  # URL path prefix from site_url, e.g. "/everydaydigitalexplained" on GitHub Pages; "" on a custom domain


def write(path, text):
    if path.endswith(".html") and BASE:
        text = text.replace('href="/', f'href="{BASE}/').replace('src="/', f'src="{BASE}/')
    out = DIST / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def build():
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    pages, problems, warnings = load_pages(cfg)
    for w in warnings:
        print("WARN ", w)
    if problems:
        for pr in problems:
            print("ERROR", pr)
        sys.exit(f"Build stopped: {len(problems)} problem(s).")
    pages.sort(key=lambda p: (p.get("published") or p["last_verified"]), reverse=True)

    global BASE
    BASE = urlparse(cfg["site_url"]).path.rstrip("/")
    shutil.rmtree(DIST, ignore_errors=True)
    DIST.mkdir()
    shutil.copy(ROOT / "styles.css", DIST / "styles.css")
    (DIST / ".nojekyll").write_text("")  # GitHub Pages: serve files as-is

    for p in pages:
        write(f'{p["slug"]}/index.html', page_html(cfg, p, pages))

    sections = ""
    for lane, (slug, label) in LANES.items():
        lp = [p for p in pages if p["lane"] == lane]
        write(f"{slug}/index.html", layout(cfg, f"{label} | {cfg['site_name']}", f"{label}: step-by-step guides checked against official sources.",
                                           f"{slug}/", f"<h1>{e(label)}</h1><ul class='list'>{list_html(lp)}</ul>"))
        sections += f'<section><h2><a href="/{slug}/">{e(label)}</a></h2><ul class="list">{list_html(lp)}</ul></section>'

    site_ld = ld({"@context": "https://schema.org", "@type": "WebSite", "name": cfg["site_name"], "url": url(cfg)})
    write("index.html", layout(cfg, f"{cfg['site_name']}: plain-English life admin, checked against the source",
                               cfg["tagline"], "", f"<p class='lede'>{e(cfg['tagline'])}</p>{sections}", site_ld))

    write("about/index.html", layout(cfg, f"How we check facts | {cfg['site_name']}",
                                     "Our editorial policy: primary sources, last-verified dates, corrections.", "about/", """
<h1>How we check facts</h1>
<p>Every page is written from official sources: IRS, Medicare.gov and CMS, FTC, FCC, USPS and state agencies.
We link those sources on the page and show the date we last checked them.</p>
<h2>Our rules</h2>
<ul>
<li>Every number, date and phone number comes from an official source linked on the page.</li>
<li>Pages with deadlines are re-checked before the deadline and after any rule change.</li>
<li>Medicare pages are education only. We never recommend a plan or carrier and never ask you to enroll through us.</li>
<li>We never claim any product can prevent fraud or identity theft. Some tools can help you notice and respond faster.</li>
<li>Affiliate links are labeled. Products we sell are labeled "our product".</li>
</ul>
<h2>Found a mistake?</h2>
<p>Tell us through the comments on our <a href="https://www.youtube.com/@EverydayDigitalExplained">YouTube channel</a>. We fix confirmed errors and update the last-verified date.</p>
"""))

    write("404.html", layout(cfg, f"Page not found | {cfg['site_name']}", "Page not found.", "404.html",
                             "<h1>Page not found</h1><p><a href='/'>Go to the home page</a>.</p>"))

    urls = [("", TODAY), ("about/", TODAY)] + [(f"{s}/", TODAY) for s, _ in LANES.values()] + \
           [(f'{p["slug"]}/', p["last_verified"]) for p in pages]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join(f"<url><loc>{e(url(cfg, u))}</loc><lastmod>{d}</lastmod></url>\n" for u, d in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {url(cfg, 'sitemap.xml')}\n")
    llms = [f"# {cfg['site_name']}", "", f"> {cfg['tagline']}", ""]
    for lane, (slug, label) in LANES.items():
        llms += [f"## {label}", ""] + [f'- [{p["title"]}]({url(cfg, p["slug"] + "/")}): {p["meta_description"]}'
                                        for p in pages if p["lane"] == lane] + [""]
    write("llms.txt", "\n".join(llms))
    print(f"Built {len(pages)} pages -> {DIST}")


if __name__ == "__main__":
    build()

"""Pinterest pack: one 1000x1500 pin per content page (pins/<slug>.png) + pinterest-bulk-upload.csv.

Run: python pinterest.py   (needs Pillow; Windows fonts). Then python build.py copies pins/ to docs/pins/.
CSV columns follow Pinterest's bulk-create spec (help.pinterest.com/en/business/article/bulk-upload-video-pins).
"""
import csv
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
FONTS = Path("C:/Windows/Fonts")
W, H, PAD = 1000, 1500, 80
FOOTER = "Free step-by-step guide \u00b7 Everyday Digital Explained"
LANE = {  # bg, card, accent, text, footer text, label, board
    "A": ("#0B2A5B", "#163D7A", "#F7931E", "#FFFFFF", "#0B2A5B", "SMALL BUSINESS", "Small Business Money Admin"),
    "B": ("#0D5C63", "#17737B", "#FFB26B", "#FFF8EE", "#0D3B3F", "PROTECT YOUR PARENTS", "Protect Your Parents"),
}
# Hook headlines (<=9 words). Pages not listed use their title.
HOOKS = {
    "2026-irs-mileage-rate-two-rates": "2026 IRS mileage: 72.5 or 76 cents a mile?",
    "ai-voice-clone-scam-family-safe-word": "AI voice-clone scam calls: set a family safe word",
    "check-if-password-leaked-free": "Has your password been leaked? Check for free",
    "data-broker-removal-how-scammers-get-your-address": "How scammers get your address: data broker opt-outs",
    "first-employee-payroll-what-software-does": "Hiring your first employee? What payroll software does",
    "free-ein-from-irs": "Get your EIN free, straight from the IRS",
    "freeze-credit-all-three-bureaus-free": "Freeze your credit at all 3 bureaus for free",
    "how-to-use-medicare-plan-finder": "How to use the official Medicare Plan Finder",
    "medical-alert-button-vs-smartwatch": "Medical alert button vs smartwatch: what each does",
    "medicare-open-enrollment-what-you-can-change": "Medicare Open Enrollment: what you can change",
    "medicare-scam-red-flags-open-enrollment": "Did Medicare really call? How to spot 3 scams",
    "package-delivery-text-scam-check-link": "Package delayed text? How to check before you tap",
    "receipts-to-spreadsheet-small-business": "Turn a shoebox of receipts into a clean spreadsheet",
    "scammed-what-to-do-first-hour": "Got scammed? What to do in the first hour",
    "stop-prescreened-credit-offers-do-not-call": "Opt out of pre-approved offers and junk calls",
    "voice-memo-to-invoice": "Turn a voice memo into a professional invoice",
    "medicare-annual-notice-of-change-how-to-read": "That thick Medicare envelope: what to check first",
    "unpaid-toll-text-scam-what-to-do": "Unpaid toll text? Don't tap that link",
    "apple-legacy-contact-how-to-set-up": "Could your family get into your Apple account?",
    "1099-k-20000-200-transactions-rule": "Payment app 1099-K: $20,000 and 200 transactions",
    "gift-card-payment-scam-what-to-do": "Paid a scammer with a gift card? Act now",
    "google-inactive-account-manager-set-up": "Pick who gets your Google data before it's deleted",
    "boi-report-letter-scam-us-companies-exempt": "BOI letter wants a fee? FinCEN says: scam.",
    "work-from-home-job-fake-check-scam": "New job sent a check? It's a scam.",
    "close-accounts-after-death-facebook-google-apple": "When someone dies: Facebook, Google and Apple request pages",
    "free-small-business-mentor-score-sbdc": "Free business mentor? Just type your ZIP code",
    "freeze-child-credit-free-under-16": "Freeze your kid's credit for free: here's how",
    "louisiana-small-succession-limit": "Louisiana's small succession limit just jumped to $200,000",
}
# Which 3 steps to tease (0-based). Pages not listed use the first 3.
PICKS = {
    "1099-nec-2000-threshold": [0, 2, 3], "2026-irs-mileage-rate-two-rates": [0, 3, 4],
    "ai-voice-clone-scam-family-safe-word": [0, 2, 4], "check-if-password-leaked-free": [0, 1, 4],
    "data-broker-removal-how-scammers-get-your-address": [0, 1, 3],
    "first-employee-payroll-what-software-does": [0, 1, 4], "free-ein-from-irs": [0, 2, 3],
    "freeze-credit-all-three-bureaus-free": [1, 2, 3], "how-to-use-medicare-plan-finder": [0, 2, 4],
    "medical-alert-button-vs-smartwatch": [1, 3, 5], "medicare-open-enrollment-what-you-can-change": [0, 2, 5],
    "package-delivery-text-scam-check-link": [0, 2, 3], "receipts-to-spreadsheet-small-business": [0, 1, 4],
    "scammed-what-to-do-first-hour": [0, 1, 5], "stop-prescreened-credit-offers-do-not-call": [0, 4, 5],
    "voice-memo-to-invoice": [0, 2, 3],
    "medicare-annual-notice-of-change-how-to-read": [1, 2, 3], "unpaid-toll-text-scam-what-to-do": [0, 2, 3], "apple-legacy-contact-how-to-set-up": [1, 3, 5], "1099-k-20000-200-transactions-rule": [0, 1, 4], "gift-card-payment-scam-what-to-do": [0, 3, 6], "google-inactive-account-manager-set-up": [1, 3, 4],
    "boi-report-letter-scam-us-companies-exempt": [1, 2, 3],
    "work-from-home-job-fake-check-scam": [0, 2, 3],
    "close-accounts-after-death-facebook-google-apple": [2, 3, 5],
    "free-small-business-mentor-score-sbdc": [1, 3, 4],
    "freeze-child-credit-free-under-16": [0, 2, 5],
    "louisiana-small-succession-limit": [0, 1, 3],
}
KEYWORDS = {
    "1099-nec-2000-threshold": "1099-NEC threshold, 1099 for contractors, small business taxes, Form W-9, 1099-K rules",
    "2026-irs-mileage-rate-two-rates": "2026 IRS mileage rate, business mileage deduction, mileage log, small business taxes, self-employed tax tips",
    "ai-voice-clone-scam-family-safe-word": "AI voice clone scam, family safe word, scam phone calls, aging parents, call screening",
    "check-if-password-leaked-free": "password leak check, data breach check, Have I Been Pwned, passkeys, online safety for seniors",
    "data-broker-removal-how-scammers-get-your-address": "data broker opt out, people search sites, remove my address online, California DROP, privacy for seniors",
    "first-employee-payroll-what-software-does": "first employee payroll, payroll software, hiring your first employee, payroll taxes, small business payroll",
    "free-ein-from-irs": "free EIN, IRS EIN application, employer identification number, start a small business, small business tax ID",
    "freeze-credit-all-three-bureaus-free": "credit freeze, free credit freeze, Equifax Experian TransUnion, credit bureaus, aging parents",
    "how-to-use-medicare-plan-finder": "Medicare Plan Finder, compare Medicare plans, Medicare open enrollment, Medicare drug coverage, aging parents",
    "medical-alert-button-vs-smartwatch": "medical alert system, fall detection, smartwatch for seniors, aging parents safety, caregiver tips",
    "medicare-open-enrollment-what-you-can-change": "Medicare open enrollment, Annual Notice of Change, Medicare 2027, Medigap rules, aging parents",
    "medicare-scam-red-flags-open-enrollment": "Medicare scams, Medicare card scam, Medicare scam calls, elder fraud warning signs, aging parents",
    "package-delivery-text-scam-check-link": "package delivery text scam, USPS text scam, smishing, report spam texts 7726, scam text messages",
    "receipts-to-spreadsheet-small-business": "organize receipts, receipts to spreadsheet, small business bookkeeping, IRS record keeping, expense tracking",
    "scammed-what-to-do-first-hour": "what to do if scammed, report fraud to FTC, scam recovery steps, payment app scam, gift card scam",
    "stop-prescreened-credit-offers-do-not-call": "opt out prescreened offers, OptOutPrescreen, Do Not Call Registry, junk mail, unwanted calls",
    "voice-memo-to-invoice": "voice memo to invoice, invoice template, AI for small business, job notes, small business invoicing",
    "medicare-annual-notice-of-change-how-to-read": "Medicare Annual Notice of Change, Medicare open enrollment 2026, Medicare Advantage plan changes, Part D drug plan, Medicare help for parents",
    "unpaid-toll-text-scam-what-to-do": "toll text scam, unpaid toll scam, E-ZPass scam text, smishing, report spam 7726",
    "apple-legacy-contact-how-to-set-up": "Apple Legacy Contact, digital estate planning, iPhone settings tips, Apple account after death, family tech help",
    "1099-k-20000-200-transactions-rule": "1099-K threshold, payment app taxes, side hustle taxes, selling online taxes, IRS 1099-K rules",
    "gift-card-payment-scam-what-to-do": "gift card scam, what to do if scammed, report fraud FTC, scam help for seniors, IRS gift card scam",
    "google-inactive-account-manager-set-up": "Google Inactive Account Manager, Google account after death, digital legacy planning, inactive Gmail account deletion, Google trusted contacts",
    "boi-report-letter-scam-us-companies-exempt": "BOI report scam, FinCEN Form 4022, beneficial ownership letter, small business scam, LLC fraud alert",
    "work-from-home-job-fake-check-scam": "fake check scam, work from home job scam, job scam warning signs, reshipping scam, FTC scam tips",
    "close-accounts-after-death-facebook-google-apple": "close deceased Facebook account, memorialize Facebook, Google deceased user request, Apple Legacy Contact, digital estate checklist",
    "free-small-business-mentor-score-sbdc": "free business mentor, SCORE mentoring, small business development center, SBA local assistance, small business help",
    "freeze-child-credit-free-under-16": "child credit freeze, child identity theft, credit freeze for kids, child SSN safety, family identity protection",
    "louisiana-small-succession-limit": "Louisiana small succession, small succession affidavit, Louisiana probate, settling a parent's estate, Louisiana estate limit 2026",
}
# Copy must never claim to prevent/stop fraud or identity theft; Medicare pages never name a product.
BANNED = re.compile(r"prevent|guarantee|stops? (fraud|identity|scam)|protects? you from", re.I)
PRODUCTS = re.compile(r"aura|nordpass|gusto|freshbooks|jobber|etsy|gumroad|kit\b|apple|iphone|pixel|google", re.I)


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def wrap(draw, text, f, width):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=f) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def balanced(draw, text, f, width):
    """Wrap, then narrow the width while the line count holds, so lines come out even (no orphan word)."""
    lines = wrap(draw, text, f, width)
    while width > 200 and len(wrap(draw, text, f, width - 20)) == len(lines):
        width -= 20
        lines = wrap(draw, text, f, width)
    return lines


def teasers(p):
    idx = PICKS.get(p["slug"], [0, 1, 2])
    return [re.sub(r"\s*\([^)]*\)", "", p["steps"][i]["name"]).strip() for i in idx]


def hook(p):
    return HOOKS.get(p["slug"], p["title"])


def check_copy(p, *texts):
    for t in texts:
        assert not BANNED.search(t), f"{p['slug']}: banned claim in {t!r}"
        if p["series"] == "S-BENEFITS":
            assert not PRODUCTS.search(t), f"{p['slug']}: product mention on Medicare page in {t!r}"
    assert len(hook(p).split()) <= 9 or p["slug"] not in HOOKS, f"{p['slug']}: hook over 9 words"


def render(p, out):
    bg, card, accent, fg, foot_fg, label, _ = LANE[p["lane"]]
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    inner = W - 2 * PAD
    footer_h = 150
    top = 90
    f_label = font("seguibl.ttf", 34)
    label_h = 34 + 60

    # Largest headline/step sizes that fit above the footer; step text weighs double so it stays big.
    sizes = sorted(((hs, ss) for hs in range(104, 59, -4) for ss in (46, 44, 42, 40, 38)),
                   key=lambda s: (s[0] + 2 * s[1], s[0]), reverse=True)
    for hs, ss in sizes:
        f_head, f_step = font("seguibl.ttf", hs), font("seguisb.ttf", ss)
        head = balanced(d, hook(p), f_head, inner)
        head_lh = int(hs * 1.12)
        steps = [balanced(d, t, f_step, inner - 180) for t in teasers(p)]
        step_lh = int(ss * 1.25)
        cards = [max(len(s) * step_lh, 84) + 64 for s in steps]
        need = label_h + len(head) * head_lh + int(hs * 0.25) + 80 + sum(cards) + 2 * 30
        if need <= H - footer_h - top - 60 and len(head) <= 5 and all(len(s) <= 2 for s in steps):
            break
    else:
        raise SystemExit(f"{p['slug']}: copy does not fit")

    y = top
    d.text((PAD, y), label, font=f_label, fill=accent)
    y += label_h
    for line in head:
        d.text((PAD, y), line, font=f_head, fill=fg)
        y += head_lh
    y += int(hs * 0.25) + 30  # clear the last line's descenders (g, p, y)
    d.rectangle([PAD, y, PAD + 140, y + 12], fill=accent)
    y += 50
    # Center the step cards in the space left above the footer.
    free = H - footer_h - 60 - y - sum(cards)
    gap = min(max(30, free // 4), 56)
    y += max(0, (free - 2 * gap) // 2)
    f_num = font("seguibl.ttf", 48)
    for n, (lines, ch) in enumerate(zip(steps, cards), 1):
        d.rounded_rectangle([PAD, y, W - PAD, y + ch], radius=28, fill=card)
        cy = y + ch // 2
        d.ellipse([PAD + 32, cy - 42, PAD + 116, cy + 42], fill=accent)
        d.text((PAD + 74, cy), str(n), font=f_num, fill=foot_fg, anchor="mm")
        ty = cy - len(lines) * step_lh // 2
        for line in lines:
            d.text((PAD + 148, ty + step_lh // 2), line, font=f_step, fill=fg, anchor="lm")
            ty += step_lh
        y += ch + gap

    d.rectangle([0, H - footer_h, W, H], fill=accent)
    fs = 40
    while d.textlength(FOOTER, font=font("seguibl.ttf", fs)) > inner:
        fs -= 1
    d.text((W // 2, H - footer_h // 2), FOOTER, font=font("seguibl.ttf", fs), fill=foot_fg, anchor="mm")
    img.save(out, optimize=True)


def description(p, link):
    tail = f" Free plain-English guide, checked against official sources: {link}"
    desc = f"{p['meta_description']} Steps: {'; '.join(teasers(p))}.{tail}"
    return desc if len(desc) <= 500 else p["meta_description"] + tail


def main():
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    site = cfg["site_url"].rstrip("/")
    (ROOT / "pins").mkdir(exist_ok=True)
    rows = []
    for f in sorted((ROOT / "content").glob("*.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        link = f"{site}/{p['slug']}/"
        desc = description(p, link)
        if p["slug"] not in KEYWORDS:
            raise SystemExit(f"{p['slug']}: add 5 KEYWORDS in pinterest.py")
        check_copy(p, hook(p), *teasers(p), p["title"], desc, KEYWORDS[p["slug"]])
        assert len(KEYWORDS[p["slug"]].split(", ")) == 5 and len(p["title"]) <= 100 and len(desc) <= 500
        render(p, ROOT / "pins" / f"{p['slug']}.png")
        rows.append([p["title"], f"{site}/pins/{p['slug']}.png", LANE[p["lane"]][6], "", desc, link, "",
                     KEYWORDS[p["slug"]]])
    with open(ROOT / "pinterest-bulk-upload.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Title", "Media URL", "Pinterest board", "Thumbnail", "Description", "Link", "Publish date", "Keywords"])
        w.writerows(rows)
    print(f"Wrote {len(rows)} pins -> pins/ and pinterest-bulk-upload.csv")


if __name__ == "__main__":
    main()

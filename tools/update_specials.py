#!/usr/bin/env python3
"""Fetch this week's (and next week's, once it's out) Woolworths Victoria catalogue from SaleFinder
and save it as specials.json for the Dinner Saver website. Standard library only, so it runs anywhere.

Run by a GitHub Actions schedule every morning. Usage: python3 update_specials.py [output.json]
"""
import html, json, os, re, sys, time, urllib.request
from datetime import date, datetime, timedelta, timezone

BASE = "https://www.salefinder.com.au"
POSTCODE_ID = os.environ.get("SALEFINDER_POSTCODE_ID", "7700")  # Narre Warren VIC 3805; any VIC metro postcode gets the same catalogue
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
MONTHS = {m: i + 1 for i, m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])}

def get(path, tries=3):
    for n in range(tries):
        try:
            req = urllib.request.Request(BASE + path, headers={"User-Agent": UA, "Cookie": f"postcodeId={POSTCODE_ID}", "Accept-Language": "en-AU"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            if n == tries - 1: raise
            time.sleep(5 * (n + 1))

def valid_dates(page):
    m = re.search(r"valid\s+\w{3}\s+(\d{1,2})\s+(\w{3})\s+(\d{4})\s*-\s*\w{3}\s+(\d{1,2})\s+(\w{3})\s+(\d{4})", page)
    if not m: return None, None
    a = date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
    b = date(int(m.group(6)), MONTHS[m.group(5)], int(m.group(4)))
    return a.isoformat(), b.isoformat()

def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

def parse_price(block):
    """Returns (unit price, unit, deal text) from a SaleFinder price block."""
    text = clean(block)
    m = re.search(r"(\d+)\s*for\s*\$\s*([\d.]+)", text, re.I)  # "2 for $10"
    if m: return round(float(m.group(2)) / int(m.group(1)), 2), "each", text
    m = re.search(r"\$\s*([\d.]+)\s*(each|per\s*kg|/\s*kg|kg|per\s*100\s*g|pk|pack)?", text, re.I)
    if not m: return None, None, text
    unit = (m.group(2) or "each").lower().replace(" ", "")
    unit = {"perkg": "per kg", "/kg": "per kg", "kg": "per kg", "per100g": "per 100g", "pk": "each", "pack": "each"}.get(unit, unit)
    return float(m.group(1)), unit, text

def parse_items(page, cat_id):
    items = []
    for m in re.finditer(r'<a href="/' + cat_id + r'/([^"]+?)/(\d+)/" class="item-image"[^>]*data-itemname="([^"]*)"', page):
        path, item_id = m.group(1), m.group(2)
        name = html.unescape(html.unescape(m.group(3))).replace("\u2122", "").replace("#", "")
        name = re.sub(r"\s*[\u2013-]\s*(From the|Excludes|Selected|Available).*$", "", name).strip()
        name = re.sub(r"[^\w)%]+$", "", name).strip()
        rest = page[m.end(): m.end() + 4000]
        po = re.search(r'<div class="price-options[^"]*">([\s\S]*?)</div>', rest)
        if not po: continue
        price, unit, text = parse_price(po.group(1))
        if price is None: continue
        save = re.search(r"Save\s*\$\s*([\d.]+)", text, re.I)
        half = re.search(r"1/2 Price|Half Price", text, re.I)
        wasm = re.search(r"\bwas\s*\$\s*([\d.]+)", text, re.I)
        multi = re.search(r"(\d+)\s*for\s*\$\s*([\d.]+)", text, re.I)
        was = None
        if wasm: was = float(wasm.group(1))
        elif save and multi: was = round((float(multi.group(2)) + float(save.group(1))) / int(multi.group(1)), 2)
        elif save: was = round(price + float(save.group(1)), 2)
        elif half: was = round(price * 2, 2)
        low = was is None and bool(re.search(r"Everyday Low Price|Low Price|Prices Dropped", text, re.I))
        cat = "/".join(path.split("/")[:-1])  # drop the product slug
        item = {"name": name, "price": price, "unit": unit, "was": was, "cat": cat}
        if low: item["low"] = True
        if multi: item["deal"] = f"{multi.group(1)} for ${multi.group(2)}"
        items.append(item)
    return items

def catalogue(slug, cat_id):
    first = get(f"/woolworths-catalogue/{slug}/{cat_id}/list")
    start, end = valid_dates(first)
    pages = sorted({int(n) for n in re.findall(rf"/{cat_id}/list\?qs=(\d+),", first)} | {1})
    seen, items = set(), []
    for n in pages:
        page = first if n == 1 else get(f"/woolworths-catalogue/{slug}/{cat_id}/list?qs={n},,,,")
        if n != 1: time.sleep(1)
        for it in parse_items(page, cat_id):
            key = it["name"].lower()
            if key not in seen: seen.add(key); items.append(it)
    return {"id": cat_id, "from": start, "to": end, "items": items}

def main(out):
    home = get("/woolworths-catalogue")
    found = []
    for slug, cid in re.findall(r"/woolworths-catalogue/(weekly-catalogue[^/\"]*)/(\d+)/", home):
        if (slug, cid) not in found: found.append((slug, cid))
    if not found: raise SystemExit("No weekly catalogue found on SaleFinder; page layout may have changed.")
    today = datetime.now(timezone(timedelta(hours=10))).date().isoformat()
    cats = []
    for slug, cid in found:
        c = catalogue(slug, cid); time.sleep(1)
        if c["to"] and c["to"] >= today and c["items"]: cats.append(c)
    if not cats: raise SystemExit("No current catalogue with items; keeping the old file.")
    cats.sort(key=lambda c: c["from"] or "")
    data = {"updated": datetime.now(timezone.utc).isoformat(timespec="minutes"), "source": "Woolworths VIC weekly catalogue (via SaleFinder)", "catalogues": cats}
    old = None
    if os.path.exists(out):
        try: old = json.load(open(out))
        except Exception: pass
    if old and old.get("catalogues") == cats:
        print("No change."); return
    json.dump(data, open(out, "w"), indent=0, ensure_ascii=False)
    for c in cats: print(f"{c['from']} to {c['to']}: {len(c['items'])} specials")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "specials.json")

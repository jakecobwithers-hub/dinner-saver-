#!/usr/bin/env python3
"""Keep a price book of every Woolworths product seen in the VIC catalogue.

Each week's catalogue has ~150 products with their special price and (usually) their normal price.
This adds them to pricebook.json so the app's "Add to the list" search can show real prices for
hundreds, then thousands, of products. Entries not seen for 26 weeks are dropped.
Standard library only. Usage: python3 tools/pricebook.py specials.json pricebook.json
"""
import json, os, sys
from datetime import date, timedelta
sp_path, out_path = sys.argv[1], sys.argv[2]
feed = json.load(open(sp_path))
book = json.load(open(out_path)).get("items", {}) if os.path.exists(out_path) else {}
added = 0
for cat in feed.get("catalogues", []):
    for it in cat.get("items", []):
        name = (it.get("name") or "").strip()
        if not name or len(name) > 90 or not it.get("price"): continue   # skip combo deals listing many products
        k = name.lower()
        e = book.get(k) or {"n": name}
        if k not in book: added += 1
        if it.get("was"): e["reg"] = float(it["was"])
        elif it.get("low"): e["reg"] = float(it["price"])
        if (cat.get("from") or "") >= (e.get("spFrom") or ""):
            e.update({"sp": float(it["price"]), "spFrom": cat.get("from"), "spTo": cat.get("to"), "unit": it.get("unit") or "each", "cat": (it.get("cat") or "").split("/")[-1]})
        e["seen"] = max(e.get("seen") or "", cat.get("from") or "")
        book[k] = e
cut = (date.today() - timedelta(weeks=26)).isoformat()
book = {k: v for k, v in book.items() if (v.get("seen") or "") >= cut}
json.dump({"updated": date.today().isoformat(), "items": book}, open(out_path, "w"), separators=(",", ":"), ensure_ascii=False)
print(f"{added} new products; {len(book)} in the price book.")

#!/usr/bin/env python3
"""Learn real Woolworths regular prices from the catalogue.

The catalogue shows the normal price ("was") for most specials, and the "Everyday Low Price" items show
their regular price. specials_map.json (written each week by the AI job) says which app item each catalogue
item is, how many app packs it equals, and whether it's the same product ("same"). Only same products
teach a price: another brand's normal price says nothing about the item you usually buy. This turns those into prices.json: {item name: {p, seen, from}}.
Runs in the daily GitHub Action after update_specials.py. Standard library only.

Usage: python3 tools/derive_prices.py specials.json specials_map.json tools/library.json prices.json
"""
import json, os, sys
sp_path, map_path, lib_path, out_path = sys.argv[1:5]
if not os.path.exists(map_path):
    print("No specials_map.json yet; nothing to learn."); sys.exit(0)
feed = json.load(open(sp_path)); mp = json.load(open(map_path)); lib = json.load(open(lib_path))
mp = mp.get("items", mp)
names = lib.get("keys", {})            # app key -> item name
est = lib.get("estimates", {})         # item name -> built-in estimate, for a sanity check
prices = json.load(open(out_path)) if os.path.exists(out_path) else {}
prices = prices.get("items", prices)
learnt = 0
for cat in feed.get("catalogues", []):
    best = {}
    for it in cat.get("items", []):
        m = mp.get(it["name"])
        if not m or not m.get("key") or m["key"] not in names: continue
        if not m.get("same"): continue     # a different brand's normal price isn't this item's price
        reg = it.get("was") or (it["price"] if it.get("low") else None)
        if not reg: continue
        ratio = float(m.get("ratio") or 1) or 1
        # only the identical pack teaches a price (bigger packs are cheaper per unit); fresh food sold per kg is fine
        if abs(ratio - 1) > 0.05 and "kg" not in (it.get("unit") or ""): continue
        p = round(float(reg) / ratio, 2)
        name = names[m["key"]]
        e = est.get(name)
        if e and not (0.4 * e <= p <= 2.5 * e): continue      # clearly a different pack or product
        if name not in best or p < best[name][0]: best[name] = (p, it["name"])
    for name, (p, src) in best.items():
        old = prices.get(name)
        if not old or (cat.get("from") or "") >= (old.get("seen") or ""):
            prices[name] = {"p": p, "seen": cat.get("from"), "from": src}; learnt += 1
json.dump({"updated": max([c.get("from") or "" for c in feed.get("catalogues", [])] or [""]), "items": prices}, open(out_path, "w"), indent=0, ensure_ascii=False)
print(f"{learnt} prices learnt or refreshed; {len(prices)} known in total.")

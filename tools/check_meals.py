#!/usr/bin/env python3
"""Checks meals.json (the weekly AI meal ideas) before it goes live. Exit code 1 = don't publish.
Usage: python3 tools/check_meals.py meals.json tools/library.json"""
import json, re, sys
meals_path, lib_path = sys.argv[1], sys.argv[2]
d = json.load(open(meals_path)); lib = json.load(open(lib_path))
errs = []
BANNED = r"\b(fish|salmon|tuna|prawn|shrimp|squid|calamari|mussel|oyster|crab|lobster|anchov|seafood|worcestershire|fish sauce|oyster sauce|peanut|almond|cashew|walnut|pecan|hazelnut|pistachio|macadamia|nutella|satay|pesto)"
ms = d.get("meals")
if not isinstance(ms, list) or not (3 <= len(ms) <= 12): errs.append("need 3-12 meals")
names = set()
for m in ms or []:
    n = m.get("n", "")
    if not n or n in names: errs.append(f"missing or duplicate name: {n!r}")
    if n in lib["meals"]: errs.append(f"{n}: already in the library")
    names.add(n)
    if m.get("k") not in ("both", "kid", "adult"): errs.append(f"{n}: k must be both/kid/adult")
    if not isinstance(m.get("st"), list) or not set(m["st"]) <= set(lib["styles"]): errs.append(f"{n}: st must be a list of {lib['styles']}")
    if not isinstance(m.get("m"), int) or not 5 <= m["m"] <= 60: errs.append(f"{n}: m (hands-on minutes) 5-60")
    ing = m.get("ing") or []
    if not 2 <= len(ing) <= 10: errs.append(f"{n}: 2-10 ing lines")
    for line in ing:
        nm = re.sub(r"\s*,\s*\$?[\d.]+\s*$", "", line).strip()
        if nm not in lib["ingredients"] and not re.search(r",\s*\$?[\d.]+\s*$", line):
            errs.append(f"{n}: '{line}' is not a library ingredient, so it needs a price: 'Name, 4.50'")
    r = m.get("recipe") or {}
    if len(r.get("ingredients") or []) < 3 or len(r.get("steps") or []) < 4: errs.append(f"{n}: recipe needs ingredients and 4+ steps")
    if re.search(BANNED, json.dumps(m).lower()): errs.append(f"{n}: mentions seafood or nuts")
for e in errs: print("ERROR:", e)
print("OK" if not errs else f"{len(errs)} problem(s)")
sys.exit(1 if errs else 0)

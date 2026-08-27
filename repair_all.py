"""Repair every drafted layout until it is legal, and print what came out."""
import sys, json
sys.path.insert(0, '.')
from tracksearch import repair, report, legal
from layouts import DRAFTS

out = {}
for key, cp in DRAFTS.items():
    fixed = cp
    for attempt, (iters, drift) in enumerate(((700, 0.020), (900, 0.008), (1200, 0.003))):
        if legal(fixed):
            break
        fixed = repair(fixed, iters=iters, drift=drift, seed=7 + attempt)
    report(key, fixed)
    out[key] = fixed
json.dump(out, open("layouts_fixed.json", "w"), indent=1)
print("\nwrote layouts_fixed.json")

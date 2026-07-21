"""Generate wave-2 configs (run AFTER the wide league completes + the
drills-first CATALOG rule lands): 4x new-baseline, 3x plan cadence 10s,
3x plan cadence 45s. New files only — never touches the frozen w*.json.

Usage: python3 make_wave2.py
"""

import json

base = json.load(open("configs/stage1-w00-base.json"))

lanes = ([("base", 20)] * 4 + [("cad10", 10)] * 3 + [("cad45", 45)] * 3)
for i, (kind, cadence) in enumerate(lanes):
    cfg = json.loads(json.dumps(base))
    a = cfg["agents"][0]
    a["name"] = f"S1 X{i:02d} {kind}"
    a["plan_every_s"] = cadence
    with open(f"configs/stage1-x{i:02d}-{kind}.json", "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"wrote configs/stage1-x{i:02d}-{kind}.json (cadence {cadence}s)")

"""Validate the route-search champion under MATCH conditions: 1x speed,
tag=match (no wedge nudges), full cluster reset, 4 repeat lanes.

Usage: uv run python validate_champion.py [champions-file]
"""

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
RDIR = HERE / "configs" / "route"

champs_file = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "route-champions.jsonl"
rows = [json.loads(l) for l in open(champs_file)]
champ = rows[-1]["champion"]
print(f"validating champion from gen {rows[-1]['gen']} "
      f"(lab best={rows[-1]['best_score']}, med={rows[-1]['champ_median']})")
print(json.dumps(champ, indent=1))

RDIR.mkdir(parents=True, exist_ok=True)
paths = []
for i in range(4):
    cfg = {"agents": [{
        "name": f"Match Val {i}",
        "mode": "skills", "script_only": True,
        "model": "none", "accounts": [],
        "timeout_cap": 150, "default_plan": champ,
    }], "fast": False, "steps": 400,
        "shared_goal": "match-mode champion validation"}
    p = RDIR / f"matchval-{i}.json"
    p.write_text(json.dumps(cfg, indent=1))
    paths.append(str(p.relative_to(HERE)))

label = f"matchval-{time.strftime('%m%d-%H%M')}"
cmd = ["uv", "run", "python", "stage.py", "--minutes", "5", "--speed", "1",
       "--tag", "match", "--label", label]
for p in paths:
    cmd += ["--lane", p]
r = subprocess.run(cmd, cwd=HERE, text=True, capture_output=True, timeout=3600)
print(r.stdout[-2500:])
print("MATCH VALIDATION COMPLETE — label", label)

"""Write the map seed into FLE's map-gen-settings.json — the file that
actually decides the map (it beats --map-gen-seed; the pinned 424242 lives
here). Run BEFORE `fle cluster start`.

Usage:
  python3 set_seed.py random    -> rolls, prints, and records the seed
  python3 set_seed.py 424242    -> pin a specific seed (lab regression map)
"""

import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
P = (HERE / ".venv/lib/python3.12/site-packages/fle/cluster/config/"
     "map-gen-settings.json")

arg = sys.argv[1] if len(sys.argv) > 1 else "random"
seed = random.randrange(1, 2**31) if arg == "random" else int(arg)

d = json.load(open(P))
d["seed"] = seed
json.dump(d, open(P, "w"), indent=2)
with open(HERE / "seed-log.jsonl", "a") as f:
    f.write(json.dumps({"ts": time.time(), "seed": seed}) + "\n")
print(seed)

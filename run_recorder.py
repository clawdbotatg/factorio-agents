"""Match run recorder: poll-diff the world every 2s and log every new
entity placement (who, what, where, game-tick) to a jsonl — every human
match becomes an imitation route for the optimizer, every bot match a
replayable ledger.

Usage: uv run python run_recorder.py [label]   (runs until killed)
Output: recordings/<label>.jsonl
"""

import json
import sys
import time
from pathlib import Path

from factorio_rcon import RCONClient

HERE = Path(__file__).parent
label = sys.argv[1] if len(sys.argv) > 1 else time.strftime("run-%m%d-%H%M")
OUT = HERE / "recordings" / f"{label}.jsonl"
OUT.parent.mkdir(exist_ok=True)

# snapshot: unit_number -> descriptor (unit_number is stable per entity)
SNAP = (
    "/sc local out={} "
    "for _, e in pairs(game.surfaces[1].find_entities_filtered{}) do "
    "if e.unit_number and e.name ~= 'character' and e.force and "
    "(e.force.name == 'player' or e.force.name == 'bot') then "
    "out[tostring(e.unit_number)] = {n=e.name, "
    "x=math.floor(e.position.x*2)/2, y=math.floor(e.position.y*2)/2, "
    "f=e.force.name, "
    "u=(e.last_user and e.last_user.name or nil)} end end "
    "rcon.print(helpers.table_to_json({tick=game.tick, ents=out}))"
)


def main():
    c = RCONClient("127.0.0.1", 27000, "factorio")
    c.connect()
    seen = {}
    n_events = 0
    print(f"recording -> {OUT}", flush=True)
    with open(OUT, "a") as f:
        while True:
            try:
                d = json.loads(c.send_command(SNAP))
                tick = d["tick"]
                ents = d.get("ents") or {}
                for uid, e in ents.items():
                    if uid not in seen:
                        seen[uid] = e
                        f.write(json.dumps({"tick": tick, "event": "built",
                                            **e}) + "\n")
                        n_events += 1
                gone = [u for u in seen if u not in ents]
                for uid in gone:
                    f.write(json.dumps({"tick": tick, "event": "removed",
                                        **seen.pop(uid)}) + "\n")
                    n_events += 1
                f.flush()
            except Exception:
                try:
                    c = RCONClient("127.0.0.1", 27000, "factorio")
                    c.connect()
                except Exception:
                    pass
            time.sleep(2)


if __name__ == "__main__":
    main()
